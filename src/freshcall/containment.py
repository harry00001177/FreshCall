"""L1 explanation check: every numeral in the LLM's output must be a member
of the fact block it was given. One unauthorised number is a failure — zero
tolerance, no partial credit. See CONTEXT.md / DECISIONS.md."""

import math
import re

_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def check_numeral_containment(text: str, fact_block: dict) -> bool:
    """A numeral is allowed if it appears anywhere in the fact block — as a
    numeric value, or embedded in a string value (e.g. an item number
    inside a SKU name like "item 502331"). Both are facts we gave the LLM,
    not numbers it invented."""
    allowed: set[float] = set()
    for v in fact_block.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            allowed.add(float(v))
        elif isinstance(v, str):
            allowed.update(float(m) for m in _NUMBER_PATTERN.findall(v))

    found = [float(m) for m in _NUMBER_PATTERN.findall(text)]
    return all(any(math.isclose(n, a, abs_tol=1e-9) for a in allowed) for n in found)
