import re
from typing import Optional, Tuple, Dict, Any
from app.models.schemas import FactValue, FactValueType, FactContext

SCALE_MULTIPLIERS = {
    'k': 1_000,
    'thousand': 1_000,
    'thousands': 1_000,
    'm': 1_000_000,
    'million': 1_000_000,
    'millions': 1_000_000,
    'mn': 1_000_000,
    'b': 1_000_000_000,
    'billion': 1_000_000_000,
    'billions': 1_000_000_000,
    'bn': 1_000_000_000,
    't': 1_000_000_000_000,
    'trillion': 1_000_000_000_000,
    'trillions': 1_000_000_000_000,
    'crore': 10_000_000,
    'crores': 10_000_000,
    'cr': 10_000_000,
    'lakh': 100_000,
    'lakhs': 100_000,
}

CURRENCY_SYMBOLS = {
    '$': 'USD',
    '€': 'EUR',
    '£': 'GBP',
    '¥': 'JPY',
    '₹': 'INR',
    'rs.': 'INR',
    'rs': 'INR',
    'rupees': 'INR',
    'inr': 'INR',
    'usd': 'USD',
    'eur': 'EUR',
    'gbp': 'GBP',
}

QUALIFIERS = [
    'approximately', 'approx', 'around', 'about', 'roughly',
    'at least', 'no less than', 'minimum',
    'more than', 'over', 'exceeding',
    'at most', 'up to', 'maximum', 'less than', 'under',
    'estimated', 'projected', 'reported', 'expected'
]

def extract_qualification(text: str) -> Tuple[Optional[str], str]:
    """Extracts qualifications (e.g., 'approximately') and returns (qualifier, cleaned_text)."""
    text_lower = text.lower().strip()
    found_qualifier = None
    for q in QUALIFIERS:
        pattern = r'\b' + re.escape(q) + r'\b'
        if re.search(pattern, text_lower):
            found_qualifier = q
            text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
            break
    return found_qualifier, text

def normalize_currency(raw_str: str) -> Optional[str]:
    """Detects currency from symbol or prefix/suffix."""
    raw_lower = raw_str.lower()
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in raw_lower:
            return code
    return None

def normalize_number_value(raw_val: str) -> FactValue:
    """
    Deterministically parses numbers, units, currencies, and multipliers.
    e.g., "$1.2 billion" -> amount: 1200000000.0, unit: "USD", currency: "USD"
    e.g., "₹8,142 Cr" -> amount: 81420000000.0, unit: "INR", currency: "INR"
    e.g., "₹81,415Mn" -> amount: 81415000000.0, unit: "INR", currency: "INR"
    e.g., "740 Mn shipments" -> amount: 740000000.0, unit: "shipments"
    """
    cleaned = raw_val.strip()
    # Strip footnote markers like (1), (1,2), or trailing asterisks/pluses
    cleaned = re.sub(r'\(\d+(?:,\s*\d+)*\)', '', cleaned)
    cleaned = re.sub(r'[*+>~]', '', cleaned).strip()

    currency = normalize_currency(cleaned)

    # Check for accounting negative format: (123) or (₹ 452 Cr) or -(452)
    is_negative = False
    paren_neg_match = re.search(r'\(\s*([$€£¥₹]|Rs\.?|INR)?\s*([\d.,]+)\s*([a-zA-Z%]+)?\s*\)', cleaned)
    if paren_neg_match:
        is_negative = True
        # remove parens for subsequent parsing
        cleaned = cleaned.replace('(', '').replace(')', '').strip()

    # Check for range, e.g. "5,000 to 6,000" or "$1B - $2B"
    range_match = re.search(r'([\d.,]+)\s*(?:-|to)\s*([\d.,]+)\s*([a-zA-Z%]+)?', cleaned, re.IGNORECASE)
    if range_match:
        try:
            num1_str = range_match.group(1).replace(',', '')
            num2_str = range_match.group(2).replace(',', '')
            scale_str = (range_match.group(3) or '').lower()
            multiplier = SCALE_MULTIPLIERS.get(scale_str, 1.0)
            min_val = float(num1_str) * multiplier
            max_val = float(num2_str) * multiplier
            return FactValue(
                type=FactValueType.RANGE,
                raw=raw_val,
                min_amount=min_val,
                max_amount=max_val,
                currency=currency,
                unit=scale_str if scale_str not in SCALE_MULTIPLIERS else currency or 'units'
            )
        except Exception:
            pass

    # Standard single number regex
    pattern = r'([$€£¥₹]|\b(?:USD|EUR|GBP|INR|Rs\.?|Rupees)\b)?\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)\s*([a-zA-Z%]+)?'
    match = re.search(pattern, cleaned, re.IGNORECASE)

    if match:
        curr_part = match.group(1) or ""
        num_part = match.group(2).replace(',', '')
        suffix = (match.group(3) or "").strip().lower()

        try:
            base_amount = float(num_part)
            if is_negative and base_amount > 0:
                base_amount = -base_amount
        except ValueError:
            return FactValue(type=FactValueType.STRING, raw=raw_val)

        multiplier = 1.0
        unit = None

        if suffix in SCALE_MULTIPLIERS:
            multiplier = SCALE_MULTIPLIERS[suffix]
            unit = currency or (normalize_currency(curr_part) if curr_part else None) or "units"
        elif suffix == "%" or "%" in cleaned:
            unit = "%"
        elif suffix:
            unit = suffix

        total_amount = base_amount * multiplier

        # Check if following words indicate scale like "1.2 billion USD" or "8,142 Cr"
        remaining = cleaned[match.end():].strip().lower()
        for scale_word, mult in SCALE_MULTIPLIERS.items():
            if re.search(r'\b' + re.escape(scale_word) + r'\b', remaining):
                if multiplier == 1.0: # avoid double multiplying
                    total_amount = base_amount * mult
                break

        # Check remaining words for unit e.g. "employees", "customers", "shipments", "tonnes"
        unit_match = re.search(
            r'\b(employees|workers|users|customers|people|shares|stores|offices|years|km|miles|tonnes|tons|shipments|parcels|pin-?codes|pincodes|centers|centres|facilities|gateways|fleet|sq\s*ft)\b',
            cleaned,
            re.IGNORECASE
        )
        if unit_match:
            unit = unit_match.group(1).lower().replace('-', '')

        detected_currency = currency or (normalize_currency(curr_part) if curr_part else None)
        if detected_currency and (not unit or unit == "units"):
            unit = detected_currency

        return FactValue(
            type=FactValueType.NUMBER,
            raw=raw_val,
            amount=round(total_amount, 4),
            unit=unit,
            currency=detected_currency
        )

    # If it's a year, e.g. "2018" or "founded in 2012"
    year_match = re.search(r'\b(19\d\d|20\d\d)\b', cleaned)
    if year_match and len(cleaned) <= 10:
        return FactValue(
            type=FactValueType.DATE,
            raw=raw_val,
            amount=float(year_match.group(1)),
            unit="year"
        )

    return FactValue(
        type=FactValueType.STRING,
        raw=raw_val
    )

def normalize_time_context(time_str: Optional[str]) -> Optional[str]:
    """
    Normalizes time strings like:
    - 'FY2024', 'FY 2024', 'Fiscal Year 2024' -> '2024-FY'
    - 'Q1 2025', '2025 Q1' -> '2025-Q1'
    - '2023' -> '2023'
    - 'March 2025' -> '2025-03'
    """
    if not time_str:
        return None

    s = time_str.strip()
    # FY / Fiscal Year match e.g. 'FY24', 'Fiscal 2021', 'Fiscal Year 2024', 'FY 2024'
    fy_match = re.search(r'\b(?:FY|Fiscal\s*Year|Fiscal|Fiscals)\s*(\d{2,4})\b', s, re.IGNORECASE)
    if fy_match:
        yr = fy_match.group(1)
        if len(yr) == 2:
            yr = "20" + yr
        return f"{yr}-FY"

    # Quarter match e.g. 'Q3 FY24', 'Q1 2025', '2025 Q1'
    q_match = re.search(r'\bQ([1-4])\s*(?:FY\s*)?(\d{2,4})\b|\b(\d{4})\s*Q([1-4])\b', s, re.IGNORECASE)
    if q_match:
        if q_match.group(1):
            q, yr = q_match.group(1), q_match.group(2)
            if len(yr) == 2:
                yr = "20" + yr
        else:
            yr, q = q_match.group(3), q_match.group(4)
        return f"{yr}-Q{q}"

    # Month Date Year match e.g. 'March 31, 2024', 'December 31, 2021'
    date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(\d{4})\b', s, re.IGNORECASE)
    if date_match:
        return f"{date_match.group(1)}-FY"

    # Year only match e.g. '2021', '2024'
    yr_match = re.search(r'\b(19\d\d|20\d\d)\b', s)
    if yr_match:
        return yr_match.group(1)

    return s.strip()

def normalize_geography(geo_str: Optional[str]) -> Optional[str]:
    """Canonical geography representation."""
    if not geo_str:
        return None
    g = geo_str.strip().title()
    if g.lower() in ['global', 'worldwide', 'international', 'world']:
        return 'Global'
    return g

def normalize_scope(scope_str: Optional[str]) -> Optional[str]:
    """Canonical scope representation."""
    if not scope_str:
        return None
    sc = scope_str.strip().lower()
    if any(k in sc for k in ['worldwide', 'all employees', 'total', 'global', 'company-wide']):
        return 'All / Global'
    return scope_str.strip()
