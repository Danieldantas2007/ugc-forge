---
name: ugc-scene-planner
description: Turns a product or topic into a scene-by-scene UGC video script, then exports it as a CSV that ugc-forge can generate. Use when the user asks for a UGC script, a talking-head ad, a short-form video plan, or wants to go from an idea to generated video scenes.
---

# UGC Scene Planner

Plans a short-form UGC video scene by scene, then writes a CSV that
`ugc-forge` turns into real images and videos.

This skill is the **skeleton**. It defines the structure, not the taste.
The prompts, the persona and the wording are yours to fill in.

## Step 1 — Collect the brief

Never write scenes before you have all five answers:

| Field | Example |
|---|---|
| Persona / creator | who is on camera |
| Product or topic | what the video is about |
| Goal | sale, awareness, social proof, storytelling |
| Total length | 8s / 15s / 30s / 60s |
| Length per scene | 8s / 10s / 15s |

Ask for anything missing. Do not guess the duration.

## Step 2 — Work out the scene count

```
scene_count = floor(total_length / scene_length)
```

The real runtime is `scene_count × scene_length`, which may be shorter
than requested when the numbers do not divide evenly. Say so before
writing anything.

## Step 3 — Assign a job to each scene

Only the first scene is a hook. Everything else has a different job.

- **1 scene** — hook, one beat, close.
- **2–3 scenes** — hook / open loop / resolution + CTA.
- **4+ scenes** — hook / open the loop / pattern interrupts / close the
  loop / CTA.

## Step 4 — Write each scene

Each scene needs three things:

1. **Line** — what the person says, in their own language.
2. **Action cue** — one visible gesture or camera move. At least one
   small human micro-action per scene (adjusting hair, shifting weight,
   a hand that hesitates). Never only the main action.
3. **Prompt** — the generation prompt, in English.

### Prompt skeleton

Fill every bracket. Delete nothing.

```
[shot size and framing] of [subject description].
[setting], [lighting], [time of day].
Action: [what they do], [micro-action].
Camera: [movement].
dialogue (lip-synced, [language]): "[the line]"

CONTINUITY: same face, same skin tone, same hair (exact colour, length
and style), wearing the exact same [garment + precise colour name]
established in the previous scene. No identity drift, no wardrobe
colour drift between scenes.

NEGATIVE: no camera operator visible, no second person in frame, no
extra limbs, no floating objects, no selfie stick, no text overlay,
no watermark, no beauty filter, no plastic skin.
```

Two rules that break generations when ignored:

- **The line goes inside the video prompt**, not only in the script.
  Models with native audio read the dialogue from the prompt to drive
  lip sync.
- **From scene 2 onward, spell out the continuity block.** Vague phrases
  like "same woman as before" get reinterpreted every time and the face
  drifts.

### Camera that follows someone

For any scene with walking or movement, describe a real person holding
a camera nearby — never "selfie style" on its own, which produces a
ghost arm.

```
The camera follows approximately one meter behind her, natural
shoulder-level handheld tracking, subtle autofocus corrections, small
operator inertia. She rarely acknowledges the camera.
```

## Step 5 — Export the CSV

Write one row per generation. Anchor images first, then the videos that
use them.

```csv
id,type,model,prompt,image,duration,aspect_ratio,size
scene-01-anchor,image,<image-model>,"<image prompt>",,,,2048*2048
scene-01-video,video,<video-model>,"<video prompt>",<anchor-url>,8,16:9,
```

Then hand it to the generator:

```bash
python -m src.forge run scenes.csv --out ./output
```

## What this skill deliberately does not do

It does not pick your models, write your hooks, or hold a prompt
library. It gives the structure a UGC video needs; the content that
fills it is yours.
