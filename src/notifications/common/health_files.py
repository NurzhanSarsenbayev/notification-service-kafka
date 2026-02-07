from __future__ import annotations

import asyncio
import time
from pathlib import Path

READY_PATH = Path("/tmp/ready")
HEARTBEAT_PATH = Path("/tmp/heartbeat")


def mark_ready() -> None:
    READY_PATH.write_text("ok\n")


def clear_ready() -> None:
    try:
        READY_PATH.unlink(missing_ok=True)
    except Exception:
        # Best-effort cleanup
        pass


async def heartbeat_loop(interval_sec: float = 5.0) -> None:
    """Write unix timestamp periodically. Best-effort; never raises."""
    while True:
        try:
            HEARTBEAT_PATH.write_text(str(time.time()))
        except Exception:
            pass
        await asyncio.sleep(interval_sec)
