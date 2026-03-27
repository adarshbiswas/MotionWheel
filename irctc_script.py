import json
from playwright.sync_api import sync_playwright

IRCTC_URL = "https://www.irctc.co.in/nget/train-search"


def load_config():
    with open("config.json") as f:
        return json.load(f)


def login(page, cfg):
    print("Logging in...")

    page.goto(IRCTC_URL)
    page.wait_for_timeout(3000)

    # Click login
    page.locator("text=LOGIN").first.click()

    # Fill credentials
    page.fill("input[formcontrolname='userid']", cfg["login"]["username"])
    page.fill("input[formcontrolname='password']", cfg["login"]["password"])

    print("👉 Solve captcha manually...")
    input("Press ENTER after captcha...")

    page.locator("button:has-text('SIGN IN')").click()

    page.wait_for_timeout(5000)
    print("✅ Login done")


def fill_journey(page, cfg):
    j = cfg["journey"]

    print("Filling journey...")

    # FROM
    page.fill("input#origin", j["from"])
    page.click(".ui-autocomplete-list-item")

    # TO
    page.fill("input#destination", j["to"])
    page.click(".ui-autocomplete-list-item")

    # DATE
    page.click("p-calendar input")
    page.fill("p-calendar input", j["date"])

    # CLASS
    page.click("p-dropdown[formcontrolname='journeyClass']")
    page.click(f"li:has-text('{j['class']}')")

    # QUOTA
    page.click("p-dropdown[formcontrolname='journeyQuota']")
    page.click(f"li:has-text('{j['quota']}')")

    print("✅ Journey filled")


def search_train(page):
    print("Searching trains...")
    page.click("button:has-text('Search')")
    page.wait_for_timeout(5000)


def select_train(page, cfg):
    train_no = cfg["journey"]["train_number"]
    cls = cfg["journey"]["class"]

    print(f"Selecting train {train_no}...")

    train = page.locator(f"text={train_no}").first
    train.scroll_into_view_if_needed()

    # click class
    train.locator(f"text={cls}").click()

    page.wait_for_timeout(2000)

    # click Book Now
    page.locator("button:has-text('Book Now')").first.click()

    print("✅ Train selected")


def fill_passenger(page, cfg):
    p = cfg["passenger"]

    print("Filling passenger details...")

    page.wait_for_selector("input[placeholder='Name']")

    page.fill("input[placeholder='Name']", p["name"])
    page.fill("input[formcontrolname='passengerAge']", p["age"])

    # Gender
    page.select_option(
        "select[formcontrolname='passengerGender']",
        value=p["gender"]
    )

    # Mobile
    page.fill("input[formcontrolname='mobileNumber']", p["mobile"])

    print("✅ Passenger filled")


def main():
    cfg = load_config()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        login(page, cfg)
        fill_journey(page, cfg)
        search_train(page)
        select_train(page, cfg)
        fill_passenger(page, cfg)

        print("\n🎯 DONE till payment page")
        print("👉 Complete payment manually")

        input("Press ENTER to close...")
        browser.close()


if __name__ == "__main__":
    main()