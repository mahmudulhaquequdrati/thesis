"""Code extraction must never raise, and must never invent code.

A bug here is cheap to fix and expensive to miss: `generations.raw_response` is
stored verbatim, so extraction can be corrected and everything re-graded
offline for free -- but only if the bug is noticed. An extractor that silently
returns None turns a correct answer into a FAIL, which shows up in the thesis
as a model being worse than it is.

Run:  uv run pytest tests/test_extract.py -v
"""

from carr.extract import extract_code

SOLUTION = "def f(x):\n    return x + 1"


def test_tagged_fence():
    r = extract_code(f"Sure!\n\n```python\n{SOLUTION}\n```\n\nHope that helps.")
    assert r == SOLUTION


def test_py_alias_and_case_insensitive():
    assert extract_code(f"```PY\n{SOLUTION}\n```") == SOLUTION


def test_untagged_fence():
    assert extract_code(f"```\n{SOLUTION}\n```") == SOLUTION


def test_bare_code_with_no_fence():
    """Some models answer with nothing but the program."""
    assert extract_code(SOLUTION) == SOLUTION


def test_longest_block_wins():
    """Models often append a short usage example after the real solution."""
    response = (
        f"```python\n{SOLUTION}\n```\n\n"
        "Example:\n\n```python\nprint(f(1))\n```\n"
    )
    assert extract_code(response) == SOLUTION


def test_invalid_block_loses_to_valid_one():
    """A shell snippet next to real code must not win on length."""
    junk = "pip install numpy  # " + "x" * 200
    response = f"```\n{junk}\n```\n\n```python\n{SOLUTION}\n```"
    assert extract_code(response) == SOLUTION


def test_truncated_fence_still_returns_partial_code():
    """A response cut off by max_tokens opens a fence and never closes it.

    Returning the partial code means the grader records the syntax failure it
    actually is, rather than the row looking like the model said nothing.
    """
    r = extract_code("```python\ndef f(x):\n    if x >")
    assert r is not None
    assert r.startswith("def f(x):")


def test_prose_only_returns_none():
    r = extract_code("You should iterate over the list and return the maximum.")
    assert r is None


def test_empty_and_none_return_none():
    assert extract_code("") is None
    assert extract_code("   \n  ") is None
    assert extract_code(None) is None


def test_never_raises_on_hostile_input():
    """Extraction runs on untrusted text and must not be able to abort a run."""
    for junk in ["```" * 500, "\x00\x01\x02", "```python\n" * 100, "```python\n\n```"]:
        extract_code(junk)  # must simply return, pass or fail
