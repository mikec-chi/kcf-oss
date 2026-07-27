# Working in this repo (agents & humans)

`kcf-oss` is the open standard: the KCF grammar stack, the reference compiler/analyzer,
and the LLM code-generation pack. **It stops at the semantic IR** — code generation is a
prompt pack, not a fixed generator.

## Orient

- `kcf-oss/docs/CONCEPTS.md` — the model of the model (start here).
- `kcf-oss/QUICKSTART.md` / `kcf-oss/docs/AUTHORING.md` — write a `.kcf`.
- `kcf-oss/codegen/README.md` — generate an app from a `ready` IR.
- `kcf-oss/mcp/` — the MCP server (the conversational pipeline).

## Common commands

```bash
python kcf-oss/tools/kcf.py compile <model>.kcf -o model-ir.json --validate
python kcf-oss/tools/kcf.py assess model-ir.json          # valid / ready + coverage gaps
python kcf-oss/tools/kcf.py check                          # the conformance gate
python kcf-oss/tools/kcf.py import-dbml <schema>.dbml --id M --namespace m
```

## The one rule for core changes

Anything that touches the **grammar / IR (`model-ir-v1`) / analyzer contract** goes
through a **[Grammar RFC](kcf-oss/docs/EXTENDING.md)** + a
**[VERSIONING](kcf-oss/docs/VERSIONING.md)** decision, and must keep `kcf check` green.
See `CONTRIBUTING.md`.

## Field reports — feed observations back to kcf-oss

As you build models, IRs, or generate apps, keep a running list of anything the toolchain
got wrong or could do better — doc↔parser drift, a compiler bump that broke a valid
`.kcf`, a coverage obligation that pushed you to over-model, a source attribute/
relationship you had to drop, a missing authoring surface, a skeleton-quality generation,
or a rough CLI/MCP edge. **This is advisory — it must never block or delay your actual
work.**

On completion, package each observation as a sanitized `kcf-field-report:v1` envelope and
submit it per [`community/field-reports/README.md`](community/field-reports/README.md):

- **write** one report per file to `community/field-reports/incoming/<id>.md`;
- if you have repo/network access, open a `field-report`-labeled issue
  (`gh issue create --label field-report --body-file <report>.md`) or a PR adding that
  file, and return the URL;
- otherwise **print the raw envelope(s) with the exact submit instructions** and hand off
  to the human. **Never claim a submission you did not make.**

Every report needs a minimal reproducer (`commands` + `snippet`) and
`domainSanitized: true` — reports are about the toolchain, never anyone's domain data.
