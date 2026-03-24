import time
import re
import ssl
import os
import urllib3
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Assuming config_manager is a local module in your project
try:
    import config_manager
except ImportError:
    # Mock fallback just in case it's missing in some environments
    class _MockConfig:
        def load_config(self): return {}
        def save_config(self, cfg): pass
    config_manager = _MockConfig()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TLSAdapter(HTTPAdapter):
    """Custom adapter to handle various TLS/SSL configurations robustly."""
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


def create_session_with_retries(retries=3, backoff_factor=0.5, verify_ssl=True):
    """Create a highly robust requests session with modern anti-bot headers and SSL fallbacks."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    if not verify_ssl:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
        adapter = TLSAdapter(ssl_context=ssl_context, max_retries=retry_strategy)
    else:
        adapter = HTTPAdapter(max_retries=retry_strategy)
    
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Modernized headers to mimic a real Chromium browser and bypass basic WAFs
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'Connection': 'keep-alive',
    })
    
    return session


def is_valid_url_format(url):
    """Quick URL format validation."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ['http', 'https'] and parsed.netloc and '.' in parsed.netloc)
    except Exception:
        return False


def is_valid_url(url):
    """Check if URL is accessible, handling SSL and timeouts intelligently."""
    if not is_valid_url_format(url):
        return False, "Invalid URL format"
        
    try:
        session = create_session_with_retries(retries=1, verify_ssl=True)
        response = session.head(url, timeout=10, allow_redirects=True)
        
        if response.status_code >= 400:
            return False, f"HTTP {response.status_code} error"
        return True, "Valid"
        
    except (requests.exceptions.SSLError, ssl.SSLError):
        try:
            session = create_session_with_retries(retries=1, verify_ssl=False)
            response = session.head(url, timeout=10, allow_redirects=True, verify=False)
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code} error"
            return True, "Valid (SSL bypassed)"
        except Exception as e:
            return False, f"SSL bypass failed: {e}"
            
    except requests.exceptions.ConnectionError:
        return False, "Connection failed - site may be down or requires Javascript/Browser"
    except requests.exceptions.Timeout:
        return False, "Connection timeout - will require Browser rendering"
    except Exception as e:
        return False, f"Error: {str(e)}"


def get_urls():
    """Interactive URL gatherer."""
    urls = []
    print("Enter URLs to scrape. Type 'done' when finished.")
    
    while True:
        url = input("URL: ").strip()
        if url.lower() == 'done' or not url:
            break
            
        if not re.match(r'^https?:\/\/', url):
            url = 'https://' + url
        
        if not is_valid_url_format(url):
            print(f"✗ Invalid URL format: {url}")
            continue
        
        print(f"Validating {url}...")
        is_valid, message = is_valid_url(url)
        
        if is_valid:
            urls.append(url)
            print(f"✓ Added: {url}")
        else:
            print(f"⚠ {message}")
            force = input("Add anyway? Site might strictly require a real browser (y/N): ").lower().strip()
            if force in ['y', 'yes', '1']:
                urls.append(url)
                print(f"✓ Added (forced): {url}")
                
    return urls


def clean_and_format_text(soup):
    """
    Advanced Readability-based Content Extractor and Markdown Generator.
    Drastically improved to ignore noise and perfectly format tables/lists.
    """
    # 1. Clean out completely irrelevant DOM elements
    for element in soup(['script', 'style', 'noscript', 'meta', 'link', 'iframe', 'svg', 
                         'canvas', 'form', 'nav', 'footer', 'aside', 'header', 'button', 'input']):
        element.decompose()
    
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    # ATUALIZAÇÃO: Adicionado filtros agressivos para caixas de navegação de Wikis
    for selector in[
        ".comment", "#comments", ".advertisement", ".sidebar", ".menu", ".cookie-banner",
        ".navbox", ".infobox", ".metadata", ".toc", "#toc",
        "table[class*='navbox']", "div[class*='navbox']", "table[class*='infobox']"
    ]:
        for el in soup.select(selector):
            el.decompose()

    # 2. Heuristic Content Detection
    main_content = None
    for selector in ['article', 'main', '[role="main"]', '#main-content', '.main-content']:
        main_content = soup.select_one(selector)
        if main_content: break
        
    if not main_content:
        candidates = soup.find_all(['div', 'section'])
        best_candidate = soup.body if soup.body else soup
        highest_score = -1
        
        for candidate in candidates:
            p_tags = candidate.find_all('p')
            score = len(p_tags)
            class_id_text = (candidate.get('class', [''])[0] + " " + candidate.get('id', '')).lower()
            if any(bad in class_id_text for bad in['wrap', 'page', 'container', 'body']):
                score -= 2
                
            if score > highest_score and score > 2:
                highest_score = score
                best_candidate = candidate
                
        main_content = best_candidate

    # 3. Robust HTML to Markdown recursive parser
    def to_markdown(node, list_depth=0):
        if isinstance(node, NavigableString):
            text = str(node)
            return re.sub(r'\s+', ' ', text)
            
        if not isinstance(node, Tag):
            return ""
            
        tag = node.name
        children_md = "".join(to_markdown(c, list_depth) for c in node.children)
        
        # Block Elements
        if tag in['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = tag[1]
            return f"\n\n{'#' * int(level)} {children_md.strip()}\n\n"
            
        elif tag == 'p':
            return f"\n\n{children_md.strip()}\n\n"
            
        elif tag in ['ul', 'ol']:
            return f"\n{children_md}\n"
            
        elif tag == 'li':
            indent = "  " * list_depth
            prefix = "- " if node.parent and node.parent.name == 'ul' else "1. "
            inner = "".join(to_markdown(c, list_depth + 1) for c in node.children).strip()
            return f"\n{indent}{prefix}{inner}"
            
        elif tag == 'blockquote':
            return "\n\n" + "\n".join(f"> {line}" for line in children_md.strip().split("\n")) + "\n\n"
            
        elif tag in ['pre', 'code']:
            if tag == 'code' and node.parent.name != 'pre':
                return f"`{children_md.strip()}`"
            text = node.get_text()
            return f"\n\n```\n{text}\n```\n\n"
            
        # ATUALIZAÇÃO: Lógica de Tabelas (GitHub Flavored Markdown) aprimorada
        elif tag == 'table':
            # Se for uma tabela DENTRO de outra tabela, o Markdown quebra. 
            # Então nós a tratamos apenas como texto plano.
            if node.find_parent('table'):
                return f" {children_md.strip()} "

            # Pega apenas as linhas que pertencem DIRETAMENTE a esta tabela (ignora tabelas filhas)
            rows =[]
            for child in node.children:
                if child.name in ['thead', 'tbody', 'tfoot']:
                    rows.extend(child.find_all('tr', recursive=False))
                elif child.name == 'tr':
                    rows.append(child)
                    
            if not rows: return ""
            
            table_md = "\n\n"
            valid_rows = 0
            
            for i, row in enumerate(rows):
                # Pega apenas as células diretas (evita vazamento de tabelas aninhadas)
                cells = row.find_all(['td', 'th'], recursive=False)
                if not cells: continue
                
                # O Markdown NÃO permite quebras de linha dentro de uma célula da tabela
                # O strip() e split() transformam quebras de linha em espaços
                cell_text =[" ".join(to_markdown(c).strip().split()) for c in cells]
                table_md += "| " + " | ".join(cell_text) + " |\n"
                
                # Adiciona a linha de separação após a primeira linha
                if valid_rows == 0:
                    table_md += "| " + " | ".join(["---"] * len(cells)) + " |\n"
                
                valid_rows += 1
            
            return table_md + "\n"

        # Inline Elements
        elif tag in ['strong', 'b']:
            return f" **{children_md.strip()}** "
            
        elif tag in ['em', 'i']:
            return f" *{children_md.strip()}* "
            
        elif tag == 'a':
            href = node.get('href', '')
            text = children_md.strip()
            if not text: return ""
            if href.startswith('http'):
                return f" [{text}]({href}) "
            return f" [{text}] "
            
        elif tag in ['br', 'hr']:
            return "\n" if tag == 'br' else "\n\n---\n\n"
            
        else:
            return children_md

    # Process and cleanup final Markdown
    raw_md = to_markdown(main_content)
    
    # Cleanup regexes
    cleaned_md = re.sub(r'\n{3,}', '\n\n', raw_md)          # Max 2 newlines
    cleaned_md = re.sub(r' +(\n|$)', r'\1', cleaned_md)     # Trailing spaces
    cleaned_md = re.sub(r'( \*\*|\*\* )', '**', cleaned_md) # Bold spacing
    cleaned_md = re.sub(r'( \*|\* )', '*', cleaned_md)      # Italic spacing
    # Remove pipes vazios excessivos que sobram de tabelas complexas
    cleaned_md = re.sub(r'\|\s+\|\s+\|', '| |', cleaned_md) 
    
    return cleaned_md.strip()


def scrape_with_requests(url, verify_ssl=True):
    """Scrapes URL using requests. Optimized for speed and encoding fallbacks."""
    try:
        session = create_session_with_retries(retries=2, verify_ssl=verify_ssl)
        response = session.get(url, timeout=20, verify=verify_ssl)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return None, None, False
            
        # Let BeautifulSoup handle charset parsing from response.content natively
        soup = BeautifulSoup(response.content, 'html.parser')
        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Page"
        
        formatted_text = clean_and_format_text(soup)
        
        if formatted_text and len(formatted_text.strip()) > 50:
            return formatted_text, page_title, True
        return None, None, False
        
    except (requests.exceptions.SSLError, ssl.SSLError):
        if verify_ssl:
            return scrape_with_requests(url, verify_ssl=False)
        return None, None, False
    except Exception:
        return None, None, False


def scrape_with_selenium(urls, use_requests_fallback=True):
    """
    Drastically improved Selenium implementation. 
    Uses Selenium 4 built-in manager (NO MORE hardcoded executable_paths).
    Incorporates advanced stealth mechanisms to bypass bot protection.
    """
    if not urls:
        print("No URLs provided for scraping.")
        return ""
    
    all_text = ""
    driver = None
    config = config_manager.load_config() if hasattr(config_manager, 'load_config') else {}
    browser_cfg = config.get("browser_config", {})
    preferred_browser = browser_cfg.get("browser_name", "Chrome")

    def get_stealth_chrome_options(is_edge=False):
        options = EdgeOptions() if is_edge else ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        # Ignore security errors to ensure page loads successfully
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--log-level=3') 
        options.add_argument('--silent')
        return options

    # Browsers to attempt, putting the config-preferred one first
    browsers = [("Chrome", "chrome"), ("Edge", "edge"), ("Firefox", "firefox")]
    browsers.sort(key=lambda x: x[0] != preferred_browser)

    for browser_name, browser_type in browsers:
        try:
            print(f"Setting up {browser_name} via Selenium 4 Auto-Manager...")
            
            if browser_type == "chrome":
                driver = webdriver.Chrome(options=get_stealth_chrome_options(is_edge=False))
            elif browser_type == "edge":
                driver = webdriver.Edge(options=get_stealth_chrome_options(is_edge=True))
            elif browser_type == "firefox":
                options = FirefoxOptions()
                options.add_argument('--headless')
                driver = webdriver.Firefox(options=options)

            if driver:
                print(f"✓ {browser_name} initialized successfully.")
                
                # Apply anti-bot stealth scripts via CDP
                if browser_type in ["chrome", "edge"]:
                    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                        "source": """
                            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                            window.navigator.chrome = {runtime: {}};
                        """
                    })
                
                # Save working browser to config
                if browser_name != preferred_browser and hasattr(config_manager, 'save_config'):
                    config["browser_config"] = {"browser_name": browser_name, "browser_type": browser_type}
                    config_manager.save_config(config)
                    
                driver.set_page_load_timeout(45)
                break
                
        except Exception as e:
            # Silently fail and try the next browser
            driver = None
            continue

    if not driver:
        print("⚠ All browsers failed to initialize. Falling back to Requests engine.")
    
    successful_scrapes = 0
    total_urls = len(urls)
    
    for i, url in enumerate(urls, 1):
        scraped = False
        formatted_text = None
        page_title = "Untitled Page"
        
        if driver:
            try:
                print(f"[{i}/{total_urls}] Loading {url} with Selenium...")
                driver.get(url)
                
                # Smart dynamic wait - wait until network is mostly idle or body loads
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Scroll to trigger lazy-loaded text/images
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(1.5) 
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
                page_source = driver.page_source
                page_title = driver.title or "Untitled Page"
                
                if page_source and len(page_source) > 500:
                    soup = BeautifulSoup(page_source, 'html.parser')
                    formatted_text = clean_and_format_text(soup)
                    
                    if formatted_text and len(formatted_text.strip()) > 50:
                        scraped = True
                        print(f"  ✓ Selenium extraction successful")
                    else:
                        print(f"  ⚠ Extracted content was too short. Trying fallback.")
                        
            except TimeoutException:
                print(f"  ⚠ Page load timeout.")
            except WebDriverException as e:
                print(f"  ⚠ Selenium Navigation Error: {str(e).splitlines()[0]}")
            except Exception as e:
                print(f"  ⚠ Unexpected Selenium Error: {e}")
        
        # Fallback to requests if Selenium didn't work or content was blocked
        if not scraped and use_requests_fallback:
            print(f"  → Attempting Requests-based extraction for {url}...")
            content, req_title, success = scrape_with_requests(url)
            if success and content:
                formatted_text = content
                page_title = req_title
                scraped = True
                print(f"  ✓ Requests extraction successful")
        
        if scraped and formatted_text:
            all_text += f"\n# {page_title}\n\n{formatted_text}\n\n---\n"
            successful_scrapes += 1
            print(f"✓ Scraped: {url}")
        else:
            print(f"✗ Failed: {url} - No readable content extracted")
            
    if driver:
        try:
            driver.quit()
        except:
            pass
            
    print(f"\n{'='*50}")
    print(f"Scraping complete: {successful_scrapes}/{total_urls} URLs successful")
    
    if not all_text.strip():
        print("⚠ Warning: No content was scraped from any URLs")
        
    return all_text


def save_to_file(text, filename="scraped_content.txt"):
    """Saves text safely to a file."""
    if not text.strip():
        print("Nothing to save.")
        return
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✓ Content successfully saved to '{filename}'")
    except IOError as e:
        print(f"✗ Error saving file: {e}")


if __name__ == "__main__":
    # Ensure BeautifulSoup is available for self-test
    urls_to_scrape = get_urls()
    if urls_to_scrape:
        scraped_content = scrape_with_selenium(urls_to_scrape)
        if scraped_content.strip():
            save_to_file(scraped_content)
            print("\n--- Preview of Scraped Content ---")
            print(scraped_content[:1500] + "\n\n... [TRUNCATED] ...")

import asyncio
import os

def scrape_with_crawl4ai(urls, headless=True):
    try:
        from crawl4ai import BrowserConfig, CrawlerRunConfig, AsyncWebCrawler, DefaultMarkdownGenerator
    except ImportError:
        print("crawl4ai is not installed, falling back to legacy scraper.")
        return None

    async def _crawl():
        os.environ["NODE_OPTIONS"] = "--no-deprecation"
        browser_config = BrowserConfig(
            headless=headless,
            verbose=False,
            use_persistent_context=True,
            user_data_dir="./.crawl4ai_profile",
        )

        wait_for_loading = """js:() => {
            const text = document.body ? document.body.innerText : '';
            return !text.includes('Loading page resources.') && !text.includes('The site isn\\'t loading');
        }"""

        config = CrawlerRunConfig(
            wait_for=wait_for_loading,
            delay_before_return_html=3.0,
            css_selector="body",
            excluded_tags=["footer", "nav"],
            excluded_selector=".toc, .wds-global-footer, #catlinks, .printfooter, .global-top-navigation, .notifications-placeholder, #community-navigation, .community-header-wrapper, .global-explore-navigation, .global-footer, .global-footer__content, .global-footer__bottom, .fandom-community-header, #navigator, #header, .full_hr, .menubar, #toolbar, #lastmodified, #footer, #cosmos-footer, #cosmos-toolbar, .cosmos-header, #cosmos-banner, .mw-header, #mw-head, #mw-panel, #mw-page-base, #mw-head-base, .mw-footer, .mw-footer-container, .vector-column-end, .vector-sticky-pinned-container, .azltable, .page__rioque ght-rail, #google_translate_element, #onetrust-banner-sdk, #onetrust-consent-sdk, #top_leaderboard-odyssey-wrapper, .navibox, .mw-collapsible, .pcomment, #google_translate_element, #goog-gt-tt, #goog-gt-vt",
            markdown_generator=DefaultMarkdownGenerator(
                options={"ignore_links": True, "skip_internal_links": True}
            )
        )

        all_text = ""
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for url in urls:
                try:
                    result = await crawler.arun(url=url, config=config)
                    if result.success:
                        all_text += f"\n--- Content from {url} ---\n"
                        all_text += str(result.markdown)
                    else:
                        print(f"Failed to crawl {url}: {result.error_message}")
                except Exception as e:
                    print(f"Error crawling {url}: {e}")
        return all_text

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running(): 
            # When we run from Tkinter, it doesn't normally have an asyncio loop running,
            # but if it does, returning coroutine and letting callers manage it would be correct.
            # We'll just run in a new thread if needed.
            pass
    except RuntimeError:
        pass
        
    return asyncio.run(_crawl())