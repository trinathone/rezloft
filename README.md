# DiceBot — Automated C2C Resume Injector for Dice.com

> **New here? Read [START_HERE.md](START_HERE.md) first.**

> Gets your resume into 8,000+ vendor databases automatically. Let vendors find you.

---

## What It Does

- Logs into your Dice.com account and searches hundreds of keywords from a file you control
- Clicks **Easy Apply** on every matching job — walks through multi-step forms, uploads your resume, submits
- Tracks every application in `applications.csv` and never applies to the same job twice

---

## Who It's For

- **C2C contractors** on the bench who need mass visibility fast
- **Bench sales recruiters** managing candidate pipelines on Dice
- **Independent IT consultants** who want inbound vendor calls instead of cold outreach

If you bill on 1099 or Corp-to-Corp and Dice is part of your sourcing strategy, this automates the grunt work.

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/youruser/dicebot.git
cd dicebot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Set up keywords
cp keywords.example.txt keywords.txt
# Edit keywords.txt — one search term per line

# 3. Configure credentials
cp env.example .env
# Edit .env with your Dice email, password, and resume path

# 4. Run
python dice_bot.py
# Or on Mac (keeps machine awake):
./run.sh
```

---

## Configuration

### `keywords.txt`

One keyword per line. Lines starting with `#` are comments. Blank lines are ignored.
Keywords are cycled **in order** — the bot rotates to the next keyword when the current one is exhausted (3 consecutive pages of already-applied jobs, or 0 results).

```
# keywords.txt example
Python Developer
AWS
Data Engineer
DevOps Engineer
```

Copy `keywords.example.txt` as a starting point — it includes 20 common IT/C2C terms.

> If `keywords.txt` is missing, the bot exits immediately with a clear error message.

---

### `.env`

| Variable | Required | Description |
|---|---|---|
| `DICE_EMAIL` | ✅ | Your Dice.com login email |
| `DICE_PASSWORD` | ✅ | Your Dice.com password |
| `RESUME_PATH` | ✅ | Absolute path to your resume PDF |
| `PROXY` | ❌ | Optional SOCKS5/HTTP proxy (`socks5://user:pass@host:port`) |
| `DEBUG` | ❌ | Set `true` for verbose logging (default: `false`) |

Additional tuning (edit `config.py` directly):

| Setting | Default | Description |
|---|---|---|
| `EASY_APPLY_ONLY` | `True` | Only apply to Easy Apply jobs |
| `JOB_TYPES` | `["fulltime"]` | Filter by job type |
| `REMOTE_ONLY` | `False` | Remote jobs only |
| `JOB_LOCATION` | `""` | Location filter (empty = nationwide) |
| `SLEEP_HOUR_START` | `2` | Bot sleeps after this hour (24h) |
| `SLEEP_HOUR_END` | `3` | Bot wakes at this hour (24h) |
| `BATCH_SIZE` | `(60, 80)` | Apps per batch before a short break |
| `BATCH_BREAK_MINUTES` | `(3, 5)` | Break duration between batches |

---

## How to Run 24/7 Free

[Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) gives you a permanently free ARM VM (4 OCPUs, 24GB RAM) — more than enough.

```bash
# On your Oracle VM (Ubuntu)
sudo apt update && sudo apt install -y python3-pip python3-venv
git clone https://github.com/youruser/dicebot.git && cd dicebot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Run headless in the background (set HEADLESS=True in config.py first)
nohup python dice_bot.py > /dev/null 2>&1 &

# Or with screen so you can detach/reattach
screen -S dicebot
python dice_bot.py
# Ctrl+A D to detach
```

Set `HEADLESS = True` in `config.py` before running on a server (no display available).

---

## Results

Measured over a real 10-day run (April 14–23, 2026):

| Metric | Value |
|---|---|
| Total applications submitted | **8,202** |
| Success rate | **99.76%** |
| Failed applications | 10 |
| Skipped (no Apply button) | 10 |
| Bot detections / CAPTCHAs triggered | **0** |
| Average per day | ~250–300 (recommended safe rate) |

> **⚠️ Running above 300 applications/day is not recommended.** Higher rates increase the risk of account action from Dice. Control throughput via `BATCH_SIZE` and `BATCH_BREAK_MINUTES` in `config.py`.

Applications are logged to `applications.csv` with timestamp, job title, URL, and status.

---

## Known Limitations

- **Dice.com only.** No LinkedIn, ZipRecruiter, Indeed, or other platforms.
- **Easy Apply jobs only.** Jobs that redirect to an external ATS (Workday, Greenhouse, Lever) are skipped — those require form-filling the bot doesn't handle.
- **No resume customization.** Same resume file uploaded to every application.
- **Terms of Service.** Automated job applications violate Dice.com's ToS. Use at your own risk. The bot includes anti-detection measures but no tool can guarantee zero risk of account action.
- **Company and location fields are blank** in `applications.csv` — Dice's search results page doesn't expose them without opening each listing individually (too slow at scale).

---

## Contributing

PRs welcome. Areas that would have the most impact:

- **Multi-platform support** — ZipRecruiter, Indeed Easy Apply
- **Resume variation** — rotate between multiple resume files per keyword category
- **Smarter form filling** — handle common ATS fields (phone, years of experience, sponsorship)
- **Dashboard** — simple web UI over `applications.csv` to track response rates

Open an issue before starting large changes.

---

## License

GPL v3 — Free to use and modify. If you build a paid product from this code, you must open source it too.
