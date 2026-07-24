---
name: Bug report
about: Something in the compiler, analyzer, or an emitter behaves incorrectly
title: "[bug] "
labels: bug
---

## What happened

<!-- A clear description of the incorrect behavior. -->

## Minimal reproduction

<!-- The smallest `.kcf` model or IR that shows the problem. Paste it inline or
     link a gist. Smaller is dramatically easier to fix. -->

```kcf
kcf model … { … }
```

## Command and output

```bash
kcf compile repro.kcf --output ir.json --validate
# paste the actual output / diagnostics / stack trace
```

## Expected behavior

<!-- What you expected instead. -->

## Environment

- KCF version / commit:
- Python version:
- OS:

## `kcf check` status

<!-- Does `kcf check` pass on your checkout? -->
