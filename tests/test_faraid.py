"""Unit tests for the Faraid calculation engine."""
from fractions import Fraction

import pytest

from app.core.faraid import (
    HEIR_LABELS,
    calculate_distribution,
    validate_heir_keys,
)


def share_of(result, key):
    """Helper: return the share of a given heir key."""
    for e in result.entries:
        if e.key == key:
            return e.share
    return Fraction(0)


def test_wife_and_two_daughters_and_father():
    """Classic: wife 1/8, 2 daughters 2/3, father takes residue."""
    r = calculate_distribution("male", ["wife", "daughter", "daughter", "father"])
    assert r.mode == "normal"
    assert share_of(r, "wife") == Fraction(1, 8)
    assert share_of(r, "daughter") == Fraction(2, 3)
    assert share_of(r, "father") == Fraction(5, 24)
    assert sum(e.share for e in r.entries) == 1


def test_husband_mother_two_full_sisters_awl():
    """Awl case: husband 1/2 + mother 1/6 + 2 sisters 2/3 = 4/3 → reduced."""
    r = calculate_distribution("male", ["husband", "mother", "full_sister", "full_sister"])
    assert r.mode == "awl"
    assert share_of(r, "husband") == Fraction(3, 8)
    assert share_of(r, "mother") == Fraction(1, 8)
    assert share_of(r, "full_sister") == Fraction(1, 2)
    assert sum(e.share for e in r.entries) == 1


def test_son_and_daughter_two_to_one():
    """Son : daughter = 2 : 1."""
    r = calculate_distribution("male", ["son", "daughter"])
    assert share_of(r, "son") == Fraction(2, 3)
    assert share_of(r, "daughter") == Fraction(1, 3)


def test_mother_and_son():
    """Mother 1/6 with child, son takes residue."""
    r = calculate_distribution("male", ["mother", "son"])
    assert share_of(r, "mother") == Fraction(1, 6)
    assert share_of(r, "son") == Fraction(5, 6)


def test_only_daughter_radd():
    """Single daughter: 1/2 fixed, radd returns surplus to her."""
    r = calculate_distribution("male", ["daughter"])
    assert r.mode == "radd"
    assert share_of(r, "daughter") == 1


def test_wife_son_daughter():
    """Wife 1/8, residue split son:daughter 2:1."""
    r = calculate_distribution("male", ["wife", "son", "daughter"])
    assert share_of(r, "wife") == Fraction(1, 8)
    assert share_of(r, "son") == Fraction(7, 12)
    assert share_of(r, "daughter") == Fraction(7, 24)
    assert share_of(r, "son") == 2 * share_of(r, "daughter")


def test_umariyyatan_husband_father_mother():
    """Husband 1/2, mother 1/3 of remainder (1/6), father residue (1/3)."""
    r = calculate_distribution("male", ["husband", "father", "mother"])
    assert share_of(r, "husband") == Fraction(1, 2)
    assert share_of(r, "mother") == Fraction(1, 6)
    assert share_of(r, "father") == Fraction(1, 3)


def test_son_blocks_siblings():
    """A son excludes all siblings and grandparents."""
    r = calculate_distribution(
        "male",
        ["son", "full_brother", "full_sister", "paternal_grandmother", "mother"],
    )
    assert share_of(r, "full_brother") == 0
    assert share_of(r, "full_sister") == 0
    assert share_of(r, "paternal_grandmother") == 0
    assert "full_brother" in r.excluded
    assert share_of(r, "mother") == Fraction(1, 6)


def test_two_daughters_two_thirds():
    """2+ daughters share 2/3, mother 1/6; radd scales both to fill the estate."""
    r = calculate_distribution("male", ["daughter", "daughter", "mother"])
    assert r.mode == "radd"
    assert share_of(r, "daughter") == Fraction(4, 5)
    assert share_of(r, "mother") == Fraction(1, 5)


def test_maternal_siblings_one_sixth_each():
    """Two maternal siblings share 1/3 (1/6 each) + mother 1/6; radd scales."""
    r = calculate_distribution("male", ["maternal_brother", "maternal_sister", "mother"])
    assert r.mode == "radd"
    assert share_of(r, "maternal_brother") == Fraction(1, 3)
    assert share_of(r, "maternal_sister") == Fraction(1, 3)
    assert share_of(r, "mother") == Fraction(1, 3)


def test_counts_parameter():
    """Explicit counts: 3 daughters + mother → 4/5 + 1/5 after radd."""
    r = calculate_distribution("male", ["daughter"], counts={"daughter": 3, "mother": 1})
    assert r.mode == "radd"
    assert share_of(r, "daughter") == Fraction(4, 5)
    assert share_of(r, "mother") == Fraction(1, 5)


def test_grandson_blocks_nephew():
    """A grandson excludes nephews and uncles."""
    r = calculate_distribution("male", ["son_son", "nephew", "paternal_uncle"])
    assert "nephew" in r.excluded
    assert "paternal_uncle" in r.excluded
    assert share_of(r, "son_son") == 1


def test_unknown_heir_raises():
    with pytest.raises(ValueError):
        calculate_distribution("male", ["son", "alien_heir"])


def test_validate_heir_keys():
    assert validate_heir_keys(["son", "daughter", "son"]) == ["son", "daughter"]
    with pytest.raises(ValueError):
        validate_heir_keys(["bogus"])


def test_all_heirs_have_labels():
    from app.core.faraid import HEIR_KEYS

    for key in HEIR_KEYS:
        assert key in HEIR_LABELS


def test_money_amounts_roundtrip():
    """Estate of Rs 1,000,000 with wife+son+daughter."""
    r = calculate_distribution("male", ["wife", "son", "daughter"])
    d = r.to_dict(estate_value=1_000_000)
    total = sum(e["amount"] for e in d["entries"])
    assert abs(total - 1_000_000) < 0.01


def test_son_daughter_with_grandson():
    """Grandson (son's son) is asabah with granddaughter 2:1 when no son."""
    r = calculate_distribution("male", ["son_son", "son_daughter"])
    assert r.mode == "normal"
    assert share_of(r, "son_son") == Fraction(2, 3)
    assert share_of(r, "son_daughter") == Fraction(1, 3)


def test_wife_only_radd():
    r = calculate_distribution("male", ["wife"])
    assert r.mode == "radd"
    assert share_of(r, "wife") == 1
