"""Core Faraid (Islamic inheritance) calculation engine.

Implements the classical Sunni (Hanafi-method) rules:

* Fixed shares (Quranic): husband, wife, father, mother, daughters,
  sisters, grandmothers, maternal siblings.
* Hajb: exclusion rules (children exclude siblings; father excludes
  grandparents; etc).
* Awl (proportional reduction when shares exceed the estate).
* Radd (proportional return of surplus to sharers when no asabah exist).
* Asabah (residuary, ordered; 2:1 male:female split within a rank).
* Umariyyatan (mother takes 1/3 of the remainder when spouse+father).

The engine returns exact fractional shares using Python's ``fractions``,
so results are never rounded until the user asks for money amounts.

This is a faithful implementation of the well-known classical rules;
always confirm sensitive estate distributions with a qualified scholar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

# ---------------------------------------------------------------------------
# Heir catalogue
# ---------------------------------------------------------------------------

HEIR_KEYS = (
    "husband",
    "wife",
    "son",
    "daughter",
    "father",
    "mother",
    "paternal_grandfather",
    "paternal_grandmother",
    "maternal_grandmother",
    "full_brother",
    "full_sister",
    "paternal_brother",
    "paternal_sister",
    "maternal_brother",
    "maternal_sister",
    "nephew",  # son of full brother
    "paternal_nephew",  # son of paternal brother
    "paternal_uncle",  # full paternal uncle
    "paternal_uncles_son",  # son of paternal uncle
    "son_son",  # grandson (son's son)
    "son_daughter",  # granddaughter (son's daughter)
    "son_sons_son",  # great-grandson
)

HEIR_LABELS: dict[str, str] = {
    "husband": "Husband",
    "wife": "Wife",
    "son": "Son",
    "daughter": "Daughter",
    "father": "Father",
    "mother": "Mother",
    "paternal_grandfather": "Paternal Grandfather",
    "paternal_grandmother": "Paternal Grandmother",
    "maternal_grandmother": "Maternal Grandmother",
    "full_brother": "Full Brother",
    "full_sister": "Full Sister",
    "paternal_brother": "Paternal Brother (same father)",
    "paternal_sister": "Paternal Sister (same father)",
    "maternal_brother": "Maternal Brother (same mother)",
    "maternal_sister": "Maternal Sister (same mother)",
    "nephew": "Nephew (son of full brother)",
    "paternal_nephew": "Nephew (son of paternal brother)",
    "paternal_uncle": "Paternal Uncle",
    "paternal_uncles_son": "Paternal Uncle's Son",
    "son_son": "Grandson (son's son)",
    "son_daughter": "Granddaughter (son's daughter)",
    "son_sons_son": "Great-Grandson (son's son's son)",
}

GENDER: dict[str, bool] = {
    "husband": False, "wife": True, "son": False, "daughter": True,
    "father": False, "mother": True,
    "paternal_grandfather": False, "paternal_grandmother": True,
    "maternal_grandmother": True,
    "full_brother": False, "full_sister": True,
    "paternal_brother": False, "paternal_sister": True,
    "maternal_brother": False, "maternal_sister": True,
    "nephew": False, "paternal_nephew": False,
    "paternal_uncle": False, "paternal_uncles_son": False,
    "son_son": False, "son_daughter": True, "son_sons_son": False,
}

CHILD_KEYS = {"son", "daughter", "son_son", "son_daughter", "son_sons_son"}
SIBLING_KEYS = {
    "full_brother", "full_sister", "paternal_brother", "paternal_sister",
    "maternal_brother", "maternal_sister",
}


# ---------------------------------------------------------------------------
# Computation structures
# ---------------------------------------------------------------------------


@dataclass
class HeirEntry:
    """A single heir present in the estate, with its computed share."""

    key: str
    label: str
    count: int = 1
    share: Fraction = Fraction(0)
    kind: str = "asabah"  # 'quranic' | 'asabah'

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "count": self.count,
            "share_numerator": self.share.numerator,
            "share_denominator": self.share.denominator,
            "share_decimal": float(self.share),
            "kind": self.kind,
            "is_male": GENDER[self.key],
        }


@dataclass
class CalculationResult:
    """Full, exact result of a distribution."""

    entries: list[HeirEntry] = field(default_factory=list)
    shares_total: Fraction = Fraction(0)
    adjusted_total: Fraction = Fraction(0)  # after awl/radd (== 1)
    mode: str = "normal"  # normal | awl | radd
    excluded: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self, estate_value: float = 0.0) -> dict:
        out = {
            "mode": self.mode,
            "shares_total_n": self.shares_total.numerator,
            "shares_total_d": self.shares_total.denominator,
            "adjusted_total_n": self.adjusted_total.numerator,
            "adjusted_total_d": self.adjusted_total.denominator,
            "excluded": self.excluded,
            "notes": self.notes,
            "entries": [e.to_dict() for e in self.entries],
        }
        if estate_value and estate_value > 0:
            base = Fraction(int(round(estate_value * 100)), 100)
            money_entries = []
            for e in self.entries:
                d = e.to_dict()
                d["amount"] = float(base * e.share)
                d["amount_display"] = _format_money(base * e.share)
                money_entries.append(d)
            out["entries"] = money_entries
        return out


def _format_money(value: Fraction) -> str:
    """Format a fraction as a PKR amount, e.g. 1234.567 -> 'Rs 1,234.57'."""
    rupees = int(value)
    paise = int(round((value - rupees) * 100))
    if paise >= 100:
        rupees += 1
        paise -= 100
    return f"Rs {rupees:,}.{paise:02d}"


# ---------------------------------------------------------------------------
# Hajb (exclusion) rules
# ---------------------------------------------------------------------------


def _apply_exclusions(present: set[str]) -> tuple[set[str], list[str]]:
    """Return (active_heirs, excluded_keys). Pure exclusion logic."""
    active = set(present)
    excluded: list[str] = []

    def remove(key: str) -> None:
        if key in active:
            active.discard(key)
            excluded.append(key)

    # Children exclude siblings and grandparents
    if present & CHILD_KEYS:
        for sib in SIBLING_KEYS:
            remove(sib)
        remove("paternal_grandfather")
        remove("paternal_grandmother")
        remove("maternal_grandmother")

    # Father excludes grandfather
    if "father" in present:
        remove("paternal_grandfather")

    # Mother excludes grandmothers
    if "mother" in present:
        remove("paternal_grandmother")
        remove("maternal_grandmother")

    # Paternal grandfather excludes paternal grandmother (Hanafi)
    if "paternal_grandfather" in active:
        remove("paternal_grandmother")

    # Maternal siblings blocked by father or children
    if "father" in present or present & CHILD_KEYS:
        remove("maternal_brother")
        remove("maternal_sister")

    # Descendants blocked by closer males
    if "son" in present:
        remove("son_son")
        remove("son_daughter")
        remove("son_sons_son")
    if "son_son" in present:
        remove("son_sons_son")

    # Nephews/uncles blocked by sons, brothers
    if present & {"son", "son_son"} or "full_brother" in present or "paternal_brother" in present:
        remove("nephew")
        remove("paternal_nephew")
        remove("paternal_uncle")
        remove("paternal_uncles_son")

    return active, excluded


# ---------------------------------------------------------------------------
# Quranic fixed shares
# ---------------------------------------------------------------------------


def _quranic_shares(active: set[str], counts: dict[str, int]) -> list[tuple[str, Fraction]]:
    """Return list of (heir_key, share_fraction) for fixed-share heirs present."""
    shares: list[tuple[str, Fraction]] = []
    has_children = bool(active & CHILD_KEYS)

    # Spouse
    if "husband" in active:
        shares.append(("husband", Fraction(1, 4) if has_children else Fraction(1, 2)))
    if "wife" in active:
        shares.append(("wife", Fraction(1, 8) if has_children else Fraction(1, 4)))

    # Father
    if "father" in active:
        if has_children:
            shares.append(("father", Fraction(1, 6)))
        # else residuary (asabah)

    # Mother
    if "mother" in active:
        sibling_count = sum(counts.get(k, 0) for k in SIBLING_KEYS if k in active)
        if has_children:
            shares.append(("mother", Fraction(1, 6)))
        elif sibling_count >= 2 and "father" not in active:
            shares.append(("mother", Fraction(1, 6)))
        elif ("husband" in active or "wife" in active) and "father" in active:
            # Umariyyatan: mother takes 1/3 of the remainder after the spouse
            if "husband" in active:
                spouse_share = Fraction(1, 2) if not has_children else Fraction(1, 4)
            else:
                spouse_share = Fraction(1, 4) if not has_children else Fraction(1, 8)
            shares.append(("mother", Fraction(1, 3) * (Fraction(1) - spouse_share)))
        else:
            shares.append(("mother", Fraction(1, 3)))

    # Grandfather
    if "paternal_grandfather" in active:
        if has_children:
            shares.append(("paternal_grandfather", Fraction(1, 6)))
        # else residuary (asabah)

    # Grandmothers
    if "paternal_grandmother" in active:
        shares.append(("paternal_grandmother", Fraction(1, 6)))
    if "maternal_grandmother" in active:
        shares.append(("maternal_grandmother", Fraction(1, 6)))

    # Daughters
    dcount = counts.get("daughter", 0)
    if dcount:
        if "son" in active:
            pass  # asabah with son (2:1)
        elif dcount == 1:
            shares.append(("daughter", Fraction(1, 2)))
        else:
            shares.append(("daughter", Fraction(2, 3)))

    # Granddaughters (son's daughter)
    sd_count = counts.get("son_daughter", 0)
    if sd_count and "son" not in active:
        if "daughter" in active:
            if counts.get("daughter", 0) == 1 and "son_son" not in active:
                shares.append(("son_daughter", Fraction(1, 6)))
        elif "son_son" in active:
            pass  # asabah with grandson (2:1)
        elif sd_count == 1:
            shares.append(("son_daughter", Fraction(1, 2)))
        else:
            shares.append(("son_daughter", Fraction(2, 3)))

    # Full sisters
    fs = counts.get("full_sister", 0)
    if fs:
        if active & {"full_brother", "son", "son_son", "father"}:
            pass  # asabah (with brother) or blocked (by son/father)
        elif active & {"daughter", "son_daughter"}:
            pass  # asabah (tier-2, with daughters)
        elif fs == 1:
            shares.append(("full_sister", Fraction(1, 2)))
        else:
            shares.append(("full_sister", Fraction(2, 3)))

    # Paternal sisters
    ps = counts.get("paternal_sister", 0)
    if ps:
        if active & {"full_brother", "paternal_brother", "son", "son_son", "father"}:
            pass  # asabah or blocked
        elif "full_sister" in active:
            if counts.get("full_sister", 0) == 1 and not (active & {"daughter", "son_daughter"}):
                shares.append(("paternal_sister", Fraction(1, 6)))
        elif active & {"daughter", "son_daughter"}:
            pass  # tier-2 asabah
        elif ps == 1:
            shares.append(("paternal_sister", Fraction(1, 2)))
        else:
            shares.append(("paternal_sister", Fraction(2, 3)))

    # Maternal siblings (1/6 each, or 1/3 shared)
    maternal = [k for k in ("maternal_brother", "maternal_sister") if k in active]
    if maternal:
        if len(maternal) == 1 and counts.get(maternal[0], 1) == 1:
            shares.append((maternal[0], Fraction(1, 6)))
        else:
            total_m = sum(counts.get(k, 1) for k in maternal)
            per = Fraction(1, 3) / total_m
            for k in maternal:
                shares.append((k, per * counts.get(k, 1)))

    return shares


# ---------------------------------------------------------------------------
# Asabah (residuary) logic
# ---------------------------------------------------------------------------

# Tier-1: male asabah in order of priority.
ASABAH_ORDER = [
    "son",
    "son_son",
    "son_sons_son",
    "father",
    "paternal_grandfather",
    "full_brother",
    "paternal_brother",
    "nephew",  # son of full brother
    "paternal_nephew",  # son of paternal brother
    "paternal_uncle",
    "paternal_uncles_son",
]

FEMALE_PAIR = {
    "son": "daughter",
    "son_son": "son_daughter",
    "full_brother": "full_sister",
    "paternal_brother": "paternal_sister",
}


def _tier1_asabah_groups(active: set[str], with_quranic: set[str]) -> list[list[str]]:
    """Ordered list of male-asabah groups; each group pairs a male with his
    female companion. Father/grandfather keep their quranic share AND take
    residue as asabah, so they are never skipped."""
    groups: list[list[str]] = []
    for male_key in ASABAH_ORDER:
        if male_key not in active:
            continue
        if male_key in ("father", "paternal_grandfather"):
            group = [male_key]
        elif male_key in with_quranic:
            continue
        else:
            group = [male_key]
        female_key = FEMALE_PAIR.get(male_key)
        if female_key and female_key in active and female_key not in with_quranic:
            group.append(female_key)
        groups.append(group)
    return groups


def _tier2_female_asabah(active: set[str], with_quranic: set[str]) -> list[str]:
    """Sisters become asabah when daughters are present (no male asabah)."""
    if not (active & {"daughter", "son_daughter"}):
        return []
    out: list[str] = []
    if "full_sister" in active and "full_sister" not in with_quranic:
        out.append("full_sister")
    if "paternal_sister" in active and "paternal_sister" not in with_quranic:
        out.append("paternal_sister")
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def calculate_distribution(
    deceased_gender: str,
    heirs: list[str] | tuple[str, ...],
    counts: dict[str, int] | None = None,
) -> CalculationResult:
    """Compute the estate distribution for the given heirs.

    Args:
        deceased_gender: "male" or "female" (kept for clarity; the share
            rules are identical in the Hanafi method).
        heirs: list of heir keys present (duplicates allowed for count).
        counts: optional map of key -> count. Overrides duplicate counting.

    Returns:
        CalculationResult with exact fractions.
    """
    del deceased_gender  # documented only; rules are gender-neutral here
    counts = counts or {}
    effective: dict[str, int] = {}
    for h in heirs:
        effective[h] = effective.get(h, 0) + 1
    for k, v in counts.items():
        effective[k] = max(effective.get(k, 0), v)

    present = set(effective.keys())
    for h in present:
        if h not in HEIR_LABELS:
            raise ValueError(f"Unknown heir key: {h}")

    active, excluded = _apply_exclusions(present)

    result = CalculationResult()
    result.excluded = excluded
    for key in excluded:
        result.notes.append(f"{HEIR_LABELS[key]} excluded — blocked by a closer heir")

    # 1. Quranic fixed shares
    quranic = _quranic_shares(active, effective)
    share_map: dict[str, Fraction] = {}
    for key, frac in quranic:
        share_map[key] = share_map.get(key, Fraction(0)) + frac

    with_quranic = {k for k, v in share_map.items() if v > 0}

    # 2. Build entries
    tier1 = _tier1_asabah_groups(active, with_quranic)
    tier2 = _tier2_female_asabah(active, with_quranic)

    entries: list[HeirEntry] = []
    for key in sorted(active):
        cnt = effective.get(key, 1)
        label = HEIR_LABELS[key]
        if key in share_map and share_map[key] > 0:
            entries.append(HeirEntry(key=key, label=label, count=cnt,
                                     share=share_map[key], kind="quranic"))
        elif any(key in g for g in tier1) or key in tier2:
            entries.append(HeirEntry(key=key, label=label, count=cnt,
                                     share=Fraction(0), kind="asabah"))

    # 3. Distribute residue
    residue = Fraction(1) - sum(e.share for e in entries)

    def entry_for(key: str) -> HeirEntry | None:
        return next((e for e in entries if e.key == key), None)

    if residue > 0 and tier1:
        group = tier1[0]
        males = [g for g in group if not GENDER[g]]
        females = [g for g in group if GENDER[g]]
        total_m = sum(effective.get(m, 1) for m in males)
        total_f = sum(effective.get(f, 1) for f in females)
        unit = residue / (2 * total_m + total_f)
        for m in males:
            me = entry_for(m)
            me.share = me.share + 2 * unit * effective.get(m, 1)  # type: ignore[union-attr]
        for f in females:
            fe = entry_for(f)
            fe.share = fe.share + unit * effective.get(f, 1)  # type: ignore[union-attr]
        residue = Fraction(0)
    elif residue > 0 and tier2:
        fs_count = effective.get("full_sister", 0)
        ps_count = effective.get("paternal_sister", 0)
        if "full_sister" in tier2 and "paternal_sister" in tier2:
            full_share = residue * Fraction(2, 3) / fs_count
            pat_share = residue * Fraction(1, 3) / ps_count
            entry_for("full_sister").share = full_share  # type: ignore[union-attr]
            entry_for("paternal_sister").share = pat_share  # type: ignore[union-attr]
        elif "full_sister" in tier2:
            entry_for("full_sister").share = residue / fs_count  # type: ignore[union-attr]
        elif "paternal_sister" in tier2:
            entry_for("paternal_sister").share = residue / ps_count  # type: ignore[union-attr]
        residue = Fraction(0)

    # 4. Awl (shares exceed the estate)
    total_now = sum(e.share for e in entries)
    if total_now > 1:
        result.mode = "awl"
        result.shares_total = total_now
        for e in entries:
            e.share = e.share / total_now
        result.adjusted_total = Fraction(1)
        result.notes.append(
            f"Awl applied: fixed shares totalled {total_now.numerator}/{total_now.denominator}, "
            f"so every share was reduced proportionally to fit the estate."
        )
    elif total_now < 1 and not tier1 and not tier2 and entries:
        # 5. Radd (surplus returned to sharers)
        surplus = Fraction(1) - total_now
        result.mode = "radd"
        for e in entries:
            e.share = e.share + surplus * (e.share / total_now)
        result.adjusted_total = Fraction(1)
        result.shares_total = Fraction(1)
        result.notes.append(
            f"Radd applied: no residuary heir, so the surplus "
            f"{surplus.numerator}/{surplus.denominator} was returned to the sharers proportionally. "
            f"(Strict Hanafi practice sends the surplus to the public treasury instead of the spouse; "
            f"this calculator follows the majority view that includes everyone.)"
        )
    else:
        result.adjusted_total = Fraction(1)
        result.shares_total = total_now

    # Ensure every entry carries a positive share
    for e in entries:
        if e.share <= 0:
            e.share = Fraction(0)

    result.entries = sorted(entries, key=lambda e: (-float(e.share), e.label))
    return result


def validate_heir_keys(heirs: list[str]) -> list[str]:
    """Raise ValueError listing unknown keys; returns deduplicated list."""
    unknown = [h for h in heirs if h not in HEIR_LABELS]
    if unknown:
        raise ValueError(f"Unknown heir key(s): {', '.join(unknown)}")
    return list(dict.fromkeys(heirs))
