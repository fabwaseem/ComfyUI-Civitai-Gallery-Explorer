from __future__ import annotations

import asyncio
import io
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from typing import Any

import aiohttp
import numpy as np
import torch
from aiohttp import web
from comfy_api.latest import ComfyExtension
from comfy_api.latest import io as comfy_io
from PIL import Image
from server import PromptServer
from typing_extensions import override

from _safety import (
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    clip_text,
    content_disposition,
    digits_only,
    is_safe_public_url,
    redact_secrets,
    safe_urlopen,
)

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVORITES_FILE = os.path.join(NODE_DIR, "civitai_favorites.json")
_FAV_LOCK = threading.Lock()
_AIO_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=30)
_STREAM_DEADLINE_S = 45.0
_MAX_FAVORITE_BYTES = 2_000_000
_MAX_UPSTREAM_TEXT = 8_000_000
_VIDEO_PROBE_BYTES = 4 * 1024 * 1024


def _read_favorites_unlocked() -> dict[str, Any]:
    if not os.path.exists(FAVORITES_FILE):
        return {}
    try:
        with open(FAVORITES_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError):
        return {}


def _write_favorites_unlocked(data: dict[str, Any]) -> None:
    tmp = FAVORITES_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, FAVORITES_FILE)
    except OSError as exc:
        print(f"CivitaiGalleryExplorer: Error saving favorites: {exc}")
        with suppress(OSError):
            os.remove(tmp)


def load_favorites() -> dict[str, Any]:
    with _FAV_LOCK:
        return _read_favorites_unlocked()


def save_favorites(data: dict[str, Any]) -> None:
    with _FAV_LOCK:
        _write_favorites_unlocked(data)


def update_favorites(mutator: Callable[[dict[str, Any]], tuple[Any, bool]]) -> Any:
    with _FAV_LOCK:
        data = _read_favorites_unlocked()
        result, dirty = mutator(data)
        if dirty:
            _write_favorites_unlocked(data)
        return result


def clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, number))


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def item_is_video(item: dict[str, Any]) -> bool:
    url = str(item.get("url") or "").lower()
    if url.endswith((".mp4", ".webm")):
        return True
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    video = str(meta.get("video") or meta.get("videoUrl") or meta.get("mp4") or meta.get("mp4Url") or "").lower()
    return video.endswith((".mp4", ".webm"))


def item_has_positive_prompt(item: dict[str, Any]) -> bool:
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    return any(str(meta.get(key) or "").strip() for key in ("prompt", "Prompt", "positive", "textPrompt"))


def item_matches_query_local(item: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    query = query.lower().strip()
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    buf = " | ".join(
        str(part or "")
        for part in [
            item.get("id"),
            item.get("url"),
            meta.get("prompt"),
            meta.get("Prompt"),
            meta.get("textPrompt"),
            meta.get("negativePrompt"),
            meta.get("NegativePrompt"),
            user.get("username") or user.get("name") or "",
            meta.get("Model") or meta.get("model") or "",
        ]
    ).lower()
    return query in buf


def _empty_image_tensor() -> torch.Tensor:
    return torch.zeros(1, 1, 1, 3, dtype=torch.float32)


def _download_image_to_tensor(url: str, timeout_s: int = 30) -> torch.Tensor:
    if not is_safe_public_url(url):
        raise ValueError("Blocked non-public image URL")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
    with safe_urlopen(req, timeout=timeout_s) as resp:
        data = resp.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds size limit")
    img = Image.open(io.BytesIO(data))
    if getattr(img, "is_animated", False):
        with suppress(EOFError, ValueError):
            img.seek(0)
    img = img.convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]


def _favorite_item_ok(item: Any) -> str | None:
    if not isinstance(item, dict) or "id" not in item:
        return None
    try:
        encoded = json.dumps(item)
    except (TypeError, ValueError):
        return None
    if len(encoded) > _MAX_FAVORITE_BYTES:
        return None
    return str(item["id"])[:128]


def _clean_tags(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []
    cleaned: list[str] = []
    for tag in tags[:50]:
        if not isinstance(tag, str):
            continue
        text = tag.strip()
        if text:
            cleaned.append(text[:64])
    return cleaned


class CivitaiGalleryExplorerNode(comfy_io.ComfyNode):
    @classmethod
    def define_schema(cls) -> comfy_io.Schema:
        return comfy_io.Schema(
            node_id="CivitaiGalleryExplorerNode",
            display_name="🖼️ Civitai Gallery Explorer",
            category="💡fabwaseem/Civitai",
            inputs=[
                comfy_io.String.Input(
                    "selection_data",
                    default="{}",
                    multiline=False,
                    tooltip="JSON payload set by the UI (selected item + flags).",
                ),
                comfy_io.String.Input(
                    "positive_prompt",
                    default="",
                    multiline=True,
                    tooltip="Positive prompt (editable).",
                ),
                comfy_io.String.Input(
                    "negative_prompt",
                    default="",
                    multiline=True,
                    tooltip="Negative prompt (editable).",
                ),
                comfy_io.String.Input(
                    "lora_data",
                    default="[]",
                    multiline=True,
                    tooltip="LoRA data (editable JSON).",
                ),
            ],
            outputs=[
                comfy_io.String.Output(display_name="positive_prompt"),
                comfy_io.String.Output(display_name="negative_prompt"),
                comfy_io.Image.Output(display_name="image"),
                comfy_io.String.Output(display_name="info"),
                comfy_io.String.Output(display_name="lora_data"),
            ],
        )

    @classmethod
    def is_changed(cls, selection_data: str, positive_prompt: str, negative_prompt: str, lora_data: str, **kwargs):
        return f"{selection_data}_{positive_prompt}_{negative_prompt}_{lora_data}"

    @classmethod
    def execute(cls, selection_data: str, positive_prompt: str, negative_prompt: str, lora_data: str):
        if not isinstance(selection_data, str) or len(selection_data) > 5_000_000:
            node_selection: Any = {}
        else:
            try:
                node_selection = json.loads(selection_data or "{}")
            except (json.JSONDecodeError, TypeError, ValueError):
                node_selection = {}

        item_data = node_selection.get("item", {}) if isinstance(node_selection, dict) else {}
        should_download = bool(node_selection.get("download_image", False)) if isinstance(node_selection, dict) else False

        meta = item_data.get("meta", {}) if isinstance(item_data, dict) else {}
        if not isinstance(meta, dict):
            meta = {}

        pos_prompt = str(
            positive_prompt
            or meta.get("prompt")
            or meta.get("Prompt")
            or meta.get("positive")
            or meta.get("textPrompt")
            or ""
        )
        neg_prompt = str(
            negative_prompt or meta.get("negativePrompt") or meta.get("NegativePrompt") or meta.get("negative") or ""
        )

        image_url = str(item_data.get("url") or "") if isinstance(item_data, dict) else ""

        info_dict = dict(meta)
        for key in ("prompt", "Prompt", "positive", "textPrompt", "negativePrompt", "NegativePrompt", "negative"):
            info_dict.pop(key, None)

        try:
            info_string = json.dumps(info_dict, indent=4, ensure_ascii=False)
        except (TypeError, ValueError):
            info_string = "{}"

        resources = meta.get("resources") or []
        civitai_resources = meta.get("civitaiResources") or []

        lora_list = []
        if isinstance(resources, list):
            for resource in resources:
                if (
                    isinstance(resource, dict)
                    and str(resource.get("type", "")).lower() == "lora"
                    and (resource.get("modelVersionId") or resource.get("hash"))
                ):
                    lora_list.append(resource)

        if isinstance(civitai_resources, list):
            for resource in civitai_resources:
                if (
                    isinstance(resource, dict)
                    and str(resource.get("type", "")).lower() == "lora"
                    and (resource.get("modelVersionId") or resource.get("hash"))
                ):
                    lora_list.append(resource)

        try:
            if isinstance(lora_data, str) and lora_data.strip() and len(lora_data) <= 2_000_000:
                try:
                    json.loads(lora_data)
                    lora_string = lora_data
                except (json.JSONDecodeError, TypeError, ValueError):
                    lora_string = json.dumps(lora_list, indent=4, ensure_ascii=False)
            else:
                lora_string = json.dumps(lora_list, indent=4, ensure_ascii=False)
        except (TypeError, ValueError):
            lora_string = "[]"

        tensor = _empty_image_tensor()

        if should_download and image_url:
            try:
                tensor = _download_image_to_tensor(image_url, timeout_s=30)
            except Exception:
                tensor = _empty_image_tensor()

        return (pos_prompt, neg_prompt, tensor, info_string, lora_string)


prompt_server = PromptServer.instance


@asynccontextmanager
async def _safe_get(session: aiohttp.ClientSession, url: str, **kwargs: Any):
    current = url
    response = None
    for _ in range(5):
        if not await asyncio.to_thread(is_safe_public_url, current):
            raise aiohttp.ClientError("Blocked non-public URL")
        response = await session.get(current, allow_redirects=False, **kwargs)
        if response.status in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            response.release()
            response = None
            if not location:
                raise aiohttp.ClientError("Redirect missing Location")
            current = urllib.parse.urljoin(current, location)
            continue
        break
    else:
        raise aiohttp.ClientError("Too many redirects")
    if response is None:
        raise aiohttp.ClientError("No response")
    try:
        yield response
    finally:
        response.release()


def _json_error(message: str, status: int = 500) -> web.Response:
    return web.json_response({"status": "error", "message": redact_secrets(message)}, status=status)


@prompt_server.routes.get("/civitai_gallery/get_all_favorites_data")
async def get_all_favorites_data(request):
    favorites = await asyncio.to_thread(load_favorites)
    return web.json_response(favorites)


@prompt_server.routes.post("/civitai_gallery/toggle_favorite")
async def toggle_favorite(request):
    try:
        data = await request.json()
        item = data.get("item") if isinstance(data, dict) else None
        item_id = _favorite_item_ok(item)
        if item_id is None or not isinstance(item, dict):
            return _json_error("Invalid item data", 400)

        def mutate(favorites: dict[str, Any]) -> tuple[str, bool]:
            if item_id in favorites:
                del favorites[item_id]
                return "removed", True
            if item.get("meta") is None or not isinstance(item.get("meta"), dict):
                item["meta"] = {}
            if "tags" not in item or not isinstance(item.get("tags"), list):
                item["tags"] = []
            item["meta"].pop("prompt_saved", None)
            favorites[item_id] = item
            return "added", True

        status = await asyncio.to_thread(update_favorites, mutate)
        return web.json_response({"status": status})
    except Exception as exc:
        return _json_error(str(exc), 500)


@prompt_server.routes.post("/civitai_gallery/add_or_update_favorite")
async def add_or_update_favorite(request):
    try:
        data = await request.json()
        item = data.get("item") if isinstance(data, dict) else None
        item_id = _favorite_item_ok(item)
        if item_id is None or not isinstance(item, dict):
            return _json_error("Invalid item data", 400)

        def mutate(favorites: dict[str, Any]) -> tuple[str, bool]:
            favorites[item_id] = item
            return "success", True

        await asyncio.to_thread(update_favorites, mutate)
        return web.json_response({"status": "success"})
    except Exception as exc:
        return _json_error(str(exc), 500)


@prompt_server.routes.get("/civitai_gallery/get_favorites_images")
async def get_favorites_images(request):
    try:
        page = clamp_int(request.query.get("page", "1"), 1, 1_000_000, 1)
        limit = clamp_int(request.query.get("limit", "50"), 1, 200, 50)
        favorites = await asyncio.to_thread(load_favorites)
        items = list(favorites.values())
        total_items = len(items)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_items = items[start_index:end_index]
        return web.json_response(
            {
                "items": paginated_items,
                "metadata": {
                    "totalItems": total_items,
                    "currentPage": page,
                    "pageSize": limit,
                    "totalPages": (total_items + limit - 1) // limit,
                },
            }
        )
    except Exception as exc:
        print(f"CivitaiGalleryExplorer: get_favorites_images error: {redact_secrets(exc)}")
        return web.json_response({"error": redact_secrets(exc)}, status=500)


@prompt_server.routes.post("/civitai_gallery/update_favorite_tags")
async def update_favorite_tags(request):
    try:
        data = await request.json()
        if not isinstance(data, dict):
            return _json_error("Invalid item data", 400)
        item_id = str(data.get("id") or "")[:128]
        tags = _clean_tags(data.get("tags", []))
        if not item_id:
            return _json_error("Missing item id", 400)

        def mutate(favorites: dict[str, Any]) -> tuple[str, bool]:
            if item_id not in favorites or not isinstance(favorites[item_id], dict):
                return "missing", False
            favorites[item_id]["tags"] = tags
            return "success", True

        status = await asyncio.to_thread(update_favorites, mutate)
        if status == "missing":
            return _json_error("Item not in favorites", 404)
        return web.json_response({"status": "success"})
    except Exception as exc:
        return _json_error(str(exc), 500)


@prompt_server.routes.get("/civitai_gallery/get_all_favorite_tags")
async def get_all_favorite_tags(request):
    try:
        favorites = await asyncio.to_thread(load_favorites)
        all_tags: set[str] = set()
        for item in favorites.values():
            if not isinstance(item, dict):
                continue
            tags = item.get("tags")
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag.strip():
                        all_tags.add(tag.strip())
        return web.json_response({"tags": sorted(all_tags, key=lambda tag: tag.lower())})
    except Exception as exc:
        return _json_error(str(exc), 500)


@prompt_server.routes.get("/civitai_gallery/images_stream")
async def get_civitai_images_stream(request):
    try:
        nsfw = clip_text(request.query.get("nsfw", "None"), 32)
        sort = clip_text(request.query.get("sort", "Most Reactions"), 64)
        period = clip_text(request.query.get("period", "Day"), 32)
        username = clip_text(request.query.get("username", ""), 100)
        tags_q = clip_text(request.query.get("tags", ""), 200)
        query_q = clip_text(request.query.get("query", ""), 200)
        base_models_q = clip_text(request.query.get("baseModels", ""), 500)

        include_videos = truthy(request.query.get("include_videos", "false"))
        hide_no_prompt = truthy(request.query.get("hide_no_prompt", "false"))
        videos_only = truthy(request.query.get("videos_only", "false"))

        cursor = request.query.get("cursor", None)
        if cursor is not None:
            cursor = clip_text(cursor, 4000) or None
        min_batch = clamp_int(request.query.get("min_batch", "50"), 1, 500, 50)

        time_budget_ms = clamp_int(request.query.get("time_budget_ms", "0"), 0, 15000, 0)
        deadline = (time.monotonic() + (time_budget_ms / 1000.0)) if time_budget_ms > 0 else None
        overall_deadline = time.monotonic() + _STREAM_DEADLINE_S

        international_version = truthy(request.query.get("international_version", "true"))
        base_domain = "civitai.com" if international_version else "civitai.work"
        base_url = f"https://{base_domain}/api/v1/images"

        model_id = digits_only(request.query.get("modelId", ""))
        model_ver_id = digits_only(request.query.get("modelVersionId", ""))
        upstream_limit = 200 if videos_only else 100

        def build_params(cur: str | None) -> dict[str, str]:
            params: dict[str, str] = {
                "limit": str(upstream_limit),
                "nsfw": nsfw,
                "sort": sort,
                "period": period,
            }
            if username:
                params["username"] = username
            if tags_q:
                params["tags"] = tags_q
            if query_q:
                params["query"] = query_q
            if model_id:
                params["modelId"] = model_id
            if model_ver_id:
                params["modelVersionId"] = model_ver_id
            if base_models_q:
                params["baseModels"] = base_models_q
            if cur:
                params["cursor"] = cur
            return params

        async def fetch_once(session: aiohttp.ClientSession, cur: str | None) -> dict[str, Any]:
            params = build_params(cur)
            async with _safe_get(session, base_url, params=params) as resp:
                text = await resp.text()
                if len(text) > _MAX_UPSTREAM_TEXT:
                    return {
                        "items": [],
                        "metadata": {"error": "upstream response too large"},
                        "next": None,
                    }
                if resp.status != 200:
                    return {
                        "items": [],
                        "metadata": {"error": f"upstream {resp.status}", "detail": text[:400]},
                        "next": None,
                    }
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return {"items": [], "metadata": {"error": "bad json"}, "next": None}

                md = data.get("metadata", {}) if isinstance(data, dict) else {}
                nxt = md.get("nextCursor") or md.get("cursor") or md.get("next") or None
                items = data.get("items", []) if isinstance(data, dict) else []
                if not isinstance(items, list):
                    items = []
                return {"items": items, "metadata": md, "next": nxt}

        started = time.monotonic()
        kept: list[dict[str, Any]] = []
        dropped = 0
        next_cursor = None

        async with aiohttp.ClientSession(timeout=_AIO_TIMEOUT, trust_env=True) as session:
            cur = cursor
            for _ in range(50):
                if time.monotonic() >= overall_deadline:
                    break
                try:
                    res = await fetch_once(session, cur)
                except (aiohttp.ClientError, TimeoutError, OSError) as exc:
                    if kept:
                        break
                    return web.json_response(
                        {"error": f"Upstream request failed: {redact_secrets(exc)}"},
                        status=502,
                    )
                rec_items = res.get("items", [])
                next_cursor = res.get("next", None)
                upstream_error = res.get("metadata", {}).get("error") if isinstance(res.get("metadata"), dict) else None
                if upstream_error and not kept and not rec_items:
                    return web.json_response({"error": str(upstream_error)[:500]}, status=502)

                for item in rec_items:
                    if not isinstance(item, dict):
                        dropped += 1
                        continue

                    if videos_only:
                        if not item_is_video(item):
                            dropped += 1
                            continue
                    elif not include_videos and item_is_video(item):
                        dropped += 1
                        continue

                    if hide_no_prompt and not item_has_positive_prompt(item):
                        dropped += 1
                        continue
                    if query_q and not item_matches_query_local(item, query_q):
                        dropped += 1
                        continue

                    kept.append(item)

                if len(kept) >= min_batch:
                    break

                if deadline is not None and time.monotonic() >= deadline and len(kept) > 0:
                    break

                if not next_cursor:
                    break

                cur = next_cursor

        served = kept[:min_batch] if min_batch > 0 else kept

        meta_out = {
            "aggregated": True,
            "nextCursor": next_cursor,
            "served": len(served),
            "droppedByFilters": dropped,
            "hasMore": bool(next_cursor),
            "nsfw": nsfw,
            "sort": sort,
            "period": period,
            "videosOnly": videos_only,
            "elapsedMs": int((time.monotonic() - started) * 1000),
            "timeBudgetMs": time_budget_ms,
        }
        return web.json_response({"items": served, "metadata": meta_out})
    except Exception as exc:
        return web.json_response({"error": f"Unhandled: {redact_secrets(exc)}"}, status=500)


@prompt_server.routes.post("/civitai_gallery/check_video_workflow")
async def check_video_workflow(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"has_workflow": False, "error": "Invalid JSON"}, status=400)
    video_url = data.get("url") if isinstance(data, dict) else None
    if not video_url:
        return web.json_response({"has_workflow": False, "error": "URL is missing"}, status=400)
    if not await asyncio.to_thread(is_safe_public_url, str(video_url)):
        return web.json_response({"has_workflow": False, "error": "URL is not allowed"}, status=400)
    try:
        headers = {"Range": "bytes=0-4194304"}
        async with (
            aiohttp.ClientSession(timeout=_AIO_TIMEOUT, trust_env=True) as session,
            _safe_get(session, str(video_url), headers=headers) as response,
        ):
            if response.status >= 400 and response.status != 416:
                return web.json_response(
                    {"has_workflow": False, "error": f"Failed to fetch video chunk, status: {response.status}"}
                )
            chunk = await response.content.read(_VIDEO_PROBE_BYTES)
            has_workflow = b'"workflow":' in chunk or b'"prompt":' in chunk
            return web.json_response({"has_workflow": has_workflow})
    except Exception as exc:
        return web.json_response({"has_workflow": False, "error": redact_secrets(exc)}, status=500)


@prompt_server.routes.get("/civitai_gallery/get_video_for_workflow")
async def get_video_for_workflow(request):
    video_url = request.query.get("url")
    if not video_url:
        return web.Response(status=400, text="Missing video URL")
    if not await asyncio.to_thread(is_safe_public_url, video_url):
        return web.Response(status=400, text="Video URL is not allowed")
    try:
        timeout = aiohttp.ClientTimeout(total=120, connect=10, sock_read=30)
        async with (
            aiohttp.ClientSession(timeout=timeout, trust_env=True) as session,
            _safe_get(session, video_url) as response,
        ):
            if response.status != 200:
                return web.Response(
                    status=response.status,
                    text=f"Failed to fetch video from source: {response.reason}",
                )
            if response.content_length and response.content_length > MAX_VIDEO_BYTES:
                return web.Response(status=413, text="Video is too large")
            filename = video_url.split("/")[-1].split("?")[0] or "video_with_workflow.mp4"
            stream = web.StreamResponse(
                status=200,
                headers={
                    "Content-Type": response.content_type or "application/octet-stream",
                    "Content-Disposition": content_disposition(filename),
                },
            )
            await stream.prepare(request)
            total = 0
            async for chunk in response.content.iter_chunked(256 * 1024):
                total += len(chunk)
                if total > MAX_VIDEO_BYTES:
                    break
                await stream.write(chunk)
            await stream.write_eof()
            return stream
    except Exception as exc:
        return web.Response(status=500, text=redact_secrets(exc))


class CivitaiGalleryExplorerExtension(ComfyExtension):
    @override
    async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
        return [CivitaiGalleryExplorerNode]


async def comfy_entrypoint() -> ComfyExtension:
    return CivitaiGalleryExplorerExtension()
