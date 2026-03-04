import os
import json
import urllib.request
import urllib.error
import ssl
import folder_paths
from nodes import LoraLoader
from comfy_api.latest import ComfyExtension, io as comfy_io
import re
import time
from tqdm import tqdm

class CivitaiLoraLoader(comfy_io.ComfyNode):
    @staticmethod
    def _safe_path_in_dir(base_dir: str, name: str):
        base_abs = os.path.abspath(base_dir)
        safe_name = CivitaiLoraLoader.safe_filename(name or "")
        dest_abs = os.path.abspath(os.path.join(base_abs, safe_name))
        try:
            common = os.path.commonpath([base_abs, dest_abs])
        except Exception:
            return None, safe_name
        if common != base_abs:
            return None, safe_name
        return dest_abs, safe_name
    @staticmethod
    def _parse_remote_total(response):
        content_range = response.headers.get("Content-Range")
        if content_range:
            match = re.search(r"/(\d+)$", content_range.strip())
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    return None

        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                return int(content_length)
            except Exception:
                return None

        return None
    @staticmethod
    def _probe_remote_size(url, headers, ctx):
        probe_headers = dict(headers)
        probe_headers["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=probe_headers)

        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                total = CivitaiLoraLoader._parse_remote_total(response)
                if total and total > 0:
                    return total
        except Exception:
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
                    tooltip="JSON string containing LoRA data"
                ),
                comfy_io.String.Input(
                    "civitai_api_key",
                    default="",
                    multiline=False,
                    tooltip="Optional: Civitai API Key for authenticated downloads"
                ),
                comfy_io.Boolean.Input(
                    "auto_download",
                    default=True,
                    tooltip="Automatically download missing LoRAs from Civitai"
                ),
                comfy_io.Boolean.Input(
                    "force_fetch",
                    default=False,
                    tooltip="Force check/download even if file exists"
                ),
            ],
            outputs=[
                comfy_io.Model.Output("model"),
                comfy_io.Clip.Output("clip"),
            ],
        )

    @staticmethod
    def safe_filename(name):
        # Equivalent to safeFilename in lora.ts
        base = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
        if base.lower().endswith('.safetensors') or base.lower().endswith('.pt'):
            return base
        return f"{base}.safetensors"

    @staticmethod
    def find_in_folder(loras_dir, resource_name):
        if not resource_name or resource_name == "unknown":
            return None

        try:
            entries = os.listdir(loras_dir)
            lower_resource = resource_name.lower()

            # 1. Partial match logic from lora.ts
            for entry in entries:
                full_path = os.path.join(loras_dir, entry)
                if not os.path.isfile(full_path):
                    continue

                entry_lower = entry.lower()
                entry_no_ext = os.path.splitext(entry_lower)[0]

                if lower_resource in entry_lower or entry_no_ext in lower_resource:
                    return entry

            # 2. Exact safe filename match
            exact = CivitaiLoraLoader.safe_filename(resource_name)
            if exact in entries:
                return exact

            return None
        except Exception:
            return None

    @classmethod
    def get_version_info(cls, version_id, file_hash, api_key=None):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        headers = {'User-Agent': 'Mozilla/5.0'}
        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key.strip()}'

        found_version_id = None
        primary_name = None

        # 1. Try by modelVersionId
        if version_id:
            url = f"https://civitai.com/api/v1/model-versions/{version_id}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx) as response:
                    if response.status == 200:
                        data = json.load(response)
                        found_version_id = data.get('id', version_id)
                        files = data.get('files', [])
                        primary = next((f for f in files if f.get('primary')), files[0] if files else None)
                        if primary:
                            primary_name = primary.get('name')
            except Exception:
                pass

        # 2. Try by hash if needed
        if (not found_version_id or not primary_name) and file_hash:
            url = f"https://civitai.com/api/v1/model-versions/by-hash/{file_hash}"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx) as response:
                    if response.status == 200:
                        data = json.load(response)
                        found_version_id = data.get('id', found_version_id)
                        files = data.get('files', [])
                        primary = next((f for f in files if f.get('primary')), files[0] if files else None)
                        if primary:
                            primary_name = primary.get('name')
            except Exception:
                pass

        # 3. If primary_name not found but we have found_version_id, try to get model info to find default file
        if found_version_id and not primary_name:
             url = f"https://civitai.com/api/v1/model-versions/{found_version_id}"
             try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=ctx) as response:
                    if response.status == 200:
                        data = json.load(response)
                        files = data.get('files', [])
                        # Fallback to first file if no primary
                        if files and len(files) > 0:
                            primary_name = files[0].get('name')
             except Exception:
                 pass

        if found_version_id and primary_name:
            return found_version_id, primary_name

        return None, None

    @classmethod
    def execute(cls, model, clip, lora_data, civitai_api_key, auto_download, force_fetch):
        # Sanitize API Key
        valid_api_key = None
        if civitai_api_key and isinstance(civitai_api_key, str) and len(civitai_api_key.strip()) > 5:
            valid_api_key = civitai_api_key.strip()

        try:
            lora_list = json.loads(lora_data)
        except Exception:
            print(f"CivitaiLoraLoader: Invalid JSON in lora_data")
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
            except:
                weight = 1.0

            model_version_id = lora.get("modelVersionId")
            file_hash = lora.get("hash")

            # Step 1: Try to find in folder by name (if name is known)
            filename = None
            if name and name != "unknown":
                filename = cls.find_in_folder(loras_dir, name)
                if filename:
                    # Found locally, nothing to log unless verbose
                    pass

            # Step 2: If not found, fetch version info to get real name
            if not filename:
                found_id, primary_name = cls.get_version_info(model_version_id, file_hash, valid_api_key)

                if found_id and primary_name:
                    # Update name/ID with what we found
                    model_version_id = found_id
                    # Check if primary_name exists on disk (sanitize and confine to loras_dir)
                    full_dest_path, safe_primary = cls._safe_path_in_dir(loras_dir, primary_name)
                    if not full_dest_path:
                        print("CivitaiLoraLoader: Unsafe destination path detected; aborting.")
                        primary_name = None
                    else:
                        primary_name = safe_primary

                    if primary_name:
                        if os.path.exists(full_dest_path):
                            filename = primary_name
                            print(f"CivitaiLoraLoader: Found LoRA '{primary_name}'")
                        elif auto_download:
                            # Download to sanitized primary_name
                            if cls.download_lora(model_version_id, primary_name, loras_dir, valid_api_key):
                                filename = primary_name
                            else:
                                print(f"CivitaiLoraLoader: Download failed for '{primary_name}'")
                        else:
                            print(f"CivitaiLoraLoader: Auto-download disabled. Missing '{primary_name}'.")
                else:
                    print(f"CivitaiLoraLoader: Could not resolve info for '{name}'")

            # Step 3: Load if we have a filename
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
        url = f"https://civitai.com/api/download/models/{version_id}"
        if api_key and api_key.strip():
            url += f"?token={api_key.strip()}"

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        headers = {'User-Agent': 'Mozilla/5.0'}
        output_path, safe_name = CivitaiLoraLoader._safe_path_in_dir(loras_dir, filename)
        if not output_path:
            print("CivitaiLoraLoader: Unsafe destination path detected; aborting download.")
            return False

        part_path = f"{output_path}.part"
        remote_size = CivitaiLoraLoader._probe_remote_size(url, headers, ctx)

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

                req = urllib.request.Request(url, headers=req_headers)
                with urllib.request.urlopen(req, context=ctx) as response:
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
                        except Exception:
                            expected_total = None

                    mode = "ab" if resume_from > 0 and response.status == 206 else "wb"
                    initial = resume_from if mode == "ab" else 0
                    with open(part_path, mode) as f:
                        with tqdm(total=expected_total, initial=initial, unit='iB', unit_scale=True, desc=f"Downloading {safe_name}", leave=True) as pbar:
                            while True:
                                chunk = response.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                pbar.update(len(chunk))

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
                if e.code == 404:
                    print("CivitaiLoraLoader: LoRA not found (404).")
                    return False
                if e.code == 401:
                    print("CivitaiLoraLoader: Unauthorized (401). Check your API Key.")
                    return False
                print(f"CivitaiLoraLoader: HTTP Error {e.code}: {e.reason}")
            except Exception as e:
                print(f"CivitaiLoraLoader: Download attempt {attempt}/{max_retries} failed: {e}")

            if attempt < max_retries:
                time.sleep(min(2 ** (attempt - 1), 8))

        print(f"CivitaiLoraLoader: Failed to download {safe_name} after {max_retries} attempts.")
        return False

class CivitaiLoraLoaderExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
        return [CivitaiLoraLoader]

async def comfy_entrypoint() -> ComfyExtension:
    return CivitaiLoraLoaderExtension()
