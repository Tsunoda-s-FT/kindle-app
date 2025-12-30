"""Kindle Web Reader Utilities

Common functions for browser control and Kindle-specific operations.
"""

import os
import re
import logging
from typing import Optional, Tuple
from playwright.async_api import Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
KINDLE_LIBRARY_URL = "https://read.amazon.co.jp/kindle-library"
KINDLE_READER_URL = "https://read.amazon.co.jp/?asin={asin}"
DEFAULT_OUTPUT_DIR = "./kindle-captures"
DEFAULT_CHROME_PROFILE = "~/Library/Application Support/Google/Chrome"
DEFAULT_FALLBACK_PROFILE = "~/Library/Application Support/Google/Chrome-Kindle"


async def create_browser_context(
    profile_path: str = DEFAULT_CHROME_PROFILE,
    headless: bool = False,
    fallback_profile_path: Optional[str] = None,
    viewport_width: int = 3840,
    viewport_height: int = 2160
) -> Tuple[BrowserContext, any]:
    """
    Create Playwright browser context with Chrome profile.

    Args:
        profile_path: Path to Chrome user data directory
        headless: Whether to run in headless mode

    Returns:
        Tuple[BrowserContext, Playwright]: Browser context and playwright instance

    Raises:
        Exception: If browser fails to launch
    """
    from playwright.async_api import async_playwright

    def _looks_like_profile_lock(error: Exception) -> bool:
        message = str(error)
        return "ProcessSingleton" in message or "profile is already in use" in message

    async def _launch_context(user_data_dir: str) -> BrowserContext:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            channel="chrome",  # Use system Chrome
            viewport={'width': viewport_width, 'height': viewport_height},
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--start-maximized',  # Start maximized
            ]
        )
        return context

    profile_path = os.path.expanduser(profile_path)
    fallback_profile_path = os.path.expanduser(fallback_profile_path) if fallback_profile_path else None

    logger.info(f"Launching browser with profile: {profile_path}")
    logger.info(f"Headless mode: {headless}")

    playwright = await async_playwright().start()

    try:
        context = await _launch_context(profile_path)
        logger.info("Browser launched successfully")
        logger.info(f"Viewport set to: {viewport_width}x{viewport_height}")
        return context, playwright

    except Exception as e:
        if fallback_profile_path and _looks_like_profile_lock(e):
            logger.warning("Chrome profile is locked, retrying with fallback profile...")
            logger.info(f"Launching browser with fallback profile: {fallback_profile_path}")
            try:
                context = await _launch_context(fallback_profile_path)
                logger.info("Browser launched successfully (fallback profile)")
                logger.info(f"Viewport set to: {viewport_width}x{viewport_height}")
                return context, playwright
            except Exception as fallback_error:
                logger.error(f"Failed to launch fallback profile: {fallback_error}")

        logger.error(f"Failed to launch browser: {e}")
        logger.error("Make sure Chrome is not running and try again")
        await playwright.stop()
        raise


async def dismiss_modal_dialogs(page: Page) -> bool:
    """
    Dismiss any modal dialogs that may appear (e.g., "Most Recent Page Read").

    Args:
        page: Playwright Page object

    Returns:
        bool: True if successful
    """
    try:
        # Check for "Most Recent Page Read" dialog
        # Look for the backdrop element that appears with ion-alert
        modal_selector = 'ion-alert[is-open="true"]'

        # Wait a moment for any dialogs to appear
        await page.wait_for_timeout(500)

        # Check if modal exists
        modal = await page.query_selector(modal_selector)
        if modal:
            logger.info("Found modal dialog, attempting to dismiss...")

            # Try to click "No" button to stay at current location
            # The button text might be "No" or localized version
            try:
                # Click the first button (usually "No" or "Cancel")
                await page.click('ion-alert button:first-of-type', timeout=3000)
                logger.info("Modal dialog dismissed successfully")
                await page.wait_for_timeout(500)
                return True
            except Exception as e:
                logger.warning(f"Failed to click modal button: {e}")
                # Try pressing Escape key as fallback
                try:
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                    logger.info("Modal dialog dismissed with Escape key")
                    return True
                except:
                    pass

        return True
    except Exception as e:
        logger.warning(f"Error dismissing modal dialogs: {e}")
        return True  # Continue anyway


async def check_session_valid(page: Page) -> bool:
    """
    Check if Kindle session is still valid (not logged out).

    Args:
        page: Playwright Page object

    Returns:
        bool: True if session is valid
    """
    current_url = page.url

    # Check if redirected to login page
    if "signin" in current_url or "login" in current_url:
        logger.warning("Session expired - redirected to login page")
        return False

    # Check for KindleRenderer availability
    try:
        has_renderer = await page.evaluate("typeof KindleRenderer !== 'undefined'")
        if not has_renderer:
            logger.warning("KindleRenderer not found - session may be invalid")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking session validity: {e}")
        return False


async def detect_login_state(page: Page) -> str:
    """
    Detect login state for Kindle Web Reader.

    Returns:
        str: "logged_in", "login_required", or "unknown"
    """
    try:
        current_url = page.url or ""
        if "signin" in current_url or "login" in current_url:
            return "login_required"

        login_selectors = [
            "#ap_email",
            "#ap_password",
            'input[type="email"]',
            'input[type="password"]',
        ]
        for selector in login_selectors:
            try:
                if await page.query_selector(selector):
                    return "login_required"
            except Exception:
                continue

        has_renderer = await page.evaluate("typeof KindleRenderer !== 'undefined'")
        if has_renderer:
            return "logged_in"
    except Exception:
        pass

    return "unknown"


async def set_layout_mode(page: Page, mode: str = "single") -> bool:
    """
    Change Kindle reader layout mode.

    Args:
        page: Playwright Page object
        mode: "single" or "double" column layout

    Returns:
        bool: True if successful
    """
    async def click_first(selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                await page.click(selector, timeout=5000)
                return True
            except Exception:
                continue
        return False

    try:
        logger.info(f"Setting layout mode to: {mode}")

        settings_selectors = [
            '[aria-label="Reader settings"]',
            '[aria-label="リーダー設定"]',
            '[aria-label="表示設定"]',
            'button:has-text("Aa")',
        ]

        if not await click_first(settings_selectors):
            logger.warning("Reader settings button not found")
            return False

        await page.wait_for_timeout(500)

        if mode == "single":
            option_selectors = [
                'text="Single Column"',
                'text="単一列"',
                'text="1列"',
                'text="1 カラム"',
                'text="1カラム"',
            ]
        elif mode == "double":
            option_selectors = [
                'text="Two Columns"',
                'text="見開き"',
                'text="2列"',
                'text="2 カラム"',
                'text="2カラム"',
            ]
        else:
            logger.warning(f"Unknown layout mode: {mode}, skipping")
            return False

        if not await click_first(option_selectors):
            logger.warning("Layout option not found")
            return False

        await page.wait_for_timeout(300)

        close_selectors = [
            'button:has-text("Close")',
            'button:has-text("閉じる")',
            'button:has-text("完了")',
            'button:has-text("OK")',
        ]

        if not await click_first(close_selectors):
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass

        await page.wait_for_timeout(500)

        logger.info(f"Layout mode set to {mode}")
        return True

    except Exception as e:
        logger.error(f"Failed to set layout mode: {e}")
        return False


async def goto_position(page: Page, position: int) -> bool:
    """
    Navigate to specific position using KindleRenderer API.

    Args:
        page: Playwright Page object
        position: Position number to navigate to

    Returns:
        bool: True if successful
    """
    try:
        logger.debug(f"Navigating to position: {position}")
        await page.evaluate(f"KindleRenderer.gotoPosition({position})")
        return True
    except Exception as e:
        logger.error(f"Failed to goto position {position}: {e}")
        return False


async def next_page(page: Page) -> bool:
    """
    Navigate to next page using KindleRenderer API.

    Args:
        page: Playwright Page object

    Returns:
        bool: True if successful
    """
    try:
        await page.evaluate("KindleRenderer.nextScreen()")
        return True
    except Exception as e:
        logger.error(f"Failed to go to next page: {e}")
        return False


async def has_next_page(page: Page) -> bool:
    """
    Check if there is a next page.

    Args:
        page: Playwright Page object

    Returns:
        bool: True if next page exists
    """
    try:
        has_next = await page.evaluate("KindleRenderer.hasNextScreen()")
        return has_next
    except Exception as e:
        logger.error(f"Failed to check next page: {e}")
        return False


async def get_current_location(page: Page) -> dict:
    """
    Parse current location from page (e.g., "Location 101 of 241 41%").

    Args:
        page: Playwright Page object

    Returns:
        dict: {current: int, total: int, percent: int} or empty dict on error
    """
    try:
        # Get text content from the page
        text = await page.evaluate("document.body.textContent")

        patterns = [
            r'(?:Location|位置)\s*[:：]?\s*(\d+)\s*(?:of|/|の)\s*(\d+)\s*(\d+)\s*[％%]'
        ]

        for pattern in patterns:
            location_match = re.search(pattern, text)
            if location_match:
                return {
                    'current': int(location_match.group(1)),
                    'total': int(location_match.group(2)),
                    'percent': int(location_match.group(3))
                }

        # Fallback to KindleRenderer positions if text parsing fails
        try:
            current_pos = await page.evaluate("KindleRenderer.getPosition?.()")
            total_pos = await page.evaluate("KindleRenderer.getMaximumPosition?.()")
            if isinstance(current_pos, (int, float)) and isinstance(total_pos, (int, float)):
                if current_pos > 0 and total_pos > 0:
                    percent = int((current_pos / total_pos) * 100)
                    return {
                        'current': int(current_pos),
                        'total': int(total_pos),
                        'percent': percent
                    }
        except Exception:
            pass

        logger.warning("Could not parse location from page")
        return {}

    except Exception as e:
        logger.error(f"Failed to get current location: {e}")
        return {}


async def get_page_position_range(page: Page) -> Optional[Tuple[int, int]]:
    """
    Get current page position range from KindleRenderer.

    Args:
        page: Playwright Page object

    Returns:
        Tuple[int, int]: (current_top, current_bottom) or None if unavailable
    """
    try:
        position_range = await page.evaluate("KindleRenderer.getPagePositionRange?.()")
        if isinstance(position_range, dict):
            current_top = position_range.get("currentTopOfPage")
            current_bottom = position_range.get("currentBottomOfPage")
            if isinstance(current_top, (int, float)) and isinstance(current_bottom, (int, float)):
                return (int(current_top), int(current_bottom))
    except Exception as e:
        logger.debug(f"Failed to get page position range: {e}")
    return None


async def get_position_range(page: Page) -> Tuple[int, int]:
    """
    Get position range (min, max) from KindleRenderer.

    Args:
        page: Playwright Page object

    Returns:
        Tuple[int, int]: (min_position, max_position)
    """
    try:
        min_pos = await page.evaluate("KindleRenderer.getMinimumPosition()")
        max_pos = await page.evaluate("KindleRenderer.getMaximumPosition()")

        logger.info(f"Position range: {min_pos} - {max_pos}")
        return (min_pos, max_pos)

    except Exception as e:
        logger.error(f"Failed to get position range: {e}")
        raise


async def wait_for_spinner_to_disappear(page: Page, timeout: float = 10.0) -> bool:
    """
    Wait for loading spinner to disappear.

    Args:
        page: Playwright Page object
        timeout: Maximum wait time in seconds

    Returns:
        bool: True if spinner disappeared or not found
    """
    try:
        # Wait for loading spinner to disappear
        # Kindle uses various elements for loading indicator
        spinner_selectors = [
            '[role="progressbar"]',
            '.progressBar',
            '[class*="loading"]',
            '[class*="spinner"]',
        ]

        # Check if any spinner exists
        for selector in spinner_selectors:
            try:
                spinner = await page.query_selector(selector)
                if spinner:
                    logger.debug(f"Found spinner: {selector}, waiting for it to disappear...")
                    # Wait for spinner to be hidden
                    await page.wait_for_selector(selector, state="hidden", timeout=timeout * 1000)
                    logger.debug(f"Spinner disappeared: {selector}")
                    return True
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for spinner {selector} to disappear")
                continue
            except Exception:
                continue

        # Also check for loading animation via JavaScript
        try:
            await page.wait_for_function(
                """() => {
                    // Check if there's any visible loading indicator
                    const spinners = document.querySelectorAll('[role="progressbar"], [class*="loading"], [class*="spinner"]');
                    for (let spinner of spinners) {
                        const style = window.getComputedStyle(spinner);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                            return false; // Still loading
                        }
                    }
                    return true; // No visible spinners
                }""",
                timeout=timeout * 1000
            )
        except PlaywrightTimeoutError:
            logger.warning("Timeout waiting for loading indicators via JS")
        except Exception:
            pass

        return True

    except Exception as e:
        logger.warning(f"Error checking for spinner: {e}")
        return True  # Continue anyway


async def wait_for_page_load(
    page: Page,
    timeout: float = 3.0,
    strategy: str = "hybrid"
) -> bool:
    """
    Wait for page to finish loading after navigation.

    Args:
        page: Playwright Page object
        timeout: Maximum wait time in seconds
        strategy: "location_change", "fixed", or "hybrid"

    Returns:
        bool: True if page loaded successfully
    """
    if strategy == "fixed":
        # Simple fixed timeout with spinner check
        spinner_timeout = max(5.0, timeout)
        await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)
        await page.wait_for_timeout(int(timeout * 1000))
        return True

    elif strategy == "location_change":
        # Wait for location text to change
        try:
            initial_location = await get_current_location(page)
            if not initial_location:
                # Fallback to fixed wait
                spinner_timeout = max(5.0, timeout)
                await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)
                await page.wait_for_timeout(int(timeout * 1000))
                return True

            initial_current = initial_location.get('current', 0)

            # Wait for location to change
            await page.wait_for_function(
                f"""() => {{
                    const text = document.body.textContent || "";
                    const match = text.match(/(?:Location|位置)\\s*[:：]?\\s*(\\d+)\\s*(?:of|\\/|の)/);
                    if (match) {{
                        return parseInt(match[1], 10) !== {initial_current};
                    }}
                    try {{
                        const pos = (typeof KindleRenderer !== 'undefined' && KindleRenderer.getPosition)
                            ? KindleRenderer.getPosition()
                            : null;
                        return (typeof pos === 'number' && pos !== {initial_current});
                    }} catch (e) {{
                        return false;
                    }}
                }}""",
                timeout=timeout * 1000
            )

            # Wait for spinner to disappear
            spinner_timeout = max(5.0, timeout)
            await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)

            # Additional settling time for images/fonts to load
            await page.wait_for_timeout(1000)
            return True

        except PlaywrightTimeoutError:
            logger.warning("Location change timeout, using fixed wait")
            spinner_timeout = max(5.0, timeout)
            await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)
            await page.wait_for_timeout(int(timeout * 1000))
            return True

    else:  # hybrid (default)
        # Try location_change with fallback to fixed
        try:
            initial_location = await get_current_location(page)

            if initial_location:
                initial_current = initial_location.get('current', 0)

                try:
                    await page.wait_for_function(
                        f"""() => {{
                            const text = document.body.textContent || "";
                            const match = text.match(/(?:Location|位置)\\s*[:：]?\\s*(\\d+)\\s*(?:of|\\/|の)/);
                            if (match) {{
                                return parseInt(match[1], 10) !== {initial_current};
                            }}
                            try {{
                                const pos = (typeof KindleRenderer !== 'undefined' && KindleRenderer.getPosition)
                                    ? KindleRenderer.getPosition()
                                    : null;
                                return (typeof pos === 'number' && pos !== {initial_current});
                            }} catch (e) {{
                                return false;
                            }}
                        }}""",
                        timeout=timeout * 1000
                    )
                except PlaywrightTimeoutError:
                    # Fallback to fixed wait
                    logger.debug("Location change timeout, continuing...")
            else:
                # No location found, just wait a bit
                await page.wait_for_timeout(500)

            # Wait for spinner to disappear (most important)
            spinner_timeout = max(5.0, timeout)
            await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)

            # Additional settling time for content to fully render
            await page.wait_for_timeout(1000)
            return True

        except Exception as e:
            logger.warning(f"Hybrid wait error: {e}, using fallback")
            spinner_timeout = max(5.0, timeout)
            await wait_for_spinner_to_disappear(page, timeout=spinner_timeout)
            await page.wait_for_timeout(int(timeout * 1000))
            return True
