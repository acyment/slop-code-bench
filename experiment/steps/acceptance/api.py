"""API acceptance helpers for SCBench visible scenarios."""

from __future__ import annotations

import contextlib
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from experiment.steps.acceptance.results import HarnessError
from experiment.steps.acceptance.results import ProductError


def find_free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ApiServer:
    def __init__(
        self,
        *,
        args: list[str],
        cwd: Path,
        base_url: str,
        stdout_path: Path,
        stderr_path: Path,
        process: subprocess.Popen[str],
    ) -> None:
        self.args = args
        self.cwd = cwd
        self.base_url = base_url
        self.stdout_path = stdout_path
        self.stderr_path = stderr_path
        self.process = process

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def request(
        self,
        method: str,
        path: str,
        *,
        timeout_s: float = 5.0,
        follow_redirects: bool = False,
        **kwargs: object,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        return httpx.request(
            method,
            url,
            timeout=timeout_s,
            follow_redirects=follow_redirects,
            **kwargs,
        )


@contextlib.contextmanager
def start_python_server(
    *,
    script: Path,
    cwd: Path,
    artifact_dir: Path,
    name: str,
    extra_args: list[str] | None = None,
    health_path: str = "/health",
    startup_timeout_s: float = 8.0,
) -> Iterator[ApiServer]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = artifact_dir / f"{name}.server.stdout.txt"
    stderr_path = artifact_dir / f"{name}.server.stderr.txt"
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    port = find_free_port()
    args = [
        sys.executable,
        str(script),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if extra_args:
        args.extend(extra_args)
    process = subprocess.Popen(  # noqa: S603
        args,
        cwd=cwd,
        text=True,
        stdout=stdout_handle,
        stderr=stderr_handle,
    )
    server = ApiServer(
        args=args,
        cwd=cwd,
        base_url=f"http://127.0.0.1:{port}",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        process=process,
    )
    try:
        wait_for_http_ok(server, health_path, timeout_s=startup_timeout_s)
        yield server
    finally:
        server.close()
        stdout_handle.close()
        stderr_handle.close()


def wait_for_http_ok(server: ApiServer, path: str, *, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if server.process.poll() is not None:
            raise ProductError(
                f"server exited before becoming healthy; stderr artifact: "
                f"{server.stderr_path}"
            )
        try:
            response = server.request("GET", path, timeout_s=1.0)
            if 200 <= response.status_code < 300:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.05)
    raise HarnessError(
        f"server did not become healthy at {path} within {timeout_s:.1f}s"
    ) from last_error
