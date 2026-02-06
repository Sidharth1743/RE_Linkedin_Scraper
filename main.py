#!/usr/bin/env python3
"""
Main workflow:
1) Login (cookies/session)
2) Search profiles by keyword
3) For each profile, either download PDF or scrape posts
"""

import asyncio
import os
import sys
import time
import random
from datetime import datetime
from threading import Thread
from queue import Queue

from playwright.sync_api import sync_playwright

from linkedin_activity_fetcher import LinkedInActivityFetcher
from download_pdf import ProfilePdfDownloader


# --- Import linkedin_scraper from the other codebase (reference repo) ---
LINKEDIN_SCRAPER_REPO = os.getenv("LINKEDIN_SCRAPER_REPO", "/home/sidharth/Desktop/linkedin_scraper")
if os.path.isdir(LINKEDIN_SCRAPER_REPO) and LINKEDIN_SCRAPER_REPO not in sys.path:
    sys.path.insert(0, LINKEDIN_SCRAPER_REPO)

try:
    from linkedin_scraper.scrapers.person_search import PersonSearchScraper
    from linkedin_scraper.core.browser import BrowserManager
except Exception as e:
    print("❌ Could not import linkedin_scraper from the reference repo.")
    print(f"   Expected path: {LINKEDIN_SCRAPER_REPO}")
    print(f"   Error: {e}")
    sys.exit(1)


async def search_profiles(keywords: str, limit: int, max_pages: int, session_path: str) -> list[str]:
    """Search for profiles by keyword using the reference scraper."""
    async with BrowserManager(headless=False, slow_mo=200) as browser:
        await browser.load_session(session_path)
        print("✓ Session loaded")

        search_scraper = PersonSearchScraper(browser.page)
        print("🔍 Searching for people...")
        profile_urls = await search_scraper.search(
            keywords=keywords, limit=limit, max_pages=max_pages
        )
        return profile_urls


def run_async(coro):
    """Run coroutine in a safe way even if an event loop is already running."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        result_queue: Queue = Queue()

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(coro)
                result_queue.put((True, result))
            except Exception as e:
                result_queue.put((False, e))
            finally:
                loop.close()

        t = Thread(target=_runner, daemon=True)
        t.start()
        ok, payload = result_queue.get()
        if ok:
            return payload
        raise payload


def _prompt_int(prompt: str, default: int) -> int:
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        print(f"⚠️ Invalid number, using default {default}")
        return default


def _safe_name(value: str) -> str:
    return (
        value.replace("https://", "")
        .replace("http://", "")
        .replace("/", "_")
        .replace(":", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
    )


def _username_from_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if "linkedin.com/in/" in value:
        return value.split("linkedin.com/in/")[-1]
    if value.startswith("http"):
        return value.split("/")[-1]
    return value


def _extract_download_url(pdf_data: dict) -> str | None:
    root_data = pdf_data.get("data", {})
    if "data" in root_data:
        root_data = root_data["data"]
    action_result = root_data.get("doSaveToPdfV2IdentityDashProfileActionsV2", {})
    return action_result.get("result", {}).get("downloadUrl")


def main():
    print("=" * 80)
    print("🔗 LinkedIn Search → Action Workflow")
    print("=" * 80)

    keywords = input("\n📝 Enter search keywords: ").strip()
    if not keywords:
        print("❌ Keywords cannot be empty")
        return

    limit = _prompt_int("🧮 Profiles limit (default 5): ", 5)
    max_pages = _prompt_int("📄 Max pages (default 1): ", 1)

    print("\nChoose action for each profile:")
    print("1) Download profile PDF")
    print("2) Scrape posts/activity")
    choice = input("Enter 1 or 2: ").strip()
    if choice not in {"1", "2"}:
        print("❌ Invalid choice")
        return

    ranges_input = None
    if choice == "2":
        ranges_input = input("\n📝 Enter target posts range (e.g., 60, 80, 100): ").strip()
        if not ranges_input:
            print("❌ Target range cannot be empty")
            return

    session_path = "linkedin_session.json"

    worker = ProfilePdfDownloader() if choice == "1" else LinkedInActivityFetcher()

    # --- Login once and save session state for async search ---
    with sync_playwright() as p:
        worker.p = p
        if not worker.login_to_linkedin():
            print("❌ Failed to initialize session")
            return

        # Save Playwright storage state so BrowserManager can load it
        if worker.context:
            worker.context.storage_state(path=session_path)

        # --- Search profiles (async) ---
        try:
            profile_urls = run_async(
                search_profiles(keywords, limit, max_pages, session_path)
            )
        except Exception as e:
            print(f"❌ Search failed: {e}")
            worker.close()
            return

        print(f"\n✓ Found {len(profile_urls)} profiles")
        if not profile_urls:
            worker.close()
            return

        # --- Act on each profile ---
        if choice == "1":
            json_dir = "output/pdf_json"
            pdf_dir = "output/username_pdf"
            os.makedirs(json_dir, exist_ok=True)
            os.makedirs(pdf_dir, exist_ok=True)

            results = []
            for i, profile_url in enumerate(profile_urls, 1):
                print(f"\n{'=' * 60}")
                print(f"[{i}/{len(profile_urls)}] {profile_url}")
                print(f"{'=' * 60}")

                urn = worker.extract_profile_urn(profile_url)
                if not urn:
                    print("   ❌ Failed to resolve URN")
                    continue

                pdf_data = worker.get_pdf_download_url(urn)
                if not pdf_data:
                    print("   ❌ Failed to get PDF data")
                    continue

                results.append({"profile": profile_url, "urn": urn, "data": pdf_data})

                download_url = _extract_download_url(pdf_data)
                if download_url:
                    filename = _safe_name(_username_from_url(profile_url))
                    pdf_path = os.path.join(pdf_dir, f"{filename}.pdf")
                    worker.download_file(download_url, pdf_path)
                else:
                    print("   ⚠️ downloadUrl not found in response")

                time.sleep(random.uniform(2, 5))

            if results:
                json_path = os.path.join(json_dir, "pdf_downloads.json")
                with open(json_path, "w") as f:
                    import json
                    json.dump(results, f, indent=2)
                print(f"\n💾 Saved {len(results)} results to {json_path}")

        else:
            for i, profile_url in enumerate(profile_urls, 1):
                print(f"\n{'=' * 60}")
                print(f"[{i}/{len(profile_urls)}] {profile_url}")
                print(f"{'=' * 60}")

                target_username = _username_from_url(profile_url)
                profile_urn = worker.extract_profile_urn(profile_url)
                if not profile_urn:
                    print("   ❌ Failed to extract profile URN")
                    continue

                ranges = worker.parse_ranges(ranges_input)
                if not ranges:
                    print("   ❌ Failed to parse target range")
                    continue

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_username = _safe_name(target_username).replace("linkedin.com_in_", "")
                target_range_str = f"0-{ranges[-1][1]}"
                session_dir_name = f"{safe_username}_{target_range_str}_{timestamp}"
                worker.session_dir = os.path.join("linkedin_data", session_dir_name)
                os.makedirs(worker.session_dir, exist_ok=True)

                pagination_token = None
                saved_files = []

                for idx, (start, end) in enumerate(ranges, 1):
                    count = end - start

                    if idx == 1:
                        activity_data = worker.fetch_profile_activity(
                            profile_urn, count=count, start=start, pagination_token=None
                        )
                    else:
                        if not pagination_token:
                            print("   ⚠️ No pagination token for next range")
                            break
                        activity_data = worker.fetch_profile_activity(
                            profile_urn, count=count, start=start, pagination_token=pagination_token
                        )

                    if not activity_data:
                        print(f"   ❌ Failed to fetch range {start}-{end}")
                        break

                    range_str = f"{start}-{end}"
                    filepath = worker.save_activity_data(
                        target_username, profile_urn, activity_data, page=idx, range_str=range_str
                    )
                    if filepath:
                        saved_files.append((range_str, filepath))

                    pagination_token = worker.extract_pagination_token(activity_data)
                    if not pagination_token and idx < len(ranges):
                        print("   ⚠️ No pagination token found in response")
                        break

                    time.sleep(1)

                if saved_files:
                    total_posts, all_posts_data = worker.process_posts_from_files(
                        saved_files, target_username
                    )
                    if all_posts_data:
                        worker.download_media_for_posts(all_posts_data, worker.session_dir)

                time.sleep(random.uniform(2, 5))

        worker.close()


if __name__ == "__main__":
    main()
