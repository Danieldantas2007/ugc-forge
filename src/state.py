"""Run state: lets an interrupted batch resume where it stopped."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

STATE_FILENAME = ".ugc-forge-state.json"


class RunState:
    """Tracks the outcome of every row so reruns skip finished work."""

    def __init__(self, output_dir: str) -> None:
        self.path = os.path.join(output_dir, STATE_FILENAME)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"rows": {}, "updated_at": None}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as handle:
                    self._data = json.load(handle)
            except (json.JSONDecodeError, OSError):
                pass
        self._data.setdefault("rows", {})

    def _flush(self) -> None:
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat()
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ------------------------------------------------------------------ api

    def is_done(self, row_id: str) -> bool:
        entry = self._data["rows"].get(row_id)
        return bool(entry and entry.get("status") == "completed")

    def get(self, row_id: str) -> dict[str, Any] | None:
        return self._data["rows"].get(row_id)

    def mark(self, row_id: str, **fields: Any) -> None:
        with self._lock:
            entry = self._data["rows"].setdefault(row_id, {})
            entry.update(fields)
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._flush()

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self._data["rows"].values():
            status = entry.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
        return counts
