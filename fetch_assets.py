"""Download the model files and database linked by the DeepSAT authors."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import file_digest
from pathlib import Path
from shutil import copyfileobj
import subprocess
from tempfile import TemporaryDirectory
from time import sleep
from urllib.parse import quote

from deepsat_local import DATABASE, MODELS


MODEL_FOLDER = (
    "https://www.dropbox.com/scl/fo/jypic61ymolrggzpjv2n1/AOqDTu7cqAvXkcwviceZtVk"
    "?rlkey=qpsymuh29cng44tpbtft06fhb&dl=1&preview="
)
ASSET_SOURCES = [
    (DATABASE, "https://www.dropbox.com/s/u7k5ztyzigs4sma/DB_010621_SM3.json?dl=1", 79450623,
     "7085287eedba5b80dbfca2af5982a305d491ee5bceb1c9ce6f4b3a38867f4c72"),
    (MODELS[1], MODEL_FOLDER + quote(MODELS[1].name), 697876912,
     "5743aee440067e775a7bc4c85c483843e7f25cec17d5e65ba91fc6640509dfea"),
    (MODELS[2], MODEL_FOLDER + quote(MODELS[2].name), 697879216,
     "6af412bb168d3de41c5214e59059c01aabd428e4af6df2ed980b2d97aec333d1"),
]
CHUNK_SIZE = 8 * 1024 * 1024


def matches_asset(path, size, sha256):
    if not path.is_file() or path.stat().st_size != size:
        return False
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest() == sha256


def fetch_chunk(url, part, start, stop, size):
    expected_range = f"content-range: bytes {start}-{stop}/{size}"
    for attempt in range(3):
        response = subprocess.run(
            ["curl.exe", "--fail", "--silent", "--show-error", "--location", "--max-time", "50",
             "--range", f"{start}-{stop}", "--output", str(part), "--dump-header", "-", url],
            capture_output=True, encoding="latin-1",
        )
        headers = response.stdout.strip().split("\n\n")[-1].lower().splitlines()
        status = headers[0].split(maxsplit=2) if headers else []
        if (response.returncode == 0 and status[1:2] == ["206"] and expected_range in headers
                and part.stat().st_size == stop - start + 1):
            return
        if attempt < 2:
            sleep(2 ** attempt)
    reason = response.stderr.strip() or "unexpected HTTP range response"
    raise OSError(f"Could not download bytes {start}-{stop} ({reason}).")


def fetch_asset(path, url, size, sha256):
    if matches_asset(path, size, sha256):
        print(f"Ready: {path.name}", flush=True)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {path.name} ({size / 1e6:.1f} MB)…", flush=True)
    with TemporaryDirectory(dir=path.parent) as work_dir:
        staging = Path(work_dir)
        offsets = range(0, size, CHUNK_SIZE)
        parts = [staging / f"{offset}.part" for offset in offsets]
        # Keep range requests bounded so a transient failure only retries one chunk.
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = [
                pool.submit(fetch_chunk, url, part, start, min(start + CHUNK_SIZE, size) - 1, size)
                for start, part in zip(offsets, parts)
            ]
            for completed, future in enumerate(as_completed(futures), 1):
                future.result()
                if completed % 8 == 0 or completed == len(parts):
                    print(f"  {completed}/{len(parts)} chunks downloaded", flush=True)

        assembled = staging / path.name
        with assembled.open("wb") as output:
            for part in parts:
                with part.open("rb") as source:
                    copyfileobj(source, output, length=1024 * 1024)
                part.unlink()
        if not matches_asset(assembled, size, sha256):
            raise OSError(f"Downloaded file failed validation: {path.name}")
        assembled.replace(path)


if __name__ == "__main__":
    try:
        for asset in ASSET_SOURCES:
            fetch_asset(*asset)
    except OSError as error:
        raise SystemExit(f"Asset setup failed: {error}") from error
