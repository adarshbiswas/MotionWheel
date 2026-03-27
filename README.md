# IRCTC Tatkal Ticket Booking Automation

Automated IRCTC Tatkal train ticket booking using **Selenium WebDriver** and **Python**.

> **Disclaimer:** This script is for educational/personal use only. It does **NOT** bypass CAPTCHA or OTP — those steps require manual entry. Use responsibly and in compliance with IRCTC's terms of service.

---

## Features

| Feature | Details |
|---|---|
| Auto-login | Fills username & password; pauses for CAPTCHA/OTP |
| Journey pre-fill | From, To, Date, Class, Quota — all from config |
| Train selection | Finds your train by number in the DOM — no manual scrolling |
| Passenger auto-fill | Name, age, gender, berth, food — supports multiple passengers |
| Tatkal countdown | Triggers search exactly at 10:00 AM |
| Payment selection | Selects IRCTC eWallet; stops before final pay |
| Speed optimisations | Images disabled, `WebDriverWait`, CSS selectors, preloaded browser |
| Multi-instance | Optional flag to open parallel browser windows |
| CLI overrides | Override config values from the command line |
| Logging | Full log files saved under `logs/` |

---

## Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **Google Chrome** — latest stable version
- **ChromeDriver** — managed automatically by `webdriver-manager`

---

## Setup

### 1. Clone / download the project

```
irctc_automation/
├── irctc_bot.py        # Main automation script
├── config.json         # Your booking configuration
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── logs/               # Created automatically at runtime
```

### 2. Create a virtual environment (recommended)

```bash
cd irctc_automation
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `selenium` — browser automation
- `webdriver-manager` — auto-downloads the correct ChromeDriver

### 4. Configure `config.json`

Open `config.json` and fill in your details:

```jsonc
{
    "login": {
        "username": "YOUR_IRCTC_USERNAME",   // ← Replace
        "password": "YOUR_IRCTC_PASSWORD"    // ← Replace
    },
    "journey": {
        "from_station": "NDLS - NEW DELHI",
        "to_station": "HWH - HOWRAH JN",
        "journey_date": "28/03/2026",        // DD/MM/YYYY
        "class": "3A",                       // See codes below
        "quota": "TQ",                       // TQ = Tatkal
        "train_number": "12301"
    },
    "passengers": [ ... ],                   // Add your passengers
    ...
}
```

#### Class codes

| Code | Class |
|------|-------|
| `1A` | First AC |
| `2A` | AC 2-Tier |
| `3A` | AC 3-Tier |
| `3E` | AC 3-Economy |
| `SL` | Sleeper |
| `CC` | AC Chair Car |
| `2S` | Second Sitting |

#### Quota codes

| Code | Quota |
|------|-------|
| `GN` | General |
| `TQ` | Tatkal |
| `PT` | Premium Tatkal |

---

## Usage

### Basic run (uses config.json)

```bash
python irctc_bot.py
```

### Override values from CLI

```bash
python irctc_bot.py --date 30/03/2026 --train 12302 --cls 2A
python irctc_bot.py --fromst "BCT - MUMBAI CENTRAL" --to "NDLS - NEW DELHI"
python irctc_bot.py --quota GN
```

### Multiple browser instances

```bash
python irctc_bot.py --multi --instances 3
```

### All CLI options

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to config file (default: `config.json`) |
| `--date DD/MM/YYYY` | Override journey date |
| `--train NUMBER` | Override train number |
| `--fromst STATION` | Override from station |
| `--to STATION` | Override to station |
| `--cls CODE` | Override class (`1A`, `2A`, `3A`, `SL`, etc.) |
| `--quota CODE` | Override quota (`GN`, `TQ`, `PT`) |
| `--multi` | Launch multiple browser windows |
| `--instances N` | Number of instances (default: 2) |

---

## How It Works — Step by Step

```
1. Browser launches (optimised Chrome)
     ↓
2. IRCTC website opens
     ↓
3. Username + password auto-filled
     ↓
4. ⏸ YOU solve CAPTCHA + enter OTP + click Sign In
     ↓
5. Script detects successful login, resumes
     ↓
6. Journey details auto-filled (from/to/date/class/quota)
     ↓
7. ⏳ Countdown timer waits until Tatkal time (10:00 AM)
     ↓
8. Search button clicked instantly
     ↓
9. Your train found by number — class selected — "Book Now" clicked
     ↓
10. Passenger details auto-filled (all passengers)
      ↓
11. Insurance / auto-upgrade toggled per config
      ↓
12. Proceeds to payment page
      ↓
13. IRCTC eWallet selected
      ↓
14. 🛑 STOPS — you confirm and pay manually
```

---

## Speed Tips for Tatkal

1. **Pre-load the browser** — set `preload_time` to `"09:58:00"` so the browser is ready.
2. **Disable images** — already enabled by default in config (`disable_images: true`).
3. **Use a Chrome profile** — set `user_data_dir` in config to reuse cookies and avoid re-login.
4. **Fast internet** — use a wired connection if possible.
5. **Multiple instances** — use `--multi` to open 2–3 windows simultaneously.
6. **Pre-fill everything** — ensure `config.json` has all correct values before Tatkal time.

---

## Manual Intervention Points

The script intentionally pauses at these points:

| Step | Why |
|------|-----|
| CAPTCHA entry | IRCTC requires visual CAPTCHA — cannot be automated |
| OTP entry | Mobile OTP verification |
| Final payment | Safety — you review amount and click Pay |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Chrome doesn't launch | Ensure Chrome is installed and up to date |
| ChromeDriver version mismatch | `webdriver-manager` should handle this automatically; try `pip install --upgrade webdriver-manager` |
| Element not found errors | IRCTC may have changed their DOM; check the CSS selectors in the script |
| Login times out | You have 5 minutes to complete CAPTCHA + OTP |
| Train not found | Verify train number and date in config; ensure the train runs on that day |
| Payment page issues | Payment gateway varies; you may need to select method manually |

---

## Project Structure

```
irctc_automation/
├── irctc_bot.py         # Main script with modular functions:
│                        #   login()
│                        #   fill_journey_details()
│                        #   search_and_select_train()
│                        #   fill_passengers()
│                        #   proceed_to_payment()
├── config.json          # All dynamic inputs (credentials, journey, passengers)
├── requirements.txt     # Python dependencies
├── README.md            # Documentation
└── logs/                # Auto-created log files (one per run)
    └── irctc_20260327_095800.log
```

---

## Security Notes

- **Credentials** are stored in `config.json` — keep this file private.
- Add `config.json` to `.gitignore` if using version control.
- The script does **not** transmit your data anywhere.
- CAPTCHA is never bypassed — full compliance with IRCTC rules.

---

## License

This project is provided **as-is** for educational purposes. The author is not responsible for any misuse or issues arising from its use. Always comply with IRCTC's terms of service.
