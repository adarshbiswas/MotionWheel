import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright

IRCTC_URL = "https://www.irctc.co.in/nget/train-search"
CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"pw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Safe console handler that won't crash on Unicode chars in Windows
_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
_console.setFormatter(_fmt)

_file = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file.setLevel(logging.INFO)
_file.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger("irctc_playwright_bot")

QUOTA_LABELS = {
    "GN": "GENERAL",
    "TQ": "TATKAL",
    "PT": "PREMIUM TATKAL",
}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def human_pause(page, min_ms: int = 45, max_ms: int = 140):
    page.wait_for_timeout(random.randint(min_ms, max_ms))


def wait_for_ready(page, locator, timeout: int = 8000):
    locator.wait_for(state="visible", timeout=timeout)
    try:
        locator.scroll_into_view_if_needed(timeout=timeout)
    except Exception:
        pass
    # Small settle wait to avoid double-click/race-like behavior on dynamic UI
    human_pause(page, 35, 90)


def human_click(page, locator, timeout: int = 8000):
    wait_for_ready(page, locator, timeout=timeout)

    # Move mouse over element before click (human-like)
    try:
        box = locator.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
            y = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            page.mouse.move(x, y, steps=random.randint(4, 8))
            human_pause(page, 30, 80)
    except Exception:
        pass

    locator.click(timeout=timeout, delay=random.randint(22, 65))
    human_pause(page, 50, 120)


def human_type(page, locator, value: str, timeout: int = 8000, clear_first: bool = True):
    wait_for_ready(page, locator, timeout=timeout)
    human_click(page, locator, timeout=timeout)
    if clear_first:
        try:
            locator.press("Control+A")
            locator.press("Backspace")
        except Exception:
            locator.fill("")
        human_pause(page, 35, 90)

    locator.type(str(value), delay=random.randint(26, 55))
    human_pause(page, 50, 120)

def human_scroll(page):
    import random

    total_scrolls = random.randint(2, 5)

    for _ in range(total_scrolls):
        scroll_amount = random.randint(200, 600)

        page.mouse.wheel(0, scroll_amount)
        page.wait_for_timeout(random.randint(300, 900))

        # small upward correction sometimes
        if random.random() > 0.7:
            page.mouse.wheel(0, -random.randint(100, 300))
            page.wait_for_timeout(random.randint(200, 600))

def login(page, cfg: dict):
    creds = cfg["login"]

    logger.info("Navigating to IRCTC...")
    
    # page.goto(IRCTC_URL, wait_until="domcontentloaded")
    page.goto(IRCTC_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)  # allow Angular to render

    # Fast click: LOGIN / REGISTER
    logger.info("Clicking LOGIN / REGISTER...")
    login_locators = [
    page.locator("text=LOGIN").first,
    page.locator("text=LOGIN / REGISTER").first,
    page.locator("button:has-text('LOGIN')").first,
    page.locator("a:has-text('LOGIN')").first,
    page.locator("span:has-text('LOGIN')").first,
    ]

    found = False

    for loc in login_locators:
        try:
            loc.wait_for(state="visible", timeout=8000)
            human_click(page, loc, timeout=5000)
            found = True
            break
        except Exception:
            continue

    if not found:
        page.screenshot(path="login_debug.png")
        raise RuntimeError("LOGIN button not found")

    logger.info("Filling credentials...")
    human_type(page, page.locator("input[formcontrolname='userid']"), creds["username"], timeout=8000)
    human_type(page, page.locator("input[formcontrolname='password']"), creds["password"], timeout=8000)

    logger.info("Clicking SIGN IN...")
    human_click(page, page.locator("button:has-text('SIGN IN')").first, timeout=5000)

    logger.info("Waiting for login success...")
    # Success signal: login form disappears OR user label appears
    try:
        page.locator("input[formcontrolname='userid']").wait_for(state="detached", timeout=45000)
    except PWTimeoutError:
        page.locator("span.user-name, .welcome-user, .loggedin, app-header .user-name").first.wait_for(timeout=10000)

    logger.info("[OK] Login successful")


def fill_journey_details(page, cfg: dict):
    j = cfg["journey"]

    logger.info("Filling journey details...")

    # From
    from_code = j["from_station"].split("-")[0].strip()
    logger.info("  From: %s (typing '%s')", j["from_station"], from_code)
    from_input = page.locator("input#origin, p-autocomplete#origin input").first
    human_type(page, from_input, from_code, timeout=5000)
    human_click(page, page.locator(".ui-autocomplete-panel .ui-autocomplete-list-item, #pr_id_1_list li").first, timeout=5000)
    logger.info("  From station selected.")

    # To
    to_code = j["to_station"].split("-")[0].strip()
    logger.info("  To: %s (typing '%s')", j["to_station"], to_code)
    to_input = page.locator("input#destination, p-autocomplete#destination input").first
    human_type(page, to_input, to_code, timeout=5000)
    human_click(page, page.locator(".ui-autocomplete-panel .ui-autocomplete-list-item, #pr_id_2_list li").first, timeout=5000)
    logger.info("  To station selected.")

    # Date — Angular p-calendar: clear then type, press Escape to close calendar overlay
    date_value = j["journey_date"]
    logger.info("  Date: %s", date_value)
    date_input = page.locator("p-calendar input").first
    human_click(page, date_input, timeout=5000)
    # Triple-click to select all existing text, then type over it
    date_input.click(click_count=3)
    date_input.press("Backspace")
    date_input.type(date_value, delay=random.randint(30, 60))
    # Close calendar popup
    date_input.press("Escape")
    page.wait_for_timeout(150)

    # Class — Angular p-dropdown
    cls = j["class"]
    logger.info("  Class: %s", cls)
    try:
        class_dd = page.locator("p-dropdown[formcontrolname='journeyClass']").first
        human_click(page, class_dd, timeout=5000)
        page.wait_for_timeout(180)
        # The dropdown panel is usually appended to body, not inside the p-dropdown
        # Try multiple patterns for the dropdown items
        class_clicked = False
        for selector in [
            f".ui-dropdown-items li:has-text('{cls}')",
            f".ui-dropdown-panel li:has-text('{cls}')",
            f"p-dropdownitem li:has-text('{cls}')",
            f"li.ui-dropdown-item:has-text('{cls}')",
        ]:
            try:
                human_click(page, page.locator(selector).first, timeout=1500)
                class_clicked = True
                break
            except PWTimeoutError:
                continue
        if not class_clicked:
            # JS fallback: click the item whose text contains the class code
            page.evaluate("""(cls) => {
                const items = document.querySelectorAll('.ui-dropdown-items li, .ui-dropdown-panel li, p-dropdownitem li');
                for (const item of items) {
                    if (item.textContent.toUpperCase().indexOf(cls) !== -1) {
                        item.click(); return;
                    }
                }
            }""", cls)
    except Exception as e:
        logger.warning("Could not select class: %s", e)

    page.wait_for_timeout(150)

    # Quota — Angular p-dropdown
    quota_code = j["quota"]
    quota_label = QUOTA_LABELS.get(quota_code, quota_code)
    logger.info("  Quota: %s (%s)", quota_code, quota_label)
    try:
        quota_dd = page.locator("p-dropdown[formcontrolname='journeyQuota']").first
        human_click(page, quota_dd, timeout=5000)
        page.wait_for_timeout(180)
        quota_clicked = False
        for selector in [
            f".ui-dropdown-items li:has-text('{quota_label}')",
            f".ui-dropdown-panel li:has-text('{quota_label}')",
            f"p-dropdownitem li:has-text('{quota_label}')",
            f"li.ui-dropdown-item:has-text('{quota_label}')",
            f".ui-dropdown-items li:has-text('{quota_code}')",
        ]:
            try:
                human_click(page, page.locator(selector).first, timeout=1500)
                quota_clicked = True
                break
            except PWTimeoutError:
                continue
        if not quota_clicked:
            page.evaluate("""(label) => {
                const items = document.querySelectorAll('.ui-dropdown-items li, .ui-dropdown-panel li, p-dropdownitem li');
                for (const item of items) {
                    if (item.textContent.toUpperCase().indexOf(label) !== -1) {
                        item.click(); return;
                    }
                }
            }""", quota_label.upper())
    except Exception as e:
        logger.warning("Could not select quota: %s", e)

    logger.info("Journey details filled")


def search_and_select_train(page, cfg: dict):
    j = cfg["journey"]
    train_no = str(j.get("train_number", "")).strip()
    cls = j["class"]

    human_scroll(page)
    logger.info("Clicking Search Trains...")
    human_click(page, page.locator("button.search_btn.train_Search:has-text('Search Trains')").first, timeout=5000)


    logger.info("Waiting for search results...")
    page.locator("app-train-avl-enq, .bull-back").first.wait_for(timeout=40000)

    if not train_no:
        logger.info("No train configured. Select manually.")
        return

    logger.info("Looking for train %s in results...", train_no)
    row = page.locator("app-train-avl-enq, .bull-back").filter(has_text=train_no).first
    row.wait_for(timeout=20000)
    row.scroll_into_view_if_needed()
    logger.info("Found train %s — scrolled into view.", train_no)

    # Click the class tab (e.g. SL, 3A) inside the train row
    logger.info("Clicking class '%s' in train row...", cls)
    class_clicked = False
    # Try multiple ways to find the class link/tab inside the row
    for selector in [
        f"td:has-text('{cls}')",
        f"a:has-text('{cls}')",
        f"strong:has-text('{cls}')",
        f"text={cls}",
    ]:
        try:
            class_el = row.locator(selector).first
            if class_el.is_visible(timeout=1000):
                human_scroll(page)
                human_click(page, class_el, timeout=2000)
                class_clicked = True
                logger.info("Class '%s' clicked via: %s", cls, selector)
                break
        except Exception:
            continue

    if not class_clicked:
        # JS fallback: find element with class text inside the row
        try:
            row.evaluate("""(el, cls) => {
                const nodes = el.querySelectorAll('td, a, strong, span');
                for (const n of nodes) {
                    if (n.textContent.trim().toUpperCase().indexOf(cls) !== -1) {
                        n.click(); return;
                    }
                }
            }""", cls)
            logger.info("Class '%s' clicked via JS fallback.", cls)
            class_clicked = True
        except Exception:
            logger.warning("Could not click class '%s' — proceeding anyway.", cls)

    # Wait for the date-wise availability panel to load after class click
    page.wait_for_timeout(2000)

    # Click the correct DATE cell inside the availability row
    # IRCTC shows dates like "Sat, 28 Mar" or "28-03-2026" etc.
    date_str = j["journey_date"]  # e.g. "28/03/2026"
    from datetime import datetime as _dt
    try:
        dt = _dt.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        dt = _dt.strptime(date_str, "%d-%m-%Y")

    # Build multiple possible date text patterns IRCTC might show
    day_num = str(dt.day)               # "28"
    day_padded = f"{dt.day:02d}"        # "28"
    month_short = dt.strftime("%b")     # "Mar"
    weekday_short = dt.strftime("%a")   # "Sat"
    date_patterns = [
        f"{weekday_short}, {day_padded} {month_short}",   # "Sat, 28 Mar"
        f"{weekday_short}, {day_num} {month_short}",      # "Sat, 28 Mar"
        f"{day_padded} {month_short}",                     # "28 Mar"
        f"{day_num} {month_short}",                        # "28 Mar"
        f"{month_short} {day_padded}",                     # "Mar 28"
        f"{day_padded}-{dt.month:02d}-{dt.year}",         # "28-03-2026"
        f"{day_padded}/{dt.month:02d}/{dt.year}",         # "28/03/2026"
    ]

    logger.info("Selecting date in availability panel (looking for: %s)...", date_patterns[0])
    date_clicked = False

    # Try clicking the date cell inside the train's availability area
    for pattern in date_patterns:
        if date_clicked:
            break
        for selector in [
            f".table-responsive td:has-text('{pattern}')",
            f"td:has-text('{pattern}')",
            f"div:has-text('{pattern}'):not(:has(div))",
            f"text={pattern}",
        ]:
            try:
                # Search within the availability section that appeared after class click
                date_el = page.locator(selector).first
                if date_el.is_visible(timeout=1500):
                    human_scroll(page)
                    human_click(page, date_el, timeout=2000)
                    date_clicked = True
                    logger.info("Date '%s' clicked via: %s", pattern, selector)
                    break
            except Exception:
                continue

    if not date_clicked:
        # JS fallback: search for any td/div containing the day+month text
        try:
            page.evaluate("""(patterns) => {
                const cells = document.querySelectorAll('td, div.availability-cell, div.avl-item, .table-responsive td');
                for (const cell of cells) {
                    const txt = cell.textContent.trim();
                    for (const p of patterns) {
                        if (txt.indexOf(p) !== -1) {
                            cell.click();
                            return;
                        }
                    }
                }
            }""", date_patterns)
            logger.info("Date clicked via JS fallback.")
            date_clicked = True
        except Exception:
            logger.warning("Could not auto-click date cell.")

    if not date_clicked:
        logger.warning("Date cell not found — please click the date manually.")
        input("  [PAUSE] Click the date '%s' in the browser, then press ENTER here..." % date_patterns[0])

    # Wait for availability status to load after date click
    page.wait_for_timeout(2000)

    # Click Book Now
    logger.info("Clicking Book Now...")
    book_clicked = False
    # Try multiple selectors — Book Now can be inside the row or at page level
    for scope, label in [(row, "row"), (page, "page")]:
        if book_clicked:
            break
        for btn_sel in [
            "button:has-text('Book Now')",
            "td button:has-text('Book Now')",
            "a:has-text('Book Now')",
            "button.btnDefault:has-text('Book Now')",
        ]:
            try:
                human_scroll(page)
                human_click(page, scope.locator(btn_sel).first, timeout=3000)
                book_clicked = True
                logger.info("Book Now clicked via: %s (scope: %s)", btn_sel, label)
                break
            except Exception:
                continue

    if not book_clicked:
        logger.error("Could not click Book Now — please click manually.")
        input("  [PAUSE] Click 'Book Now' in the browser, then press ENTER here...")
    else:
        logger.info("[OK] Book Now clicked for train %s", train_no)


# Map config gender text to IRCTC <select> option values
GENDER_MAP = {"Male": "M", "Female": "F", "Transgender": "T"}
# Map config berth text to IRCTC <select> option values
BERTH_MAP = {
    "Lower": "LB", "Middle": "MB", "Upper": "UB",
    "Side Lower": "SL", "Side Upper": "SU", "No Preference": "",
}
# Map config nationality text to IRCTC <select> option values
NATIONALITY_MAP = {"India": "IN", "india": "IN"}


def fill_passengers(page, cfg: dict):
    passengers = cfg.get("passengers", [])
    booking_options = cfg.get("booking_options", {})
    if not passengers:
        return

    logger.info("Filling passenger details...")

    # Wait for the passenger form page to load
    logger.info("  Waiting for passenger form to load...")
    passenger_form_loaded = False
    form_selectors = [
        "input[placeholder='Name']",
        "input[formcontrolname='passengerAge']",
        "select[formcontrolname='passengerGender']",
    ]
    for sel in form_selectors:
        try:
            page.locator(sel).first.wait_for(timeout=20000)
            passenger_form_loaded = True
            logger.info("  Passenger form detected via: %s", sel)
            break
        except PWTimeoutError:
            continue

    if not passenger_form_loaded:
        # Maybe there's a popup/dialog to dismiss first (insurance opt-out, etc.)
        logger.info("  Checking for popups/dialogs to dismiss...")
        for dismiss_sel in [
            "button:has-text('No')",           # Insurance opt-out
            "button:has-text('OK')",
            "button.dismiss",
            ".ui-dialog button",
        ]:
            try:
                btn = page.locator(dismiss_sel).first
                if btn.is_visible(timeout=2000):
                    btn.click(timeout=2000)
                    logger.info("  Dismissed popup via: %s", dismiss_sel)
                    page.wait_for_timeout(1000)
            except Exception:
                continue

        # Try waiting again after dismissing popups
        try:
            page.locator("input[placeholder='Name']").first.wait_for(timeout=15000)
        except PWTimeoutError:
            logger.error("Passenger form not found. Page may require manual action.")
            input("  [PAUSE] Navigate to the passenger form, then press ENTER here...")

    for idx, pax in enumerate(passengers):
        logger.info("  Passenger %d: %s, %s, Age %s", idx + 1, pax.get('name'), pax.get('gender'), pax.get('age'))

        # Click "+ Add Passenger" for 2nd passenger onward
        if idx > 0:
            try:
                human_scroll(page)
                human_click(page, page.locator("span.prenext:has-text('+ Add Passenger')").first, timeout=3000)
                page.wait_for_timeout(500)
                logger.info("  Clicked '+ Add Passenger'.")
            except Exception:
                logger.warning("  Could not click '+ Add Passenger'.")

        # --- Name (p-autocomplete input with placeholder='Name') ---
        # The field may be readonly if a saved passenger is already loaded
        try:
            name_input = page.locator("input[placeholder='Name']").nth(idx)
            is_readonly = name_input.get_attribute("readonly", timeout=2000)
            if is_readonly is not None:
                current_val = name_input.input_value(timeout=1000)
                logger.info("    Name is readonly (pre-filled: '%s') - skipping.", current_val)
            else:
                human_type(page, name_input, str(pax.get("name", "")), timeout=3000)
                # If autocomplete dropdown appears, select first matching item
                try:
                    human_scroll(page)
                    human_click(page, page.locator(".ui-autocomplete-panel .ui-autocomplete-list-item").first, timeout=2000)
                    logger.info("    Name selected from autocomplete: %s", pax.get('name'))
                except PWTimeoutError:
                    logger.info("    Name typed: %s (no autocomplete match)", pax.get('name'))
        except Exception as e:
            logger.warning("    Could not fill name: %s", e)

        page.wait_for_timeout(160)  # human-like pause (faster)

        # --- Age ---
        try:
            age_input = page.locator("input[formcontrolname='passengerAge']").nth(idx)
            is_readonly = age_input.get_attribute("readonly", timeout=1000)
            if is_readonly is not None:
                logger.info("    Age is readonly (pre-filled) - skipping.")
            else:
                human_type(page, age_input, str(pax.get("age", "")), timeout=2000)
                age_input.press("Tab")
                logger.info("    Age filled: %s", pax.get('age'))
        except Exception as e:
            logger.warning("    Could not fill age: %s", e)

        page.wait_for_timeout(140)  # human-like pause (faster)

        # --- Gender ---
        # May be a <select> or a readonly <input> if pre-filled from saved passenger
        try:
            gender_select = page.locator("select[formcontrolname='passengerGender']").nth(idx)
            if gender_select.is_visible(timeout=1000):
                gender_text = str(pax.get("gender", "Male"))
                gender_val = GENDER_MAP.get(gender_text, "M")
                gender_select.select_option(value=gender_val, timeout=3000)
                logger.info("    Gender selected: %s -> %s", gender_text, gender_val)
            else:
                logger.info("    Gender field not a <select> (likely pre-filled) - skipping.")
        except Exception as e:
            logger.info("    Gender pre-filled or not editable - skipping. (%s)", e)

        page.wait_for_timeout(140)  # human-like pause (faster)

        # --- Nationality ---
        try:
            nat_select = page.locator("select[formcontrolname='passengerNationality']").nth(idx)
            if nat_select.is_visible(timeout=1000):
                nationality = str(pax.get("nationality", "India"))
                nat_val = NATIONALITY_MAP.get(nationality, nationality)
                if len(nat_val) == 2:
                    nat_select.select_option(value=nat_val, timeout=3000)
                    logger.info("    Nationality selected: %s -> %s", nationality, nat_val)
            else:
                logger.info("    Nationality pre-filled - skipping.")
        except Exception:
            logger.info("    Nationality pre-filled or not editable - skipping.")

        page.wait_for_timeout(140)  # human-like pause (faster)

        # --- Berth Preference (always editable <select>) ---
        try:
            berth_text = str(pax.get("berth_preference", "No Preference"))
            berth_val = BERTH_MAP.get(berth_text, "")
            page.locator("select[formcontrolname='passengerBerthChoice']").nth(idx).select_option(
                value=berth_val, timeout=3000
            )
            logger.info("    Berth selected: %s -> %s", berth_text, berth_val)
        except Exception as e:
            logger.warning("    Could not select berth: %s", e)

        page.wait_for_timeout(180)  # human-like pause between passengers (faster)

    # --- Mobile Number ---
    # Use type() with delay to properly trigger Angular form validation
    mobile = str(booking_options.get("mobile_number", "")).strip()
    if mobile:
        try:
            mob_input = page.locator("input[formcontrolname='mobileNumber']").first
            human_scroll(page)
            human_type(page, mob_input, mobile, timeout=3000)
            # Tab out to trigger Angular validation/change events
            mob_input.press("Tab")
            logger.info("  Mobile filled: %s", mobile)
        except Exception as e:
            logger.warning("  Could not fill mobile number: %s", e)

    logger.info("[OK] Passenger details filled")

    # --- DEBUG: Check Angular form validity ---
    logger.info("  [DEBUG] Checking form validity...")
    try:
        form_debug = page.evaluate("""() => {
            const result = {};

            // Check all invalid fields on the page
            const invalidFields = document.querySelectorAll('.ng-invalid');
            result.invalid_count = invalidFields.length;
            result.invalid_fields = [];
            invalidFields.forEach(el => {
                const name = el.getAttribute('formcontrolname') ||
                             el.getAttribute('name') ||
                             el.getAttribute('id') ||
                             el.getAttribute('placeholder') ||
                             el.tagName;
                const val = el.value || '';
                const cls = el.className || '';
                if (name && name !== 'undefined') {
                    result.invalid_fields.push({
                        field: name,
                        value: val.substring(0, 30),
                        classes: cls.substring(0, 80)
                    });
                }
            });

            // Check required empty fields
            const requiredEmpty = document.querySelectorAll('input[required]:not([readonly])');
            result.required_empty = [];
            requiredEmpty.forEach(el => {
                if (!el.value || el.value.trim() === '') {
                    result.required_empty.push(
                        el.getAttribute('formcontrolname') ||
                        el.getAttribute('placeholder') ||
                        el.tagName
                    );
                }
            });

            // Check if mobile is filled
            const mob = document.querySelector("input[formcontrolname='mobileNumber']");
            result.mobile_value = mob ? mob.value : 'NOT FOUND';

            // Check payment radio
            const radio = document.querySelector('input[type="radio"][name="paymentType"]:checked');
            result.payment_radio = radio ? radio.value : 'NONE SELECTED';

            return result;
        }""")
        logger.info("  [DEBUG] Invalid field count: %s", form_debug.get('invalid_count'))
        for f in form_debug.get('invalid_fields', []):
            logger.info("  [DEBUG]   INVALID: %s = '%s'", f['field'], f['value'])
        for f in form_debug.get('required_empty', []):
            logger.info("  [DEBUG]   REQUIRED BUT EMPTY: %s", f)
        logger.info("  [DEBUG] Mobile value: '%s'", form_debug.get('mobile_value'))
        logger.info("  [DEBUG] Payment radio: %s", form_debug.get('payment_radio'))
    except Exception as e:
        logger.warning("  [DEBUG] Could not check form: %s", e)


def proceed_to_payment(page, cfg: dict):
    logger.info("Proceeding to payment...")

    # --- Ensure payment radio button value="3" is selected ---
    logger.info("  Checking payment method radio...")
    try:
        radio_box = page.locator("p-radiobutton#\\33  .ui-radiobutton-box, p-radiobutton[id='3'] .ui-radiobutton-box").first
        is_active = radio_box.get_attribute("class", timeout=2000)
        if is_active and "ui-state-active" in is_active:
            logger.info("  Payment radio value=3 already selected - no action needed.")
        else:
            page.locator("label[for='3']").first.click(timeout=3000)
            logger.info("  Payment radio value=3 clicked.")
    except Exception:
        try:
            already_checked = page.evaluate("""() => {
                const radio = document.querySelector('input[type="radio"][name="paymentType"][value="3"]');
                return radio ? radio.checked : false;
            }""")
            if already_checked:
                logger.info("  Payment radio value=3 already checked (JS confirm).")
            else:
                page.evaluate("""() => {
                    const label = document.querySelector('label[for="3"]');
                    if (label) label.click();
                }""")
                logger.info("  Payment radio clicked via JS.")
        except Exception as e:
            logger.warning("  Could not verify payment radio: %s", e)

    logger.info("=" * 50)
    logger.info("[OK] All details filled! Review and click Continue manually.")
    logger.info("  -> Verify passenger details, mobile number, payment mode.")
    logger.info("  -> Click 'Continue', solve CAPTCHA, and complete payment.")
    logger.info("  -> Browser stays open until you press ENTER here.")
    input("\n  >>> Press ENTER here to close the browser when done... ")



def main():
    cfg = load_config()
    timeout_ms = int(cfg.get("optimization", {}).get("explicit_wait", 8)) * 1000
    # Always run headed mode for human-like behavior and lower bot suspicion
    headless = False
    logger.info("Headless mode disabled (forced headed browser).")

    with sync_playwright() as p:
        # Launch bundled Chromium (faster, cleaner)
        # browser = p.chromium.launch(
        #     headless=headless,
        #     slow_mo=12,
        #     args=[
        #         "--start-maximized",
        #         "--disable-blink-features=AutomationControlled",
        #         "--disable-infobars",
        #         "--no-default-browser-check",
        #     ],
        # )
        # context = browser.new_context(
        #     viewport={"width": 1366, "height": 900},
        # )

        browser = p.chromium.launch(
            channel="chrome",  # ✅ Use real Chrome
            headless=False,
            slow_mo=15,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
                "--disable-web-security",
            ],
        )

        context = browser.new_context(
            viewport=None,  # ✅ real full screen
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            geolocation={"latitude": 28.6139, "longitude": 77.2090},
            permissions=["geolocation"],

            # 🔥 VERY IMPORTANT (fix your blocked requests issue)
            service_workers="block"
        )

        # Basic anti-detection hardening for heavily protected pages.
        # context.add_init_script("""
        #     Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        #     Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        #     Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        #     Object.defineProperty(navigator, 'plugins', {
        #         get: () => [1, 2, 3, 4, 5]
        #     });
        # """)
        context.add_init_script("""
            /* Hide webdriver */              
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            /* Fake plugins */
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            /* Fake languages */
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-IN', 'en']
            });

            /* Fake platform */
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            /* Fake Chrome runtime */
            window.chrome = {
                runtime: {},
                loadTimes: function(){},
                csi: function(){}
            };

            /* Fix permissions (VERY IMPORTANT) */
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );

            /* WebGL fingerprint spoof */
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
                if (parameter === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
                return getParameter(parameter);
            };

            /* Fix iframe detection */
            Object.defineProperty(window, 'frameElement', {
                get: () => null
            });

            /* Add slight randomness to timing */
            const originalNow = Date.now;
            Date.now = function() {
                return originalNow() + Math.floor(Math.random() * 10);
            };
        """)

        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            logger.info("Log file: %s", LOG_FILE)
            logger.info("=" * 50)
            logger.info("STEP 1/5: Login")
            login(page, cfg)
            logger.info("=" * 50)
            logger.info("STEP 2/5: Fill journey details")
            fill_journey_details(page, cfg)
            logger.info("=" * 50)
            logger.info("STEP 3/5: Search & select train")
            search_and_select_train(page, cfg)
            logger.info("=" * 50)
            logger.info("STEP 4/5: Fill passengers")
            fill_passengers(page, cfg)
            logger.info("=" * 50)
            logger.info("STEP 5/5: Proceed to payment")
            proceed_to_payment(page, cfg)
        except Exception as exc:
            logger.exception("Fatal error: %s", exc)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
