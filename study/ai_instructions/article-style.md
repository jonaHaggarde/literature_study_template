# Writing style for articles

Applies to the hand-written text of everything under `articles/` and to gate reports. Not to
chat: in chat a second wording helps the reader understand, in an article it costs the reader
time. READMEs and instruction files keep their own convention.

The failure to avoid: **the same content twice in different words**, in one sentence ("X, in
other words Y"), in neighbouring sentences, or in two sections. Everything below serves that.

## Rules

**Content**

1. **One home per fact.** State it once, where it belongs. Elsewhere give a cross-reference
   (`§3.2`, a table, an ID). An abstract and a conclusion may restate; nothing else may.
2. **Every sentence carries a claim, number, source, decision or definition.** If removing it
   loses nothing, remove it.
3. **Numbers over adjectives.** "Robust", "efficient", "significant", "important", "various"
   need a value, a comparison or a citation in the same sentence, or they go.
4. **One name per concept.** Define a term at first use, then use it unchanged. Do not cycle
   "method / approach / technique / algorithm" for variety.
5. **A claim from the literature carries a citation.** With none, it is our assumption or
   inference, and says so.
6. **State uncertainty once, specifically:** what, why, how large. No scattered "may",
   "might", "could potentially".
7. **No praise words:** novel, comprehensive, powerful, state-of-the-art.

**Structure**

8. **A section starts with its content.** No sentence announcing what it will do, no
   roadmap paragraph, no "in this section".
9. **No summary paragraphs** except the abstract, a conclusion and a list of open issues.
10. **Parallel content goes in a table, an equation or a list of full claims.** Prose is for
    reasoning with steps. A list of bare noun phrases is a table that was not drawn.
11. **Length follows content.** No page counts, no padding to fill, no cutting to fit.
12. **An example only when it removes an ambiguity.** Define every symbol at first use;
    number only the equations that are referred to.

**Process (what to do, in this order)**

13. **List, then write, then cut.** The skeleton's "Contains" text is the claim list for a
    section. Write it. Then one pass whose only job is deletion: for each sentence, is it a
    claim from the list, or already said?
14. **Before adding a paragraph, search the article for the same fact** (grep a key term).
15. **Run `python study/scripts/style_check.py <article>` before reporting a draft or an
    edit.** Fix every *problem*. Decide each *judgment call*, and keep it if it is right.

## What the check does and does not do

`style_check.py` is advisory: it never fails a build. It reports **problems** (clear cases)
and **judgment calls** (a person decides).

| Finds | Kind |
|---|---|
| filler phrases, summary phrases outside a conclusion, stacked hedges | problem |
| a claim with no named source ("studies show") with no citation in the sentence | problem |
| a sentence whose content another sentence already carries | problem |
| an evaluative word with no number or citation in its sentence | judgment |
| a nearby sentence, or a second clause, that restates | judgment |
| a sentence over 40 words; many hedges; a list of bare phrases; a connective used 3 times | judgment |

It skips comments, `\todo` text, equations, tables, TikZ, generated files, abstracts and
conclusions (for the restatement checks), and any line ending `% style-ignore`.

It cannot tell whether a sentence adds anything, or catch a restatement that shares few
words. Rules 13 and 14, and the user's review, cover those.

**The phrase list grows from the user's review.** When the user flags a phrase, add it to
`style-phrases.txt` (one line, a tier heading above it) so the check finds it next time.
