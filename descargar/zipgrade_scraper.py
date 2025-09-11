#!/usr/bin/env python3
"""
ZipGrade Quiz CSV Downloader (Full format with student responses)

This script automates the process of logging into a ZipGrade account,
navigating to the list of quizzes, and downloading the CSV file for each quiz
containing full student responses. It uses Selenium with ChromeDriver to
simulate browser interactions.

Important considerations:

* **Respect ZipGrade Terms of Service**: Always review and abide by the site's
  terms and conditions. Automating downloads may violate terms if done
  excessively or for commercial purposes.
* **Credentials Security**: Do not hard‑code your username and password in
  this script. Instead, supply them via environment variables or a `.env`
  file using the `python‑dotenv` package. Example of `.env` contents:

    ZIPGRADE_EMAIL="your_email@example.com"
    ZIPGRADE_PASSWORD="your_secure_password"
    DOWNLOAD_DIR="/path/to/save/csvs"  # optional

* **Browser Drivers**: The script uses `webdriver‑manager` to install and
  manage the appropriate ChromeDriver. You need Google Chrome or Chromium
  installed on your system.
* **Headless vs Headful**: By default the script runs in headless mode.
  Use the `--headful` flag to see the browser in action.

Usage examples:

    # Download all quizzes
    python zipgrade_scraper.py

    # Run with a visible browser window
    python zipgrade_scraper.py --headful

    # Filter quizzes by title containing a phrase
    python zipgrade_scraper.py --only "Quiz 1"

    # Limit to processing at most 5 quizzes
    python zipgrade_scraper.py --max 5

    # Dry run (list quizzes but don't download)
    python zipgrade_scraper.py --dry-run

The script attempts to be resilient to changes in ZipGrade's HTML by
checking multiple possible selectors for important elements (login fields,
navigation links, etc.). If the site layout changes significantly, you may
need to update the selector lists below.
"""

import argparse
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --------------------------------------------------------------
# Configuration: selectors and timeouts
# --------------------------------------------------------------

# Root URLs
BASE_URL = "https://www.zipgrade.com"
LOGIN_URL = f"{BASE_URL}/login/"

# Timeouts (seconds)
SHORT_TIMEOUT = 10
DEFAULT_TIMEOUT = 20
LONG_TIMEOUT = 45

# Selectors for login form fields and submit button. If ZipGrade changes
# its login page, add or adjust selectors in these lists. The script
# checks each in order until one is found.
LOGIN_SELECTORS = {
    "email": [
        (By.NAME, "email"),
        (By.NAME, "username"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.ID, "email"),
        (By.ID, "username"),
    ],
    "password": [
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.ID, "password"),
    ],
    "submit": [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//button[contains(., 'Log in') or contains(., 'Sign in') or contains(., 'Ingresar')]"),
        (By.XPATH, "//input[@type='submit']"),
    ],
}

# Navigation link for quizzes
QUIZZES_LINK_SELECTORS = [
    (By.LINK_TEXT, "Quizzes"),
    (By.PARTIAL_LINK_TEXT, "Quiz"),
    (By.XPATH, "//a[contains(., 'Quizzes') or contains(., 'Quiz')]"),
]

# Table listing quizzes: selectors for rows, quiz link, and date cell
QUIZ_LIST_SELECTORS = {
    "rows": [
        (By.CSS_SELECTOR, "table tbody tr"),
        (By.CSS_SELECTOR, "[role='row']"),
        (By.CSS_SELECTOR, ".table tbody tr"),
        (By.XPATH, "//tr[td]"),
    ],
    "title_link": [
        (By.CSS_SELECTOR, "a"),
        (By.CSS_SELECTOR, "td a"),
        (By.XPATH, ".//a"),
    ],
    "date_cell": [
        (By.CSS_SELECTOR, "td:nth-child(2)"),
        (By.CSS_SELECTOR, ".date, time"),
        (By.XPATH, ".//td[contains(@class, 'date') or .//time]"),
    ],
}


# Link to download full CSV on statistics page
FULL_CSV_LINK_SELECTORS = [
    (By.XPATH, "//a[contains(., 'Full format with student responses')]"),
    (By.XPATH, "//a[contains(., 'Full') and contains(., 'student') and contains(., 'responses')]"),
    (By.PARTIAL_LINK_TEXT, "Full format"),
]

# Selectors targeting the quiz statistics section and its CSV dropdown button.
# ZipGrade shows the "Quiz Statistics" heading inside a panel on the quiz page,
# and the CSV download options live in a dropdown button within that panel.
QUIZ_STATS_CSV_BUTTON_SELECTORS = [
    # Button labelled CSV inside the stats panel (case‑insensitive match)
    (By.XPATH,
     "//div[contains(translate(., 'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ'),'QUIZ STATISTICS')]//button[contains(@class,'dropdown-toggle') and contains(.,'CSV')]"),
    # Fallback: any CSV dropdown button on the page
    (By.XPATH, "//button[contains(@class,'dropdown-toggle') and contains(.,'CSV')]"),
]

# Selectors for the menu item that downloads the full CSV with student responses
CSV_MENU_FULL_STUDENT_SELECTORS = [
    # Match by href pattern and target="export"
    (By.CSS_SELECTOR, "ul.dropdown-menu a[target='export'][href*='/quiz/full/'][href*='/all/'][href$='.CSV']"),
    (By.CSS_SELECTOR, "ul.dropdown-menu a[target='export'][href*='/quiz/full/'][href*='/all/'][href$='.csv']"),
    # Match by href pattern regardless of target attribute
    (By.XPATH, "//ul[contains(@class,'dropdown-menu')]//a[contains(@href,'/quiz/full/') and contains(@href,'/all/') and (contains(@href,'.CSV') or contains(@href,'.csv'))]"),
    # Fallback: match by visible text if href pattern changes or translations occur
    (By.XPATH, "//ul[contains(@class,'dropdown-menu')]//a[contains(., 'Full Format') and contains(., 'student responses')]"),
    (By.XPATH, "//ul[contains(@class,'dropdown-menu')]//a[contains(., 'Full format') and contains(., 'student responses')]"),
]

# New: Selectors for the CSV dropdown button on the statistics page.
# ZipGrade displays a button labelled "CSV" with classes `btn-circle`,
# `btn-default`, and `dropdown-toggle`. Clicking this button reveals
# a menu containing download options including "Full format with student
# responses". These selectors attempt to locate that button via classes
# and text or icon content.
CSV_DROPDOWN_BUTTON_SELECTORS = [
    # CSS classes match the default button styling
    (By.CSS_SELECTOR, "button.btn.btn-circle.btn-default.dropdown-toggle"),
    # Button containing the text 'CSV'
    (By.XPATH, "//button[contains(@class,'dropdown-toggle') and contains(.,'CSV')]") ,
    # Button with floppy disk icon and CSV label
    (By.XPATH, "//button[.//i[contains(@class,'fa-floppy-o')] and contains(normalize-space(.), 'CSV')]") ,
]


# --------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing or replacing illegal characters."""
    # Replace illegal characters with spaces
    sanitized = re.sub(r"[\\/*?\"<>|:]", " ", name)
    # Collapse multiple spaces into one
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    # Limit length to avoid OS issues
    return sanitized[:180]


def wait_for_first(driver, candidates, timeout=DEFAULT_TIMEOUT, parent=None):
    """Wait for the first matching element from a list of selector candidates.

    Args:
        driver: Selenium WebDriver
        candidates: list of (By, selector) tuples
        timeout: how many seconds to wait
        parent: optional WebElement to search inside

    Returns:
        The first found WebElement, or raises TimeoutException.
    """
    last_exception = None
    for by, sel in candidates:
        try:
            if parent is None:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, sel))
                )
            else:
                # Use a lambda to allow waiting for presence within a parent
                element = WebDriverWait(driver, timeout).until(
                    lambda d: parent.find_element(by, sel)
                )
            return element
        except Exception as exc:
            last_exception = exc
            continue
    # If we get here, no candidate matched
    if last_exception:
        raise last_exception
    raise TimeoutException(f"None of the selectors matched: {candidates}")


def wait_for_all(driver, candidates, timeout=DEFAULT_TIMEOUT):
    """Wait for all elements matching any candidate (for lists of rows)."""
    last_exception = None
    for by, sel in candidates:
        try:
            elements = WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((by, sel))
            )
            if elements:
                return elements
        except Exception as exc:
            last_exception = exc
            continue
    if last_exception:
        raise last_exception
    raise TimeoutException(f"None of the selectors returned elements: {candidates}")


# --------------------------------------------------------------------
# Rate limit detection and handling
# --------------------------------------------------------------------

class RateLimitError(Exception):
    """Raised when ZipGrade indicates too many download attempts have been made."""
    pass


class PopupError(Exception):
    """Raised when an unexpected popup window is detected during download."""
    pass


def page_has_rate_limit(driver) -> bool:
    """Check if the current page displays a rate limit error message.

    ZipGrade shows an error such as "Too many attempts. Please try again later"
    when too many downloads are initiated in a short time.  This helper scans
    the page for that message.

    Returns True if the rate limit message is found, False otherwise.
    """
    try:
        # Search for the error text on the page (case insensitive)
        xpath = "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'too many attempts')]"
        WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return True
    except Exception:
        return False


def login(driver, email: str, password: str):
    """Perform login on ZipGrade using the provided credentials."""
    driver.get(LOGIN_URL)
    # Fill email
    email_field = wait_for_first(driver, LOGIN_SELECTORS["email"], timeout=LONG_TIMEOUT)
    email_field.clear()
    email_field.send_keys(email)
    # Fill password
    password_field = wait_for_first(driver, LOGIN_SELECTORS["password"])
    password_field.clear()
    password_field.send_keys(password)
    # Submit form
    submit_button = wait_for_first(driver, LOGIN_SELECTORS["submit"])
    submit_button.click()
    # Wait until the quizzes link is present (login success)
    try:
        wait_for_first(driver, QUIZZES_LINK_SELECTORS, timeout=LONG_TIMEOUT)
    except TimeoutException:
        # It's possible the link is hidden behind a menu; we don't treat this as fatal here
        pass


def navigate_to_quizzes(driver):
    """Navigate to the Quizzes list page."""
    try:
        link = wait_for_first(driver, QUIZZES_LINK_SELECTORS, timeout=SHORT_TIMEOUT)
        link.click()
        time.sleep(1.0)
        return
    except Exception:
        # As a fallback, try to directly access common quizzes URL
        fallback_url = f"{BASE_URL}/quiz/"
        driver.get(fallback_url)
        time.sleep(1.0)


def list_quizzes(driver):
    """Retrieve a list of available quizzes on the current page.

    Returns a list of dictionaries with keys: title, href, date_text.
    """
    rows = wait_for_all(driver, QUIZ_LIST_SELECTORS["rows"], timeout=LONG_TIMEOUT)
    quizzes = []
    for row in rows:
        # Extract title and link
        try:
            title_link = wait_for_first(driver, QUIZ_LIST_SELECTORS["title_link"], parent=row, timeout=SHORT_TIMEOUT)
            title_text = title_link.text.strip() or "Untitled Quiz"
            href = title_link.get_attribute("href")
        except Exception:
            continue
        # Extract date if available
        date_text = ""
        try:
            date_cell = wait_for_first(driver, QUIZ_LIST_SELECTORS["date_cell"], parent=row, timeout=SHORT_TIMEOUT)
            date_text = date_cell.text.strip()
        except Exception:
            pass
        quizzes.append({
            "title": title_text,
            "href": href,
            "date_text": date_text,
        })
    return quizzes


def open_quiz_and_download(driver, quiz_info, download_dir: Path, dry_run=False):
    """Open a quiz and download the full CSV of student responses.

    Args:
        driver: WebDriver instance
        quiz_info: dict with keys title, href, date_text
        download_dir: directory to save CSV
        dry_run: if True, only report the file that would be downloaded

    Returns:
        Path of the downloaded file (or intended path in dry_run)
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    # Navigate to quiz page
    driver.get(quiz_info["href"])
    # The "Quiz Statistics" box is part of the quiz page itself.  Locate the
    # CSV dropdown button inside that box and open its menu.
    try:
        csv_button = wait_for_first(driver, QUIZ_STATS_CSV_BUTTON_SELECTORS, timeout=LONG_TIMEOUT)
        # Scroll into view and click to reveal the dropdown menu
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", csv_button)
        time.sleep(0.2)
        try:
            csv_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", csv_button)
        # Allow the dropdown to render
        time.sleep(0.5)
    except Exception:
        # If the CSV button can't be found, we'll still try to locate the download link globally
        pass
    # Locate the "Full format with student responses" link in the dropdown
    download_link = wait_for_first(driver, CSV_MENU_FULL_STUDENT_SELECTORS, timeout=LONG_TIMEOUT)
    # Prepare file name
    date_part = quiz_info["date_text"][:10] if quiz_info["date_text"] else datetime.now().strftime("%Y-%m-%d")
    sanitized_title = sanitize_filename(quiz_info["title"])
    target_name = f"{date_part} - {sanitized_title} - full.csv"
    target_path = download_dir / target_name
    if dry_run:
        print(f"Would download: {target_name}")
        return target_path
    # Initiate download and monitor download directory
    before_files = set(os.listdir(download_dir))
    original_handles = driver.window_handles
    download_link.click()
    # Short pause to allow for potential redirection or rate limit message
    time.sleep(0.5)
    # Detect unexpected popup windows
    current_handles = driver.window_handles
    new_handles = [h for h in current_handles if h not in original_handles]
    if new_handles:
        driver.switch_to.window(new_handles[0])
        driver.close()
        driver.switch_to.window(original_handles[0])
        raise PopupError("Unexpected popup window detected")
    if page_has_rate_limit(driver):
        # Rate limit encountered immediately after click
        raise RateLimitError("Too many attempts")
    # Wait for a new file to appear (not .crdownload) and rename it
    elapsed = 0
    poll_interval = 1.0
    while elapsed < 60:
        time.sleep(poll_interval)
        elapsed += poll_interval
        # If the page now displays the rate limit message, abort and requeue
        if page_has_rate_limit(driver):
            raise RateLimitError("Too many attempts")
        after_files = set(os.listdir(download_dir))
        new_files = after_files - before_files
        completed = [f for f in new_files if not f.endswith(".crdownload")]
        if completed:
            # Choose the most recent file
            latest = max(
                [download_dir / f for f in completed],
                key=lambda p: p.stat().st_mtime,
                default=None
            )
            if latest:
                # Move/rename
                try:
                    latest.rename(target_path)
                except Exception:
                    # Use a unique suffix if a file already exists
                    suffix = int(time.time())
                    target_path = download_dir / f"{target_path.stem} ({suffix}){target_path.suffix}"
                    latest.rename(target_path)
                print(f"Downloaded: {target_path.name}")
                return target_path
    raise TimeoutException("Timed out waiting for file to download.")


@contextmanager
def chrome_driver(headless: bool, download_dir: Path):
    """Context manager to initialize and quit a Chrome WebDriver."""
    # Chrome preferences: disable download prompts
    prefs = {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        # Allow multiple automatic downloads without prompting
        "profile.default_content_setting_values.automatic_downloads": 1,
        # Disable popup blocking to ensure downloads proceed
        "profile.default_content_settings.popups": 0,
    }
    options = webdriver.ChromeOptions()
    if headless:
        # Use new headless mode for better stability
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,768")
    options.add_experimental_option("prefs", prefs)
    driver = None
    try:
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
        yield driver
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def parse_args():
    """Parse command‑line arguments."""
    parser = argparse.ArgumentParser(description="Download full CSVs of ZipGrade quizzes.")
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run with a visible browser instead of headless mode."
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Only process quizzes whose title contains this case‑insensitive substring."
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of quizzes to process."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the files that would be downloaded without actually downloading."
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default=None,
        help="Directory where CSVs will be saved. Overrides DOWNLOAD_DIR env variable."
    )
    return parser.parse_args()


def main():
    # Load environment variables from .env file if present
    load_dotenv()
    args = parse_args()
    # Retrieve credentials from environment
    email = os.getenv("ZIPGRADE_EMAIL")
    password = os.getenv("ZIPGRADE_PASSWORD")
    if not email or not password:
        print("Error: You must set ZIPGRADE_EMAIL and ZIPGRADE_PASSWORD in your environment or .env file.", file=sys.stderr)
        sys.exit(1)
    # Determine download directory
    download_dir_str = args.download_dir or os.getenv("DOWNLOAD_DIR") or "./zipgrade_downloads"
    download_dir = Path(download_dir_str).expanduser()
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(
            f"Error: Could not create download directory '{download_dir}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Using download directory: {download_dir.resolve()}")
    # Use headless mode unless headful flag is passed
    headless = not args.headful
    with chrome_driver(headless=headless, download_dir=download_dir) as driver:
        # Login
        login(driver, email, password)
        # Navigate to quizzes page
        navigate_to_quizzes(driver)
        # List quizzes
        quizzes = list_quizzes(driver)
        if not quizzes:
            print("No quizzes found on the quizzes page.")
            return
        # Apply filters
        if args.only:
            substring = args.only.lower()
            quizzes = [q for q in quizzes if substring in q["title"].lower()]
        if args.max:
            quizzes = quizzes[: args.max]
        print(f"Found {len(quizzes)} quizzes to process.")
        # Process quizzes with retry logic to handle rate limiting
        to_process = list(quizzes)
        rate_limited = []

        def process_batch(batch):
            processed = 0
            while batch:
                quiz = batch.pop(0)
                print(f"Processing: {quiz['title']} ({quiz['date_text']})")
                try:
                    open_quiz_and_download(
                        driver,
                        quiz,
                        download_dir=download_dir,
                        dry_run=args.dry_run,
                    )
                    processed += 1
                except PopupError:
                    print(f"  Popup detected on '{quiz['title']}'. Will retry after remaining quizzes.", file=sys.stderr)
                    batch.append(quiz)
                except RateLimitError as rl_err:
                    # Record for later retry
                    print(f"  Rate limit encountered on '{quiz['title']}'. Will retry later.", file=sys.stderr)
                    rate_limited.append(quiz)
                except Exception as ex:
                    print(f"  Error processing '{quiz['title']}': {ex}", file=sys.stderr)
            return processed

        # Initial pass
        processed_count = process_batch(to_process)
        # Retry failed downloads due to rate limiting
        rounds = 0
        max_rounds = 3  # number of retry rounds
        backoff_seconds = 30  # base backoff between rounds
        while rate_limited and rounds < max_rounds and not args.dry_run:
            rounds += 1
            wait_time = backoff_seconds * rounds
            print(f"Waiting {wait_time} seconds before retrying {len(rate_limited)} quizzes...")
            time.sleep(wait_time)
            # Copy and clear the list for this round
            to_retry = rate_limited[:]
            rate_limited.clear()
            processed_this_round = process_batch(to_retry)
            # If nothing processed in this round, break to avoid infinite loop
            if processed_this_round == 0:
                break
        # Report any quizzes that still failed after retries
        if rate_limited:
            print("\nThe following quizzes could not be downloaded due to persistent rate limit errors:")
            for quiz in rate_limited:
                print(f"  - {quiz['title']} ({quiz['date_text']})")


if __name__ == "__main__":
    main()