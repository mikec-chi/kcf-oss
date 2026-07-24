# KCF Tests

The test suite includes schema-valid and intentionally invalid IR fixtures,
runtime drift and semantic delta fixtures, an automated-rule fixture index,
four textual domain trials with golden compiler snapshots, organizational
knowledge validation, profile closure, three-emitter completeness, migration,
module locks, and compatibility checks.

Run all gates with `python tools/kcf.py check`.

`fixtures/` contains:

- `valid/`: a semantic IR expected to produce no errors;
- `invalid/`: deliberate violations across all implemented analyzer families,
  including organizational knowledge and epistemic governance;
- `delta/`: a changed model used to verify compatibility classification;
- `runtime/`: compatible and drifted runtime manifests.

Run the complete suite with:

```powershell
python tools/run_conformance.py
```
