"""Lecture par navigateur dans un processus séparé, tué à l'échéance (C166, relecture).

Un site peut bloquer Chromium (boucle JavaScript sans fin) : aucun délai interne ne l'arrête
alors. Le processus de lecture est lancé dans sa propre session ; à l'échéance, il est tué avec
tout ce qu'il a lancé (pilote Playwright, Chromium). Un seul navigateur à la fois : la mémoire
de l'hébergeur reste bornée.
"""

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from prospection.sources.web_reader import SLOW, UNREACHABLE, ReadResult, WebPage

LAUNCH_SECONDS = 3.0  # démarrage de Python et de Chromium, en plus de la lecture
_ONE_AT_A_TIME = threading.Semaphore(1)


def render_isolated(url: str, seconds: float, test_services_url: str | None = None) -> ReadResult:
    """`test_services_url` : bout en bout et tests, chaque site est demandé au faux local."""
    command = [sys.executable, "-m", "prospection.sources.browser_child", url, str(seconds),
               test_services_url or ""]  # fmt: skip
    with _ONE_AT_A_TIME:
        process = subprocess.Popen(  # noqa: S603 (liste d'arguments, jamais de shell)
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True
        )
        try:
            out, _ = process.communicate(timeout=seconds + LAUNCH_SECONDS)
        except subprocess.TimeoutExpired:
            return ReadResult(None, SLOW)
        finally:
            _kill_session(process.pid)
            process.wait()
    return _decode(out)


def _kill_session(session: int) -> None:
    """Tue chaque processus de la session (Chromium peut changer de groupe de processus)."""
    for stat in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
            if int(fields[3]) == session:  # champ « session » de /proc/<pid>/stat
                os.kill(int(stat.parent.name), signal.SIGKILL)
        except (OSError, ValueError, IndexError):
            continue


def _decode(out: bytes) -> ReadResult:
    try:
        data = json.loads(out)
        if data.get("problem"):
            return ReadResult(None, str(data["problem"]))
        page = WebPage(str(data["url"]), str(data["html"]), float(data["seconds"]),
                       truncated=bool(data["truncated"]))  # fmt: skip
    except (ValueError, KeyError, TypeError):
        return ReadResult(None, UNREACHABLE)
    return ReadResult(page)
