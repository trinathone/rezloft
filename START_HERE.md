# 👋 Start Here — Read This First

## Step 1 — Install Python
Download Python 3.11+ from https://python.org/downloads
✅ Check "Add Python to PATH" during Windows install
Verify: python --version (should show 3.11 or higher)

## Step 2 — Install Dependencies
Open terminal in this folder and run:

```
pip install -r requirements.txt
playwright install chromium
```

(This takes 2-3 minutes — Chromium is ~150MB)

## Step 3 — Run Setup Wizard
```
python setup.py
```

This will ask you:
- Your Dice.com email and password
- Job type (contract / fulltime / both)
- Your keywords (we give you a ChatGPT prompt to generate them)
- Daily application speed (50–400/day)

Setup takes under 3 minutes and configures everything automatically.

## Step 4 — Run the Bot
```
python dice_bot.py
```

⚠️ Keep terminal open while running.
💡 Want 24/7 running? See README.md for Oracle Cloud free setup.

## Having Issues?
Paste this into Claude.ai or ChatGPT:
```
"Help me set up this project: [YOUR GITHUB URL]"
```
The AI will guide you through any errors step by step.
