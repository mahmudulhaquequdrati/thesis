# The CARR course — everything, from zero, to a written thesis

You are reading this because you want to understand your own thesis completely:
what it asks, why that is a real question, how every number was produced, what
every line of code does, and how to turn all of it into a document you can
defend.

This course assumes **nothing**. Not that you know what a token is, not that you
know SQL, not that you know what a confidence interval is, not that you know
what a thesis is supposed to look like. Every one of those is taught here, from
the ground up, in the order you need them.

---

## How this course works

**Four parts, forty lessons, about six weeks at an hour a day.** You can go
faster. You should not go faster on Part 2.

| Part | What it teaches | Lessons | Time |
|---|---|---|---|
| **0. Orientation** | What a thesis is. What *yours* is. | 01 | 1 hour |
| **1. Foundations** | LLMs, tokens, money, benchmarks, grading, SQL, statistics, economics | 02–10 | ~1 week |
| **2. The science** | Every question this thesis asks and every answer it found | 11–20 | ~1 week |
| **3. The code** | All ~2,000 lines, file by file, and the bug each rule prevents | 21–31 | ~2 weeks |
| **4. The writing** | Structure, chapter by chapter drafting, figures, the defence | 32–40 | ~2 weeks |

### Every lesson has the same five sections

1. **In one sentence** — the whole lesson, compressed. Read it first and last.
2. **The idea, from zero** — plain English, with an everyday analogy. No jargon
   introduced without a definition in the same paragraph.
3. **Why it is in *your* thesis** — the specific place this idea appears in your
   work, with the real number attached.
4. **Do this** — something to run or read, and exactly what you should see.
   Nothing in this course costs money.
5. **Check yourself** — questions, with answers at the bottom. If you cannot
   answer them, re-read before moving on. These are the questions an examiner
   asks in different clothes.

### The rules of the course

- **Never skip the "Do this".** Reading about a thing and watching it happen are
  different kinds of knowing. The second one survives a viva.
- **Answer the checks out loud, in your own words.** If you can only answer by
  quoting the lesson, you do not have it yet.
- **Ask me anything, any time.** These files are the spine; I am the tutor. Say
  "explain lesson 14 again but slower" or "why is the denominator 107 and not
  320" and I will go as deep as you need.
- **A lesson a day beats seven in one day.** This material is cumulative.

---

## Before lesson 01 — make the machine work

One command, once. If this passes, everything in the course will run.

```bash
cd ~/thesis
uv sync                    # builds the Python 3.12 environment
uv run pytest -q           # expect: 119 passed
```

If you do not know what `uv` is, that is fine — lesson 21 explains it. For now
it is "the thing that installs the right versions of everything".

---

## What you already have (so you know what you are learning *about*)

Your thesis is **finished as science**. The measuring is done. Nothing in this
course requires spending another cent.

| | |
|---|---|
| Question | *Reasoning models "think" before answering. That thinking is billed but invisible. When is it worth paying for?* |
| Problems measured | **320** (from a pool of 884) |
| Configurations | **10** = 5 models × thinking off/on |
| API calls bought | **1,373**, of which 1,280 graded |
| Total spent | **$5.25** |
| Headline finding | On hard problems, thinking **more than doubles** the pass rate (24.9% → 54.2%). On easy ones it buys almost nothing. |
| What remains | **Prose.** Chapters 1, 2, 8, 9 to write; 14 edits owed to the proposal `.docx`. |

That last row is why this course ends where it does. Part 4 is not theory — it
is you writing the actual document, with me alongside.

---

## The full lesson list

### Part 0 — Orientation

| # | Lesson | One line |
|---|---|---|
| [01](01-what-is-a-thesis.md) | What a thesis is, and what yours is | A thesis is a defended claim, not a project report |

### Part 1 — Foundations *(nothing here is about your thesis yet — it is the vocabulary you need to understand it)*

| # | Lesson | One line |
|---|---|---|
| [02](02-what-is-an-llm.md) | What a language model actually is | Text in, text out, one token at a time |
| [03](03-reasoning-models.md) | Reasoning models and the invisible bill | 392 of 412 tokens you never see |
| [04](04-buying-tokens.md) | How you buy tokens, and who you buy them from | APIs, OpenRouter, and what a price really is |
| [05](05-benchmarks.md) | What a benchmark is | A problem, its tests, and where they come from |
| [06](06-grading-code.md) | What it means to *grade* generated code | pass@1, sandboxes, and why `==` is not enough |
| [07](07-databases-and-sql.md) | Databases and SQL from zero | Tables, SELECT, JOIN, GROUP BY — your whole results section is SQL |
| [08](08-statistics-1.md) | Statistics I — samples, means, denominators | Why "72%" means nothing without an *n* |
| [09](09-statistics-2.md) | Statistics II — uncertainty and the bootstrap | How to say "probably between 82% and 92%" honestly |
| [10](10-economics-of-choice.md) | The economics of choosing | Cost-per-correct, Pareto frontiers, hulls, oracles |

### Part 2 — The science of this thesis *(the heart of the course)*

| # | Lesson | One line |
|---|---|---|
| [11](11-the-question.md) | The question, and why it is real | Three reasons this is not a made-up problem |
| [12](12-the-design.md) | The experimental design | 320 problems × 10 configs, and why each choice was made |
| [13](13-saturation.md) | Finding 1 — most benchmark problems are useless | 141 of 320 can tell configurations apart |
| [14](14-when-thinking-helps.md) | Finding 2 — thinking works, conditionally | Doubles on hard, nothing on easy |
| [15](15-expensive-failure.md) | Finding 3 — expensive failure | 29,584 tokens to return nothing, 15% of all spend |
| [16](16-the-abort-story.md) | Finding 4 — the claim that was refuted | How a token ceiling manufactured a finding |
| [17](17-frontier-and-oracle.md) | Finding 5 — the frontier, the hull, the oracle | 13.8 points is what knowing the problem is worth |
| [18](18-router-collapse.md) | Finding 6 — the router collapsed, and why | A negative result that says which direction to fix |
| [19](19-measurement-validity.md) | Finding 7 — three ways the platform lies | Arguably your strongest chapter |
| [20](20-limitations.md) | What this is *not* | Say it before an examiner does |

### Part 3 — The code, line by line

| # | Lesson | One line |
|---|---|---|
| [21](21-python-and-the-repo.md) | Python, `uv`, and the shape of the repo | How to run anything in this project |
| [22](22-config-and-effort.md) | `models.yaml`, `effort.py`, `cost.py` | The roster, the 10 configs, and tokens → dollars |
| [23](23-providers.md) | `providers/base.py`, `providers/openrouter.py` | The one file that spends money |
| [24](24-extract.md) | `extract.py` | Markdown → runnable Python, and never raising |
| [25](25-verify.md) | `execute/verify.py` — **the most important file** | The grader, the sandbox, and the macOS bug |
| [26](26-benchmarks-code.md) | `benchmarks/livecodebench.py`, `execute/_lcb_runner.py` | The hard tier, and its two execution styles |
| [27](27-database-code.md) | `db.py` | The schema, and `request_hash` — never pay twice |
| [28](28-runner.md) | `experiment.py`, `runner.py` | The cost cap that aborts before spending |
| [29](29-analysis-code.md) | `stats.py`, `analysis.py` | Every number in the thesis |
| [30](30-router-figures.md) | `router.py`, `figures.py` | The router, the decomposition, the four PNGs |
| [31](31-scripts-and-tests.md) | `scripts/`, `tests/` | The tools, and the 119 tests that keep it honest |

### Part 4 — Writing the thesis

| # | Lesson | One line |
|---|---|---|
| [32](32-what-examiners-want.md) | What an examiner is actually looking for | Four things, and none of them is "impressive" |
| [33](33-thesis-structure.md) | The structure, chapter by chapter | Your nine chapters and what goes in each |
| [34](34-writing-ch1-2.md) | Writing Chapter 1 and 2 | Introduction and Background |
| [35](35-writing-ch3-4.md) | Writing Chapter 3 and 4 | Method, and Measurement Validity |
| [36](36-writing-ch5-7.md) | Writing Chapters 5–7 | The three results chapters |
| [37](37-writing-ch8-9.md) | Writing Chapter 8 and 9 | Limitations and Conclusion |
| [38](38-figures-tables-citations.md) | Figures, tables and citations | Making the evidence readable |
| [39](39-the-docx-edits.md) | The 14 edits owed to your proposal | Reconciling what you proposed with what you found |
| [40](40-defending-it.md) | Defending it | Twenty questions you will be asked, and your answers |

---

## The other documents, and when to read them

You do not need these yet. The course tells you when.

| Document | Read it when |
|---|---|
| [START-HERE.md](../START-HERE.md) | Now, if you want the one-hour version first. This course is the slow version of it. |
| [research-framing.md](../research-framing.md) | After lesson 11. It is the science stated compactly. |
| [data-spec.md](../data-spec.md) | During lesson 23. |
| [docx-revisions.md](../docx-revisions.md) | During lesson 39. |
| [codebase-tour.md](../codebase-tour.md) | Optional, during Part 3. ⚠️ Written early; some parts are stale. |
| `THESIS.md` | Throughout. It is the source of truth for status, decisions and risks. |

---

## One thing to hold on to

Your thesis is not the code. The code was a means. **The thesis is the table** —
1,373 rows saying what each model, at each thinking setting, on each problem,
cost and whether it worked. Nobody has published that table. Every rule in the
repository exists to stop it being quietly wrong.

And twice it *was* quietly wrong, and the checks caught it. Those two catches are
in Part 2, lessons 16 and 19, and they are among the best material you have.

➡️ **Start with [lesson 01](01-what-is-a-thesis.md).**
