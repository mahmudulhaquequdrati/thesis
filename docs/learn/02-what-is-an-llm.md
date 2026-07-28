# Lesson 02 — What a language model actually is

*Part 1 · about 45 minutes · after lesson 01*

---

## In one sentence

> A language model is a machine that, given some text, guesses the next small
> piece of text — and does that over and over until it stops.

---

## The idea, from zero

### The guessing game

Finish this: *"The capital of France is ___"*

You said Paris. You did not look it up; you have seen that pattern so many times
that the answer arrives automatically.

That is the entire mechanism. A language model has read an enormous amount of
text and learned, statistically, what tends to come next. Ask it anything and it
plays the same game: **what piece of text most plausibly follows what I have so
far?**

Then — and this is the part people miss — it **adds its own guess to the text and
guesses again.**

```
"The capital of France is"          → guesses " Paris"
"The capital of France is Paris"    → guesses "."
"The capital of France is Paris."   → guesses "<stop>"
```

That loop is called **generation**. Everything an AI appears to do — reasoning,
writing code, arguing — is that loop running for a while.

### Tokens: the "small pieces"

The model does not work in letters, and not quite in words. It works in
**tokens** — chunks of text of about 3–4 characters on average.

```
"def reverse_string(s):"
 ↓ becomes roughly
["def", " reverse", "_string", "(", "s", "):"]        ← 6 tokens
```

Rough conversions worth memorising, because your whole budget is denominated in
them:

| | |
|---|---|
| 1 token | ~4 characters of English |
| 1 token | ~0.75 of a word |
| 100 tokens | ~75 words, ~half a page of a paragraph |
| 1,000 tokens | ~750 words, ~1.5 pages |

**Why tokens and not words?** Because a fixed vocabulary of ~100,000 word-pieces
covers every language, every typo, and every variable name a programmer ever
invented, without the model ever meeting a word it has no symbol for.

### Why tokens are the only unit that matters here

Because **tokens are the unit of the bill.** You do not pay per question. You do
not pay per second. You pay per token, in and out:

- **Prompt tokens** (also called *input*) — what you send.
- **Completion tokens** (also called *output*) — what it sends back.

And output is far more expensive than input — typically 2–4× per token on the
models in your roster. Look at your own price table:

| model | input $/M tokens | output $/M tokens |
|---|---|---|
| `qwen/qwen3.5-9b` | 0.100 | **0.150** |
| `deepseek/deepseek-v4-flash` | 0.091 | **0.182** |
| `qwen/qwen3.6-35b-a3b` | 0.140 | **1.000** |
| `deepseek/deepseek-v4-pro` | 0.625 | **1.251** |
| `moonshotai/kimi-k2.6` | 0.770 | **3.400** |

*(These are the real prices you paid, from [`config/models.yaml`](../../config/models.yaml).
They are higher than the prices OpenRouter advertises for the same models —
because those headline prices belong to a different, more heavily compressed
version of the model. That gap is a finding, not a mistake, and lesson 19 is
about it.)*

"$/M" means dollars per **million** tokens. So one million output tokens from
Kimi costs $3.40, and from Flash costs $0.182 — an **18.7× spread** for the same
number of tokens.

Hold on to that. Half your thesis is about a token count, and the other half is
about what a token costs.

### The three things you control

When you send a request, you choose:

1. **Which model.** Bigger/newer usually means better and dearer.
2. **The prompt.** The text you send. In your thesis this is *the problem
   statement, verbatim* — deliberately, so you are measuring models rather than
   your own prompt engineering.
3. **Parameters.** Settings that shape the generation. Two matter to you:

   - **`temperature`** — randomness. At `temperature = 0` the model always picks
     its single most likely next token, so the same prompt gives (almost) the
     same answer every time. At higher values it samples more adventurously.
     **Your thesis uses 0.** Two reasons: it halves cost (no need to sample
     repeatedly), and it makes "the cheapest config that solves this problem" a
     *fixed fact* rather than a coin flip.
   - **`max_tokens`** — a ceiling on how much output you will accept. When the
     model hits it, generation is cut off mid-sentence and you are told
     `finish_reason = "length"`. **You pay for everything generated up to the
     cut.** This parameter causes one of your biggest findings — lesson 16.

### What comes back

A response object with two useful halves:

```
content: "def reverse_string(s):\n    return s[::-1]"     ← the text
usage:   { prompt_tokens: 99, completion_tokens: 412, ... } ← the meter
```

**`usage` is where all your cost data comes from.** Every dollar figure in your
thesis is derived from that field. If you remember one implementation fact from
this lesson, make it that one.

---

## Why it is in *your* thesis

Three places, directly.

**1. The unit of analysis.** Your database stores `prompt_tokens`,
`completion_tokens` and `reasoning_tokens` on every single one of the 1,373 API
calls. Not because tokens are interesting in themselves, but because
`tokens × price = dollars`, and dollars are what the thesis is about.

**2. The measured prompt sizes.** On Day 2 you measured how big your prompts
actually are: **median 99 tokens for HumanEval+, 36 for MBPP+**. You had assumed
600. That single measurement re-priced the entire experiment, because it proved
that **input cost is negligible** — effectively 100% of your budget is output
and thinking. That is why the cost model in `carr/cost.py` is 25 lines instead
of something complicated.

**3. `temperature = 0` is a design decision with a reason.** It appears in your
decisions log (THESIS.md §12, 2026-07-25): *"n=1, temperature=0 — halves cost
and makes routing labels deterministic."* An examiner may ask "why didn't you
sample five times per problem and average?" Your answer is that sentence, plus:
five samples would have cost 5× and the budget was $15.

⚠️ **And a caveat you must know:** some thinking endpoints *silently ignore*
`temperature`. Your harness therefore logs `temperature_sent` on every row —
what you asked for, recorded, so that if it was overridden you can at least say
so. That is a small example of a habit that runs through your whole codebase:
**record what you asked for, not just what you got.**

---

## Do this

**1. Watch a real request happen (free — it uses no API key).**

```bash
cd ~/thesis
uv run python scripts/day2_inspect_problems.py 2>/dev/null | head -30
```

This prints benchmark problems — the exact text that gets sent as a prompt. Look
at how short they are. That shortness *is* the finding from point 2 above.

**2. See the token counts on real purchased calls.**

```bash
uv run python scripts/view.py HumanEval/0
```

You get one line per configuration, with tokens and cost. Look for two things:

- the **cost spread** across configurations for the *same* problem
- how much larger the thinking configs' token counts are

Do not worry about the columns you do not recognise. Lesson 03 explains the one
that matters most.

**3. Build the number sense.** In your head:

- A 100-token prompt to Flash at $0.091/M input costs how much?
  → `100 ÷ 1,000,000 × 0.091` = **$0.0000091**. Nine millionths of a dollar.
- A 30,000-token thinking trace from Kimi at $3.40/M output?
  → `30,000 ÷ 1,000,000 × 3.40` = **$0.102**. Ten cents. **11,000× the input.**

That asymmetry is the shape of your entire budget.

---

## Check yourself

1. What is a token, roughly, in characters and in words?
2. Why does the model's own output get fed back into itself?
3. What is `temperature = 0` and why did your thesis choose it?
4. What does `finish_reason = "length"` mean, and do you still pay?
5. Your prompts turned out to be ~99 tokens instead of the assumed 600. Why did
   that change the experiment's cost model so much?
6. Which field of the API response is the source of every dollar in your thesis?

<details>
<summary>Answers</summary>

1. ~4 characters, ~0.75 words. A million tokens is about 750,000 words.
2. Because generation is a loop: the model only ever predicts *one next token*,
   so producing a paragraph means predicting a token, appending it, and
   predicting again from the longer text.
3. It makes the model always take its most likely next token, so output is
   (nearly) deterministic. Chosen because it halves cost versus sampling
   repeatedly, and makes the "cheapest configuration that passes" label a fixed
   fact rather than a random one.
4. The response was cut off at the `max_tokens` ceiling before the model
   finished. **Yes, you pay for every token generated up to the cut** — and you
   may get nothing usable for it. This is the mechanism behind lesson 16.
5. Because it proved input cost is a rounding error: essentially the entire
   budget is output plus thinking tokens. It let the cost model stay simple and
   moved all attention to the output side.
6. `usage` — specifically `prompt_tokens`, `completion_tokens`, and (lesson 03)
   `completion_tokens_details.reasoning_tokens`.

</details>

---

➡️ Next: [Lesson 03 — Reasoning models and the invisible bill](03-reasoning-models.md)
