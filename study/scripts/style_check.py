#!/usr/bin/env python3
"""
Advisory style check for the hand-written text of the articles under articles/.

It looks for the residue of padded writing, so the user's review time goes on content:
filler phrases, evaluative words with nothing behind them, stacked hedges, a claim with no
named source, and above all text that says the same thing twice in other words, whether in
two clauses of one sentence, in neighbouring sentences, or in two sections. The rules it
supports are in ai_instructions/article-style.md; the phrases it matches are in
ai_instructions/style-phrases.txt, which grows when the user flags a phrase.

Findings are of two kinds. A *problem* is a clear case. A *judgment* is a case a person must
decide (a restatement is sometimes right: an abstract or a conclusion may restate). Neither
fails a build, and the validator only warns about problems.

What is skipped: comments, `\\todo` text, equations, tables, figures drawn in TikZ, verbatim
text, citations and cross-references, generated files, and any line carrying the marker
`% style-ignore`. Sentences in an abstract and in a conclusion or summary section are exempt
from the restatement checks.

What it cannot see: whether a sentence adds anything, and restating that shares few words.
Those rest on the rules and on the user's review.

Usage (from study/):
    python scripts/style_check.py              # every article
    python scripts/style_check.py rationale    # one article
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_bibliography import ARTICLES_DIR, article_dirs  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PHRASES_PATH = REPO_ROOT / "ai_instructions" / "style-phrases.txt"
GENERATED = {"references.tex", "versions.tex", "comparison_rows.tex"}
EXEMPT_FILES = {"conclusion.tex", "summary.tex", "abstract.tex"}
IGNORE_MARK = "style-ignore"

LONG_SENTENCE_WORDS = 40
DUPLICATE_JACCARD = 0.6
NEARBY_JACCARD = 0.4
NEARBY_CONTAINMENT = 0.7
MIN_CONTENT_WORDS = 7
MIN_CLAUSE_WORDS = 4
HEDGES_PER_1000 = 8
HEDGE_MIN_WORDS = 300
BARE_ITEMS = 4
BARE_ITEM_WORDS = 3

STOP = set("""a an the and or but if then than that this these those of to in on at by for with from as is are was
were be been being it its into onto over under not no nor so such can could may might will would shall should
we our us you your they their there here which who whom whose what when where why how also only just very more
most less least each every both either neither any all some one two three first second third per via while
whereas because since between among across about after before during within without upon is has have had do does
did done""".split())
HEDGE_WORDS = ("may", "might", "could", "possibly", "perhaps", "potentially", "somewhat", "relatively")
ABBREVIATIONS = re.compile(r"\b(e\.g|i\.e|et al|fig|eq|vs|cf|sec|tab|approx|no)\.", re.I)


@dataclass
class Finding:
    file: str
    line: int
    severity: str   # "problem" or "judgment"
    rule: str
    text: str


# ---- the phrase list -------------------------------------------------------------------------

def load_phrases(path=PHRASES_PATH):
    """{section: [(compiled regex, source text)]} from style-phrases.txt."""
    sections, current = {}, None
    if not path.exists():
        return sections
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections[current] = []
        elif current:
            pattern = line[3:] if line.startswith("re:") else re.escape(line)
            sections[current].append((re.compile(rf"(?<![\w-]){pattern}(?![\w-])", re.I), pattern))
    return sections


# ---- masking: keep the prose, blank the rest, keep every offset ------------------------------

def blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def blank_todo(text):
    r"""Blank every \todo{...} including nested braces."""
    out, i = text, 0
    while True:
        start = out.find("\\todo{", i)
        if start < 0:
            return out
        depth, j = 0, start + 5
        while j < len(out):
            depth += (out[j] == "{") - (out[j] == "}")
            if depth == 0:
                break
            j += 1
        out = out[:start] + re.sub(r"[^\n]", " ", out[start:j + 1]) + out[j + 1:]
        i = start + 1


def stage_one(text):
    """Comments, ignored lines, \\todo text and non-prose environments blanked; commands kept."""
    lines = [re.sub(r"[^\n]", " ", ln) if IGNORE_MARK in ln else ln for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"(?<!\\)%.*", blank, text)
    text = blank_todo(text)
    envs = "equation\\*?|align\\*?|eqnarray\\*?|gather\\*?|multline\\*?|tabular\\*?|tabularx|verbatim|lstlisting|tikzpicture"
    text = re.sub(rf"\\begin\{{({envs})\}}.*?\\end\{{\1\}}", blank, text, flags=re.S)
    text = re.sub(r"\$[^$\n]*\$|\\\[.*?\\\]|\\\(.*?\\\)", blank, text, flags=re.S)
    return text


def stage_two(text):
    """Commands blanked too, leaving plain prose at the same offsets."""
    text = re.sub(r"\\(cite[a-z]*|ref|eqref|autoref|label|input|include|bibliography|bibliographystyle|"
                  r"usepackage|documentclass|newcommand|renewcommand|section|subsection|subsubsection|"
                  r"paragraph|caption|begin|end)\*?(\[[^\]]*\])*(\{[^}]*\})*", blank, text)
    text = re.sub(r"\\(textbf|emph|textit|texttt|textsc|text|mbox)\{", blank, text)
    text = re.sub(r"\\[a-zA-Z]+\*?", blank, text)
    text = re.sub(r"\\.", blank, text)
    return re.sub(r"[{}~]", " ", text)


# ---- sentences --------------------------------------------------------------------------------

def content_stems(s):
    words = re.findall(r"[a-z][a-z-]{2,}", s.lower())
    return {w[:6] for w in words if w not in STOP}


def similarity(a, b):
    if not a or not b:
        return 0.0, 0.0
    inter = len(a & b)
    return inter / len(a | b), inter / min(len(a), len(b))


def split_sentences(prose):
    """[(start, end)] of sentences of at least four words, abbreviations and decimals kept whole."""
    protected = ABBREVIATIONS.sub(lambda m: m.group(0).replace(".", "\x00"), prose)
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\x00", protected)
    spans = []
    for m in re.finditer(r"[^.!?]+[.!?]*", protected):
        seg = prose[m.start():m.end()]
        if len(re.findall(r"[A-Za-z]{2,}", seg)) >= 4:
            spans.append((m.start() + len(seg) - len(seg.lstrip()), m.end()))
    return spans


@dataclass
class Sentence:
    file: str
    line: int
    para: int
    index: int
    text: str
    original: str
    stems: set
    exempt: bool
    start: int = 0
    end: int = 0


def excerpt(s, n=70):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1] + "\u2026"


# ---- one file ---------------------------------------------------------------------------------

def analyse_file(label, text, exempt_file, phrases):
    """(findings, sentences) for one hand-written file."""
    stage1 = stage_one(text)
    prose = stage_two(stage1)
    abstract = [(m.start(), m.end()) for m in re.finditer(r"\\begin\{abstract\}.*?\\end\{abstract\}", stage1, re.S)]
    findings, sentences = [], []

    def line_of(pos):
        return text.count("\n", 0, pos) + 1

    for idx, (a, b) in enumerate(split_sentences(prose)):
        s = prose[a:b]
        in_abstract = any(x <= a < y for x, y in abstract)
        sentences.append(Sentence(label, line_of(a), len(re.findall(r"\n[ \t]*\n", prose[:a])), idx, s,
                                  text[a:b], content_stems(s), exempt_file or in_abstract, a, b))

    def phrase_hits(section, severity, rule, skip_with_cite=False, skip_in_exempt=False):
        for rx, _src in phrases.get(section, []):
            for m in rx.finditer(prose):
                if skip_in_exempt and exempt_file:
                    continue
                if skip_with_cite:
                    own = next((x for x in sentences if x.start <= m.start() < x.end), None)
                    if own and "\\cite" in own.original:
                        continue
                findings.append(Finding(label, line_of(m.start()), severity, rule, m.group(0)))

    phrase_hits("always", "problem", "filler phrase")
    phrase_hits("unless-conclusion", "problem", "summary phrase outside a conclusion", skip_in_exempt=True)
    phrase_hits("hedge-stack", "problem", "stacked hedges")
    phrase_hits("attribution", "problem", "claim with no named source", skip_with_cite=True)

    for s in sentences:   # evaluative words with nothing behind them
        has_support = bool(re.search(r"\d|\\cite", s.original))
        if has_support:
            continue
        for rx, _src in phrases.get("cluster", []):
            m = rx.search(s.text)
            if m:
                findings.append(Finding(label, s.line, "judgment", "evaluative word with no number or source",
                                        f"'{m.group(0)}' in: {excerpt(s.text.strip())}"))
                break

    for s in sentences:   # very long sentences
        n = len(re.findall(r"[A-Za-z]+", s.text))
        if n > LONG_SENTENCE_WORDS:
            findings.append(Finding(label, s.line, "judgment", f"sentence of {n} words", excerpt(s.text.strip())))

    for s in sentences:   # two clauses of one sentence saying the same
        clauses = [c for c in re.split(r"[,;:]|\u2014|--|\bwhich\b|\bthat is\b", s.text) if c.strip()]
        sets = [content_stems(c) for c in clauses]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                if min(len(sets[i]), len(sets[j])) >= MIN_CLAUSE_WORDS:
                    jac, _ = similarity(sets[i], sets[j])
                    if jac >= DUPLICATE_JACCARD and not s.exempt:
                        findings.append(Finding(label, s.line, "judgment", "two clauses of one sentence say the same",
                                                excerpt(s.text.strip())))
                        break
            else:
                continue
            break

    words = re.findall(r"[A-Za-z]+", prose)
    if len(words) >= HEDGE_MIN_WORDS:
        hedges = sum(1 for w in words if w.lower() in HEDGE_WORDS)
        if hedges * 1000 / len(words) > HEDGES_PER_1000:
            findings.append(Finding(label, 1, "judgment", "many hedges",
                                    f"{hedges} hedge words in {len(words)} words; state the uncertainty once, "
                                    "with its size"))

    for m in re.finditer(r"(?:^[ \t]*\\item\b[^\n]*\n?){%d,}" % BARE_ITEMS, stage1, re.M):   # bare noun-phrase lists
        items = [re.sub(r"\\item\s*", "", ln).strip() for ln in m.group(0).splitlines() if ln.strip()]
        if all(len(re.findall(r"[A-Za-z]+", i)) <= BARE_ITEM_WORDS for i in items):
            findings.append(Finding(label, line_of(m.start()), "judgment", "list of bare phrases",
                                    "make each item a claim, or a table"))
    return findings, sentences


def repeat_findings(label_texts, phrases):
    """Judgment calls for words used three or more times across the whole article."""
    findings = []
    for rx, src in phrases.get("repeat", []):
        hits = []
        for label, prose in label_texts:
            hits += [(label, prose.count("\n", 0, m.start()) + 1) for m in rx.finditer(prose)]
        if len(hits) >= 3:
            findings.append(Finding(hits[0][0], hits[0][1], "judgment", "repeated connective",
                                    f"'{src}' used {len(hits)} times"))
    return findings


def restatements(sentences):
    """Findings for sentences that say what another sentence says."""
    findings = []
    for i, a in enumerate(sentences):
        for b in sentences[i + 1:]:
            if a.exempt or b.exempt or min(len(a.stems), len(b.stems)) < MIN_CONTENT_WORDS:
                continue
            jac, cont = similarity(a.stems, b.stems)
            where = f"{b.file}:{b.line}" if a.file != b.file else f"line {b.line}"
            if jac >= DUPLICATE_JACCARD:
                findings.append(Finding(a.file, a.line, "problem", "says what another sentence says",
                                        f"{excerpt(a.text.strip(), 50)} ~ {where}"))
            elif a.file == b.file and a.para == b.para and abs(a.index - b.index) <= 2 \
                    and (jac >= NEARBY_JACCARD or cont >= NEARBY_CONTAINMENT):
                findings.append(Finding(a.file, a.line, "judgment", "restated in a nearby sentence",
                                        f"{excerpt(a.text.strip(), 50)} ~ line {b.line}"))
    return findings


# ---- an article -------------------------------------------------------------------------------

def article_files(adir):
    files = [adir / "main.tex"] if (adir / "main.tex").exists() else []
    if (adir / "sections").exists():
        files += [p for p in sorted((adir / "sections").glob("*.tex")) if p.name not in GENERATED]
    return files


def check_article(adir, phrases=None):
    """All findings for one article, sorted by file and line."""
    phrases = load_phrases() if phrases is None else phrases
    findings, sentences, prose_by_file = [], [], []
    for path in article_files(adir):
        label = path.relative_to(adir).as_posix()
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        f, s = analyse_file(label, text, path.name in EXEMPT_FILES, phrases)
        findings += f
        sentences += s
        prose_by_file.append((label, stage_two(stage_one(text))))
    findings += restatements(sentences)
    findings += repeat_findings(prose_by_file, phrases)
    return sorted(findings, key=lambda f: (f.file, f.line, f.severity))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[0] if argv else None
    dirs = [d for d in article_dirs() if only in (None, d.name)]
    if not dirs:
        print("No articles found." if not only else f"No article named '{only}'.", file=sys.stderr)
        return 1
    phrases = load_phrases()
    total_problems = total_judgments = 0
    for adir in dirs:
        findings = check_article(adir, phrases)
        for f in findings:
            print(f"articles/{adir.name}/{f.file}:{f.line} [{f.severity}] {f.rule}: {f.text}")
        problems = sum(1 for f in findings if f.severity == "problem")
        total_problems += problems
        total_judgments += len(findings) - problems
    print(f"{total_problems} problem(s), {total_judgments} judgment call(s). Advisory: nothing here fails a build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
