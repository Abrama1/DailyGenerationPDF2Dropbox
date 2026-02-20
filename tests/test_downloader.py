from __future__ import annotations

from pathlib import Path
import tempfile

import httpx
import pytest

from app.worker.downloader import DownloadError, download_pdf


PDF_BYTES = b"%PDF-1.7\n%Fake\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
NOT_PDF_BYTES = b"hello, not a pdf"


def test_download_pdf_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=PDF_BYTES,
        )

    transport = httpx.MockTransport(handler)

    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.pdf"
        path = download_pdf("https://example.com/report.pdf", out)
        assert path.exists()
        assert path.read_bytes().startswith(b"%PDF")


def test_download_pdf_non_200(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    transport = httpx.MockTransport(handler)
    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.pdf"
        with pytest.raises(DownloadError):
            download_pdf("https://example.com/report.pdf", out)


def test_download_pdf_rejects_non_pdf(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=NOT_PDF_BYTES,
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "report.pdf"
        with pytest.raises(DownloadError):
            download_pdf("https://example.com/report.pdf", out)
