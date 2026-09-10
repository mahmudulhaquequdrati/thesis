# Background and related work

Every section here earns its place by being needed later. Readers who know the field can skip to §2.8, which states the gap.

## Language models and tokens

A large language model (LLM) does one thing: given some text, it predicts the next piece of text, repeatedly. The piece is a **token**, roughly three quarters of a word. Everything an LLM reads and writes is counted in tokens, and API providers bill per token. Two counters exist on every call:

- **prompt tokens** (input): what was sent. Cheap.
- **completion tokens** (output): what the model generated. Expensive, typically 2–10× the input price per token.

In this study the input side is nearly irrelevant. Median prompt sizes are 99 tokens for HumanEval+ and 36 for MBPP+ (measured on day 2), and the longest LiveCodeBench prompt is under 4,000 characters. Effectively the whole budget is output.

## Reasoning models and the invisible bill

A **reasoning model** (or "thinking model") generates a long internal monologue before its answer: trying approaches, checking itself, backtracking. Three facts about that monologue underpin the thesis:

1. **It is billed.** It is part of `completion_tokens`.
2. **It is usually hidden.** Providers often return only the final answer, or a summary.
3. **It is reported separately** in the usage object, as `completion_tokens_details.reasoning_tokens`.

The arithmetic trap that follows is that reasoning tokens are a **subset** of completion tokens, not an addition to them:

$$
\text{visible tokens} = \text{completion tokens} - \text{reasoning tokens}.
$$

Adding the two would double-charge every reasoning-enabled call, inflating exactly the configurations under study. The project's cost module exists mostly to make that impossible (Chapter 3.9).

The API exposes an **effort** control. In this study two settings are used: `reasoning: {enabled: false}` and `reasoning: {effort: "high"}`. One (model, effort) pair is a **configuration**. Chapter 4 reports that the graded settings between those two are accepted and ignored by the providers tested, so the axis is binary in practice.

## Buying tokens: aggregators, providers, quantization

The project buys every call through **OpenRouter**, an aggregator: one account, one key, one request format, hundreds of models. The alternative was six accounts and six client adapters on a $15 budget.

The fact most newcomers do not know is that **one model name is not one thing**. An open-weight model is a file of weights anyone can download and serve. The aggregator routes a request to whichever **provider** is serving that model. For `deepseek-v4-pro` there were 18 of them on the snapshot date, charging from $0.87 to $3.48 per million output tokens. The aggregator's model listing reports only the cheapest provider's price, but routing may choose any of them.

**Quantization** is the second half of the problem. Serving a large model cheaply usually means compressing its weights from 16-bit (`bf16`) through 8-bit (`fp8`) to 4-bit (`fp4`). A 4-bit version of a model is measurably worse than the 16-bit version, and the cheapest provider is usually the most compressed. An unpinned evaluation therefore compares an unknown mixture of compressed variants at unrecorded prices. Chapter 3.3 gives the mitigation and Chapter 4 the evidence.

## Code benchmarks, pass@1 and contamination

A **benchmark** is a set of problems, each of which is a prompt plus a set of tests. There is nothing else. This study uses three:

| Benchmark | What it is | Pool |
|---|---|---|
| **HumanEval+** [@chen2021; @liu2023] | 164 hand-written Python function problems, the field's standard easy set, with EvalPlus's extended hidden tests | 164 |
| **MBPP+** [@austin2021; @liu2023] | "Mostly Basic Python Problems", also with extended tests. 378 problems, not the often-quoted 500: the 378 span task ids 2–809, of which 224 lie inside the canonical 11–510 split and 154 outside it | 378 |
| **LiveCodeBench (LCB)** [@jain2024] | Contest problems from AtCoder and LeetCode, labelled easy, medium or hard by the benchmark; releases v5 and v6 loaded | 342 |

**Why the "+".** The original HumanEval ships very few tests per problem, so incorrect solutions pass surprisingly often. EvalPlus generates many more test inputs (HumanEval/0 alone has 1,006) and re-grades. Using the "+" variants makes a pass harder to earn, which strengthens every claim.

**pass@1** is the accuracy metric: did the model's single attempt pass every hidden test? One attempt, no retries, temperature 0. Formally, for a set of calls $S$ with pass indicators $s_i \in \{0, 1\}$,

$$
\text{pass@1}(S) = \frac{1}{|S|}\sum_{i \in S} s_i .
$$

**Contamination** means a benchmark problem was in a model's training data, so the model recalls rather than solves. LiveCodeBench was designed to resist this by dating each problem so that evaluators can filter to problems newer than a model's training cutoff. That design requires the benchmark to keep updating. It has not: its newest problem is dated 2025-04-06, the dataset stopped updating on 2025-06-05, and every model in this roster is a 2026 release. LCB enters this thesis as a **difficulty tier**, not as a contamination control (Chapter 8).

## Grading generated code

The model returns prose with code in it. Two steps produce a pass or a fail: **extraction** (pull the program out of the prose) and **execution** (run it against the tests in a guarded subprocess). Three things make execution harder than it sounds. Generated code must never run unguarded, because a model will eventually emit something destructive. Pass/fail is not string equality: floating-point answers need a tolerance, some MBPP tasks are graded by set equality, and others only assert the output is not `None`. And LiveCodeBench problems come in two styles, programs that read standard input and print output, and methods on a `Solution` class, neither of which is "call a function and compare the return value". Chapter 3.7 describes the grader; Chapter 3.13 describes the bug it caught.

## Routing and adaptive inference

**Routing** means reading an incoming request and choosing which model (or here, which configuration) to send it to before calling any model. The chronology that bounds this thesis:

| Work | What it does | What it does not do |
|---|---|---|
| RouterBench [@hu2024] | 405k outcomes, 11 models, per-query cost; introduces convex-hull evaluation for routers | No effort axis |
| RouteLLM [@ong2024] | Learns a strong/weak router from preference data | Two models, no effort axis, general chat, trained classifier |
| Universal routing [@jitkrittum2025] | Routes to models unseen at training time via correctness vectors | Model-only; not code |
| Budget Guidance [@li2025] | Steers one model's thinking length via an auxiliary predictor over hidden states | Needs white-box access; single model |
| AnytimeReasoner [@qi2025] | RL training so one model performs across thinking budgets | Requires fine-tuning; single model; maths |
| Route-To-Reason [@rtr2025] | Allocates both model and reasoning strategy under a budget | Appears to require training (not read in full; Appendix I) |
| When Routing Collapses [@collapse2026] | Names the degeneracy where a router picks one model everywhere | Diagnostic, not a dataset |
| HRBench [@hrbench2026] | 6 models × 5 benchmarks including code, 12 switching settings | (not read in full) |
| DART [@dart2026] | Training-free adaptive thinking budgets over a text-only API | Must generate draft answers first, so it costs tokens and is not pre-inference |
| LLMRouterBench [@llmrouterbench2026] | 33 models, 21 datasets, 400k instances | Explicitly no effort axis |
| **Agent-as-a-Router / CodeRouterBench** [@aar2026] | Routing for coding tasks, 8 backends, 9,999 tasks × 8 models released with cost | **No effort axis, no reasoning-token column**, closed-weight backends, trained (LoRA) router |

**k-nearest neighbours (k-NN)** is the simplest router: find the $k$ most similar already-measured problems and copy what worked for them. There is no training; it is a lookup. Cover and Hart [@cover1967] bound its asymptotic error at twice the Bayes error, which is the reason to prefer it over anything fancier on sixty problems.

## Overthinking and non-termination

That reasoning models sometimes think far longer than a problem needs, and sometimes fail to stop at all, is documented: Chen et al. [@chen2024overthink] measure it on trivial arithmetic, Sui et al. [@sui2025] survey it, and ThoughtTerminator [@thoughtterminator2025], SelfBudgeter [@selfbudgeter2025] and RecurGuard [@recurguard2026] propose detectors and mitigations. **The phenomenon is not novel here.** What is less covered is its economics: what non-termination costs as a share of a real budget, across a roster whose prices vary by orders of magnitude, on code.

## Measurement validity through aggregators

Two recent sources found the same hazard this thesis reports in Chapter 4. *The Silent Hyperparameter* [@silent2026] quantifies self-hosted backend variance at up to 16.6 percentage points, and a community audit [@lesswrong2026] found 31 of 32 surveyed repositories using OpenRouter without pinning a provider. The gap that remains, and that Chapter 4 fills, is the commercial-aggregator case with reasoning modes and cost attached.

## The gap

Existing work routes between models. Where reasoning effort is considered, it is either trained, or requires generating a draft output, or is not priced. **No published dataset records (model × thinking-mode) outcomes for code generation with reasoning-token cost attached**, and that quantity carries most of the cost of a thinking call. This thesis measures it.
