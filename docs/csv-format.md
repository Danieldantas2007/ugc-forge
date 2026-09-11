# CSV format

One row, one generation. The file must be UTF-8 with a header line.

## Required columns

| Column | Values | Notes |
|---|---|---|
| `id` | any string | Must be unique in the file. Slugified into the output filename. |
| `type` | `image` or `video` | Decides which endpoint is called. |
| `model` | model id | From the Atlas Cloud model library. |
| `prompt` | text | Wrap in double quotes if it contains commas. |

## Optional columns

| Column | Example | Applies to |
|---|---|---|
| `image` | `https://…/frame.png` | Reference image or first frame. Separate several with `\|`. |
| `duration` | `8` | Video length in seconds. Must be a value the model supports. |
| `aspect_ratio` | `16:9` | Model dependent. |
| `size` | `2048*2048` | Mostly image models. |
| `seed` | `12345` | Reproducible output where supported. |
| `negative_prompt` | text | Only some models honour this. |

Unknown columns are ignored, so you can keep notes of your own in the
file (a `scene`, `owner` or `status` column, for example).

## Rules that save money

- Run `--dry-run` first. It validates ids, types and payloads without
  calling the API.
- Keep anchor images in rows above the videos that use them, so you can
  paste the resulting URL in before the second pass.
- `duration` has to be one of the values the chosen model accepts.
  Unsupported values are rejected by the API rather than rounded.

## Resuming

Progress is stored in `.ugc-forge-state.json` inside the output folder.
Rows marked `completed` are skipped on the next run. To regenerate a
single row, delete its entry from that file — or just change its `id`.
