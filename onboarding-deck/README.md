# Onboarding deck

Ten slides that introduce the template to a new user. This folder is the source of the deck;
the published copy is a Slides artifact on claude.ai.

- `deck.json` holds the slide order; `slides/<id>.html` holds one slide each (1920x1080,
  inline styles, speaker notes in an `<aside>`).
- To change the deck, edit a slide here and ask Claude to republish it. Keep it consistent with
  the root `CLAUDE.md` and `README.md`: it says Claude sets up the environment on "let's start"
  and can search for papers itself.
- A `.pptx` or PDF export, if one is added, is saved next to this file as `onboarding-deck.pptx`
  (export it from the artifact's menu; it is a snapshot, so the source here stays the truth).

Why the source is kept here: an export can be opened by anyone but cannot be edited back into
the artifact; the source can.
