"""Server-side point-buy validation, mirroring the frontend logic in
`frontend/src/lib/creationCalculations.ts` (`spentPoints`) so a malformed
request can't persist an illegal ability spread. Cost table is reference
data (`fixtures/point_buy_costs.json`, also served as-is via
`GET /api/point-buy-costs`); this module is the computation side."""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

ABILITY_KEYS = ("ST", "GE", "KO", "IN", "WE", "CH")


def point_buy_costs() -> dict[int, int]:
    with open(FIXTURES_DIR / "point_buy_costs.json", encoding="utf-8") as f:
        raw: dict[str, int] = json.load(f)
    return {int(score): cost for score, cost in raw.items()}


def spent_points(ability_scores: dict[str, int]) -> int:
    costs = point_buy_costs()
    return sum(costs.get(score, 0) for score in ability_scores.values())
