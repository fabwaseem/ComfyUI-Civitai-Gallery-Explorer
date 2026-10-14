from __future__ import annotations

import contextlib
import json
import os
import re
import time
import urllib.error
import urllib.request

import folder_paths
from comfy_api.latest import ComfyExtension
from comfy_api.latest import io as comfy_io
from nodes import LoraLoader
from tqdm import tqdm

from _safety import (
    API_TIMEOUT_S,
    DOWNLOAD_TIMEOUT_S,
    MAX_LORA_BYTES,
    clean_model_hash,
    digits_only,
    redact_secrets,
    safe_join,
    safe_urlopen,
)
from _safety import (
    safe_filename as _safe_filename,
)


class CivitaiLoraLoader(comfy_io.ComfyNode):
    @staticmethod
    def _safe_path_in_dir(base_dir: str, name: str):
        safe_name = CivitaiLoraLoader.safe_filename(name or "")
        return safe_join(base_dir, safe_name), safe_name

    @staticmethod
    def _parse_remote_total(response):
        content_range = response.headers.get("Content-Range")
        if content_range:
            match = re.search(r"/(\d+)$", content_range.strip())
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None

        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                return None

        return None

    @staticmethod
    def _probe_remote_size(url, headers):
        probe_headers = dict(headers)
        probe_headers["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=probe_headers)  # noqa: S310

        try:
            with safe_urlopen(req, timeout=API_TIMEOUT_S) as response:
                total = CivitaiLoraLoader._parse_remote_total(response)
                if total and total > 0:
                    return total
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None

        return None

    @classmethod
    def define_schema(cls) -> comfy_io.Schema:
        return comfy_io.Schema(
            node_id="CivitaiLoraLoader",
            display_name="☁️ Civitai LoRA Loader",
            category="💡fabwaseem/Civitai",
            inputs=[
                comfy_io.Model.Input("model", tooltip="Model to apply LoRAs to"),
                comfy_io.Clip.Input("clip", tooltip="CLIP to apply LoRAs to"),
                comfy_io.String.Input(
                    "lora_data",
                    default="[]",
                    multiline=True,
                    tooltip="JSON string containing LoRA data",
                ),
                comfy_io.String.Input(
                    "civitai_api_key",
                    default="",
                    multiline=False,
                    tooltip="Optional: Civitai API Key for authenticated downloads",
                ),
                comfy_io.Boolean.Input(
                    "auto_download",
                    default=True,
                    tooltip="Automatically download missing LoRAs from Civitai",
                ),
                comfy_io.Boolean.Input(
                    "force_fetch",
                    default=False,
                    tooltip="Force check/download even if file exists",
                ),
            ],
            outputs=[
                comfy_io.Model.Output("model"),
                comfy_io.Clip.Output("clip"),
            ],
        )

    @staticmethod
    def safe_filename(name):
        return _safe_filename(name)

    @staticmethod
    def find_in_folder(loras_dir, resource_name):
        if not resource_name or resource_name == "unknown":
            return None

        try:
            entries = os.listdir(loras_dir)
            lower_resource = resource_name.lower()

            for entry in entries:
                if os.path.basename(entry) != entry:
                    continue
                full_path = os.path.join(loras_dir, entry)
                if not os.path.isfile(full_path):
                    continue

                entry_lower = entry.lower()
                entry_no_ext = os.path.splitext(entry_lower)[0]

                if lower_resource in entry_lower or entry_no_ext in lower_resource:
                    return entry

            exact = CivitaiLoraLoader.safe_filename(resource_name)
            if exact in entries:
                return exact

            return None
        except OSError:
            return None

    @classmethod
    def _read_version(cls, url, headers):
        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        with safe_urlopen(req, timeout=API_TIMEOUT_S) as response:
            if response.status != 200:
                return None
            data = json.load(response)
        return data if isinstance(data, dict) else None

    @classmethod
    def _primary_name_from_payload(cls, data):
        files = data.get("files", []) if isinstance(data, dict) else []
        if not isinstance(files, list) or not files:
            return None
        primary = next((f for f in files if isinstance(f, dict) and f.get("primary")), None)
        if primary is None:
            primary = files[0] if isinstance(files[0], dict) else None
        if not primary:
            return None
        name = primary.get("name")
        return str(name) if name else None

    @classmethod
    def get_version_info(cls, version_id, file_hash, api_key=None):
        headers = {"User-Agent": "Mozilla/5.0"}
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"

        version_id = digits_only(version_id)
        file_hash = clean_model_hash(file_hash)
        found_version_id = None
        primary_name = None

        if version_id:
            url = f"https://civitai.com/api/v1/model-versions/{version_id}"
            try:
                data = cls._read_version(url, headers)
                if data:
                    found_version_id = digits_only(data.get("id", version_id)) or version_id
                    primary_name = cls._primary_name_from_payload(data)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
                pass

        if (not found_version_id or not primary_name) and file_hash:
            url = f"https://civitai.com/api/v1/model-versions/by-hash/{file_hash}"
            try:
                data = cls._read_version(url, headers)
                if data:
                    found_version_id = digits_only(data.get("id", found_version_id)) or found_version_id
                    primary_name = cls._primary_name_from_payload(data) or primary_name
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
                pass

        if found_version_id and not primary_name:
            url = f"https://civitai.com/api/v1/model-versions/{found_version_id}"
            try:
                data = cls._read_version(url, headers)
                if data:
                    primary_name = cls._primary_name_from_payload(data)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
                pass

        if found_version_id and primary_name:
            return found_version_id, primary_name

        return None, None

    @classmethod
    def _resolve_and_maybe_download(
        cls, name, model_version_id, file_hash, api_key, auto_download, force_fetch, loras_dir
    ):
        found_id, primary_name = cls.get_version_info(model_version_id, file_hash, api_key)
        if not (found_id and primary_name):
            print(f"CivitaiLoraLoader: Could not resolve info for '{name}'")
            return None

        full_dest_path, safe_primary = cls._safe_path_in_dir(loras_dir, primary_name)
        if not full_dest_path:
            print("CivitaiLoraLoader: Unsafe destination path detected; aborting.")
            return None

        exists = os.path.exists(full_dest_path)
        if exists and not (force_fetch and auto_download):
            print(f"CivitaiLoraLoader: Found LoRA '{safe_primary}'")
            return safe_primary

        if not exists and not auto_download:
            print(f"CivitaiLoraLoader: Auto-download disabled. Missing '{safe_primary}'.")
            return None

        if cls.download_lora(found_id, safe_primary, loras_dir, api_key):
            return safe_primary

        print(f"CivitaiLoraLoader: Download failed for '{safe_primary}'")
        if os.path.exists(full_dest_path):
            return safe_primary
        return None

    @classmethod
    def execute(cls, model, clip, lora_data, civitai_api_key, auto_download, force_fetch):
        valid_api_key = None
        if civitai_api_key and isinstance(civitai_api_key, str) and len(civitai_api_key.strip()) > 5:
            valid_api_key = civitai_api_key.strip()

        if not isinstance(lora_data, str) or len(lora_data) > 2_000_000:
            print("CivitaiLoraLoader: Invalid JSON in lora_data")
            return (model, clip)

        try:
            lora_list = json.loads(lora_data)
        except (json.JSONDecodeError, TypeError, ValueError):
            print("CivitaiLoraLoader: Invalid JSON in lora_data")
            return (model, clip)

        if not isinstance(lora_list, list):
            return (model, clip)

        loras_dirs = folder_paths.get_folder_paths("loras")
        if not loras_dirs:
            print("CivitaiLoraLoader: No LoRA directory found!")
            return (model, clip)

        loras_dir = loras_dirs[0]

        for lora in lora_list:
            if not isinstance(lora, dict):
                continue

            name = lora.get("name", "unknown")
            try:
                weight = float(lora.get("strength", lora.get("weight", 1.0)))
            except (TypeError, ValueError):
                weight = 1.0

            model_version_id = lora.get("modelVersionId")
            file_hash = lora.get("hash")

            local_filename = None
            if name and name != "unknown":
                local_filename = cls.find_in_folder(loras_dir, name)

            filename = None
            if local_filename and not force_fetch:
                filename = local_filename
            else:
                filename = cls._resolve_and_maybe_download(
                    name,
                    model_version_id,
                    file_hash,
                    valid_api_key,
                    auto_download,
                    force_fetch,
                    loras_dir,
                )
                if not filename and local_filename:
                    filename = local_filename

            if filename:
                print(f"CivitaiLoraLoader: Loading LoRA '{filename}' (strength={weight})")
                try:
                    model, clip = LoraLoader().load_lora(model, clip, filename, weight, weight)
                except Exception as e:
                    print(f"CivitaiLoraLoader: Error loading LoRA '{filename}': {e}")
            else:
                print(f"CivitaiLoraLoader: Skipping LoRA '{name}' (not found)")

        return (model, clip)

    @staticmethod
    def download_lora(version_id, filename, loras_dir, api_key=None):
        version_id = digits_only(version_id)
        if not version_id:
            print("CivitaiLoraLoader: Invalid model version id; aborting download.")
            return False

        url = f"https://civitai.com/api/download/models/{version_id}"
        if api_key and str(api_key).strip():
            url += f"?token={str(api_key).strip()}"

        headers = {"User-Agent": "Mozilla/5.0"}
        output_path, safe_name = CivitaiLoraLoader._safe_path_in_dir(loras_dir, filename)
        if not output_path:
            print("CivitaiLoraLoader: Unsafe destination path detected; aborting download.")
            return False

        part_path = f"{output_path}.part"
        try:
            remote_size = CivitaiLoraLoader._probe_remote_size(url, headers)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            remote_size = None

        if remote_size and remote_size > MAX_LORA_BYTES:
            print(f"CivitaiLoraLoader: Remote file is too large to download ({remote_size} bytes).")
            return False

        if os.path.exists(output_path):
            final_size = os.path.getsize(output_path)
            if remote_size and final_size == remote_size:
                return True
            if not remote_size and final_size > 0:
                return True
            os.replace(output_path, part_path)

        max_retries = 5
        chunk_size = 1024 * 1024

        for attempt in range(1, max_retries + 1):
            try:
                resume_from = os.path.getsize(part_path) if os.path.exists(part_path) else 0
                req_headers = dict(headers)
                if resume_from > 0:
                    req_headers["Range"] = f"bytes={resume_from}-"

                req = urllib.request.Request(url, headers=req_headers)  # noqa: S310
                with safe_urlopen(req, timeout=DOWNLOAD_TIMEOUT_S) as response:
                    if response.status not in (200, 206):
                        raise RuntimeError(f"Download failed with status {response.status}")

                    if resume_from > 0 and response.status == 200 and os.path.exists(part_path):
                        os.remove(part_path)
                        resume_from = 0

                    content_length = response.headers.get("Content-Length")
                    expected_total = CivitaiLoraLoader._parse_remote_total(response)
                    if response.status == 206 and content_length and expected_total is None:
                        try:
                            expected_total = resume_from + int(content_length)
                        except ValueError:
                            expected_total = None

                    if expected_total and expected_total > MAX_LORA_BYTES:
                        raise RuntimeError("Remote file exceeds the download size limit")

                    mode = "ab" if resume_from > 0 and response.status == 206 else "wb"
                    initial = resume_from if mode == "ab" else 0
                    with (
                        open(part_path, mode) as f,
                        tqdm(
                            total=expected_total,
                            initial=initial,
                            unit="iB",
                            unit_scale=True,
                            desc=f"Downloading {safe_name}",
                            leave=True,
                        ) as pbar,
                    ):
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            pbar.update(len(chunk))
                            if pbar.n > MAX_LORA_BYTES:
                                raise RuntimeError("Download exceeded the size limit")

                current_size = os.path.getsize(part_path)
                verified_total = remote_size or expected_total
                if verified_total and current_size < verified_total:
                    raise RuntimeError(f"Incomplete download: {current_size}/{verified_total} bytes")

                os.replace(part_path, output_path)
                final_size = os.path.getsize(output_path)
                if verified_total and final_size < verified_total:
                    raise RuntimeError(f"Incomplete final file: {final_size}/{verified_total} bytes")

                print(f"CivitaiLoraLoader: Download complete: {safe_name}")
                return True
            except urllib.error.HTTPError as e:
                if e.code == 416 and os.path.exists(part_path):
                    with contextlib.suppress(OSError):
                        os.remove(part_path)
                    print("CivitaiLoraLoader: Resume range was rejected; restarting download.")
                elif e.code == 404:
                    print("CivitaiLoraLoader: LoRA not found (404).")
                    return False
                elif e.code == 401:
                    print("CivitaiLoraLoader: Unauthorized (401). Check your API Key.")
                    return False
                else:
                    print(f"CivitaiLoraLoader: HTTP Error {e.code}: {e.reason}")
            except Exception as e:
                print(
                    f"CivitaiLoraLoader: Download attempt {attempt}/{max_retries} failed: "
                    f"{redact_secrets(e)}"
                )

            if attempt < max_retries:
                time.sleep(min(2 ** (attempt - 1), 8))

        print(f"CivitaiLoraLoader: Failed to download {safe_name} after {max_retries} attempts.")
        return False


class CivitaiLoraLoaderExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
        return [CivitaiLoraLoader]


async def comfy_entrypoint() -> ComfyExtension:
    return CivitaiLoraLoaderExtension()
