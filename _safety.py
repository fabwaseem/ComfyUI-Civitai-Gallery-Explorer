"""Shared guards for outbound requests and on-disk paths."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

MAX_IMAGE_BYTES = 128 * 1024 * 1024
MAX_VIDEO_BYTES = 512 * 1024 * 1024
MAX_LORA_BYTES = 10 * 1024 * 1024 * 1024
API_TIMEOUT_S = 30
DOWNLOAD_TIMEOUT_S = 60

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata.internal",
    }
)
_TOKEN_RE = re.compile(r"(token=)[^&\s\"']+", re.IGNORECASE)
_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


def redact_secrets(text: object) -> str:
    return _TOKEN_RE.sub(r"\1***", str(text))


def clip_text(value: object, limit: int) -> str:
    text = str(value or "")
    text = "".join(ch for ch in text if ch >= " " or ch == "\t")
    if limit > 0:
        text = text[:limit]
    return text.strip()


def digits_only(value: object, limit: int = 20) -> str | None:
    text = str(value or "").strip()
    if text.isdigit() and 0 < len(text) <= limit:
        return text
    return None


def clean_model_hash(value: object) -> str | None:
    text = str(value or "").strip()
    if re.fullmatch(r"[A-Fa-f0-9]{8,128}", text):
        return text
    return None


def safe_filename(name: str) -> str:
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name or ""))
    base = base.strip().rstrip(". ")
    if not base or base in {".", ".."}:
        base = "lora"
    stem = base.split(".", 1)[0].upper()
    if stem in _RESERVED_NAMES:
        base = f"_{base}"
    if len(base) > 180:
        base = base[:180].rstrip(". ")
    lower = base.lower()
    if lower.endswith((".safetensors", ".pt")):
        return base
    return f"{base}.safetensors"


def safe_join(base_dir: str, filename: str) -> str | None:
    if not base_dir or not filename or os.path.basename(filename) != filename:
        return None
    base_real = os.path.realpath(base_dir)
    if not os.path.isdir(base_real):
        return None
    dest = os.path.realpath(os.path.join(base_real, filename))
    try:
        if os.path.commonpath([base_real, dest]) != base_real:
            return None
    except ValueError:
        return None
    return dest


def content_disposition(filename: str) -> str:
    base = os.path.basename(str(filename or "").split("?", 1)[0])
    base = re.sub(r'[\r\n"]', "", base).strip() or "video.mp4"
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:180].strip("._") or "video"
    if "." not in ascii_name:
        ascii_name = f"{ascii_name}.mp4"
    return f'attachment; filename="{ascii_name}"'


def is_safe_public_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    raw = url.strip()
    if not raw or len(raw) > 4096 or any(ch in raw for ch in "\r\n\x00"):
        return False
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False
    host = parsed.hostname
    if not host:
        return False
    host_l = host.lower().rstrip(".")
    if host_l in _BLOCKED_HOSTS or host_l.endswith((".localhost", ".local")):
        return False
    try:
        literal = ipaddress.ip_address(host_l)
    except ValueError:
        literal = None
    if literal is not None:
        return bool(literal.is_global)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host_l, port, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            resolved = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not resolved.is_global:
            return False
    return True


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: A003, PLR0913
        joined = urllib.parse.urljoin(req.full_url, newurl)
        if not is_safe_public_url(joined):
            raise urllib.error.URLError("Blocked redirect to a non-public URL")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(req: urllib.request.Request, timeout: float):
    if not is_safe_public_url(req.full_url):
        raise urllib.error.URLError("Blocked non-public URL")
    opener = urllib.request.build_opener(_SafeRedirectHandler)
    return opener.open(req, timeout=timeout)  # noqa: S310
