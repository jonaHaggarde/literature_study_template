# intake/

The start of the pipeline: what the user tells Claude about the project, before anything is
written.

```
your files + interview  →  intake.md (Claude's digest)  →  articles/definition
```

- **Your files go here untouched,** in one of two folders so you can always tell whose they
  are: `own/` for what you wrote, `received/` for what someone else gave you (a client, a
  university, a rulebook). Claude never edits either. A PDF is converted to markdown next to
  itself (`convert_intake.py`), so it is read from text and not from the PDF again.
- **The interview** adds what the files do not say. Claude asks; the answers are recorded.
- **`intake.md`** is Claude's digest of both. It is for Claude, not for reading, and it is
  not reviewed: each line has an ID (`I-12`) and names the file or interview answer it came
  from. The definition article cites these IDs, and anything it states that has no intake line
  is marked as inferred, for the user to confirm or strike.

The article `articles/definition` is the document the user reviews and accepts. If `intake.md`
and the definition disagree, the definition wins.

Run `/intake` to start or extend it. `python study/scripts/intake_check.py` (also run by the
validator) fails on a duplicate ID, a line with no source, or a `\intake{I-n}` in an article
whose ID does not exist.

**Not decided yet:** whether the intake is an interview, a form, or both. `/intake` runs the
interview.
