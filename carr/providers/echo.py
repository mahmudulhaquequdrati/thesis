"""A free, offline, deterministic stand-in for a real model.

Why this exists: the pipeline -- extraction, grading, storage, both viewers --
needs to be exercised end to end before the pilot spends money. Every component
downstream of the API call is real here. Only the API call is faked.

**This module imports no HTTP client.** That is the $0 guarantee, enforced by
what is importable rather than by a flag someone can forget to pass.

Responses are built from evalplus's canonical solution, so grading them is
meaningful rather than noise. In particular, every response in `canonical` mode
must grade PASS -- which turns a seeding run into a mass-scale version of
tests/test_verify.py::test_canonical_solutions_pass, across hundreds of
problems instead of three.

Everything is seeded from (seed, problem_id, config label), so the same
command always produces the same dataset. Reproducibility is a graded property
of a thesis (CLAUDE.md section 3).
"""

from __future__ import annotations

import hashlib
import random

from carr.providers.base import Generation, Usage

SEED = 20260726

# Applied to the canonical solution, first match only, to build a near-miss:
# code that looks right and is subtly wrong. This is the failure mode that
# matters, because it is what a weak model actually produces -- and what the
# evalplus "plus" tests exist to catch. tests/test_verify.py's WRONG fixture is
# the same idea by hand, and it scores 846/1006.
_MUTATIONS = [
    ("sorted(", "list("),
    (" <= ", " < "),
    (" >= ", " > "),
    (" != ", " == "),
    (" < ", " <= "),
    (" > ", " >= "),
    ("range(1,", "range("),
    (" + 1", " + 2"),
    (" - 1", " - 2"),
]

_PREAMBLE = (
    "Here is a solution. I iterate over the input and handle the edge cases "
    "described in the docstring.\n\n"
)

_PROSE_ONLY = (
    "To solve this you should iterate over the input, track the best candidate "
    "seen so far, and return it at the end. Watch out for the empty-input case "
    "and for duplicate values, which the docstring implies should be treated as "
    "distinct. The overall complexity is O(n log n) if you sort first, or O(n) "
    "if you can use a hash map instead."
)


def _reference(problem: dict) -> str:
    """The known-good program: prompt + canonical solution.

    Concatenation is how evalplus itself builds ground truth. It works for both
    datasets: HumanEval+'s canonical_solution is a function body that continues
    the prompt, and MBPP+'s prompt is a docstring literal that a whole function
    definition can legally follow.
    """
    return problem["prompt"] + problem["canonical_solution"]


def _mutate(code: str, entry_point: str) -> tuple[str, str]:
    """Return (mutated_code, mode). Falls back to a stub if nothing matches.

    The fallback SHADOWS the entry point with a do-nothing definition at module
    level rather than editing the body. An earlier version appended an indented
    `return None`, which Python attached to the end of the real function where
    it was unreachable -- so the row was labelled a failure mode and quietly
    graded PASS. A mock that mislabels is the same class of bug as a grader
    that mislabels, so it gets the same treatment: make it structurally
    impossible rather than probably fine.
    """
    for needle, replacement in _MUTATIONS:
        if needle in code:
            return code.replace(needle, replacement, 1), "near_miss"
    return (
        f"{code}\n\ndef {entry_point}(*args, **kwargs):\n    return None\n",
        "stub",
    )


def _pass_propensity(config, tier: float) -> float:
    """How often this config should produce correct code.

    Not a claim about reality -- it is a shape, chosen so the seeded dataset has
    a visible cost-vs-accuracy gradient for the viewers to show. Real numbers
    come from the pilot. `tier` is the config's position in the cheapest-first
    ordering, normalised to 0..1.
    """
    p = 0.34 + (0.28 if config.thinking else 0.0) + 0.22 * tier
    return min(p, 0.92)


class EchoProvider:
    """Deterministic fake backend. Costs nothing and touches no network."""

    name = "echo"

    def __init__(self, problems: dict[str, dict], n_configs: int = 9,
                 seed: int = SEED):
        self._problems = problems
        self._n_configs = max(1, n_configs)
        self._seed = seed

    def _rng(self, problem_id: str, config_label: str) -> random.Random:
        key = f"{self._seed}\x00{problem_id}\x00{config_label}".encode()
        return random.Random(int.from_bytes(hashlib.sha256(key).digest()[:8], "big"))

    def complete(self, prompt: str, config, *, problem_id: str,
                 max_tokens: int = 4096, temperature: float = 0.0) -> Generation:
        problem = self._problems[problem_id]
        rng = self._rng(problem_id, config.label)

        tier = getattr(config, "tier_index", 0) / max(1, self._n_configs - 1)
        p_pass = _pass_propensity(config, tier)

        roll = rng.random()
        if roll < p_pass:
            mode = "canonical"
        elif roll < p_pass + 0.62 * (1 - p_pass):
            mode = "near_miss"
        elif roll < p_pass + 0.78 * (1 - p_pass):
            mode = "truncated"
        elif roll < p_pass + 0.93 * (1 - p_pass):
            mode = "prose_only"
        else:
            mode = "error"

        if mode == "error":
            return Generation(
                error="mock: upstream returned 502",
                latency_ms=rng.randint(200, 900),
                is_mock=True,
                mock_mode=mode,
                provider_gen_id=f"mock-{rng.getrandbits(48):012x}",
            )

        reference = _reference(problem)

        if mode == "canonical":
            body = reference
        elif mode == "near_miss":
            body, mode = _mutate(reference, problem["entry_point"])
        elif mode == "truncated":
            # Cut mid-body, the way a max_tokens ceiling actually cuts: the
            # fence is opened and never closed. carr/extract.py must still
            # recover the partial code so it is graded as broken, not as absent.
            cut = max(1, int(len(reference) * 0.55))
            body = reference[:cut]
        else:  # prose_only
            body = None

        if body is None:
            text = _PROSE_ONLY
            finish = "stop"
        elif mode == "truncated":
            text = _PREAMBLE + "```python\n" + body
            finish = "length"
        else:
            text = _PREAMBLE + "```python\n" + body + "\n```\n"
            finish = "stop"

        # chars/4 is the same rough tokeniser docs/data-spec.md already uses for
        # prompt sizing. Good enough for a mock; the pilot measures the truth.
        visible = max(1, len(text) // 4)
        reasoning = 0 if not config.thinking else rng.randint(1800, 4200)

        return Generation(
            raw_response=text,
            usage=Usage(
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=visible + reasoning,
                reasoning_tokens=reasoning,
            ),
            finish_reason=finish,
            # Thinking is slow; the shape matters for the latency column.
            latency_ms=rng.randint(400, 1500) + reasoning * rng.randint(2, 4),
            is_mock=True,
            mock_mode=mode,
            provider_gen_id=f"mock-{rng.getrandbits(48):012x}",
        )
