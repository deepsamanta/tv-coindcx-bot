import os

# ===== MODE =====
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "false"

# ===== COINDCX API =====
COINDCX_KEY = os.getenv("COINDCX_KEY")
COINDCX_SECRET = os.getenv("COINDCX_SECRET")

# ===== TRADING PARAMS =====
LEVERAGE = int(os.getenv("LEVERAGE", 5))
DEFAULT_QTY = float(os.getenv("DEFAULT_QTY", 0.001))

# ===== RISK SETTINGS =====
TP_PERCENT = 0.04   # 4%
SL_PERCENT = 0.05   # 5%
