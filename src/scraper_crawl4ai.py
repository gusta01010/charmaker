import asyncio
import subprocess
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Environment configurations to silence Node warnings
os.environ["NODE_OPTIONS"] = "--no-deprecation"

class ScraperCrawl4AI:
    def __init__(self):
        # Selectors to remove unwanted elements (exactly as in the original filter)
        self.excluded_selector = (
            ".toc, .wds-global-footer, #catlinks, .printfooter, .global-top-navigation, "
            ".notifications-placeholder, #community-navigation, .community-header-wrapper, "
            ".global-explore-navigation, .global-footer, .global-footer__content, "
            ".global-footer__bottom, .fandom-community-header, #navigator, #header, "
            ".full_hr, .menubar, #toolbar, #lastmodified, #footer, #cosmos-footer, "
            "#cosmos-toolbar, .cosmos-header, #cosmos-banner, .mw-header, #mw-head, "
            "#mw-panel, #mw-page-base, #mw-head-base, .mw-footer, .mw-footer-container, "
            ".vector-column-end, .vector-sticky-pinned-container, .azltable, .page__right-rail, "
            "#google_translate_element, #onetrust-banner-sdk, #onetrust-consent-sdk, "
            "#top_leaderboard-odyssey-wrapper, .mw-cookiewarning-container, .nv-view, .nv-talk, "
            ".nv-edit, .navibox, .pcomment, #google_translate_element, #goog-gt-tt, "
            "#goog-gt-vt, .adthrive-comscore, .adthrive-footer-message, .adthrive-ad, "
            ".adthrive-footer, .raptive-content-terms-modal, .adthrive-ccpa-modal, "
            "#adt-ii, #adthrive-mcmp"
        )
        # Tries to load config if available
        try:
            import config_manager
            self.config = config_manager.load_config()
        except ImportError:
            self.config = {}
            
        self.browser_path = self._get_browser_path()

    def _get_browser_path(self):
        """Tries to find a compatible browser on the system."""
        # 1. Tries manual path from config.json
        manual_path = self.config.get("browser_config", {}).get("binary_path")
        if manual_path and os.path.exists(manual_path):
            return manual_path

        # 2. Common paths for Brave, Chrome and Edge (Windows priority)
        potential_paths = [
            # Brave
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            # Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Edge
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]

        for path in potential_paths:
            if os.path.exists(path):
                print(f"✅ Browser found: {path}")
                return path

        # If nothing is found, returns the old default as fallback and warns
        print("⚠️ No compatible browser found automatically.")
        return r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

    async def _start_browser(self):
        """Starts the browser in an isolated instance with debug port enabled."""
        print(f"🌐 Starting new isolated browser instance at: {self.browser_path}")
        
        # Creates a local profile directory to ensure it's a new and isolated window
        profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".crawl4ai_profile")
        os.makedirs(profile_path, exist_ok=True)
        
        # Command to open the browser via subprocess
        cmd = [
            self.browser_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile_path}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,720"
        ]
        
        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("⏳ Waiting for isolated environment initialization...")
        await asyncio.sleep(5)  # Waits for the browser to stabilize (ASYNC)
        return proc

    async def scrape(self, urls):
        """
        Executes the scraping process:
        1. Opens the Browser
        2. Resolves Cloudflare (if any) for each URL
        3. Captures the HTML of each page
        4. Processes with Crawl4AI via raw:// prefix
        """
        if isinstance(urls, str):
            urls = [urls]

        # Clears empty or duplicate URLs
        urls = [u.strip() for u in urls if u and u.strip()]
        if not urls:
            return ""

        browser_proc = await self._start_browser()
        all_markdowns = []
        
        async with async_playwright() as p:
            try:
                # Connects to the browser via IPv4 to avoid ECONNREFUSED ::1 error
                browser = None
                for i in range(10): # Increased number of attempts
                    try:
                        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=30000)
                        break
                    except Exception as e:
                        if i == 9: raise e
                        print(f"   ⏳ Connection attempt {i+1} failed, retrying...")
                        await asyncio.sleep(2)

                if not browser:
                    raise Exception("Could not connect to the browser via CDP.")

                # Gets default context
                context = browser.contexts[0]
                
                # REUSES A SINGLE PAGE to avoid "Target closed" and "Failed to open tab" errors
                page = await context.new_page()
                
                # Closes initial empty tabs (except ours)
                for p_to_close in context.pages:
                    if p_to_close != page:
                        try:
                            await p_to_close.close()
                        except: pass

                # Initializes crawler WITHOUT browser config to avoid Playwright conflicts
                # If we use raw://, Crawl4AI can function only as an HTML processor
                async with AsyncWebCrawler(verbose=False) as crawler:
                    for url in urls:
                        try:
                            # Checks if browser is still connected
                            if not browser.is_connected():
                                print("⚠️ Browser connection lost. Attempting to reconnect...")
                                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=30000)
                                context = browser.contexts[0]
                                page = await context.new_page()

                            print(f"📥 Accessing: {url}")
                            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                            
                            # Cloudflare detection loop (Ray ID)
                            print(f"🔍 Checking protections for {url}...")
                            for attempt in range(300): # 5 minutes
                                try:
                                    status = await page.evaluate("""() => {
                                        const isWaiting = document.title.includes('Just a moment') || 
                                                         document.body.innerText.includes('Checking your browser') ||
                                                         document.body.innerText.includes('verify you are human') ||
                                                         !!document.querySelector('#challenge-form') ||
                                                         !!document.querySelector('.cf-browser-verification');
                                        
                                        const hasRayId = !!(document.querySelector('[id*="ray-id"]') || 
                                                          document.querySelector('[class*="ray-id"]') || 
                                                          document.body.innerText.includes('Ray ID'));
                                        
                                        return { isBlocked: hasRayId || isWaiting };
                                    }""")
                                    
                                    if not status['isBlocked']:
                                        # Checks if real content loaded
                                        text = await page.evaluate("document.body?.innerText || ''")
                                        if len(text.strip()) > 100:
                                            print("   ✅ Content loaded/verified.")
                                            break
                                    else:
                                        if attempt % 15 == 0:
                                            print(f"   ⏳ [Action Required] Cloudflare barrier detected. Solve the challenge in the browser...")
                                except Exception as e:
                                    # If the page was closed or something
                                    if "closed" in str(e).lower():
                                        raise e
                                    pass
                                await asyncio.sleep(1)
                            
                            await asyncio.sleep(2.0)
                            raw_html = await page.content()
                            
                            # Processing with Crawl4AI
                            print(f"🔄 Processing content with Crawl4AI ({url})...")
                            
                            run_config = CrawlerRunConfig(
                                css_selector="body",
                                excluded_tags=["footer", "nav"],
                                excluded_selector=self.excluded_selector,
                                markdown_generator=DefaultMarkdownGenerator(
                                    options={"ignore_links": True, "skip_internal_links": True}
                                ),
                            )
                            
                            # IMPORTANT: We use the crawler only to convert the HTML we ALREADY HAVE
                            result = await crawler.arun(url=f"raw://{raw_html}", config=run_config)
                            if result.success:
                                all_markdowns.append(result.markdown)
                            else:
                                print(f"❌ Crawl4AI error: {result.error_message}")
                                
                        except Exception as e:
                            print(f"❌ Error processing URL {url}: {e}")
                            if "closed" in str(e).lower():
                                # If the browser died, try to reopen on next URL via reconnection at top
                                break
                
            except Exception as e:
                print(f"❌ Critical error in browser connection: {e}")
            
            finally:
                # Cleanup: Kills only the specific browser instance we opened
                print("\n🏁 Finishing scraper and closing window...")
                try:
                    if 'browser' in locals() and browser:
                        await browser.close()
                except: pass

                try:
                    browser_proc.terminate()
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(browser_proc.pid)], capture_output=True)
                except Exception:
                    pass
        
        return "\n\n".join(all_markdowns)
    
# Compatibility interface for the rest of the project
def scrape_url(urls):
    scraper = ScraperCrawl4AI()
    return asyncio.run(scraper.scrape(urls))

if __name__ == "__main__":
    # Quick test and file saving for manual mode compatibility
    test_urls = [
        "https://taimanin.fandom.com",
    ]
    
    print("\n🚀 Starting manual mode for ScraperCrawl4AI...")
    resultado = scrape_url(test_urls)
    
    if resultado:
        output_file = "scraped_content.txt"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(resultado)
            print(f"\n✅ Success! Content extracted and saved to: {output_file}")
            print(f"Summary: {resultado[:200]}...")
        except Exception as e:
            print(f"❌ Error saving file: {e}")
    else:
        print("\n❌ Extraction failed.")
