# Usage log

A running record of how this repo actually gets used: the *shape* of a session,
never what it was about. It exists so the template this repo came from can be
designed from real use. Nothing reads it during normal work, and you do not
need to open it.

**What an entry is.** One short line: a new kind of request the template had no
step for, a moment the user asked for a structural rework and not a tweak, a
convention that fit badly, a script or check that misbehaved, an idea said in
passing. Claude appends entries with `.claude/log_usage.py` (see the "Usage
log" section of the root `CLAUDE.md`).

**What never goes in.** Anything about the project's subject: no names, no
quantities, no file contents, no paths, no URLs, no secrets. The script refuses
text that looks like any of these. If a line would only make sense to someone
who knows the project, it does not belong here.

**What to do with it.** Nothing, until you want to give feedback to the template:
copy the file to wherever that is tracked. It is committed with the repo; if the
remote is shared or public and you would rather it stayed local, add
`.claude/usage-log.md` to `.gitignore`. To turn logging off, delete the
"Usage log" section from the root `CLAUDE.md`.

## Entries

