# Public launch checklist

The repository scaffolding is done and gated. The remaining items need your
hands (accounts, hosting, recording, publishing) — they can't be completed from
inside this workspace. Ordered by impact.

## Tier 0 — make it real (do first)

- [ ] **Create the standalone repo.** From the monorepo root (optionally set
      `GIT_AUTHOR_EMAIL` to your real Composable Holdings contact first):
      `GIT_AUTHOR_EMAIL=you@yourdomain.com bash kcf-oss/packaging/make-oss-repo.sh ../kcf-public`
      (copies `kcf-oss/` + `semantic-core/`, adds root scaffold, `git init`,
      first commit — copies only the open-source stack, never the proprietary
      overlay).
- [ ] **Verify the install** in the new repo:
      `cd ../kcf-public && python -m venv .venv && . .venv/Scripts/activate && pip install -e . && kcf check`
- [ ] **Replace `OWNER`** with your GitHub org/user across `README.md`,
      `pyproject.toml`, `OPEN_CORE.md`, `CONTRIBUTING.md`, and `.github/`.
      (`git grep -l OWNER`)
- [ ] **Push to GitHub:**
      `gh repo create kcf --public --source=. --remote=origin --push`
- [ ] Set the repo **description** and **topics** (`semantics`, `code-generation`,
      `llm`, `dsl`, `ebnf`, `intermediate-representation`).
- [ ] Set the enforcement contact in `CODE_OF_CONDUCT.md` (`[INSERT CONTACT]`).

## Tier 1 — the wow

- [ ] **Record the demo GIF:** `bash kcf-oss/packaging/record-demo.sh record`
      (needs `asciinema` + `agg`), then commit `demo.gif` and embed it near the
      top of `README.md`.
- [ ] **Enable GitHub Discussions** (the issue-template `config.yml` links to it).
- [ ] Add `good first issue` / `help wanted` labels and seed 3–5 starter issues
      (new example `.kcf` domains, a new emitter target, docs polish).

## Tier 2 — reach

- [x] **Hosted playground** — BUILT: `kcf-oss/playground/` (FastAPI + single-page
      UI; `Dockerfile` included). Remaining is *hosting* it: `fly launch
      --dockerfile kcf-oss/playground/Dockerfile` (or Render/Railway/Cloud Run),
      then link it from the README's "Try it in the browser" section.
- [x] **PyPI wheel** — DONE: the wheel maps `kcf-oss/` → the `kcf_oss` package and
      bundles the runtime data; `pip install kcf-oss` provides `kcf`
      (compile/assess/emit verified from a clean install, no `semantic-core`
      needed). Remaining is *publishing*: `python -m build && twine upload dist/*`
      (reserve the `kcf-oss` name on PyPI first; set up a Trusted Publisher /
      `PYPI_API_TOKEN`).
- [ ] **Docs site** — publish `kcf-oss/docs/` via GitHub Pages / MkDocs so
      concepts are indexable and linkable (retire the PDF-only theory).

## Tier 3 — announce

- [ ] Launch post framed on the pain — *"stop LLM code generators from
      hallucinating your domain model"* — with the GIF and a playground link.
      Target: Hacker News (Show HN), r/programming, relevant LLM/dev communities.
      **Do not** lead with "a 29-module grammar stack."
- [ ] Cross-link from any existing project pages; submit to awesome-lists in the
      code-generation / DSL space.

## Guardrail

Everything above stays within the open standard (`kcf-oss` + `semantic-core`).
Nothing here touches or exposes the proprietary overlay.
