"""Thin client for the Atlas Cloud unified model API.

Docs: https://www.atlascloud.ai/docs
Submit  (POST): /api/v1/model/generateImage | /api/v1/model/generateVideo
Poll     (GET): /api/v1/model/prediction/{prediction_id}
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

BASE_URL = os.environ.get("ATLASCLOUD_BASE_URL", "https://api.atlascloud.ai/api/v1")

IMAGE_ENDPOINT = "/model/generateImage"
VIDEO_ENDPOINT = "/model/generateVideo"
PREDICTION_ENDPOINT = "/model/prediction/{prediction_id}"


class AtlasError(RuntimeError):
    """Raised when the API returns an error or a generation fails."""


@dataclass
class Prediction:
    prediction_id: str
    status: str
    outputs: list[str]
    raw: dict[str, Any]

    @property
    def done(self) -> bool:
        return self.status in {"completed", "succeeded", "failed", "canceled"}

    @property
    def ok(self) -> bool:
        return self.status in {"completed", "succeeded"}


class AtlasClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key or os.environ.get("ATLASCLOUD_API_KEY")
        if not self.api_key:
            raise AtlasError(
                "Missing API key. Set ATLASCLOUD_API_KEY in your environment "
                "or copy .env.example to .env."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    # ---------------------------------------------------------------- submit

    def submit(self, kind: str, payload: dict[str, Any]) -> str:
        """Start an async generation and return its prediction id."""
        if kind not in {"image", "video"}:
            raise AtlasError(f"Unknown generation kind: {kind!r}")

        endpoint = IMAGE_ENDPOINT if kind == "image" else VIDEO_ENDPOINT
        response = self.session.post(
            f"{self.base_url}{endpoint}", json=payload, timeout=self.timeout
        )
        data = self._unwrap(response)

        prediction_id = data.get("prediction_id") or data.get("id")
        if not prediction_id:
            raise AtlasError(f"No prediction id in response: {data}")
        return str(prediction_id)

    # ------------------------------------------------------------------ poll

    def get(self, prediction_id: str) -> Prediction:
        url = f"{self.base_url}{PREDICTION_ENDPOINT.format(prediction_id=prediction_id)}"
        response = self.session.get(url, timeout=self.timeout)
        data = self._unwrap(response)

        outputs = data.get("outputs") or []
        if isinstance(outputs, str):
            outputs = [outputs]

        return Prediction(
            prediction_id=prediction_id,
            status=str(data.get("status", "unknown")),
            outputs=[str(item) for item in outputs],
            raw=data,
        )

    def wait(
        self,
        prediction_id: str,
        interval: float = 3.0,
        max_wait: float = 1800.0,
    ) -> Prediction:
        """Poll until the prediction finishes, fails, or hits max_wait."""
        started = time.monotonic()
        while True:
            prediction = self.get(prediction_id)
            if prediction.done:
                if not prediction.ok:
                    reason = prediction.raw.get("error") or prediction.status
                    raise AtlasError(f"Generation failed: {reason}")
                return prediction

            if time.monotonic() - started > max_wait:
                raise AtlasError(
                    f"Timed out after {max_wait:.0f}s waiting for {prediction_id}"
                )
            time.sleep(interval)

    # -------------------------------------------------------------- download

    def download(self, url: str, destination: str) -> str:
        with requests.get(url, stream=True, timeout=300) as response:
            response.raise_for_status()
            with open(destination, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1 << 16):
                    handle.write(chunk)
        return destination

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _unwrap(response: requests.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:  # pragma: no cover - network edge case
            raise AtlasError(
                f"Non-JSON response ({response.status_code}): {response.text[:200]}"
            ) from exc

        if response.status_code >= 400:
            message = body.get("message") or body.get("error") or response.text[:200]
            raise AtlasError(f"HTTP {response.status_code}: {message}")

        data = body.get("data", body)
        if not isinstance(data, dict):
            raise AtlasError(f"Unexpected response shape: {body}")
        return data
