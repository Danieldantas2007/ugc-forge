"""ugc-forge — batch image and video generation from a CSV of prompts.

    python -m src.forge run examples/scenes.example.csv --out ./output

Every row becomes one generation on Atlas Cloud. Progress is written to
.ugc-forge-state.json inside the output folder, so an interrupted run picks
up exactly where it stopped instead of paying twice for the same prompt.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .atlas import AtlasClient, AtlasError
from .state import RunState

REQUIRED_COLUMNS = {"id", "type", "model", "prompt"}

EXTENSION_BY_TYPE = {"image": ".png", "video": ".mp4"}

# CSV columns that map straight onto the API payload when present.
PASSTHROUGH_COLUMNS = (
    "size",
    "aspect_ratio",
    "resolution",
    "duration",
    "seed",
    "negative_prompt",
)


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", value) or "item"


def read_rows(csv_path: str) -> list[dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"CSV is missing required column(s): {', '.join(sorted(missing))}"
            )
        rows = [
            {(key or "").strip(): (value or "").strip() for key, value in row.items()}
            for row in reader
        ]

    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        if not row.get("id"):
            raise SystemExit(f"Row {index} has an empty id.")
        if row["id"] in seen:
            raise SystemExit(f"Duplicate id {row['id']!r} on line {index}.")
        seen.add(row["id"])
        if row.get("type") not in EXTENSION_BY_TYPE:
            raise SystemExit(
                f"Row {row['id']}: type must be 'image' or 'video', "
                f"got {row.get('type')!r}."
            )
    return rows


def build_payload(row: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": row["model"], "prompt": row["prompt"]}

    for column in PASSTHROUGH_COLUMNS:
        value = row.get(column)
        if not value:
            continue
        if column in {"duration", "seed"}:
            payload[column] = int(float(value))
        else:
            payload[column] = value

    # A single reference/first-frame image, or a pipe-separated list of them.
    image = row.get("image", "")
    if image:
        urls = [part.strip() for part in image.split("|") if part.strip()]
        payload["image" if len(urls) == 1 else "images"] = (
            urls[0] if len(urls) == 1 else urls
        )

    return payload


def process_row(
    client: AtlasClient | None,
    state: RunState,
    row: dict[str, str],
    output_dir: str,
    poll_interval: float,
    dry_run: bool,
) -> tuple[str, str]:
    row_id = row["id"]

    if state.is_done(row_id):
        return row_id, "skipped (already done)"

    payload = build_payload(row)

    if dry_run or client is None:
        return row_id, f"dry-run -> {payload['model']}"

    state.mark(row_id, status="submitting", model=row["model"])
    prediction_id = client.submit(row["type"], payload)
    state.mark(row_id, status="running", prediction_id=prediction_id)

    prediction = client.wait(prediction_id, interval=poll_interval)

    saved: list[str] = []
    extension = EXTENSION_BY_TYPE[row["type"]]
    for index, url in enumerate(prediction.outputs):
        suffix = "" if len(prediction.outputs) == 1 else f"-{index + 1}"
        filename = f"{slugify(row_id)}{suffix}{extension}"
        client.download(url, os.path.join(output_dir, filename))
        saved.append(filename)

    state.mark(
        row_id,
        status="completed",
        prediction_id=prediction_id,
        files=saved,
        outputs=prediction.outputs,
    )
    return row_id, f"done -> {', '.join(saved) or 'no file'}"


def run(args: argparse.Namespace) -> int:
    rows = read_rows(args.csv)
    os.makedirs(args.out, exist_ok=True)

    state = RunState(args.out)
    # A dry run only validates the CSV, so it must work without a key.
    client = None if args.dry_run else AtlasClient(api_key=args.api_key)

    pending = [row for row in rows if not state.is_done(row["id"])]
    print(f"{len(rows)} row(s) in CSV, {len(pending)} to generate.")
    if not pending:
        print("Nothing to do — everything already finished.")
        return 0

    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                process_row,
                client,
                state,
                row,
                args.out,
                args.poll_interval,
                args.dry_run,
            ): row["id"]
            for row in pending
        }
        for future in as_completed(futures):
            row_id = futures[future]
            try:
                _, message = future.result()
                print(f"  [ok]   {row_id}: {message}")
            except (AtlasError, OSError) as exc:
                failures += 1
                state.mark(row_id, status="failed", error=str(exc))
                print(f"  [fail] {row_id}: {exc}", file=sys.stderr)

    print(f"\nSummary: {state.summary()}")
    print(f"Files in: {os.path.abspath(args.out)}")
    return 1 if failures else 0


def status(args: argparse.Namespace) -> int:
    state = RunState(args.out)
    counts = state.summary()
    if not counts:
        print("No run state found in this folder yet.")
        return 0
    for key, value in sorted(counts.items()):
        print(f"{key}: {value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ugc-forge",
        description="Batch image and video generation on Atlas Cloud, from a CSV.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="generate everything in a CSV")
    run_parser.add_argument("csv", help="path to the CSV file")
    run_parser.add_argument("--out", default="./output", help="output folder")
    run_parser.add_argument(
        "--workers", type=int, default=2, help="parallel generations (default 2)"
    )
    run_parser.add_argument(
        "--poll-interval", type=float, default=3.0, help="seconds between polls"
    )
    run_parser.add_argument("--api-key", default=None, help="overrides the env var")
    run_parser.add_argument(
        "--dry-run", action="store_true", help="validate the CSV without generating"
    )
    run_parser.set_defaults(func=run)

    status_parser = subparsers.add_parser("status", help="show progress of a run")
    status_parser.add_argument("--out", default="./output", help="output folder")
    status_parser.set_defaults(func=status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except AtlasError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Run the same command again to resume.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
