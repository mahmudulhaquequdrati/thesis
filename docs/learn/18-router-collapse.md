# Lesson 18 — Finding 6: the router collapsed, and why

*Part 2 · about 1 hour · after lesson 17*

**This is the chapter you are most nervous about. By the end of this lesson you
should want to write it.**

---

## In one sentence

> The router captured **none** of the 13.8-point prize — and the gap
> decomposition proves the fault was **not** the features, which converts a
> failure into a diagnosis.

---

## The finding

### What was built

A router that, given a *new* problem, predicts which configuration to send it to.
The design constraint was deliberate and it is your novelty claim:

> **The cheapest possible router — no forward pass, no drafts, no hidden states,
> no training.**

So the features are only things you can compute **for free, before calling any
model**:

- difficulty tier
- number of tests
- prompt length

No trial generation (that costs tokens — DART, a competitor, needs draft answers
and is therefore not pre-inference). No model internals (you do not have them —
these are API-served models). No training (that needs labelled data you would
have to buy).

The method is **k-nearest-neighbours**: for a new problem, find the *k* most
similar known problems, and copy whatever configuration was cheapest-and-passing
for them.

Evaluated **leave-one-out**: predict each problem using all the others, never
itself. This matters — evaluating on data you fitted on is the classic way to
report a number that evaporates on contact with reality.

### The result

| | |
|---|---|
| Oracle (cheats) | 98.3% |
| Convex hull (blind mixture) | 65.0% |
| **k-NN router** | **65.0%** |
| **Improvement over the hull** | **+0.0 points** |

The router **collapsed to a single configuration**. It predicts the same answer
for every problem, so it *is* the hull, exactly.

This has a name in the literature — *When Routing Collapses* (Feb 2026) — and you
cited it as a risk in THESIS.md §15.3 **before** it happened. Then it happened,
in your own data.

### Why it collapsed — the decomposition

Here is the part that turns this from a failure into a contribution. The
question is: **whose fault is it?**

There are two candidate culprits:

| Candidate | The claim | How to test it |
|---|---|---|
| **The features** | Difficulty, test count and prompt length simply do not contain enough information | Compute the best possible accuracy achievable *from those features alone* |
| **The estimator** | The features are fine; the k-NN method fails to use them | If the ceiling is high but k-NN is low, the method is at fault |

You computed the ceiling — bucket the problems by their feature values, and give
each bucket its best possible configuration:

| | |
|---|---|
| Oracle (knows the answers) | 98.3% |
| **Ceiling from these features alone** | **98.3%** |
| k-NN actually achieves | 65.0% |
| **Feature insufficiency** | **0.0 points** |
| **Estimation error** | **33.3 points** |

> **The features are sufficient. The estimator is not.**

The entire 33.3-point gap is the method's fault, and none of it is the
information's fault. That is a completely different finding from "routing
doesn't work here."

### The mechanism, in one paragraph

Why does k-NN collapse? Because of what it is asked to predict.

The label is *"the cheapest configuration that passes this problem"*. And that
label is **dominated by one configuration** — `flash|off` is the cheapest thing
on the roster, so whenever it passes, it is the answer. It passes often.

A nearest-neighbour vote takes the **modal** (most common) label among the
neighbours. When one label is the majority nearly everywhere, the mode is that
label nearly everywhere. So the router predicts it everywhere, and collapses.

> **The collapse is a property of the *objective*, not the inputs.**

And that immediately names the fix: **use a cost-aware objective instead of
modal-label classification.** Predict *expected cost under each configuration*
and pick the minimiser, rather than predicting the argmin label directly. That
is concrete future work with a direction, not a shrug.

### ⚠️ The caveat you must state

The feature ceiling is **fitted**: 12 buckets over 60 problems, 5 problems per
bucket. With that few problems per bucket, a bucket can hit its optimum by luck.

So **98.3% is an optimistic upper bound, not an achievable target.** It is
recorded in the code as a caveat and it must be in the chapter.

Which weakens the claim to: *the features look sufficient at this sample size;
the estimation error is large and unambiguous.* The second half is the robust
part, and it is the half your conclusion rests on.

### Why a negative result is worth having

Say all four of these, in this order, and the chapter defends itself:

1. **The question was answered.** RQ4 asked whether a training-free router beats
   every fixed strategy. The answer is **no**, measured against the correct and
   deliberately strengthened baseline.
2. **The evaluation was honest.** Leave-one-out. Compared against the hull, not
   against a strawman. Had you compared against "the best single configuration",
   the router would have looked like a success.
3. **The failure was diagnosed.** 0.0 points of feature insufficiency, 33.3 of
   estimation error. Most negative results cannot say which part broke.
4. **The direction is named.** Cost-aware objective, not modal classification.

> *"A negative result that says which direction to fix is worth more than a
> marginal positive one."*

Note point 2 carefully. **A weaker baseline would have produced a positive
result.** You chose the harder comparison and reported the worse outcome. That
choice is the most examiner-visible integrity signal in the entire thesis, and
you should make it explicit rather than hoping it is noticed.

### What this does to your thesis's identity

The proposal's title promised a router. The router adds +0.0 points.

So **the thesis is a measurement study**, and RQ4 is one measured section within
it that reports a negative with a diagnosis. That is `.docx` edit #1 of 14
(lesson 39).

This is not a demotion. Measurement studies are a legitimate and common form of
contribution, and yours has something most routing papers lack: a table nobody
else has, and an honest account of what can and cannot be squeezed from it.

---

## Why it matters for the writing

This section sits at the end of **Chapter 6**, after the oracle establishes the
13.8-point prize. The narrative arc is:

> There is 13.8 points on the table (lesson 17) → here is the cheapest possible
> attempt to claim it → it claims none → and here is precisely why, and what
> would work instead.

Presentation rules:

- **Do not apologise.** State the result flatly and move to the decomposition.
- **Lead with the decomposition table.** It is the contribution; the 65.0% is
  just the setup.
- **State the caveat in the same section**, not in Chapter 8.
- **End with the named fix.** A negative result that ends with a direction reads
  as a contribution; one that ends with "further work is needed" reads as a
  shrug.

---

## Do this

**1. See the collapse and the decomposition.**

```bash
cd ~/thesis
uv run python scripts/results.py | sed -n '/RQ4b/,/RQ3/p'
```

**2. Read the tests that keep the evaluation honest.**

```bash
uv run pytest tests/test_router.py -v
```

Ten tests. Some check leave-one-out honesty (that a problem never sees itself);
others check the decomposition assigns blame correctly. **Read the test names —
they are a list of the ways this evaluation could have lied to you.**

**3. See the dominance of the label yourself.**

```sql
SELECT config_id, COUNT(*) AS times_cheapest FROM (
  SELECT g.problem_id, g.config_id,
         ROW_NUMBER() OVER (PARTITION BY g.problem_id ORDER BY g.cost_actual_usd) AS rank_
  FROM generations g JOIN results r USING (gen_id)
  WHERE g.is_mock = 0 AND r.passed = 1
) WHERE rank_ = 1 GROUP BY config_id ORDER BY times_cheapest DESC;
```

One configuration dominates the list. **That skew is the collapse, visible in raw
data.** A method that predicts the most common label will predict that one
almost everywhere — and be right often enough to look fine, while adding
nothing.

**4. Practise saying it without flinching.**

> *"The router adds nothing over the convex hull. The decomposition shows the
> features are sufficient and the estimator is at fault, because the
> cheapest-passing label is dominated by one configuration and a nearest-neighbour
> vote returns the modal label. The fix is a cost-aware objective. I evaluated
> against the hull rather than the best single model, which is the harder
> baseline — against the easier one this would have looked like a success."*

Say it until it is flat and confident. It is a good paragraph.

---

## Check yourself

1. What makes this "the cheapest possible router", and why is that the novelty
   claim?
2. What is leave-one-out evaluation and why does it matter?
3. What did the router achieve, and against what baseline?
4. Explain the gap decomposition: what are the two candidates and what did the
   numbers say?
5. Why does k-NN collapse? What is the fix?
6. What is the caveat on the feature ceiling, and what does it leave intact?
7. Why would a weaker baseline have made this look like a success, and why does
   that matter?

<details>
<summary>Answers</summary>

1. It uses only free, pre-inference features — difficulty tier, test count,
   prompt length — with no forward pass, no draft generations, no model
   internals and no training. It is the novelty claim because closer prior work
   either trains (Route-To-Reason, CodeRouterBench's LoRA) or must generate
   drafts (DART).
2. Predicting each problem using all the others but never itself. Without it you
   would be evaluating on data you fitted on, and the reported accuracy would
   not survive new data.
3. 65.0% — **exactly** the convex hull, so +0.0 points. It collapsed to
   predicting a single configuration everywhere.
4. Candidates: insufficient features, or an inadequate estimator. The ceiling
   achievable from those features alone is 98.3%, matching the oracle, so
   feature insufficiency is 0.0 points and estimation error is 33.3.
5. Because the label "cheapest configuration that passes" is dominated by one
   configuration, and a nearest-neighbour vote returns the modal label — so it
   returns that one everywhere. The fix is a cost-aware objective: predict
   expected cost per configuration and minimise, rather than classifying the
   argmin label.
6. The ceiling is fitted over 12 buckets on 60 problems (5 each), so it is an
   optimistic upper bound rather than an achievable target. What survives is the
   robust half: the estimation error is large and unambiguous.
7. Against "the best single configuration", a mixture-beating router looks good
   almost automatically. Choosing the hull made the result worse and the claim
   honest — and stating that choice explicitly is the clearest integrity signal
   in the thesis.

</details>

---

➡️ Next: [Lesson 19 — Finding 7: three ways the platform lies](19-measurement-validity.md)
