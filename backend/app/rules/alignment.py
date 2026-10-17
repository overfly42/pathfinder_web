"""Character alignment (roadmap slice 10, step 0b — the Paladin's
"rechtschaffen gut" and the Druide's "any neutral component" restrictions).

Codes are the language-neutral two-letter abbreviations (LG … CE); the
frontend owns the German/English labels. Which alignments a class allows is
data (`BaseClass.allowed_alignments`), this module only knows the code set
and how to check a character's classes against it."""

from collections.abc import Iterable

from ..models import BaseClass

ALIGNMENTS: tuple[str, ...] = ("LG", "NG", "CG", "LN", "N", "CN", "LE", "NE", "CE")


def alignment_conflicts(alignment: str | None, roots: Iterable[BaseClass]) -> list[str]:
    """Names of every root class in `roots` whose `allowed_alignments`
    `alignment` doesn't satisfy. A missing alignment conflicts with every
    restricted class — callers decide whether that matters (creation: yes;
    a legacy character without alignment levelling up: no)."""
    conflicts: list[str] = []
    for root in roots:
        allowed = root.allowed_alignments
        if allowed and alignment not in allowed:
            conflicts.append(root.name)
    return sorted(set(conflicts))
