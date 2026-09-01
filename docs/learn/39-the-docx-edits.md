# Lesson 39 — The 14 edits owed to your proposal

*Part 4 · about 3 hours of work · after lesson 38*

---

## In one sentence

> Your proposal describes a thesis you did not write — four of its claims are now
> actively wrong, and this lesson is the ordered checklist for fixing them.

---

## Why this exists

`Thesis_Project_Proposal.docx` (Revision 2, July 2026) promised a **router**. It
cited LiveCodeBench **for contamination resistance**. It contained **no
measurement-validity section**. It positioned novelty against work that is now
~12 months stale.

None of those were mistakes when written. All four are wrong now, because you
measured.

The full working list is [docs/docx-revisions.md](../docx-revisions.md). This
lesson is how to *use* it.

---

## The four structural edits — do these first

Everything else follows from them.

### Edit 1 — The title and framing

**From:** *Cost-Aware Reasoning Routing (CARR) — a training-free router that
picks the cheapest (model, thinking-mode) pair that still solves the problem.*

**To something like:** *When is reasoning worth paying for? A cost measurement of
thinking modes in open-weight code generation.*

**Why:** the router adds **+0.0 points** over the hull and collapses to one
configuration. **A thesis titled after its method, where the method fails, spends
its whole length apologising.**

The measurement survives and is the stronger contribution anyway. The router
becomes one section reporting a negative-but-diagnostic result.

### Edit 2 — The research questions

Rewrite RQ1–RQ5 around measurement rather than router-building:

| | Question | Answer |
|---|---|---|
| RQ1 | What predicts how long a model reasons? | Difficulty, monotonically: 642 → 17,547 tokens |
| RQ2 | When is that reasoning wasted, and what does it cost? | 49 calls, 29,584 mean tokens, $0.56, no answer |
| RQ3 | Can waste be cut at runtime? | An abort curve exists; **no free threshold does** |
| RQ4 | Is there headroom for a router, and can one exploit it? | 13.8 points exist; a router captures 0 |

Keep RQ5 only if you report it as thin — Kimi has 16–23 problems.

### Edit 3 — The gap analysis

Four closer works landed after the proposal: **Agent-as-a-Router /
CodeRouterBench, Route-To-Reason, DART, HRBench.** Plus *When Routing Collapses*,
which names the degeneracy you then reproduce.

**Do not claim a novel router.** Claim the measurement and the validity findings,
and state the one concrete gap: CodeRouterBench's `model` column holds eight model
names and nothing else — **no effort axis, no reasoning-token column.**

### Edit 12 — Every LiveCodeBench contamination claim

**The property does not hold.** Newest problem 2025-04-06; dataset stopped
updating 2025-06-05; every roster model is a 2026 release.

Rewrite **every** citation of LCB-as-contamination-control to
LCB-as-difficulty-tier, and state the exposure as a limitation backed by stored
release dates.

> *This is the edit most likely to be caught by an examiner if left.*

---

## The other ten, in order

| # | Edit | The number that justifies it |
|---|---|---|
| 4 | **Add a measurement-validity section** | 18 providers, $0.87–$3.48; 1.54× billing; 13,731 tokens against a 2,000 budget; 35,837 against 16,000; $0.00 cancellation |
| 5 | Roster: five models, **three families**, and the pinning method | fp8-or-better; per-endpoint prices, not headline |
| 6 | Separate the **pool** from the **run set** | Pool 884; run 320; 1,373 generations; $5.24; paired 107 |
| 7 | Describe the **second grading harness** | Two LCB execution styles; no canonical solutions, so hand-written references |
| 8 | CPC and TPC **with intervals** | Ratio estimator; resample problems; 5 adjacent pairs overlap |
| 9 | Rewrite the router section as a **negative result** | Oracle 98.3% at $0.00111; hull 84.5%; headroom 13.8; router +0.0; 0.0 / 33.3 decomposition |
| 10 | Three **risks are now results** | Saturation confirmed (141 of 320); routing collapse confirmed; budget held at $5.24 of $15 under a $6 cap |
| 11 | **Add the results** — there were none before | 24.9% → 54.2%; 305× CPC; the dominated frontier model; ~15% waste on the reasoning arm |
| 13 | Write **Limitations** properly | 26.3% censoring; binary effort axis; single sample; overlap with prior overthinking work |
| 14 | **Include the self-refutation** | 56 calls above 10,000 tokens succeeded; 88% [82,92] for 49% [35,61] |

⚠️ **On edit 7:** the working list quotes **112 stdin / 63 functional**, which is
the v6-only split. The pool you actually used is v5+v6 — **217 stdin / 125
functional of 342.** Use the pool figures, and fix the working list while you are
there.

---

## How to do this without losing a week

**1. Work top-down.** 1, 2, 3, 12 first. They change what the document is
*about*, and every later edit is easier once the frame is right.

**2. If time is short**, `docx-revisions.md` names the minimum: **1, 2, 3 and
12** are the ones that would otherwise be *actively wrong* at submission. Wrong
is worse than incomplete.

**3. Keep the original.** Save `Thesis_Project_Proposal.docx` untouched and work
in a copy. The proposal is evidence of what you set out to do, and the *distance*
between it and the final document is itself a story worth being able to tell
accurately.

**4. Every number gets copied**, never remembered:

```bash
cd ~/thesis
uv run python scripts/results.py > /tmp/thesis-numbers.txt
```

**5. Tick them off.** Fourteen items, in `docx-revisions.md`. Mark each done as
you go, and note anything you deliberately skipped and why — that note is your
answer if it comes up.

---

## The thing this lesson is really teaching

You are about to rewrite a document because the evidence contradicted it.

That is not a failure of planning. It is what the word *research* means. A
proposal is a hypothesis about what you will find; **finding something else is
the normal outcome of a real experiment**, and the ability to say so cleanly is
the skill being assessed.

You have an unusually good version of this story, because you can show:

- The change was made **on 2026-07-26, in week 2**, not discovered at the end.
- It was **driven by data** — the pilot's routing collapse.
- It was **de-risking**: the new question yields a result either way.
- The router was then measured anyway, and **the reframing was vindicated**.

Say that in one paragraph in Chapter 3 or Chapter 1. It converts what looks like
a retreat into evidence of judgement.

---

## Do this

**1. Read the full list.**

```bash
cd ~/thesis
open docs/docx-revisions.md
```

**2. Copy the proposal before touching it.**

```bash
cp Thesis_Project_Proposal.docx Thesis_Project_Proposal-ORIGINAL.docx
```

**3. Do edit 1 today.** Just the title and the framing paragraph. It is the
smallest edit and the one everything else depends on.

**4. Write the reframing paragraph.** Four sentences: what the proposal
promised, what the pilot showed, what the question became, and that the router
was measured anyway and confirmed the change. This paragraph will be used more
than once — in Chapter 1, in Chapter 3, and out loud at your defence.

---

## Check yourself

1. Which four edits are structural, and why must they come first?
2. Why is a thesis titled after a failed method a problem?
3. If you had time for only four edits, which four and why?
4. What is the one concrete gap you may still claim against CodeRouterBench?
5. Why keep an untouched copy of the proposal?
6. Which edit is most likely to be caught by an examiner if left undone?
7. Why is the reframing a strength rather than a retreat?

<details>
<summary>Answers</summary>

1. Title/framing, research questions, gap analysis, and the LiveCodeBench
   contamination claims. They determine what the document is about, so every
   other edit is written differently depending on them.
2. Because the whole document ends up apologising for its own title. Retitling
   around the measurement makes the same evidence read as a contribution.
3. Edits 1, 2, 3 and 12 — the ones that would otherwise be actively wrong at
   submission, rather than merely incomplete.
4. Its `model` column holds eight model names and nothing else: no effort axis
   and no reasoning-token column — the quantity carrying most of a thinking
   call's cost.
5. Because it is evidence of what you set out to do, and the distance between it
   and the final thesis is a story you should be able to tell accurately.
6. Edit 12 — the LiveCodeBench contamination claims, since the dataset's own
   release dates make the claim checkable in minutes.
7. Because it was made in week 2, driven by pilot data, chosen because the new
   question yields a result either way — and the router was measured anyway and
   confirmed the change was right.

</details>

---

➡️ Next: [Lesson 40 — Defending it](40-defending-it.md)
