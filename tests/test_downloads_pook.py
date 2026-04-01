"""Tests for download tools (httpx-based — use unittest.mock instead of pook)."""

from unittest.mock import MagicMock, patch

from gitlab_mcp.tools.uploads import download_attachment
from gitlab_mcp.tools.releases import download_release_asset

PROJECT_ID = "278964"


def _make_httpx_client_mock(content: bytes) -> MagicMock:
    """Build a mock httpx.Client context manager returning the given response content."""
    response = MagicMock()
    response.content = content
    response.raise_for_status = MagicMock()

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get = MagicMock(return_value=response)
    return client


def test_download_attachment(gitlab_token, tmp_path):
    """Smoke test: download_attachment saves a file and returns DownloadResult."""
    output_file = str(tmp_path / "attachment.txt")
    mock_client = _make_httpx_client_mock(b"attachment content")

    with patch("gitlab_mcp.tools.uploads.httpx.Client", return_value=mock_client):
        result = download_attachment(PROJECT_ID, "secret123", "attachment.txt", output_file)

    assert result.status == "downloaded"
    assert result.filename == "attachment.txt"
    assert result.size_bytes == len(b"attachment content")


def test_download_release_asset(gitlab_token, tmp_path):
    """Smoke test: download_release_asset saves a file and returns ReleaseAssetDownload."""
    output_file = str(tmp_path / "asset.zip")
    mock_client = _make_httpx_client_mock(b"release asset data")

    with patch("gitlab_mcp.tools.releases.httpx.Client", return_value=mock_client):
        result = download_release_asset(
            PROJECT_ID, "v1.0.0", "https://example.com/asset.zip", output_file
        )

    assert result.status == "downloaded"
    assert result.filename == "asset.zip"
    assert result.size_bytes == len(b"release asset data")
