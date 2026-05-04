import sys

if sys.version_info < (3, 11):
    print("❌ ERROR: Python 3.11+ required. Download from python.org/downloads")
    sys.exit(1)

try:
    import playwright
except ImportError:
    print("❌ ERROR: Run this first: pip install -r requirements.txt")
    sys.exit(1)

import getpass
import os
import re
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"
KEYWORDS_FILE = Path(__file__).parent / "keywords.txt"
CONFIG_FILE = Path(__file__).parent / "config.py"

# ── Speed presets (batch_size, batch_break_minutes) ──────────
SPEED_PRESETS = {
    "1": {"label": "50–100  (Low — very safe, slower results)",    "batch_size": (10, 15),  "break": (8, 12)},
    "2": {"label": "100–200 (Medium — safe, steady results)",      "batch_size": (20, 30),  "break": (6, 10)},
    "3": {"label": "200–300 (High — recommended ✅)",              "batch_size": (60, 80),  "break": (3, 5)},
    "4": {"label": "300–400 (Max — faster but higher visibility)", "batch_size": (80, 100), "break": (2, 3)},
}


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print("Welcome to DiceBot Setup 🤖")
    print("━" * 30)
    print()


def prompt_choice(prompt: str, valid: set) -> str:
    while True:
        val = input(prompt).strip()
        if val in valid:
            return val
        print(f"  Please enter one of: {', '.join(sorted(valid))}")


# ── Step 1 — Credentials ─────────────────────────────────────
def step_credentials():
    print("Step 1/5 — Dice.com Credentials")
    print()

    while True:
        email = input("  Enter your Dice email: ").strip()
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print("  ✅ Format looks good")
            break
        print("  ❌ That doesn't look like a valid email, try again.")

    print()
    while True:
        password = getpass.getpass("  Enter your Dice password: ")
        if password:
            break
        print("  ❌ Password cannot be empty.")

    return email, password


# ── Step 2 — Job Type ─────────────────────────────────────────
def step_job_type():
    print()
    print("Step 2/5 — Job Type Preference")
    print()
    print("  What type of roles are you targeting?")
    print("  [1] Contract / C2C only")
    print("  [2] Full-time only")
    print("  [3] Both")
    print()
    choice = prompt_choice("  Enter choice (1/2/3): ", {"1", "2", "3"})

    mapping = {
        "1": ["contract"],
        "2": ["fulltime"],
        "3": ["contract", "fulltime"],
    }
    labels = {"1": "Contract / C2C", "2": "Full-time only", "3": "Contract + Full-time"}
    return mapping[choice], labels[choice]


# ── Step 3 — Keywords ─────────────────────────────────────────
def step_keywords():
    print()
    print("Step 3/5 — Your Keywords")
    print()
    print('  Enter your target role/skills (e.g. Python, AWS, DevOps)')
    print()
    print("  💡 Not sure what keywords to use? Ask ChatGPT this:")
    print("  ┌─────────────────────────────────────────────────────┐")
    print('  │ "Give me 30 Dice.com job search keywords for a      │')
    print('  │  [YOUR ROLE] with skills in [YOUR SKILLS].          │')
    print('  │  Format: one keyword per line, no bullets."         │')
    print("  └─────────────────────────────────────────────────────┘")
    print()
    print("  Paste your keywords below (one per line, empty line to finish):")
    print()

    keywords = []
    while True:
        line = input("  ").strip()
        if not line:
            if keywords:
                break
            print("  (Enter at least one keyword)")
            continue
        if not line.startswith("#"):
            keywords.append(line)

    return keywords


# ── Step 4 — Speed ────────────────────────────────────────────
def step_speed():
    print()
    print("Step 4/5 — Daily Application Speed")
    print()
    print("  How many applications per day?")
    print("  Recommended: 250 (safe) | Max: 400 | Minimum: 50")
    print()
    for k, v in SPEED_PRESETS.items():
        print(f"  [{k}] {v['label']}")
    print()
    choice = prompt_choice("  Enter choice (1/2/3/4): ", set(SPEED_PRESETS.keys()))
    return choice, SPEED_PRESETS[choice]


# ── Step 5 — Review ───────────────────────────────────────────
def step_review(email, job_label, keywords, speed_label):
    print()
    print("Step 5/5 — Review & Confirm")
    print()
    print(f"  ✅ Email:       {email}")
    print(f"  ✅ Job Type:    {job_label}")
    print(f"  ✅ Keywords:    {len(keywords)} loaded")
    print(f"  ✅ Daily Limit: {speed_label}")
    print()
    choice = prompt_choice("  Save and start? (y/n): ", {"y", "n", "Y", "N"})
    return choice.lower() == "y"


# ── Write files ───────────────────────────────────────────────
def write_env(email: str, password: str):
    lines = []
    existing = {}

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    existing["DICE_EMAIL"] = email
    existing["DICE_PASSWORD"] = password

    for k, v in existing.items():
        lines.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(lines) + "\n")


def write_keywords(keywords: list):
    KEYWORDS_FILE.write_text("\n".join(keywords) + "\n")


def patch_config(job_types: list, batch_size: tuple, batch_break: tuple):
    text = CONFIG_FILE.read_text()

    # Job types
    types_repr = repr(job_types)
    text = re.sub(
        r"^JOB_TYPES\s*=\s*.+$",
        f"JOB_TYPES       = {types_repr}",
        text,
        flags=re.MULTILINE,
    )

    # Batch size
    text = re.sub(
        r"^BATCH_SIZE\s*=\s*.+$",
        f"BATCH_SIZE            = {batch_size}",
        text,
        flags=re.MULTILINE,
    )

    # Batch break minutes
    text = re.sub(
        r"^BATCH_BREAK_MINUTES\s*=\s*.+$",
        f"BATCH_BREAK_MINUTES   = {batch_break}",
        text,
        flags=re.MULTILINE,
    )

    CONFIG_FILE.write_text(text)


# ── Main ──────────────────────────────────────────────────────
def main():
    clear()
    banner()

    email, password = step_credentials()
    job_types, job_label = step_job_type()
    keywords = step_keywords()
    speed_choice, speed_preset = step_speed()
    confirmed = step_review(email, job_label, keywords, speed_preset["label"])

    if not confirmed:
        print()
        print("  Setup cancelled. Run python setup.py again when ready.")
        sys.exit(0)

    write_env(email, password)
    write_keywords(keywords)
    patch_config(job_types, speed_preset["batch_size"], speed_preset["break"])

    print()
    print("━" * 30)
    print("✅ Setup complete! Run:  python dice_bot.py")
    print()
    print("💬 Join the community: https://t.me/+rz7W7lhhUEkwOTM1")
    print("📧 Support: trinath.connect@proton.me")
    print()


if __name__ == "__main__":
    main()
