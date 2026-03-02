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
                    # Check if primary_name exists on disk
                    full_dest_path = os.path.join(loras_dir, primary_name)

                    if os.path.exists(full_dest_path):
                        filename = primary_name
                        print(f"CivitaiLoraLoader: Found LoRA '{primary_name}'")
                    elif auto_download:
                        # Download to primary_name
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

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                if response.status != 200:
                    print(f"CivitaiLoraLoader: Download failed with status {response.status}")
                    return False

                # Use provided filename
                output_path = os.path.join(loras_dir, filename)

                if os.path.exists(output_path):
                    return True

                total_size = int(response.headers.get('Content-Length', 0))

                chunk_size = 8192
                with open(output_path, "wb") as f:
                    with tqdm(total=total_size, unit='iB', unit_scale=True, desc=f"Downloading {filename}", leave=True) as pbar:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            pbar.update(len(chunk))

                print(f"CivitaiLoraLoader: Download complete: {filename}")
                return True

        except urllib.error.HTTPError as e:
             if e.code == 404:
                 print(f"CivitaiLoraLoader: LoRA not found (404).")
             elif e.code == 401:
                 print(f"CivitaiLoraLoader: Unauthorized (401). Check your API Key.")
             else:
                 print(f"CivitaiLoraLoader: HTTP Error {e.code}: {e.reason}")
             return False
        except Exception as e:
             print(f"CivitaiLoraLoader: Error downloading: {e}")
             return False

class CivitaiLoraLoaderExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[comfy_io.ComfyNode]]:
        return [CivitaiLoraLoader]

async def comfy_entrypoint() -> ComfyExtension:
    return CivitaiLoraLoaderExtension()
