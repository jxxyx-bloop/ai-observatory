---
name: Add a coding tool
about: Ask for (or offer) support for an AI coding CLI or IDE agent
labels: provider
---

**Tool name and homepage**

**Where does it write transcripts?**
e.g. `~/.qwen/sessions/**/*.jsonl`

**Paste 2–3 anonymised records** (redact any prompt or completion text — we only
need the shape and the token fields):

```json
```

**Are you able to add it yourself?**
If your tool writes JSONL with token counts on a record, it needs no Python —
just a spec file and a fixture. See
[collectors/specs/README.md](../../observatory/collectors/specs/README.md).
You have the transcripts to test against, which the maintainers do not.
