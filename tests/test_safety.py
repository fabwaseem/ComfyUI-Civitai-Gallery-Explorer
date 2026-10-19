import os
import socket
import sys

import conftest

_safety = sys.modules[f"{conftest.NODE_PACKAGE.__name__}._safety"]
clean_model_hash = _safety.clean_model_hash
content_disposition = _safety.content_disposition
digits_only = _safety.digits_only
is_safe_public_url = _safety.is_safe_public_url
redact_secrets = _safety.redact_secrets
safe_filename = _safety.safe_filename
safe_join = _safety.safe_join


def test_blocks_local_and_non_http_urls():
    assert not is_safe_public_url("http://127.0.0.1/secret")
    assert not is_safe_public_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe_public_url("http://10.1.2.3/lora")
    assert not is_safe_public_url("http://[::1]/secret")
    assert not is_safe_public_url("file:///etc/passwd")
    assert not is_safe_public_url("http://localhost/x")
    assert not is_safe_public_url("https://user:pass@civitai.com/api")
    assert not is_safe_public_url("https://metadata.google.internal/")
    assert not is_safe_public_url(None)


def test_allows_public_hostname(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert is_safe_public_url("https://image.civitai.com/x/original=true/a.jpeg")


def test_rejects_hostname_that_resolves_private(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.9", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    assert not is_safe_public_url("https://image.civitai.com/a.jpeg")


def test_safe_join_stays_inside_directory(tmp_path):
    dest = safe_join(str(tmp_path), "model.safetensors")
    assert dest == os.path.realpath(tmp_path / "model.safetensors")
    assert safe_join(str(tmp_path), "../etc/passwd") is None
    assert safe_join(str(tmp_path), "nested/file.safetensors") is None


def test_safe_filename_keeps_normal_names_and_blocks_traversal():
    assert safe_filename("My Lora.safetensors") == "My Lora.safetensors"
    assert safe_filename("My Lora") == "My Lora.safetensors"
    assert "/" not in safe_filename("../../etc/passwd")
    assert "\x00" not in safe_filename("bad\x00name")


def test_redacts_download_token():
    redacted = redact_secrets("https://civitai.com/api/download/models/1?token=super-secret")
    assert "super-secret" not in redacted
    assert "token=***" in redacted


def test_content_disposition_strips_header_injection():
    header = content_disposition('clip.mp4"\r\nX-Injected: yes')
    assert "\r" not in header
    assert "\n" not in header
    assert header.startswith('attachment; filename="')


def test_id_and_hash_validation():
    assert digits_only(2487375) == "2487375"
    assert digits_only("../1") is None
    assert clean_model_hash("ABCdef0123") == "ABCdef0123"
    assert clean_model_hash("not a hash") is None
