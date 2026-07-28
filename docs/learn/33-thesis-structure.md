# Lesson 33 — The structure, chapter by chapter

*Part 4 · about 1 hour · after lesson 32*

---

## In one sentence

> Nine chapters, four of them already built as evidence, and each one answers a
> single question a reader is holding at that moment.

---

## The shape

A thesis is an **hourglass**:

```
   WIDE   1 Introduction        the world, the problem, why anyone should care
    |     2 Background          what is known, what is missing
    |     3 Method              exactly what you did
 NARROW   4 Measurement validity  why the instrument can be trusted
    |     5 Results             what you found
    |     6 The frontier        what it means economically
    |     7 Runtime abort       one mechanism, examined
    |     8 Limitations         where the claims stop
   WIDE   9 Conclusion          back to the world: what should someone do now
```

Wide, narrow, wide. Chapters 1–2 open outward; 3–7 are tight and specific; 8–9
open back out. Every reader knows this shape without being told, and violating it
is disorienting.

---

## Your nine chapters

### Ch 1 — Introduction *(to write)*

**The reader's question:** *why should I keep reading?*

| Element | Your material |
|---|---|
| The hook | 392 of 412 tokens on "reverse a string" |
| The problem | The cost is invisible; you cannot price from the visible answer |
| The stakes | 305× CPC spread — $50 vs $15,000/month |
| The gap | CodeRouterBench has no reasoning-token column |
| The question | The one sentence |
| Contributions | A numbered list of 4–5 |
| Roadmap | One line per chapter |

**Length:** 4–6 pages. **Written last**, or at least revised last — you cannot
promise contributions you have not finished writing.

### Ch 2 — Background *(to write)*

**The reader's question:** *what do I need to know, and what is already done?*

| Section | Content |
|---|---|
| 2.1 Reasoning models | What a reasoning trace is; why it is hidden |
| 2.2 Token pricing | How billing works; why reasoning ⊂ completion matters |
| 2.3 Code benchmarks | HumanEval+/MBPP+/LiveCodeBench; pass@1; contamination |
| 2.4 Routing | RouteLLM → Route-To-Reason → DART → CodeRouterBench |
| 2.5 Overthinking | ThoughtTerminator, SelfBudgeter, RecurGuard |
| 2.6 **The gap** | What none of them record |

**Length:** 8–12 pages.

⚠️ **The trap:** background that is a tutorial. Every paragraph must earn its
place by being needed later. If you explain something in Chapter 2 that never
returns, cut it.

⚠️ **The obligation:** your prior-art analysis is ~12 months stale in the
proposal, and §15.3 lists four closer works. **Cite them yourself, generously,
and state precisely what each does that you do not.** An examiner who names a
paper you missed has found a hole; one whose paper you already discussed
generously has found a colleague.

### Ch 3 — Method *(built — lessons 12, 21–28)*

**The reader's question:** *could I do this again and get the same answer?*

1. The unit of measurement (one row)
2. Roster and pinning (provider + quantization, and why)
3. The effort axis (models paired with themselves)
4. Problems: pool 884, run 320, stratified, seeded
5. Protocol: pass@1, temperature 0, one sample
6. Grading: one file, standard checker, canonical validation, the macOS bug
7. Cost measurement: computed vs actual, batch reconciliation
8. Cost controls: cap on worst case, cheapest-first, `request_hash`
9. **What went wrong and what changed** — the pilot's findings, the ceiling
   raises, the unbalanced grid

**Length:** 10–15 pages. Section 9 is the one most students omit and the one that
makes the chapter credible.

### Ch 4 — Measurement validity *(built — lesson 19)*

**The reader's question:** *can this instrument be trusted at all?*

The three platform lies, the one helpful behaviour, the mitigations applied, and
the general recommendation. **This chapter is absent from your proposal** and is
arguably your strongest material.

**Length:** 5–8 pages.

### Ch 5 — Results *(built — lessons 13, 14, 15)*

**The reader's question:** *what did you find?*

1. **Saturation first** — it tells the reader how to read everything after
2. Thinking works, conditionally — the headline table
3. Reasoning length and difficulty
4. Expensive failure — the three-way outcome table
5. Cost per correct — 305×, with intervals

**Length:** 10–15 pages.

### Ch 6 — The frontier *(built — lessons 17, 18)*

**The reader's question:** *what does this mean for what I should do?*

1. The 6 × 60 denominator
2. Frontier, dominance, the two-vertex hull
3. The dominated frontier model
4. Why the hull is the baseline (the proposition)
5. Oracle, and the 13.8-point gap
6. **The router, its collapse, and the decomposition**

**Length:** 8–12 pages.

### Ch 7 — Runtime abort *(built — lesson 16)*

**The reader's question:** *can any of this waste be recovered?*

Told as a narrative: mechanism → the pilot's claim → the censoring insight →
refutation → the honest curve → residual censoring → the general lesson.

**Length:** 6–10 pages.

### Ch 8 — Limitations *(to write — lesson 20)*

**The reader's question:** *where does this stop being true?*

Seven limitations, each as fact / damage / survival, opened by the two-sentence
framing.

**Length:** 3–5 pages. Short and dense.

### Ch 9 — Conclusion *(to write)*

**The reader's question:** *what should I do differently on Monday?*

1. Restate the question and answer it in one paragraph
2. The practitioner's guidance: **thinking on hard problems, off elsewhere;
   expect ~15% waste; abort at 16k if you will trade 12% of solutions for half
   the cost**
3. The researcher's guidance: **pin your provider and quantization; report your
   truncation rate; say which subset of your benchmark carries signal**
4. Future work, named specifically — a cost-aware routing objective; a
   re-measurement without a token ceiling
5. Close on the sentence you opened with

**Length:** 3–4 pages.

---

## The order to write in

**Not** 1 → 9. Write where the material is thickest and your understanding is
warmest:

| Order | Chapter | Why |
|---|---|---|
| 1st | **5 Results** | The numbers exist; it is transcription plus care |
| 2nd | **6 Frontier** | Same, and it follows 5 |
| 3rd | **7 Abort** | A story you already know |
| 4th | **4 Measurement validity** | Self-contained, all evidence in `models.yaml` |
| 5th | **3 Method** | Easier once you have seen which details the results relied on |
| 6th | **8 Limitations** | Collects what 3–7 exposed |
| 7th | **2 Background** | You now know exactly what needs introducing |
| 8th | **9 Conclusion** | Needs all findings settled |
| 9th | **1 Introduction** | Promises what the document delivers |
| 10th | Abstract | Last, always |

**Writing the introduction first is the most common way to lose a week.** You
end up promising a document you have not written, then editing the promise
repeatedly.

---

## Do this

**1. Build the skeleton file.**

Create the document with all nine chapter headings and their section headings —
empty. Then paste, under each section, the numbers it will use. You now have a
map instead of a blank page.

**2. Check the evidence exists for each section.**

```bash
cd ~/thesis
uv run python scripts/results.py > /tmp/thesis-numbers.txt
wc -l /tmp/thesis-numbers.txt
```

Keep that file open while you write. **Every number you type should be
copy-pasted from it, never remembered.**

**3. Write one section today.** Chapter 5, section 1 (saturation). You know it
cold from lesson 13. Aim for 400 words.

---

## Check yourself

1. What is the hourglass shape, and why does it matter?
2. Which chapters are already built as evidence, and what does "built" mean?
3. Why must Chapter 5 open with saturation rather than the headline finding?
4. What is the trap in Chapter 2, and what is the obligation?
5. Why write the introduction last?
6. Which Chapter 3 section do most students omit, and why does it matter?

<details>
<summary>Answers</summary>

1. Wide (context) → narrow (your specific work) → wide (implications). It matches
   what a reader expects and controls when they need broad versus precise
   attention.
2. Chapters 3, 4, 5, 6 and 7. "Built" means the evidence exists and is
   reproducible from `scripts/results.py` — only the prose is missing.
3. Because saturation determines how every later number must be read: 179 of 320
   problems cannot distinguish configurations, so any average over all of them is
   diluted.
4. The trap is writing a tutorial — background that never returns later. The
   obligation is citing the four closer works (Route-To-Reason, DART, HRBench,
   CodeRouterBench) yourself and stating exactly what each does that you do not.
5. Because it promises the contributions and roadmap of a document that must
   already exist; writing it first means rewriting the promise repeatedly.
6. "What went wrong and what changed" — the pilot's findings, the ceiling raises,
   the unbalanced grid. It matters because a method chapter where nothing went
   wrong is not credible to anyone who has run an experiment.

</details>

---

➡️ Next: [Lesson 34 — Writing Chapters 1 and 2](34-writing-ch1-2.md)
