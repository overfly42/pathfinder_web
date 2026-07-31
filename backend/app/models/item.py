from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Identity-only catalog of gear/equipment, replacing `items.json`'s flat
    name/price list. `category` is a plain categorization tag (e.g. "weapon",
    "armor", "shield", "gear", "tool", "consumable") — same plain-string
    convention as `BaseFeat.type`/`BaseTrait.area` — not evaluated by any
    rule logic yet (no AC/attack-bonus computation exists, see roadmap slice
    3 vs. 4), only there so a picker can group/filter by it now instead of
    needing a schema change later. `price` is in gold pieces; fractional
    (e.g. 0.01 for a torch)."""

    __tablename__ = "base_items"

    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    price: Mapped[float] = mapped_column(Float)
