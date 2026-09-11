# ugc-forge

**From a spreadsheet of prompts to finished UGC videos, in one command.**

[![Powered by Atlas Cloud](https://www.atlascloud.ai/oss-program/powered-by-atlas-cloud.svg)](https://www.atlascloud.ai/?ref=YOUR_INVITE_CODE)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)

Generating one video at a time in a web UI is fine for a demo. It falls
apart the moment you need forty scenes for a campaign: you babysit a
browser tab, you lose track of which prompt produced which file, and a
dropped connection means paying twice for the same generation.

`ugc-forge` takes a CSV, generates every row through the
[Atlas Cloud](https://www.atlascloud.ai/?ref=YOUR_INVITE_CODE) API,
downloads the results with readable filenames, and remembers exactly
where it stopped.

It ships with a companion skill that turns an idea into that CSV.

---

## What you get

- **Batch generation** — images and videos in the same run.
- **Resume** — interrupt it, run the same command again, finished rows
  are skipped. No double billing.
- **Readable output** — files named after your row ids, not hashes.
- **One key, 400+ models** — Seedance, Kling, Seedream, Nano Banana,
  Flux and the rest, by changing one column.
- **A scene planner skill** — structure for turning a brief into scenes.

---

## Install

```bash
git clone https://github.com/Danieldantas2007/ugc-forge.git
cd ugc-forge
pip install -r requirements.txt

cp .env.example .env      # then paste your key
export ATLASCLOUD_API_KEY="your-api-key"
```

Get a key at [atlascloud.ai/console/api-keys](https://www.atlascloud.ai/console/api-keys).
Your key stays in `.env`, which is gitignored. Never commit it.

---

## Use

**Windows, no terminal at all:** double-click `gerar.bat`, or drag a CSV
file onto it. It checks your setup, saves your API key on first run,
validates the file, asks for confirmation, then generates and opens the
output folder.

Everything below is the cross-platform command line.

Validate the CSV without spending anything:

```bash
python -m src.forge run examples/scenes.example.csv --dry-run
```

Generate for real:

```bash
python -m src.forge run examples/scenes.example.csv --out ./output
```

Check where a run stands:

```bash
python -m src.forge status --out ./output
```

Options: `--workers` for parallel generations (default 2),
`--poll-interval` for seconds between status checks,
`--api-key` to override the environment variable.

---

## The CSV

Four columns are required: `id`, `type`, `model`, `prompt`. Everything
else is optional and passed straight to the model.

```csv
id,type,model,prompt,image,duration,aspect_ratio,size
scene-01-anchor,image,bytedance/seedream-v4.7/text-to-image,"A woman by a kitchen window, morning light",,,,2048*2048
scene-01-video,video,bytedance/seedance-v2.0/image-to-video,"She turns and starts talking",https://…/anchor.png,8,16:9,
```

| Column | Required | Notes |
|---|---|---|
| `id` | yes | unique; becomes the filename |
| `type` | yes | `image` or `video` |
| `model` | yes | any Atlas Cloud model id |
| `prompt` | yes | the generation prompt |
| `image` | no | reference or first frame; separate several with `\|` |
| `duration` | no | seconds, for video |
| `aspect_ratio` | no | `16:9`, `9:16`, `1:1` |
| `size` | no | `2048*2048` and similar |
| `seed` | no | for reproducible results |
| `negative_prompt` | no | where the model supports it |

Full reference: [docs/csv-format.md](docs/csv-format.md).

Model ids live in the
[Atlas Cloud model library](https://www.atlascloud.ai/models).

---

## The scene planner skill

[`skill/SKILL.md`](skill/SKILL.md) is an agent skill (Claude Code, or any
agent that reads skill files) that walks a brief into a scene list and
writes the CSV this tool consumes.

It gives you the structure a UGC video needs — scene count, what job
each scene does, the prompt skeleton, the continuity block that stops
faces drifting between scenes. The prompts and the persona are yours to
write.

---

## How it works

```
CSV row ──▶ POST /model/generateImage or /generateVideo ──▶ prediction_id
              │
              └──▶ GET /model/prediction/{id}  (poll until done)
                        │
                        └──▶ download ──▶ output/<id>.mp4
                                              │
                                              └──▶ state file updated
```

State lives in `.ugc-forge-state.json` inside your output folder.
Delete it to force a full regeneration.

---

## Contributing

Issues and pull requests are welcome. Useful directions: more output
formats, a webhook mode instead of polling, cost estimation before a
run, and adapters for other providers.

---

## License

MIT — see [LICENSE](LICENSE).

Built on [Atlas Cloud](https://www.atlascloud.ai/?ref=YOUR_INVITE_CODE),
one API key for 400+ image, video, audio, 3D and LLM models.
