# <Model title> — e.g. "Bookshelf"

- **Author:** <your name or handle>
- **Profile:** business-application <!-- or operational-system / organizational-knowledge / event-driven-system / ai-application / analytics-platform -->
- **Status:** valid <!-- valid | ready -->
- **Tags:** <3–6 tags, e.g. library, catalog, crud>
- **License:** Apache-2.0 <!-- keep unless you have a reason not to -->

## What it models

<One or two paragraphs: what domain this captures and who it's for. Be honest
about scope — what it deliberately includes and leaves out.>

## Key decisions & assumptions

- <e.g. "Books are identified by ISBN; editions are out of scope.">
- <e.g. "Borrowing is modelled as a command; fines are not.">

## How to use it

```bash
python kcf-oss/tools/kcf.py compile community/models/<your-domain>/model.kcf -o model-ir.json --validate
# then generate an app from it via the codegen pack or the MCP server:
#   see ../../../kcf-oss/docs/KNOWLEDGE_CODING.md
```
