# 03 - Controlled Vocabulary

## Gate

Resolve material lexical ambiguity before creating semantic identities.

## Prompt

```text
Extract the controlled vocabulary from the approved domain brief and source
requirements.

For every term record:

- preferred term;
- aliases and abbreviations;
- definition;
- possible senses;
- selected sense in this domain;
- proposed primary KCF kind;
- requirement evidence;
- ambiguity status;
- whether human approval is required.

Pay special attention to overloaded terms such as account, order, request,
approval, service, process, policy, model, case, load, role, and resource.

Produce:

- [PROJECT_ROOT]/domain/02-vocabulary.md
- [PROJECT_ROOT]/domain/02-open-questions.md

Do not silently resolve ambiguity that would change concept kind, identity,
behavior, authority, lifecycle, or application scope.

The phase passes only when material terms have one approved domain sense or an
explicit blocking question.
```

