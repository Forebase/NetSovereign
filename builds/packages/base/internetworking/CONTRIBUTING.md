# Contributing

## Principles

1. The core describes infrastructure; it does not manage infrastructure.
2. Prefer immutable value objects and composition over deep inheritance.
3. Keep runtime dependencies at zero unless a compelling cross-platform need arises.
4. Use standard-library types such as `ipaddress` where they are already canonical.
5. Platform-specific collection and mutation belong in adapters or companion packages.

## Checks

```bash
pytest
ruff check .
mypy src
python -m build
```
