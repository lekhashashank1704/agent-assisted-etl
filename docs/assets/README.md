# Architecture artwork

- `architecture.png`: 2800 x 2340 raster export for GitHub, LinkedIn media and presentations.
- `architecture.svg`: editable, accessible vector source with selectable text and a descriptive title.
- `../../scripts/render_architecture.py`: common geometry and text for both formats.

## Reproduce

```sh
python -m pip install -e ".[diagrams]"
python scripts/render_architecture.py
```

Pillow is an optional artwork dependency; the ETL runtime does not need it. Rendering was verified with Pillow 13.0.0 and Windows Segoe UI. Linux falls back to DejaVu Sans, then Pillow's default font; raster text metrics can vary with installed fonts. Generated SVG uses system font fallbacks and remains editable. The renderer checks card text width and vertical bounds.

## Visual semantics

Blue identifies human control and source inspection; purple identifies the bounded AI schema-planning role; teal identifies local policy and deterministic execution; amber identifies approval and recovery; coral identifies quarantine; cyan identifies reporting. Dashed boxes are proposed enterprise extensions and are explicitly unimplemented. The dashed recovery connector represents an operator-triggered fresh attempt.

The design follows the user's supplied four-plane reference, with implementation details reconciled to the current code: 10 MiB/100,000-row defaults, a 20-second API timeout, at most two SDK retries, `BEGIN IMMEDIATE`, order-level idempotency, current module names, 77 tests and 11 scripted scenarios. It does not claim autonomous multi-agent orchestration, production deployment or successful live API evaluation.

Update evidence numbers and control descriptions when the implementation changes. The detailed execution and transaction diagrams remain in `../ARCHITECTURE.md`.
