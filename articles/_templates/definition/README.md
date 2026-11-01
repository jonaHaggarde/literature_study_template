# definition

The accepted statement of what the project is. Everything after it rests on it, and
`study/ai_instructions/scope.md` is derived from it.

| | |
|---|---|
| Gate | `definition` (light): the user's acceptance (`/gate definition`, then `gate.py close definition`) comes before `scope.md` is written and before any paper is gathered or converted |
| Written from | `intake.md` (Claude's digest of the user's intake). Each statement is tagged with its intake line (`\intake{I-12}`) or marked `\inferred`, which the user confirms or strikes at review. |
| Feeds | `scope.md`, written from the accepted article and kept in step by `scope_sync.py`: after a refinement it is stale, and is updated when the user says they are ready, not after each change. The map, the review and the requirements read the scope and the assumptions |
| Contains no | solutions, literature, requirements on a design |

**Run `/definition`** to draft it from `intake.md`, to revise it after your review, to refine
it after acceptance, and to write `scope.md` from it once accepted. It never runs `review`, and runs `gate.py open` and `gate.py close` only when you tell
it to. In a fork the first real draft replaces the skeleton's row and is
version `0.1`.

**Varies per project:** the constraints section is dropped when nothing is given; the
stakeholder table is dropped for a study with one person.

**Open (to settle with the user):** whether the assumption register is generated from the
article or kept next to it.
