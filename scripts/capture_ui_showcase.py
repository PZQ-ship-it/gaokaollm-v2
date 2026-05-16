"""Capture the thesis UI showcase pages as deterministic PNG figures."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path(
    os.environ.get(
        "THESIS_FIGURE_DIR",
        r"D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures",
    )
)

VIEWS = {
    "elicitation": "fig_3_5_elicitation_console.png",
    "report": "fig_3_6_final_decision_report.png",
    "admin": "fig_3_7_admin_trace_dashboard.png",
}


def _find_browser() -> Path:
    candidates = [
        shutil.which("msedge"),
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        shutil.which("chrome"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("Chrome or Edge is required for headless screenshots.")


def _is_ready(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return 200 <= response.status < 300
    except (OSError, URLError):
        return False


def _wait_until_ready(url: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _is_ready(url):
            return
        time.sleep(0.3)
    raise TimeoutError(f"Timed out waiting for {url}")


def _start_server(host: str, port: int) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--loop",
            "asyncio",
            "--log-level",
            "warning",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _capture(browser: Path, url: str, target: Path, width: int, height: int) -> None:
    before_mtime = target.stat().st_mtime if target.exists() else None
    with tempfile.TemporaryDirectory() as profile_dir:
        subprocess.run(
            [
                str(browser),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--force-device-scale-factor=1",
                f"--user-data-dir={profile_dir}",
                f"--window-size={width},{height}",
                f"--screenshot={target.resolve()}",
                url,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if not target.exists():
        raise RuntimeError(f"Screenshot was not created: {target}")
    after_mtime = target.stat().st_mtime
    if before_mtime is not None and after_mtime <= before_mtime:
        raise RuntimeError(f"Screenshot was not updated: {target}")


def capture_all(
    *,
    host: str,
    port: int,
    output_dir: Path,
    width: int,
    height: int,
) -> list[Path]:
    browser = _find_browser()
    base_url = f"http://{host}:{port}"
    health_url = f"{base_url}/health"
    server = None
    if not _is_ready(health_url):
        server = _start_server(host, port)
        _wait_until_ready(health_url, timeout_s=20)

    output_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    try:
        for view, filename in VIEWS.items():
            target = output_dir / filename
            url = f"{base_url}/ui-showcase?view={view}"
            _capture(browser, url, target, width, height)
            rendered.append(target)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=8)
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    rendered = capture_all(
        host=args.host,
        port=args.port,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
    )
    for path in rendered:
        print(path)


if __name__ == "__main__":
    main()
