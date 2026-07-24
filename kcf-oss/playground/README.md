# KCF Playground

A zero-persistence web wrapper around the open-source toolchain. Paste a `.kcf`
model and see, in one round trip:

1. **compile** → the normalized semantic IR (or a syntax error with `line:col`)
2. **assess** → the readiness verdict (`valid` / `ready` / coverage gaps)
3. **generate code** → pick a tech stack and get the ready-to-paste LLM prompt
   (the stack-agnostic system prompt + this model's IR + the stack's single-shot
   example). This is the lead path: KCF stops at the IR; your LLM writes the code.

The deterministic `vertical-slice` emitter is also available (`schema.sql`,
`openapi.json`, … + a lossless `trace-manifest`) as an optional baseline.

It reuses the exact reference functions the `kcf` CLI uses — no extra semantics,
no network calls, no proprietary overlay.

## Run locally

```bash
pip install -r kcf-oss/playground/requirements.txt
uvicorn app:app --app-dir kcf-oss/playground --reload
# open http://127.0.0.1:8000   (Cmd/Ctrl+Enter runs)
```

Run from the repository root so the toolchain finds `semantic-core/` as a
sibling of `kcf-oss/`.

## Run with Docker

```bash
# build context is the repo root
docker build -f kcf-oss/playground/Dockerfile -t kcf-playground .
docker run -p 8000:8000 kcf-playground
```

## Deploy (any container host)

The Docker image is self-contained and listens on `$PORT` 8000. It runs on
Fly.io, Render, Railway, Cloud Run, or any container platform:

- **Fly.io:** `fly launch --dockerfile kcf-oss/playground/Dockerfile`
- **Render / Railway:** point at the repo, set the Dockerfile path, expose 8000.
- **Cloud Run:** `gcloud run deploy --source .` after moving the Dockerfile to
  the repo root (or pass `--dockerfile`).

## API

- `GET /api/example` → `{ "source": "<the prefilled sample model>" }`
- `POST /api/run` `{ "source": "<.kcf text>" }` →
  `{ stage, ok, ir?, diagnostics?, assess?, emit?: { files, manifest }, error? }`
- `GET /api/stacks` → `{ "stacks": [ { "id", "title" }, … ] }`
- `POST /api/codegen` `{ "source": "<.kcf text>", "stack": "<id>" }` →
  `{ ok, stack, systemPrompt, userPrompt }` — the assembled, ready-to-paste
  code-generation prompt for the chosen stack (IR embedded).

Input is capped at 64 KB. The compiler is a parser, not an evaluator; models are
never executed.

## Future: fully static (no backend)

The compiler and analyzer are pure Python, so a later version can run entirely
in the browser via Pyodide and deploy to GitHub Pages with no server. This
FastAPI version is the simplest thing that works and is easy to host today.
