"""
Bot 1 Configuration — Full Time + Easy Apply, max throughput.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ──────────────────────────────────────────────
DICE_EMAIL    = os.getenv("DICE_EMAIL", "")
DICE_PASSWORD = os.getenv("DICE_PASSWORD", "")

# ── Search Keywords ───────────────────────────────────────────
KEYWORDS_FILE = Path(__file__).parent / "keywords.txt"


def load_keywords() -> list:
    """Load search keywords from keywords.txt in the project root."""
    if not KEYWORDS_FILE.exists():
        print(
            "ERROR: keywords.txt not found. Please create it with one keyword "
            "per line. See keywords.example.txt for reference."
        )
        sys.exit(1)

    keywords = []
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            keywords.append(line)

    if not keywords:
        print(
            "ERROR: keywords.txt is empty or contains only comments. "
            "Please add at least one keyword."
        )
        sys.exit(1)

    return keywords

# ── Only 2 Filters Applied ───────────────────────────────────
EASY_APPLY_ONLY = True
JOB_TYPES       = ["fulltime"]   # fulltime only
REMOTE_ONLY     = False
JOB_LOCATION    = ""             # no location filter — widest net

# ── Speed — tuned for ~60 apps/hour ─────────────────────────
MIN_DELAY             = 1
MAX_DELAY             = 3
PAGE_LOAD_WAIT        = (1, 2)
TYPING_SPEED          = (40, 100)
MAX_CONSECUTIVE_FAILS = 5
BREAK_EVERY_N_APPS    = 10
BREAK_DURATION        = (20, 40)
BATCH_SIZE            = (60, 80)
BATCH_BREAK_MINUTES   = (3, 5)

# ── Sleep Schedule ───────────────────────────────────────────
SLEEP_HOUR_START = 2   # 2am
SLEEP_HOUR_END   = 3   # 3am — only 1 hour break

# ── Browser ──────────────────────────────────────────────────
BROWSER_PROFILE_DIR = Path(__file__).parent / "browser_data"
HEADLESS            = False
PROXY               = os.getenv("PROXY", "")

# ── Logging ──────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "dice_bot.log"
CSV_LOG  = Path(__file__).parent / "applications.csv"
DEBUG    = os.getenv("DEBUG", "false").lower() == "true"
