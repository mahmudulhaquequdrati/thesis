# Lesson 38 — Figures, tables and citations

*Part 4 · about 1 hour · after lesson 37*

---

## In one sentence

> A figure supports exactly one claim, a table carries the numbers a reader needs
> to check you, and a citation is a promise you have read the thing.

---

## Figures

### The rule: one figure per claim

You have four, and each maps to one:

| File | Claim it supports | Chapter |
|---|---|---|
| `01-effort-by-tier.png` | Thinking helps on hard problems and barely on easy | 5 |
| `02-reasoning-vs-outcome.png` | Long reasoning means failure to finish, not effort | 5 |
| `03-frontier-and-hull.png` | Two hull vertices, a dominated frontier model, 13.8 points | 6 |
| `04-abort-tradeoff.png` | The honest tradeoff, with its uncertainty | 7 |

**If you cannot state a figure's claim in one sentence, it is decoration.** Four
figures that each carry a claim beat twelve that carry impressions.

### The rules your figures already follow

| Rule | Why it is defensible out loud |
|---|---|
| **Error bars wherever an interval exists** | A bare chart implies precision the data lacks — five CPC pairs overlap |
| **Greyscale-safe** | Colour never the sole carrier of information; survives printing and colour-blind readers |
| **Sample sizes on the panel** | Several rest on 60–107 problems; a reader should not have to hunt |
| **Y-axis starts at zero for proportions** | A truncated axis exaggerates differences — the most common honest-looking distortion |
| **Regenerated, never hand-edited** | A hand-tweaked PNG is a number that no longer matches its source |

### Captions

A caption should let someone reading only the figures understand the finding.
Three parts: **what is shown, the denominator, and the reading**.

> **Figure 1.** Pass rate with reasoning disabled (left bar) and enabled (right)
> for each difficulty tier, with 95% bootstrap confidence intervals over
> problems. Sample sizes shown above each pair. **The effect of reasoning is
> concentrated in the LiveCodeBench medium and hard tiers; on HumanEval+ and
> MBPP+ both arms exceed 72% regardless of setting.**

The bolded sentence is what most readers will take away. Write it deliberately.

### Placement

- Reference every figure in the text by number: *"Figure 3 shows…"*.
- **Interpret it in words.** A figure that is not explained is not evidence — the
  reader may see something different from what you intend.
- Place it near its discussion.

---

## Tables

### When a table beats a figure

Use a **table** when the reader needs the exact number (to check you, to cite
you, to reproduce you). Use a **figure** when the reader needs the shape.

Your headline tables:

| Table | Content |
|---|---|
| Roster | 5 models: slug, family, pinned provider, quantization, both prices |
| Coverage | Pool 884 / run 320 / per-arm problem counts / paired 107 |
| Pass rate by tier | off vs on, with `n` for each arm |
| Outcome split | passed / failed / billed-no-answer, with mean reasoning tokens and spend |
| CPC | per configuration, with 95% intervals |
| Frontier | per configuration cost and accuracy, hull vertices marked |
| Gap decomposition | oracle / ceiling / k-NN / insufficiency / estimation error |

### Rules

1. **Every table has an `n` column or an `n` in its caption.**
2. **Consistent precision.** Costs to 5 significant figures ($0.00021), pass
   rates to one decimal (54.2%). Do not switch mid-table.
3. **Mark what is not established.** If two rows' intervals overlap, say so in
   the caption rather than letting the ordering imply a finding.
4. **Units in the header**, not in every cell: `cost ($/problem)`.

---

## Citations

### The three jobs

1. **Credit** — someone else's idea, marked as theirs.
2. **Support** — a claim you did not verify yourself.
3. **Positioning** — showing where your work sits.

Job 3 is the one that matters most in Chapter 2, and it is where you must be
generous.

### What you must cite, and why

| Claim | Cite | Why |
|---|---|---|
| Convex-hull evaluation of routers | RouterBench | Shows the hull baseline is standard practice, not something you invented |
| The k-NN bound | Cover & Hart (1967) | Classical |
| Routing collapse | *When Routing Collapses* (Feb 2026) | Names the phenomenon you then reproduce |
| Joint model + reasoning allocation | Route-To-Reason (May 2025) | Predates your proposal and occupies part of the claimed gap |
| Training-free adaptive thinking | DART (Jun 2026) | Nearest on the training-free angle |
| Code routing with released cost data | Agent-as-a-Router / CodeRouterBench (Jun 2026) | **The closest prior work.** Must be cited |
| Reasoning non-termination | ThoughtTerminator, SelfBudgeter, RecurGuard | You are not novel on the phenomenon |
| Backend variance | *The Silent Hyperparameter* (May 2026) | Shows your validity finding is part of a real problem |

⚠️ **Two honesty obligations.**

**First:** your own notes record that these assessments rest on *"search
summaries and PDF extraction, not full reads"*, and that *"existence and rough
scope are reliable; precise claims are not."*

> **You must read Route-To-Reason, Agent-as-a-Router and HRBench in full before
> submission.** Writing "X does not do Y" about a paper you have skimmed is the
> fastest way to be corrected in a viva by someone who has read it.

**Second:** cite the works that threaten your novelty **prominently**, not in a
footnote. An examiner who finds Agent-as-a-Router and sees you engaged with it
carefully reads you as current. One who finds it absent reads everything else
more sceptically.

### Style

- Pick one style (numeric `[12]` or author–year) and never mix.
- **Never cite something you have not opened.** Citation chains propagate errors.
- Cite the *published* version where one exists.
- If you rely on a dataset, cite the dataset, not just the paper.

---

## The consistency check before submission

Numbers drift between drafts. Grep for them:

```bash
cd ~/thesis
grep -rn '1,373\|1,280\|\$5\.24\|\$5\.25\|320 problems\|884\|54\.2\|24\.9\|13\.8\|305' \
  THESIS.md README.md docs/ | head -40
```

Then check the same values in your `.docx`. `CLAUDE.md` §1 requires this for the
repository; **do it for the thesis document too.**

Three specific traps:

- **$5.24 vs $5.25.** $5.24 is the cost of the generations; $5.25 is total spend
  including day-1 probes. **Pick which one each sentence means and be
  consistent.**
- **The saturation counts changed as grading completed** — an earlier figure of
  84/116/120 was superseded by **81/98/141**. Make sure only the later numbers
  appear.
- **LiveCodeBench style counts.** `docx-revisions.md` item 7 quotes **112 stdin /
  63 functional**, which is the v6-only split. The pool you actually used is
  v5+v6: **217 stdin / 125 functional of 342.** Use the pool figures.

---

## Do this

**1. Regenerate the figures and write their captions.**

```bash
uv run python scripts/make_figures.py && open data/figures/
```

For each, write the three-part caption. Test the bolded reading sentence on
someone who has not read the thesis.

**2. Build the citation table.** One row per work: what it does, what it does
not, **and whether you have read it in full**. The unread ones are your reading
list.

**3. Run the consistency grep** above and fix anything inconsistent, in the
repository *and* in the `.docx`.

**4. Do the figures-only test.** Show someone the four figures with captions and
nothing else. Ask what the thesis found. If they can tell you, the figures are
carrying their weight.

---

## Check yourself

1. What is the test for whether a figure earns its place?
2. Why do your figures have error bars, and why do the axes start at zero?
3. What are the three parts of a caption?
4. When is a table better than a figure?
5. Why must works that threaten your novelty be cited prominently?
6. What reading do you still owe, and why does it matter specifically?
7. Name two number-consistency traps in this project.

<details>
<summary>Answers</summary>

1. Can you state the single claim it supports in one sentence? If not, it is
   decoration.
2. Error bars because a bare chart of these numbers would imply precision the
   data lacks — five CPC pairs overlap. Zero-based axes because truncating an
   axis on a proportion exaggerates differences.
3. What is shown; the denominator; and the reading — the one-sentence takeaway.
4. When the reader needs the exact number to check, cite or reproduce you. A
   figure is for shape; a table is for values.
5. Because an examiner who finds them absent reads the whole thesis more
   sceptically, whereas careful engagement reads as being current in the field.
6. Full reads of Route-To-Reason, Agent-as-a-Router (CodeRouterBench) and
   HRBench — current assessments rest on summaries, and "X does not do Y" about a
   skimmed paper is the easiest claim to be corrected on.
7. Any two: $5.24 (generations) versus $5.25 (total spend); the superseded
   saturation counts 84/116/120 versus the current 81/98/141; the LiveCodeBench
   style split 112/63 (v6 only) versus 217/125 (the v5+v6 pool actually used).

</details>

---

➡️ Next: [Lesson 39 — The 14 edits owed to your proposal](39-the-docx-edits.md)
