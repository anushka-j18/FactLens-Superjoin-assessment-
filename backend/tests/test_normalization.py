import pytest
from app.services.normalizer import FactNormalizer


def test_million_vs_m_numeric_normalization():
    """Test '$10M' vs '$10 million' vs 'USD 10,000,000' normalize to 10000000.0 USD."""
    val1, scale1 = FactNormalizer.normalize_number("$10M")
    val2, scale2 = FactNormalizer.normalize_number("$10 million")
    val3, scale3 = FactNormalizer.normalize_number("USD 10,000,000")

    assert val1 == 10_000_000.0
    assert val2 == 10_000_000.0
    assert val3 == 10_000_000.0

    curr1 = FactNormalizer.normalize_currency("$10M")
    curr2 = FactNormalizer.normalize_currency("$10 million")
    curr3 = FactNormalizer.normalize_currency("USD 10,000,000")

    assert curr1 == "USD"
    assert curr2 == "USD"
    assert curr3 == "USD"


def test_thousand_vs_k_unit_normalization():
    """Test '1,200 employees' vs 'workforce of 1.2K' normalize to 1200.0 employees."""
    val1, _ = FactNormalizer.normalize_number("1,200 employees")
    val2, _ = FactNormalizer.normalize_number("1.2K workforce")

    assert val1 == 1200.0
    assert val2 == 1200.0

    unit1 = FactNormalizer.normalize_unit("employees", "workforce")
    unit2 = FactNormalizer.normalize_unit("workforce", "employees")

    assert unit1 == "employees"
    assert unit2 == "employees"


def test_percentage_normalization():
    """Test percentage normalization converts strings to decimal floats."""
    pct1 = FactNormalizer.normalize_percentage("14%")
    pct2 = FactNormalizer.normalize_percentage("14 percent")
    pct3 = FactNormalizer.normalize_percentage("5.4%")

    assert pct1 == 0.14
    assert pct2 == 0.14
    assert pct3 == 0.054


def test_currency_normalization():
    """Test currency symbol and ISO code normalization."""
    assert FactNormalizer.normalize_currency("$10M") == "USD"
    assert FactNormalizer.normalize_currency("USD 10,000,000") == "USD"
    assert FactNormalizer.normalize_currency("₹4,600 Cr") == "INR"
    assert FactNormalizer.normalize_currency("INR 46,000,000,000") == "INR"
    assert FactNormalizer.normalize_currency("Rs. 500") == "INR"
    assert FactNormalizer.normalize_currency("€250 million") == "EUR"
    assert FactNormalizer.normalize_currency("£100k") == "GBP"


def test_date_and_fiscal_period_normalization():
    """Test temporal context standardization (FY24, Q1 FY24, CY2024)."""
    temp1 = FactNormalizer.normalize_temporal_context("FY24")
    temp2 = FactNormalizer.normalize_temporal_context("FY 2024")
    temp3 = FactNormalizer.normalize_temporal_context("Q1 FY24")
    temp4 = FactNormalizer.normalize_temporal_context("2024")

    assert temp1["canonical"] == "FY2024"
    assert temp2["canonical"] == "FY2024"
    assert temp3["canonical"] == "Q1 FY2024"
    assert temp4["canonical"] == "CY2024"


def test_same_value_different_periods_distinctness():
    """Test that facts with identical values in different timeframes remain distinct."""
    fact1 = {
        "subject": "Company",
        "predicate": "revenue",
        "value": "$10M",
        "normalized_value": 10_000_000.0,
        "temporal_context": "FY2024",
        "geographic_scope": "Global",
    }
    fact2 = {
        "subject": "Company",
        "predicate": "revenue",
        "value": "$10M",
        "normalized_value": 10_000_000.0,
        "temporal_context": "Q1 2024",
        "geographic_scope": "Global",
    }

    comp = FactNormalizer.are_facts_comparable(fact1, fact2)
    assert comp["is_comparable"] is True
    assert comp["temporal_match"] is False  # Timeframes differ!
    assert "Different timeframes" in comp["comparison_reason"]


def test_same_value_different_scope_distinctness():
    """Test that facts with identical values in different geographic scopes remain distinct."""
    fact1 = {
        "subject": "Company",
        "predicate": "revenue",
        "value": "$10M",
        "normalized_value": 10_000_000.0,
        "temporal_context": "FY2024",
        "geographic_scope": "North America",
    }
    fact2 = {
        "subject": "Company",
        "predicate": "revenue",
        "value": "$10M",
        "normalized_value": 10_000_000.0,
        "temporal_context": "FY2024",
        "geographic_scope": "Global",
    }

    comp = FactNormalizer.are_facts_comparable(fact1, fact2)
    assert comp["is_comparable"] is True
    assert comp["geographic_match"] is False  # Geographic scopes differ!
    assert "Different geographic scopes" in comp["comparison_reason"]


def test_ambiguous_value_handling():
    """Test handling of ambiguous or non-numeric strings."""
    val, scale = FactNormalizer.normalize_number("active status")
    assert val is None
    assert scale is None

    curr = FactNormalizer.normalize_currency("N/A status")
    assert curr is None

    pct = FactNormalizer.normalize_percentage("No percentage here")
    assert pct is None
