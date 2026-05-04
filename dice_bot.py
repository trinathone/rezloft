"""
Dice.com Auto-Apply Bot — Production v2
========================================
- Contract + Easy Apply filters only
- Broad queries: roles + states + government + cities
- Target: ~60 applications/hour
- Auto-recovers from crashes, tab deaths, CAPTCHAs
- Sleeps 2am-3am, polls every 60s to wake reliably
- No screenshots, rotating logs, clean dedup
"""

import asyncio
import random
from datetime import datetime

from playwright.async_api import async_playwright, Page, BrowserContext

import config as cfg
from utils import (
    logger, human_delay, short_delay, micro_delay, break_delay,
    bezier_mouse_move, random_mouse_wander, human_type,
    scroll_to_read, STEALTH_JS, random_viewport, random_user_agent,
    ApplicationTracker,
)


class DiceBot:
    def __init__(self):
        self.tracker   = ApplicationTracker()
        self.page: Page = None
        self.context: BrowserContext = None
        self.consecutive_fails = 0
        self.used_urls  = set()
        self.batch_applied = 0
        self.batch_target  = random.randint(*cfg.BATCH_SIZE)
        self.keywords: list = []
        self.query_index: int = 0

    # ── Entry Point ──────────────────────────────────────────
    async def run(self):
        if not cfg.DICE_EMAIL or not cfg.DICE_PASSWORD:
            logger.error("DICE_EMAIL / DICE_PASSWORD not set in .env")
            return

        self.keywords = cfg.load_keywords()
        logger.info(f"Loaded {len(self.keywords)} keywords from keywords.txt")

        logger.info("=" * 55)
        logger.info("Dice Bot v2 — Contract + Easy Apply — ~60 apps/hr")
        logger.info(f"Keywords: {len(self.keywords)} | Sleep: {cfg.SLEEP_HOUR_START}:00-{cfg.SLEEP_HOUR_END}:00")
        logger.info("=" * 55)

        self.used_urls = self.tracker.get_all_applied_urls()
        logger.info(f"Loaded {len(self.used_urls)} previously applied URLs")

        cfg.BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        consecutive_crashes = 0

        while True:
            if self._is_sleep_time():
                await self._sleep_until_wake()
                continue

            try:
                await self._run_session()
                consecutive_crashes = 0
            except Exception as e:
                consecutive_crashes += 1
                logger.error(f"Session crashed (#{consecutive_crashes}): {e}", exc_info=True)
                wait = min(30 * consecutive_crashes, 300)
                logger.info(f"Auto-restarting in {wait}s...")
                await asyncio.sleep(wait)
                if consecutive_crashes >= 10:
                    logger.warning("10 consecutive crashes — cooling down 10 min")
                    await asyncio.sleep(600)
                    consecutive_crashes = 0

    # ── Session ───────────────────────────────────────────────
    async def _run_session(self):
        viewport = random_viewport()
        ua       = random_user_agent()

        async with async_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                f"--window-size={viewport['width']},{viewport['height']}",
            ]

            launch_kwargs = dict(
                user_data_dir=cfg.BROWSER_PROFILE_DIR,
                headless=cfg.HEADLESS,
                args=launch_args,
                slow_mo=random.randint(15, 40),
                viewport=viewport,
                user_agent=ua,
                locale="en-US",
                timezone_id="America/New_York",
                color_scheme=random.choice(["light", "dark", "no-preference"]),
            )

            if cfg.PROXY:
                launch_kwargs["proxy"] = {"server": cfg.PROXY}

            self.context = await p.chromium.launch_persistent_context(**launch_kwargs)
            await self.context.add_init_script(STEALTH_JS)

            self.page = (
                self.context.pages[0]
                if self.context.pages
                else await self.context.new_page()
            )
            await self.page.bring_to_front()

            # Close any stray popup tabs that open during apply
            self.context.on("page", self._handle_popup)

            try:
                await self._login()
                await self._main_loop()
            except BotBlockedError:
                logger.error("Bot blocked — closing session to rotate fingerprint")
            except Exception as e:
                logger.error(f"Session error: {e}", exc_info=True)
            finally:
                s = self.tracker.summary()
                logger.info(
                    f"Session done — Applied={s['applied']} "
                    f"Skipped={s['skipped']} Failed={s['failed']}"
                )
                try:
                    await self.context.close()
                except Exception:
                    pass
                # Minimum cooldown before any browser restart attempt.
                # Prevents rapid-fire relaunch cycles on network dropout
                # (ERR_INTERNET_DISCONNECTED exits _run_session cleanly,
                # so consecutive_crashes never increments — without this
                # sleep the outer loop restarts immediately, causing 70+
                # relaunches per minute).
                await asyncio.sleep(10)

    # ── Popup / New Tab Handler ───────────────────────────────
    def _handle_popup(self, page):
        """Close any external ATS tabs that open on Apply click."""
        async def _close():
            try:
                await asyncio.sleep(1.5)
                logger.info(f"Closing external popup: {page.url}")
                await page.close()
            except Exception:
                pass
        asyncio.ensure_future(_close())

    # ── Login ─────────────────────────────────────────────────
    async def _login(self):
        logger.info("Checking login state...")
        await self.page.goto(
            "https://www.dice.com/dashboard",
            wait_until="domcontentloaded",
            timeout=60_000,
        )
        await short_delay()

        url = self.page.url.lower()
        if "login" not in url and "signin" not in url:
            logger.info("Already logged in.")
            return

        logger.info("Logging in...")

        email_el = self.page.locator('input[name="email"], input[type="email"]').first
        await email_el.wait_for(state="visible", timeout=15_000)
        await bezier_mouse_move(self.page, random.randint(400, 800), random.randint(300, 500))
        await human_type(email_el, cfg.DICE_EMAIL)
        await short_delay()

        await self.page.locator('button[type="submit"]').first.click()
        await short_delay()

        pw_el = self.page.locator('input[type="password"]').first
        try:
            await pw_el.wait_for(state="visible", timeout=8_000)
            await human_type(pw_el, cfg.DICE_PASSWORD)
            await short_delay()
            await self.page.locator('button[type="submit"]').first.click()
            await short_delay()
        except Exception:
            logger.warning("Password field not found — complete login in browser.")

        # Wait up to 5 min for manual login / 2FA
        for i in range(60):
            await asyncio.sleep(5)
            url = self.page.url.lower()
            if "login" not in url and "signin" not in url and "verify" not in url:
                logger.info("Login successful.")
                return
            if i % 6 == 0 and i > 0:
                logger.info(f"Waiting for login... {i*5}s elapsed")

        raise RuntimeError("Login timed out after 5 minutes")

    # ── Main Loop ─────────────────────────────────────────────
    async def _main_loop(self):
        page_num = 1
        current_query = self.keywords[self.query_index]
        consecutive_skipped_pages = 0

        while True:
            if self._is_sleep_time():
                return

            # Batch break
            if self.batch_applied >= self.batch_target:
                mins = random.uniform(*cfg.BATCH_BREAK_MINUTES)
                logger.info(f"Batch of {self.batch_applied} done. Resting {mins:.1f} min...")
                await asyncio.sleep(mins * 60)
                self.batch_target  = random.randint(*cfg.BATCH_SIZE)
                self.batch_applied = 0
                self.query_index = (self.query_index + 1) % len(self.keywords)
                current_query = self.keywords[self.query_index]
                page_num = 1
                consecutive_skipped_pages = 0

            # Too many consecutive fails — rotate to next keyword
            if self.consecutive_fails >= cfg.MAX_CONSECUTIVE_FAILS:
                logger.warning("Too many failures — rotating keyword and pausing 90s")
                self.consecutive_fails = 0
                self.query_index = (self.query_index + 1) % len(self.keywords)
                current_query = self.keywords[self.query_index]
                page_num = 1
                consecutive_skipped_pages = 0
                await asyncio.sleep(90)

            # Page watchdog
            if not await self._ensure_page_alive():
                logger.error("Page unrecoverable — restarting session")
                return

            logger.info(f"Query: '{current_query}' | Page {page_num}")
            await self._run_search(current_query, page_num)

            jobs = await self._collect_jobs()
            if not jobs:
                logger.info(f"No jobs on page {page_num} — switching to next keyword")
                self.query_index = (self.query_index + 1) % len(self.keywords)
                current_query = self.keywords[self.query_index]
                page_num = 1
                consecutive_skipped_pages = 0
                await asyncio.sleep(random.uniform(3, 8))
                continue

            random.shuffle(jobs)
            max_this_page  = random.randint(5, 10)
            applied_this_page = 0

            for job in jobs:
                if self._is_sleep_time():
                    return
                if applied_this_page >= max_this_page:
                    break
                if self.batch_applied >= self.batch_target:
                    break
                if self.consecutive_fails >= cfg.MAX_CONSECUTIVE_FAILS:
                    break
                if job["url"] in self.used_urls:
                    continue

                self.used_urls.add(job["url"])
                await self._apply_to_job(job)
                applied_this_page += 1
                self.batch_applied += 1

                if (
                    self.tracker.session_count > 0
                    and self.tracker.session_count % cfg.BREAK_EVERY_N_APPS == 0
                ):
                    await break_delay()

                await human_delay()
                await random_mouse_wander(self.page)

            # Exhaustion detection: jobs exist but all already applied to
            if applied_this_page == 0 and len(jobs) > 0:
                consecutive_skipped_pages += 1
                logger.debug(
                    f"All jobs on page {page_num} already applied — "
                    f"skipped page {consecutive_skipped_pages}/3"
                )
                if consecutive_skipped_pages >= 3:
                    logger.info(
                        f"Keyword '{current_query}' exhausted "
                        f"(3 consecutive all-skipped pages) — rotating"
                    )
                    self.query_index = (self.query_index + 1) % len(self.keywords)
                    current_query = self.keywords[self.query_index]
                    page_num = 1
                    consecutive_skipped_pages = 0
                    await asyncio.sleep(random.uniform(3, 8))
                    continue
            else:
                consecutive_skipped_pages = 0

            # Short rest then next page
            rest = random.uniform(3, 8)
            logger.info(f"Next page in {rest:.0f}s...")
            await asyncio.sleep(rest)
            page_num += 1

    # ── Search ────────────────────────────────────────────────
    async def _run_search(self, keyword: str, page: int = 1):
        params = f"?q={keyword.replace(' ', '+')}"
        if cfg.JOB_LOCATION:
            params += f"&location={cfg.JOB_LOCATION.replace(' ', '+')}"
        if cfg.REMOTE_ONLY:
            params += "&filters.isRemote=true"
        if "contract" in cfg.JOB_TYPES:
            params += "&filters.employmentType=CONTRACTS"
        elif "fulltime" in cfg.JOB_TYPES:
            params += "&filters.employmentType=FULLTIME"
        if cfg.EASY_APPLY_ONLY:
            params += "&filters.easyApply=true"
        params += f"&page={page}"

        url = f"https://www.dice.com/jobs{params}"
        logger.info(f"Loading search: {keyword} (page {page})")

        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except Exception:
            # Fallback — just wait for network to settle a bit
            await asyncio.sleep(3)

        await short_delay()
        await scroll_to_read(self.page)

    # ── Collect Jobs ──────────────────────────────────────────
    async def _collect_jobs(self) -> list:
        jobs = []
        seen_urls = set()

        try:
            await self.page.wait_for_selector(
                'a[data-testid="job-search-job-detail-link"]',
                timeout=12_000,
            )
        except Exception:
            return jobs

        raw = await self.page.evaluate("""() => {
            const links = document.querySelectorAll('a[data-testid="job-search-job-detail-link"]');
            const results = [];
            for (const a of links) {
                const title = (a.getAttribute('aria-label') || a.innerText || '').trim();
                const href = a.href;
                if (title && href) results.push({ title, url: href });
            }
            return results;
        }""")

        for item in raw:
            url = item["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            jobs.append({
                "title":    item["title"],
                "company":  "",
                "location": "",
                "url":      url,
            })

        logger.info(f"Found {len(jobs)} jobs")
        return jobs

    # ── Page Watchdog ─────────────────────────────────────────
    async def _ensure_page_alive(self) -> bool:
        try:
            await self.page.evaluate("1")
            return True
        except Exception:
            logger.warning("Page died — attempting tab recovery...")
            try:
                self.page = await self.context.new_page()
                await self.context.add_init_script(STEALTH_JS)
                logger.info("Recovered: new tab opened.")
                return True
            except Exception as e:
                logger.error(f"Context also dead: {e}")
                return False

    # ── Apply ─────────────────────────────────────────────────
    async def _apply_to_job(self, job: dict):
        try:
            if not await self._ensure_page_alive():
                raise RuntimeError("Page unrecoverable")

            logger.info(f"Applying: {job['title']}")

            try:
                await self.page.goto(
                    job["url"], wait_until="domcontentloaded", timeout=45_000
                )
            except Exception:
                await asyncio.sleep(2)

            await short_delay()
            await scroll_to_read(self.page)

            # Check for block BEFORE clicking anything
            if await self._detect_block():
                raise BotBlockedError("CAPTCHA or block detected")

            # Find Apply button
            apply_btn = None
            for sel in [
                'a[data-testid="apply-button"]',
                'button[data-testid="apply-button"]',
                'a:has-text("Easy Apply")',
                'button:has-text("Easy Apply")',
                'a:has-text("Apply")',
            ]:
                loc = self.page.locator(sel).first
                try:
                    if await loc.is_visible(timeout=1_500):
                        apply_btn = loc
                        break
                except Exception:
                    continue

            if not apply_btn:
                self.tracker.log(
                    job["title"], job["company"], job["location"],
                    job["url"], "skipped", "No Apply button"
                )
                return

            # Skip if button is disabled — means already applied on Dice
            # Check via JS for instant response, no timeout needed
            is_disabled = await self.page.evaluate("""() => {
                const btn = document.querySelector('[data-testid="apply-button"]');
                return btn ? btn.disabled || btn.getAttribute('data-disabled') === 'true' : false;
            }""")
            if is_disabled:
                self.tracker.log(
                    job["title"], job["company"], job["location"],
                    job["url"], "skipped", "Already applied (button disabled)"
                )
                return

            # Bezier click
            box = await apply_btn.bounding_box()
            if box:
                await bezier_mouse_move(
                    self.page,
                    int(box["x"] + box["width"] / 2 + random.randint(-5, 5)),
                    int(box["y"] + box["height"] / 2 + random.randint(-3, 3)),
                )
                await micro_delay()

            await apply_btn.click()
            await asyncio.sleep(random.uniform(1.5, 3))

            await self._handle_apply_form()

            self.tracker.log(
                job["title"], job["company"], job["location"],
                job["url"], "applied"
            )
            self.consecutive_fails = 0

        except BotBlockedError:
            raise  # bubble up to session level — triggers full restart

        except Exception as e:
            self.consecutive_fails += 1
            logger.error(f"Failed: {job['title']} — {e}")
            self.tracker.log(
                job["title"], job["company"], job["location"],
                job["url"], "failed", str(e)[:200]
            )

    # ── Form Handler ──────────────────────────────────────────
    async def _handle_apply_form(self):
        await asyncio.sleep(1.5)

        # Walk through up to 8 form steps
        for _ in range(8):
            # Try Submit first
            for sel in [
                'button:has-text("Submit Application")',
                'button:has-text("Submit")',
                'a:has-text("Submit Application")',
                'a:has-text("Submit")',
            ]:
                btn = self.page.locator(sel).first
                try:
                    if await btn.is_visible(timeout=1_000):
                        box = await btn.bounding_box()
                        if box:
                            await bezier_mouse_move(
                                self.page,
                                int(box["x"] + box["width"] / 2),
                                int(box["y"] + box["height"] / 2),
                            )
                        await micro_delay()
                        await btn.click()
                        logger.info("Submitted.")
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue

            # Try Next / Continue
            found_next = False
            for sel in [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'a:has-text("Next")',
                'a:has-text("Continue")',
            ]:
                btn = self.page.locator(sel).first
                try:
                    if await btn.is_visible(timeout=1_000):
                        await btn.click()
                        await short_delay()
                        found_next = True
                        break
                except Exception:
                    continue

            if not found_next:
                break

        await asyncio.sleep(1.5)

    # ── Block Detection ───────────────────────────────────────
    async def _detect_block(self) -> bool:
        try:
            for sel in [
                'iframe[src*="captcha"]',
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                '#captcha-container',
                '.captcha-wrapper',
                '[data-testid="captcha"]',
            ]:
                try:
                    if await self.page.locator(sel).first.is_visible(timeout=800):
                        return True
                except Exception:
                    continue

            title = (await self.page.title()).lower()
            for signal in ["access denied", "403", "blocked", "too many requests", "429"]:
                if signal in title:
                    return True

            # Also check page body for block signals
            body = await self.page.evaluate("() => document.body?.innerText?.toLowerCase() || ''")
            for signal in ["you have been blocked", "unusual traffic", "verify you are human"]:
                if signal in body:
                    return True

        except Exception:
            pass
        return False

    # ── Sleep Schedule ────────────────────────────────────────
    def _is_sleep_time(self) -> bool:
        hour = datetime.now().hour
        return cfg.SLEEP_HOUR_START <= hour < cfg.SLEEP_HOUR_END

    async def _sleep_until_wake(self):
        logger.info(
            f"Sleep time ({cfg.SLEEP_HOUR_START}:00-{cfg.SLEEP_HOUR_END}:00). "
            f"Polling every 60s until {cfg.SLEEP_HOUR_END}:00..."
        )
        while self._is_sleep_time():
            await asyncio.sleep(60)
        logger.info("Woke up. Resuming...")


# ── Custom Exceptions ─────────────────────────────────────────
class BotBlockedError(Exception):
    pass


# ── Entry Point ───────────────────────────────────────────────
async def main():
    bot = DiceBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
