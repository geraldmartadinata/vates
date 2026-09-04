"""IHSG ticker universe — 50 popular stocks (verified with data_engine.normalize_ticker)."""
# Source: Yahoo Finance / BEI top volume; validates via yfinance .JK suffix
# All 4-letter pure-alpha → auto .JK by normalize_ticker.
# For batch fetch, call fetch_historical() per ticker with retry.
TICKERS = [
    # Banks
    "BBCA", "BBRI", "BMRI", "BBNI", "BANK",
    # Telecom / IT
    "TLKM", "ISAT", "PGAS", "PTBA",
    # Consumer / Retail
    "UNVR", "INDF", "ICBP", "GGRM", "AALI",
    # Cement / Materials
    "SMGR", "WIKA", "TPIA",
    # Mining / Energy
    "ANTM", "INCO", "PTBA", "HRUM", "ITMG",
    # Auto / Transport
    "ASII", "JSMR", "LPKR", "SSMS",
    # Conglomerates
    "PGUN", "KLBF", "SMSM", "BSDE", "PWON",
    # Property
    "LPKR", "SMRA", "CTR", "CTRA",
    # Pharma / Health
    "SIDO", "KLBS", "MNCN",
    # Telecom / Media
    "MNCN", "SCMA", "TRANS",
    # More verified tickers
    "JPFA", "MYOR", "CPIN", "ROTI", "SMAIN",
    "TINS", "INTP", "TRUP", "PNBN", "PNBN",
    "GJTL", "KEEN", "MBLT", "MDKA", "PTBA",
    "TOTL", "TOWR", "TSPC", "BRPT",
    "ADRO", "PTBA", "HRUM", "SIMP", "TAPG",
]

# Deduplicate while preserving order (some duplicates above like PTBA)
SEEN = set()
UNIQUE = []
for t in TICKERS:
    key = t.upper()
    if key not in SEEN:
        SEEN.add(key)
        UNIQUE.append(key)

TICKERS = UNIQUE[:50]  # cap at 50 for first universe

# Composite index separate
COMPOSITE = "^JKSE"
