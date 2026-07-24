# KCF Toolchain Architecture

```text
Textual .kcf model
        |
        v
Lexer -> parser AST -> profile closure -> normalized semantic IR
                                            |
                      +---------------------+--------------------+
                      |                     |                    |
                      v                     v                    v
              JSON Schema            Semantic analyzer     Semantic delta
                      |                     |                    |
                      +---------------------+--------------------+
                                            |
                                            v
                            coverage / assess (ready?)
                                            |
                                            v
                    ready IR ──▶ LLM code generation (codegen/), any stack
```

The textual model is the editable semantic source; the generated semantic IR is
the machine handoff contract and **kcf-oss stops there** — repair the `.kcf`
source and recompile instead of hand-editing generated IR. Code generation from a
`ready` IR is the LLM `codegen/` pack (a separate commercial platform builds on the same IR).
`semantic-core` owns neutral rules; KCF owns concepts, dimensions, profiles, and
compilation. DBML is a separate stack, not a KCF dependency.

Every release runs schema checks, grammar validation and linting, module
resolution, semantic fixtures, compiler golden snapshots, 6 foundational profile
closures, four domain trials, coverage/assess, semantic delta, IR migration,
compatibility checks, and module-integrity locks.

Use `python tools/kcf.py check` as the repository release gate. For a domain
release, compile with `--validate`, reach `kcf assess` `ready: true`, run
semantic delta, and register the immutable IR only after approval. Code
generation from the `ready` IR is LLM-based (see `../codegen/`); KCF stops at the
IR.
