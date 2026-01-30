import os

# ===== MODE =====
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "false"

# ===== COINDCX API =====
COINDCX_KEY = os.getenv("COINDCX_KEY")
COINDCX_SECRET = os.getenv("COINDCX_SECRET")

# ===== CAPITAL & LEVERAGE =====
CAPITAL_USDT = float(os.getenv("CAPITAL_USDT", 5))   # fixed $5
LEVERAGE = int(os.getenv("LEVERAGE", 5))             # fixed 5x

# ===== RISK SETTINGS =====
TP_PERCENT = 0.04   # 4%
SL_PERCENT = 0.05   # 5%
