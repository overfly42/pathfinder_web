from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog of gear/equipment, replacing `items.json`'s flat name/price
    list. `category` is a plain categorization tag (e.g. "weapon", "armor",
    "shield", "gear", "tool", "consumable") — same plain-string convention as
    `BaseFeat.type`/`BaseTrait.area`, mostly not evaluated by any rule logic
    (no attack-bonus computation exists yet), only there so a picker can
    group/filter by it. `price` is in gold pieces; fractional (e.g. 0.01 for
    a torch).

    `ac_bonus`/`max_dex_bonus` (roadmap slice 4) are the exception: real,
    computed fields for category "armor"/"shield" — `ac_bonus` is the flat
    AC bonus while equipped, `max_dex_bonus` (armor only) caps the Dex
    modifier applied to AC while worn. Both null for every other category."""

    __tablename__ = "base_items"

    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    price: Mapped[float] = mapped_column(Float)
    ac_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_dex_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
