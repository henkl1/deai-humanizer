# Contributing

Thanks for improving DeAI Humanizer.

## Development

```bash
python -m pip install -e ".[image,dev]"
python -m unittest -v
```

Keep changes focused and rule-based where possible. The project should remain easy to run without external services.

## Pull Request Checklist

- Add or update tests for behavior changes.
- Run `python -m unittest -v`.
- Do not add credentials, private data, model keys, generated caches, or local reference archives.
- Preserve the safety boundary: no detector evasion, watermark removal, metadata stripping, provenance hiding, or recovery of redacted private information.

## Style

- Prefer clear deterministic rules over complex abstractions.
- Keep public APIs backward compatible where practical.
- Use concise prompt/edit wording that is ready to paste into image tools.
