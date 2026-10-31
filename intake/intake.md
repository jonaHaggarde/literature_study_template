# Intake digest

For Claude, not for reading, and not reviewed by the user. Built by `/intake` from the files
in this folder and from the interview. One row per claim; IDs are never reused or
renumbered. The definition article cites these IDs and is the document the user reviews.
Checked by `study/scripts/intake_check.py`.

Kinds: `fact`, `goal`, `constraint`, `preference`, `said` (the user's own words, kept as said),
`unknown` (asked and not answered), `suspicion` (the user's hunch, not a fact),
`out-of-bounds`.

| ID | Kind | Statement | Source |
|---|---|---|---|
