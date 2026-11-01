# Dependency snapshot

`constraints.txt` records exact versions installed in the verified local Python environment. It excludes the editable application and contains no local paths or credentials. It is an environment snapshot, not a hash-verified cross-platform lock file.

To request the same versions while installing the project:

```sh
python -m pip install -c requirements/constraints.txt -e ".[dev]"
```

The package dependency declarations in pyproject.toml remain authoritative. CI also exercises allowed dependency ranges so compatibility regressions are visible. A snapshot can fail on an unsupported platform; do not silently relax pins and claim an identical environment. Regenerate intentionally after reviewing updates, rerun all gates, and record the actual environment in VALIDATION.md.

Before production use, choose an organizational lock/provenance process with artifact hashes, an approved index and platform-specific validation.
