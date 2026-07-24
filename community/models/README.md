# Community Models

Share a `.kcf` domain model you've built. Good models are the fastest way for
newcomers to learn KCF and a head start for anyone modelling a similar domain.

## Layout

One folder per model, named in `kebab-case`:

```
community/models/
  your-domain/
    model.kcf      # the model (must compile and be `valid`)
    README.md      # what it is, who made it, how to use it
```

Copy [`TEMPLATE/`](TEMPLATE/) to start.

## Requirements

- **`model.kcf`** — must **compile** and be **`valid`** (analyzer-clean). Aim for
  `ready` (no required coverage gaps) when you can, but `valid` is the bar. Model
  only what the domain really means; don't invent detail to look complete.
- **`README.md`** — fill in the template header: title, author, `profile`, a
  one-paragraph description, and 3–6 tags. Note anything a user should know
  (assumptions, what it deliberately leaves out).
- **Self-contained** — no external references; one model per folder.

## Check it before you PR

```bash
# validate every community model (compiles + asserts `valid`):
python community/models/validate.py

# or just yours, with the CLI (compile to IR, then assess it for coverage):
python kcf-oss/tools/kcf.py compile community/models/your-domain/model.kcf -o model-ir.json --validate
python kcf-oss/tools/kcf.py assess  model-ir.json
```

CI runs `validate.py`, so a green run locally means a green PR.

## Tips

- Pick the closest `profile` (`business-application`, `operational-system`,
  `organizational-knowledge`, `event-driven-system`, `ai-application`,
  `analytics-platform`) but let your domain drive the content.
- Reference/lookup entities → mark `mutability "read-only";`.
- See [`../../kcf-oss/mcp/authoring-brief.md`](../../kcf-oss/mcp/authoring-brief.md)
  for the full `.kcf` syntax and what `valid` vs `ready` means.
