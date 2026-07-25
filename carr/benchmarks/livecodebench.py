"""LiveCodeBench loader -- the hard tier. Free download, no API calls.

Why this exists: HumanEval+ and MBPP+ saturate. The first real grid cell had
all 10 configs solve HumanEval/0, including every no-reasoning one. If every
problem is solved by the cheapest config, "which config should I use" has the
answer "the cheapest" and RQ4 has nothing to decide. LCB v6 is 80 hard and 52
medium problems against 43 easy, which is the headroom that argument needs.

READ THIS BEFORE CITING LCB AS CONTAMINATION-FREE -- it is not, for us:

    LCB's whole design is release-date filtering: evaluate only on problems
    published after a model's training cutoff. That works when the benchmark
    keeps updating. It stopped. The newest release on HuggingFace is v6, last
    modified 2025-06-05, and its newest problem is dated 2025-04-06. Every
    model on our roster is a 2026 release. There is no post-cutoff window
    available to us, so contamination is UNCONTROLLED here.

    LCB therefore enters this thesis as a DIFFICULTY tier, not as a
    contamination control. `contest_date` is still stored per problem so the
    exposure can be quantified and reported as a limitation.

Format notes, both of which differ from evalplus:

  * Two problem styles. AtCoder problems (112/175) are stdin->stdout programs.
    LeetCode problems (63/175) ship `starter_code` and are graded by calling a
    method. They need genuinely different execution, see carr/execute/verify.py.
  * NO canonical solutions. evalplus ships reference implementations, which is
    what test_canonical_solutions_pass uses to prove the harness works. LCB
    ships none, so that check is replaced by hand-written reference solutions
    for a few problems in tests/test_verify_lcb.py.
"""

from __future__ import annotations

import base64
import json
import pickle
import urllib.request
import zlib
from pathlib import Path

from appdirs import user_cache_dir

CACHE_DIR = Path(user_cache_dir("carr"))

# v6 is the final release. test6.jsonl is the incremental batch it added:
# 175 problems, 2025-01-04 to 2025-04-06. ~134 MB, mostly test cases.
RELEASE = "v6"
FILENAME = "test6.jsonl"
URL = ("https://huggingface.co/datasets/livecodebench/code_generation_lite"
       f"/resolve/main/{FILENAME}")

# Appended to stdin-style problems. The benchmark statement alone does not say
# how the program receives its input, so the task is not well-posed without it.
# It is a constant string, identical across every config, so it cannot confound
# the effort axis -- but it IS a deviation from "send the prompt unmodified"
# (docs/data-spec.md section 2) and is recorded as one.
STDIN_INSTRUCTION = (
    "\n\nRead the input from standard input and write the answer to standard "
    "output. Provide a complete Python program."
)

_CACHE: dict[str, dict] = {}


def _decode_tests(raw: str) -> list[dict]:
    """LCB stores private tests as base64(zlib(pickle(json))). Public are plain."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return json.loads(pickle.loads(zlib.decompress(base64.b64decode(raw.encode()))))


def download(force: bool = False) -> Path:
    """Fetch test6.jsonl into the cache. ~134 MB, free, once."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = CACHE_DIR / FILENAME
    if dest.exists() and not force:
        return dest

    tmp = dest.with_suffix(".part")
    print(f"  downloading LiveCodeBench {RELEASE} (~134 MB, one time)...")
    with urllib.request.urlopen(URL) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)   # atomic, so an interrupted download is never mistaken
    print(f"  cached at {dest}")                          # for a complete one
    return dest


def build_prompt(problem: dict) -> str:
    """Exactly what gets sent to the model, and the same for every config.

    Unlike HumanEval+, an LCB record is a prose problem statement rather than a
    function stub, so *some* framing is unavoidable. It is kept to the minimum
    that makes the task well-posed: the starter class for LeetCode problems, or
    one sentence about stdin/stdout for AtCoder ones.
    """
    body = problem["question_content"]
    starter = (problem.get("starter_code") or "").strip()
    if starter:
        return f"{body}\n\n{starter}"
    return body + STDIN_INSTRUCTION


def get_livecodebench(force_download: bool = False) -> dict[str, dict]:
    """Return {task_id: problem}, task_id like 'LiveCodeBench/abc387_b'.

    Shaped to look like an evalplus record where the fields mean the same
    thing, so callers do not need to branch: `prompt`, `entry_point`,
    `base_input` (public tests) and `plus_input` (private tests).
    """
    if _CACHE and not force_download:
        return _CACHE

    path = download(force=force_download)
    problems: dict[str, dict] = {}

    with open(path) as f:
        for line in f:
            d = json.loads(line)
            public = _decode_tests(d["public_test_cases"])
            private = _decode_tests(d["private_test_cases"])
            starter = (d.get("starter_code") or "").strip()

            problems[f"LiveCodeBench/{d['question_id']}"] = {
                "task_id": f"LiveCodeBench/{d['question_id']}",
                "prompt": build_prompt(d),
                # Functional problems are graded by calling this method on a
                # Solution class; stdin problems have no entry point at all.
                "entry_point": _starter_method(starter) if starter else "",
                "style": "functional" if starter else "stdin",
                "starter_code": starter,
                "base_input": public,      # the examples shown in the statement
                "plus_input": private,     # the hidden ones. Same split as evalplus
                "difficulty": d["difficulty"],
                "platform": d["platform"],
                "contest_date": d["contest_date"][:10],
                "question_title": d["question_title"],
            }

    _CACHE.update(problems)
    return problems


def _starter_method(starter: str) -> str:
    """The method name from a LeetCode starter, e.g. 'class Solution:\\n def f('."""
    for line in starter.splitlines():
        line = line.strip()
        if line.startswith("def "):
            return line[4:].split("(")[0].strip()
    return ""


if __name__ == "__main__":
    import collections

    problems = get_livecodebench()
    diff = collections.Counter(p["difficulty"] for p in problems.values())
    style = collections.Counter(p["style"] for p in problems.values())
    dates = sorted(p["contest_date"] for p in problems.values())
    tests = sorted(len(p["base_input"]) + len(p["plus_input"]) for p in problems.values())

    print(f"  problems      {len(problems)}")
    print(f"  difficulty    {dict(diff)}")
    print(f"  style         {dict(style)}")
    print(f"  contest_date  {dates[0]} -> {dates[-1]}")
    print(f"  tests/problem min {tests[0]}  median {tests[len(tests) // 2]}  max {tests[-1]}")
    example = next(iter(problems.values()))
    print(f"\n  example {example['task_id']}  ({example['difficulty']}, {example['style']})")
    print("  " + example["prompt"][:300].replace("\n", "\n  "))
