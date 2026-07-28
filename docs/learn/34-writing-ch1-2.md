# Lesson 34 — Writing Chapters 1 and 2

*Part 4 · about 2 hours of writing · after lesson 33*

---

## In one sentence

> Chapter 1 makes a stranger care in two pages; Chapter 2 gives them exactly the
> background they need and no more, and cites the four papers that nearly scooped
> you.

---

## Chapter 1 — Introduction

### The seven-move structure

**Move 1 — The concrete hook.** Never open with "In recent years, large language
models have…". Open with the thing that surprised you:

> *A trivial request — "write a Python function that reverses a string" — returned
> 412 completion tokens. The visible answer was three lines. **392 of those
> tokens were reasoning the user never sees, and pays for.***

Specific, verifiable, and it makes the problem physical in two sentences.

**Move 2 — Generalise the problem.** Reasoning models emit billed, invisible
tokens. You cannot price a call from its answer. There is no published guidance
on when to enable thinking for code generation.

**Move 3 — The stakes.** Cost per correct answer spans **305×** across an
open-weight roster — the difference between a $50 and a $15,000 monthly bill for
the same work.

**Move 4 — What is missing.** The nearest work, CodeRouterBench (June 2026),
releases 9,999 tasks × 8 models with per-call cost. **Its `model` column holds
eight model names and nothing else: no effort axis, no reasoning-token column.**
The quantity that carries most of a thinking call's cost is the one it does not
record.

**Move 5 — The question.** One sentence, set apart on the page.

**Move 6 — Contributions.** A numbered list. Yours:

1. A measured table of **1,373 graded generations** across 320 problems and 10
   (model × thinking-mode) configurations, with reasoning tokens and actual
   billed cost per call.
2. Evidence that the value of reasoning is **conditional on difficulty** — more
   than doubling pass rate on hard problems (24.9% → 54.2%) and buying almost
   nothing on standard benchmarks.
3. A quantification of **benchmark saturation**: only 141 of 320 problems can
   distinguish any configuration from another.
4. **Three measurement-validity findings** about commercial aggregators — silent
   provider and quantization substitution, ignored reasoning-budget parameters,
   non-binding token ceilings — plus one that enables a new control.
5. A measurement of the **value of problem-level information** (13.8 accuracy
   points) and a **decomposition** showing that a free-feature router fails on
   estimation rather than on information.

**Move 7 — Roadmap.** One line per chapter.

### Rules for Chapter 1

- **Every number in it appears again later.** The introduction promises; the
  body pays.
- **No forward-referenced jargon.** If "convex hull" appears in Chapter 1, it
  needs a clause defining it.
- **Do not hide the negative.** Contribution 5 says a router fails. Putting that
  in the introduction is a strength signal, and it stops the reader feeling
  misled in Chapter 6.

### Sentences to steal

> This thesis measures what that thinking costs and when it is worth paying for.

> The cheapest configuration in this study answers a correct solution for
> $0.00021; the dearest for $0.06320. Both are open-weight models accessed
> through the same API on the same day.

> Fewer than half the problems in the standard benchmarks used for this kind of
> study are capable of distinguishing one configuration from another.

---

## Chapter 2 — Background

### The test for every paragraph

> **Does something later in the thesis become unreadable without this?**

If no, cut it. Chapter 2 is not a demonstration that you read widely; it is the
minimum equipment a reader needs.

### 2.1 Reasoning models

What a reasoning trace is. Why providers hide it. The critical arithmetic:
**reasoning tokens are a subset of completion tokens.** State it here and refer
back — it is the axis your whole thesis measures.

### 2.2 Token pricing and cost measurement

Per-token billing, input vs output asymmetry. Why cost must be **measured, not
derived** from response length: a 5–10× understatement otherwise. Introduce
**CPC** here so Chapter 5 can use it without ceremony.

### 2.3 Code generation benchmarks

HumanEval → HumanEval+ (why the `+` exists: the originals were weak enough that
buggy solutions passed). MBPP+ — and note **378, not 500**. LiveCodeBench, its
release-date design, **and that the design requires the benchmark to keep
updating**. Define pass@1 and contamination.

### 2.4 Routing and adaptive inference

Chronological, ending with the four works closest to you:

| Work | What it does | What it does not do |
|---|---|---|
| RouteLLM (2025) | Model routing by query | No effort axis |
| Route-To-Reason (May 2025) | Joint model **and** reasoning-strategy allocation under budget | Appears to require training |
| DART (Jun 2026) | Training-free adaptive thinking budgets, text-only API | **Must generate drafts** — not pre-inference, and it costs tokens |
| HRBench (May 2026) | 6 models × 5 benchmarks incl. code, 12 switching settings | — |
| **CodeRouterBench** (Jun 2026) | Code routing, 8 backends, 9,999×8 released with cost | **No effort axis, no reasoning-token column**; closed-weight; trained router (LoRA) |
| When Routing Collapses (Feb 2026) | Names the degeneracy where routers pick one model | — |

⚠️ **Be generous and precise.** Overstating what a competitor lacks is the
easiest way to lose credibility, and the "what it does not do" column must be
checkable. Your own notes flag that these assessments rest on search summaries
and PDF extraction rather than full reads — **so read Route-To-Reason,
Agent-as-a-Router and HRBench in full before submission.** That is real work
still owed.

### 2.5 Overthinking and non-termination

ThoughtTerminator, SelfBudgeter, RecurGuard. **State plainly that the phenomenon
is not novel here**, and that your contribution is the economic framing: what it
costs as a share of a real budget, across a roster spanning 305× in CPC.

Conceding this in Chapter 2 costs you nothing and buys you the reader's trust
for the rest of the document.

### 2.6 The gap

Three or four sentences, no more:

> Existing work routes between **models**. Where reasoning effort is considered,
> it is either trained, or it requires generating draft output, or it is not
> priced. **No published dataset records (model × thinking-mode) outcomes for
> code generation with reasoning-token cost attached** — and that quantity
> carries most of the cost of a thinking call. This thesis measures it.

---

## Do this

**1. Write Chapter 1, Move 1, five different ways.** Five openings, one
paragraph each. Read them aloud. Keep the one that makes a non-technical person
lean in.

**2. Draft the contributions list.** Five numbered items, one sentence each, each
with a number in it. This list is the spine of the entire document — if an item
has no number, it is not a contribution yet.

**3. Fill the prior-art table honestly.**

```bash
cd ~/thesis
sed -n '/### 15.3/,/^---/p' THESIS.md
```

For each work, write one sentence on what it does and one on what it does not.
**Mark which claims you have verified by reading the paper and which rest on
summaries** — then read the three that matter before you submit.

**4. Write §2.6 first.** The gap paragraph is the hardest and shortest. Once it
is right, sections 2.1–2.5 exist only to make it land, and you will know what to
cut.

---

## Check yourself

1. Why open with the 392-of-412 example rather than with context about LLMs?
2. What must be true of every number in the introduction?
3. Why put the router's failure in the contributions list?
4. What is the test for whether a Chapter 2 paragraph earns its place?
5. Why concede in Chapter 2 that overthinking is not novel?
6. What is the one concrete gap CodeRouterBench leaves you, and why is it the
   right thing to claim?
7. What prior-art work do you still owe before submission?

<details>
<summary>Answers</summary>

1. Because it is specific, verifiable and makes the problem physical in two
   sentences, where a general opening asks the reader to supply their own
   motivation.
2. It must appear again later, backed by evidence. The introduction promises;
   the body pays.
3. Because it is a genuine contribution — a measured negative with a diagnosis —
   and because hiding it until Chapter 6 would make the reader feel misled.
4. Would something later in the thesis become unreadable without it? If not, cut
   it.
5. Because ThoughtTerminator, SelfBudgeter and RecurGuard already cover it, and
   conceding it early costs nothing while buying trust for the claims that are
   yours — the economic framing.
6. Its `model` column holds eight model names with no effort axis and no
   reasoning-token column. It is the right claim because it is specific,
   checkable against released data, and it is exactly the quantity your thesis
   measures.
7. Full reads of Route-To-Reason, Agent-as-a-Router (CodeRouterBench) and
   HRBench — the current assessments rest on summaries and PDF extraction.

</details>

---

➡️ Next: [Lesson 35 — Writing Chapters 3 and 4](35-writing-ch3-4.md)
