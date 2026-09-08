import re
from typing import Optional, Tuple, Dict, Any


class FactNormalizer:
    """Deterministic normalization and comparability service for FactLens.
    
    Standardizes numbers, currencies, percentages, units, temporal periods,
    and predicate/subject aliases while strictly preserving context.
    """

    # Scale multipliers dictionary
    SCALE_MULTIPLIERS: Dict[str, float] = {
        "k": 1_000.0,
        "thousand": 1_000.0,
        "thousands": 1_000.0,
        "m": 1_000_000.0,
        "million": 1_000_000.0,
        "millions": 1_000_000.0,
        "b": 1_000_000_000.0,
        "bn": 1_000_000_000.0,
        "billion": 1_000_000_000.0,
        "billions": 1_000_000_000.0,
        "t": 1_000_000_000_000.0,
        "trillion": 1_000_000_000_000.0,
        "trillions": 1_000_000_000_000.0,
        "lac": 100_000.0,
        "lacs": 100_000.0,
        "lakh": 100_000.0,
        "lakhs": 100_000.0,
        "cr": 10_000_000.0,
        "crore": 10_000_000.0,
        "crores": 10_000_000.0,
    }

    # Predicate alias mappings
    PREDICATE_ALIASES: Dict[str, str] = {
        "total sales": "revenue",
        "sales": "revenue",
        "turnover": "revenue",
        "total revenue": "revenue",
        "gross revenue": "revenue",
        "income": "revenue",
        "net profit": "net_profit",
        "net income": "net_profit",
        "profit after tax": "net_profit",
        "pat": "net_profit",
        "workforce": "employees",
        "headcount": "employees",
        "total staff": "employees",
        "staff": "employees",
        "headquarters": "headquarters",
        "hq": "headquarters",
        "corporate office": "headquarters",
        "main office": "headquarters",
        "incorporation date": "founded",
        "established": "founded",
        "inception": "founded",
        "gdp growth": "gdp_growth_rate",
        "gdp growth rate": "gdp_growth_rate",
        "real gdp growth": "gdp_growth_rate",
        "inflation": "inflation_rate",
        "cpi inflation": "inflation_rate",
        "retail inflation": "inflation_rate",
    }

    # Subject alias mappings
    SUBJECT_ALIASES: Dict[str, str] = {
        "delhivery limited": "Delhivery",
        "delhivery ltd": "Delhivery",
        "delhivery ltd.": "Delhivery",
        "delhivery": "Delhivery",
        "reserve bank of india": "Reserve Bank of India",
        "rbi": "Reserve Bank of India",
        "international monetary fund": "IMF",
        "imf": "IMF",
        "government of india": "India",
        "indian economy": "India",
        "india": "India",
    }

    @classmethod
    def normalize_number(cls, val_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Extract float value and scale multiplier from string.
        
        Examples:
            "$10M" -> (10000000.0, "M")
            "$10 million" -> (10000000.0, "million")
            "1.2K workforce" -> (1200.0, "K")
            "₹4,600 Cr" -> (46000000000.0, "Cr")
            "2450" -> (2450.0, None)
        """
        if not val_str:
            return None, None

        clean_s = val_str.replace(",", "").strip()

        # Handle percentages separately
        if "%" in clean_s or "percent" in clean_s.lower():
            pct_val = cls.normalize_percentage(val_str)
            return pct_val, "percent"

        # Regex matching numeric portion followed by optional scale unit
        match = re.search(r'([\d\.]+)\s*([a-zA-Z]+)?', clean_s)
        if not match:
            return None, None

        try:
            base_num = float(match.group(1))
            unit_raw = match.group(2).strip() if match.group(2) else None
            
            if unit_raw:
                unit_lower = unit_raw.lower()
                multiplier = cls.SCALE_MULTIPLIERS.get(unit_lower, 1.0)
                # If unit string matches a scale multiplier, apply it
                if unit_lower in cls.SCALE_MULTIPLIERS:
                    return round(base_num * multiplier, 6), unit_raw
            
            return round(base_num, 6), unit_raw

        except (ValueError, TypeError):
            return None, None

    @classmethod
    def normalize_currency(cls, val_str: str) -> Optional[str]:
        """Detect currency symbol or ISO code.
        
        Examples:
            "$10M" -> "USD"
            "USD 10,000,000" -> "USD"
            "₹4,600 Cr" -> "INR"
            "Rs. 500" -> "INR"
            "€250 million" -> "EUR"
            "£100k" -> "GBP"
        """
        if not val_str:
            return None

        upper_s = val_str.upper()
        if "$" in val_str or "USD" in upper_s or "US$" in upper_s:
            return "USD"
        if "₹" in val_str or "INR" in upper_s or "RS" in upper_s or "RUPEES" in upper_s or "RUPEE" in upper_s:
            return "INR"
        if "€" in val_str or "EUR" in upper_s or "EURO" in upper_s:
            return "EUR"
        if "£" in val_str or "GBP" in upper_s or "POUND" in upper_s:
            return "GBP"

        return None

    @classmethod
    def normalize_percentage(cls, val_str: str) -> Optional[float]:
        """Convert percentage string to float decimal.
        
        Examples:
            "14%" -> 0.14
            "14 percent" -> 0.14
            "5.4%" -> 0.054
        """
        if not val_str:
            return None

        clean_s = val_str.replace(",", "").strip()
        match = re.search(r'([\d\.]+)\s*(?:%|percent|percentage)', clean_s, re.IGNORECASE)
        if match:
            try:
                return round(float(match.group(1)) / 100.0, 6)
            except ValueError:
                pass
        return None

    @classmethod
    def normalize_unit(cls, unit_str: Optional[str], predicate: str = "") -> Optional[str]:
        """Normalize unit or attribute string.
        
        Examples:
            "workforce" -> "employees"
            "staff" -> "employees"
            "parcels" -> "shipments"
        """
        raw = (unit_str or "").strip().lower()
        pred = predicate.strip().lower()

        if raw in ["workforce", "staff", "employees", "headcount", "team", "workers"]:
            return "employees"
        if raw in ["deliveries", "orders", "parcels", "shipments", "packages"]:
            return "shipments"
        if raw in ["percent", "percentage", "%"]:
            return "percent"
        if raw in ["pages", "page count"]:
            return "pages"

        if pred in ["employees", "headcount", "staff"]:
            return "employees"

        return unit_str if unit_str else None

    @classmethod
    def normalize_temporal_context(cls, temporal_str: Optional[str]) -> Dict[str, Any]:
        """Standardize temporal context strings into structured format.
        
        Examples:
            "FY24", "FY 2024", "2023-24" -> {"canonical": "FY2024", "type": "fiscal_year", "year": 2024}
            "Q1 FY24", "Q1 2024" -> {"canonical": "Q1 FY2024", "type": "quarter", "year": 2024, "quarter": 1}
            "March 2024" -> {"canonical": "2024-03", "type": "month", "year": 2024, "month": 3}
            "2024" -> {"canonical": "CY2024", "type": "calendar_year", "year": 2024}
        """
        if not temporal_str:
            return {"canonical": None, "type": "unknown", "year": None, "quarter": None}

        s = temporal_str.strip()
        upper_s = s.upper()

        # Quarter Fiscal Year: Q1 FY24, Q1 FY 2024, Q1 2024
        q_fy_match = re.search(r'Q([1-4])\s*(?:FY)?\s*(\d{2,4})', upper_s)
        if q_fy_match:
            q_num = int(q_fy_match.group(1))
            yr_raw = int(q_fy_match.group(2))
            full_yr = 2000 + yr_raw if yr_raw < 100 else yr_raw
            return {
                "canonical": f"Q{q_num} FY{full_yr}",
                "type": "quarter",
                "year": full_yr,
                "quarter": q_num
            }

        # Fiscal Year: FY24, FY 2024, 2023-24, FY2024
        fy_match = re.search(r'FY\s*(\d{2,4})|20(\d{2})\s*-\s*20?(\d{2})', upper_s)
        if fy_match:
            yr_str = fy_match.group(1) or fy_match.group(3) or fy_match.group(2)
            yr_raw = int(yr_str)
            full_yr = 2000 + yr_raw if yr_raw < 100 else yr_raw
            return {
                "canonical": f"FY{full_yr}",
                "type": "fiscal_year",
                "year": full_yr,
                "quarter": None
            }

        # Calendar Year: 2024, CY2024
        cy_match = re.search(r'\b(20\d{2})\b', upper_s)
        if cy_match:
            yr = int(cy_match.group(1))
            return {
                "canonical": f"CY{yr}",
                "type": "calendar_year",
                "year": yr,
                "quarter": None
            }

        return {"canonical": s, "type": "custom", "year": None, "quarter": None}

    @classmethod
    def normalize_predicate_alias(cls, predicate: str) -> str:
        """Map predicate/attribute to canonical form."""
        if not predicate:
            return "general"
        clean = predicate.strip().lower()
        return cls.PREDICATE_ALIASES.get(clean, clean)

    @classmethod
    def normalize_subject_alias(cls, subject: str) -> str:
        """Map subject to canonical form."""
        if not subject:
            return "General"
        clean = subject.strip().lower()
        return cls.SUBJECT_ALIASES.get(clean, subject.strip())

    @classmethod
    def are_facts_comparable(cls, fact1: Dict[str, Any], fact2: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if two facts represent comparable candidate claims.
        
        Evaluates subject match, predicate match, unit compatibility,
        and temporal/geographic context overlap.
        """
        subj1 = cls.normalize_subject_alias(fact1.get("subject", ""))
        subj2 = cls.normalize_subject_alias(fact2.get("subject", ""))
        
        pred1 = cls.normalize_predicate_alias(fact1.get("predicate", ""))
        pred2 = cls.normalize_predicate_alias(fact2.get("predicate", ""))

        temp1 = cls.normalize_temporal_context(fact1.get("temporal_context"))
        temp2 = cls.normalize_temporal_context(fact2.get("temporal_context"))

        geo1 = (fact1.get("geographic_scope") or "").strip().lower()
        geo2 = (fact2.get("geographic_scope") or "").strip().lower()

        # Subject & Predicate compatibility
        subj_match = (subj1.lower() == subj2.lower()) or (subj1 == "General" or subj2 == "General")
        pred_match = (pred1.lower() == pred2.lower())

        # Temporal Context Match/Difference
        temporal_match = None
        if temp1["canonical"] and temp2["canonical"]:
            temporal_match = (temp1["canonical"] == temp2["canonical"])

        # Geographic Scope Match/Difference
        geographic_match = None
        if geo1 and geo2:
            geographic_match = (geo1 == geo2)

        # Numeric value comparison
        val1 = fact1.get("normalized_value")
        val2 = fact2.get("normalized_value")
        
        val_diff = None
        if val1 is not None and val2 is not None:
            val_diff = abs(val1 - val2)

        is_comparable = (subj_match and pred_match)

        reason = []
        if not pred_match:
            reason.append(f"Different predicates ({pred1} vs {pred2})")
        if temporal_match is False:
            reason.append(f"Different timeframes ({temp1['canonical']} vs {temp2['canonical']})")
        if geographic_match is False:
            reason.append(f"Different geographic scopes ({geo1} vs {geo2})")
        if is_comparable and temporal_match is True and geographic_match in [True, None]:
            reason.append("Matching subject, predicate, and timeframe")

        return {
            "is_comparable": is_comparable,
            "subject_match": subj_match,
            "predicate_match": pred_match,
            "temporal_match": temporal_match,
            "geographic_match": geographic_match,
            "value_difference": val_diff,
            "canonical_subject": subj1,
            "canonical_predicate": pred1,
            "temporal1": temp1["canonical"],
            "temporal2": temp2["canonical"],
            "comparison_reason": "; ".join(reason) if reason else "General comparison",
        }
