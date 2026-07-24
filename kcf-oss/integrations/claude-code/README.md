# KCF in Claude Code

Two ways to use KCF from [Claude Code](https://claude.com/claude-code):

## 1. Add the MCP server (required)

```bash
pip install "kcf-oss[mcp]"
claude mcp add kcf -- kcf-mcp
```

That gives Claude Code the KCF tools (`compile`, `assess`, `coverage`, `scaffold`,
`list_stacks`, `codegen_prompt`, `authoring_reference`) and the guided
**`model_domain`** prompt — available as `/kcf` (MCP prompts show up in the
prompt menu). Just say *"Model a support desk with KCF and generate a FastAPI
backend"* and it runs the whole loop.

## 2. Add the slash command (optional convenience)

Copy the command into your commands directory so `/kcf-model` triggers the flow
explicitly:

```bash
# project-scoped:
mkdir -p .claude/commands && cp kcf-oss/integrations/claude-code/commands/kcf-model.md .claude/commands/
# or user-scoped (all projects):
mkdir -p ~/.claude/commands && cp kcf-oss/integrations/claude-code/commands/kcf-model.md ~/.claude/commands/
```

Then:

```
/kcf-model a library with books, members, and loans
```

It drafts a `.kcf` model, `assess`es it, fixes the required gaps, enriches the
recommended ones, and generates the app for a stack you choose — building from a
checked specification instead of prose. (Requires the MCP server from step 1.)
