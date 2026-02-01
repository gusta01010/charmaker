import time
import re
import ssl
import os
import urllib3
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import config_manager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TLSAdapter(HTTPAdapter):
    """Custom adapter to handle various TLS/SSL configurations."""
    
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        if self.ssl_context:
            kwargs['ssl_context'] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)


def create_session_with_retries(retries=3, backoff_factor=0.5, verify_ssl=True):
    """Create a requests session with retry logic and SSL handling."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    # try with different SSL contexts if needed
    if not verify_ssl:
        # creates a permissive SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        # also try with older TLS versions for legacy sites
        ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
        adapter = TLSAdapter(ssl_context=ssl_context, max_retries=retry_strategy)
    else:
        adapter = HTTPAdapter(max_retries=retry_strategy)
    
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # set common headers to avoid blocks
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    return session

def is_valid_url_format(url):
    """Quick URL format validation - lightweight check for basic structure"""
    try:
        parsed = urlparse(url)
        # Check if it has scheme and netloc, and netloc contains at least a dot
        return (parsed.scheme in ['http', 'https'] and 
                parsed.netloc and 
                '.' in parsed.netloc and
                len(parsed.netloc.split('.')) >= 2)
    except:
        return False

def is_valid_url(url):
    """Check if URL is valid and accessible with network request."""
    try:
        # Parse URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        
        # Create session with retries and SSL handling
        session = create_session_with_retries(retries=2, verify_ssl=True)
        
        try:
            # quick HEAD request to check if URL is accessible
            response = session.head(url, timeout=15, allow_redirects=True)
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code} error"
            return True, "Valid"
        except (requests.exceptions.SSLError, ssl.SSLError):
            # Retry without SSL verification
            session = create_session_with_retries(retries=2, verify_ssl=False)
            response = session.head(url, timeout=15, allow_redirects=True, verify=False)
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code} error"
            return True, "Valid (SSL bypassed)"
    
    except requests.exceptions.ConnectionError as e:
        error_msg = str(e).lower()
        if 'handshake' in error_msg or 'ssl' in error_msg or 'certificate' in error_msg:
            return False, "SSL/TLS handshake failed - will try with Selenium"
        return False, "Connection failed - site may be down"
    except requests.exceptions.Timeout:
        return False, "Connection timeout - will try with Selenium"
    except requests.exceptions.InvalidURL:
        return False, "Malformed URL"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_urls():
    """Get URLs from user input with validation."""
    urls = []
    print("Enter URLs to scrape. Type 'done' when finished.")
    
    while True:
        url = input("URL: ").strip()
        if url.lower() == 'done' or url == '':
            break
        if not url:
            continue
            
        # Add protocol if missing
        if not re.match(r'^https?:\/\/', url):
            url = 'https://' + url
        
        # Quick format validation first
        if not is_valid_url_format(url):
            print(f"✗ Invalid URL format: {url}")
            continue
        
        # Validate URL accessibility
        print(f"Validating {url}...")
        is_valid, message = is_valid_url(url)
        
        if is_valid:
            urls.append(url)
            print(f"✓ Added: {url}")
        else:
            # For SSL/connection errors, still allow adding since we have fallbacks
            if 'ssl' in message.lower() or 'handshake' in message.lower() or 'will try' in message.lower():
                print(f"⚠ {message}")
                urls.append(url)
                print(f"✓ Added (will attempt with fallback methods): {url}")
            else:
                print(f"✗ Skipped: {message}")
                
                # Ask if user wants to add anyway
                force_add = input("Add anyway? (y/N): ").lower().strip()
                if force_add in ['y', 'yes', '1']:
                    urls.append(url)
                    print(f"⚠ Added (forced): {url}")
    
    return urls


def clean_and_format_text(soup):
    """
    Extract and format content from a BeautifulSoup object, with improved logic
    for handling complex pages like Wikipedia and better table processing.
    Designed to be flexible for any website.
    """
    
    # Remove comments first
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # Remove unwanted elements
    for element in soup(["script", "style", "noscript", "meta", "link", "iframe", "svg", "canvas", "textarea", "input", "button", "form"]):
        element.decompose()

    # Specifically remove comment forms or other interaction areas
    for selector in ["#pcomment-form", ".reply-form", ".comment-form"]:
        for element in soup.select(selector):
            element.decompose()

    # Enhanced content selectors with priority ordering
    content_selectors = [
        'body > div.main-container > div.resizable-container > div.page.has-right-rail > main',
        'main', 'article', '[role="main"]', '[role="article"]',  # Semantic HTML5 first
        '#content', '#main-content', '.main-content', '#mw-body', '.content', '.bodyContent',
        '.post-content', '#vector-body', '#mw-content-text', 'div[role="main"]',
        '.entry-content', '.article-content', '.page-content', '.story-body',
        '.article-body', '.post-body', '[itemprop="articleBody"]'
    ]
    
    # Find first available content area
    main_content = None
    for selector in content_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # Fallback to body
    if not main_content:
        main_content = soup.body or soup

    # check if this is the user-specified priority container to allow all content
    is_priority_container = False
    priority_selector = 'body > div.main-container > div.resizable-container > div.page.has-right-rail > main'
    if main_content:
        # check if main_content is or contains the priority content
        priority_match = soup.select_one(priority_selector)
        if priority_match and (main_content == priority_match or priority_match in main_content.parents):
            is_priority_container = True

    if main_content and not is_priority_container:
        # standard cleaning for other sites
        for element in main_content.find_all(['nav', 'footer', 'aside', 'header', 'script', 'style']):
            element.decompose()

    def clean_cell_text(cell):
        """Clean text from a table cell."""
        # remove images and citations
        for element in cell.find_all(['img', 'sup', 'small']):
            element.decompose()
        
        # get clean text
        text = cell.get_text(separator=' ', strip=True)
        return re.sub(r'\s+', ' ', text).strip()

    def process_element(element):
        if isinstance(element, NavigableString):
            text = element.strip()
            # Skip if it's just whitespace or special characters
            if re.match(r'^[\s\-–—·•|]*$', text):
                return ""
            return text
            
        if not isinstance(element, Tag):
            return ""
            
        tag_name = element.name
        
        # Skip empty elements early
        if not element.get_text(strip=True) and tag_name not in ['br', 'hr']:
            return ""
        
        # Handle tables with improved logic
        if tag_name == 'table':
            # Skip tables that are likely layout tables
            table_text = element.get_text(strip=True)
            if len(table_text) < 20:  # Too small to be content
                return ""
            
            # Check if it's a data table (has headers or multiple rows)
            headers = element.find_all('th')
            rows = element.find_all('tr')
            
            if len(rows) < 2 and not headers:  # Single row without headers
                return ""
            
            table_rows = []
            
            # Process header row if exists
            if headers:
                header_texts = []
                for th in headers[:10]:  # Limit columns to prevent spam
                    header_text = clean_cell_text(th)
                    if header_text:
                        header_texts.append(header_text)
                
                if header_texts:
                    table_rows.append("| " + " | ".join(header_texts) + " |")
                    # Markdown table separator
                    separators = ["---"] * len(header_texts)
                    table_rows.append("| " + " | ".join(separators) + " |")
            
            # Process data rows
            row_count = 0
            empty_row_count = 0
            
            for row in rows[:100]:  # Limit rows to prevent huge tables
                # Skip rows that only contain headers if we already processed headers
                if headers and row.find_all('th') and not row.find_all('td'):
                    continue
                    
                cells = []
                cell_count = 0
                
                for cell in row.find_all(['td', 'th'])[:10]:  # Limit columns
                    cell_text = clean_cell_text(cell)
                    cells.append(cell_text if cell_text else "")
                    if cell_text:
                        cell_count += 1
                
                # Only add rows that have at least one non-empty cell
                if cell_count > 0:
                    table_rows.append("| " + " | ".join(cells) + " |")
                    row_count += 1
                else:
                    empty_row_count += 1
                    
                # Stop if too many empty rows in a row
                if empty_row_count > 3:
                    break
            
            # Only return table if it has meaningful content
            if table_rows and row_count > 0:
                return "\n\n" + "\n".join(table_rows) + "\n\n"
            else:
                return ""
        
        # Handle pre/code blocks
        if tag_name in ['pre', 'code']:
            code_text = element.get_text(strip=False)
            if code_text.strip():
                if tag_name == 'pre' or (element.parent and element.parent.name == 'pre'):
                    return f"\n```\n{code_text.strip()}\n```\n"
                else:
                    return f" `{code_text.strip()}` "
            return ""
        
        # Handle blockquotes
        if tag_name == 'blockquote':
            quote_content = []
            for child in element.children:
                child_text = process_element(child)
                if child_text:
                    quote_content.append(child_text)
            
            if quote_content:
                joined = ' '.join(quote_content).strip()
                # Add > to each line of the quote
                quoted = '\n'.join([f"> {line}" for line in joined.split('\n') if line.strip()])
                return f"\n{quoted}\n"
            return ""
        
        # Process children for other elements
        content = []
        for child in element.children:
            child_content = process_element(child)
            if child_content:  # Only add non-empty content
                content.append(child_content)
        
        if not content and tag_name not in ['br', 'hr']:  # Skip if no content after processing
            return ""
            
        joined_content = " ".join(content).strip()
        
        # Format based on tag type
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            # Skip headers that are too short or just numbers
            if len(joined_content) < 2 or re.match(r'^\d+\.?$', joined_content):
                return ""
            return f"\n\n{'#' * level} {joined_content}\n\n"
        elif tag_name == 'p':
            return f"\n{joined_content}\n"
        elif tag_name == 'div':
            # Only add newlines if it seems like a block element
            if len(joined_content) > 50 or '\n' in joined_content:
                return f"\n{joined_content}\n"
            return joined_content
        elif tag_name == 'li':
            # Check parent to determine list type
            parent = element.find_parent(['ul', 'ol'])
            if parent and parent.name == 'ol':
                # Try to get the index
                siblings = parent.find_all('li', recursive=False)
                try:
                    index = siblings.index(element) + 1
                    return f"{index}. {joined_content}\n"
                except ValueError:
                    return f"1. {joined_content}\n"
            else:
                return f"- {joined_content}\n"
        elif tag_name in ['strong', 'b']:
            return f"**{joined_content}**"
        elif tag_name in ['em', 'i']:
            return f"*{joined_content}*"
        elif tag_name == 'u':
            return f"<u>{joined_content}</u>"
        elif tag_name == 's' or tag_name == 'strike' or tag_name == 'del':
            return f"~~{joined_content}~~"
        elif tag_name == 'a':
            # User wants to avoid the URL part, just keep the text in brackets
            if not joined_content or not joined_content.strip():
                return ""
            return f"[{joined_content}]"
        elif tag_name == 'br':
            return "\n"
        elif tag_name == 'hr':
            return "\n---\n"
        elif tag_name in ['ul', 'ol']:
            return f"\n{joined_content}\n"
        else:
            return joined_content

    # Process the main content
    result = process_element(main_content)
    
    # Clean up the final result
    # Remove excessive newlines (strictly more than 1 blank line)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Remove empty bullets and list items
    result = re.sub(r'^[•·\-]\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^\d+\.\s*$', '', result, flags=re.MULTILINE)
    
    # Clean up empty headers
    result = re.sub(r'^#+\s*$', '', result, flags=re.MULTILINE)
    
    # Remove multiple spaces (but preserve indentation if any, though we don't use it much)
    result = re.sub(r' {2,}', ' ', result)

    # Remove empty brackets [ ], [  ] or similar artifacts
    result = re.sub(r'\[\s*\]', '', result)
    
    # Remove trailing whitespace on each line
    result = re.sub(r'[ \t]+$', '', result, flags=re.MULTILINE)
    
    # Fix spacing around bold/italic
    result = re.sub(r'\*\* ', '**', result)
    result = re.sub(r' \*\*', '**', result)
    result = re.sub(r'\* ', '*', result)
    result = re.sub(r' \*', '*', result)
    
    # Final cleanup - remove leading/trailing whitespace
    result = result.strip()
    
    # If result is too short, it's probably not meaningful content
    if len(result.split()) < 10:
        return ""
    
    return result


def scrape_with_requests(url, verify_ssl=True):
    """
    Scrape a single URL using requests library.
    Returns (content, title, success) tuple.
    """
    try:
        session = create_session_with_retries(retries=3, verify_ssl=verify_ssl)
        response = session.get(url, timeout=30, verify=verify_ssl)
        response.raise_for_status()
        
        # Check if we got actual HTML content
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return None, None, False
        
        # use content (bytes) instead of text to let BeautifulSoup handle encoding detection
        # this is especially important for sites with non-UTF-8 encodings (like Shift-JIS)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        page_title = "Untitled Page"
        if soup.title and soup.title.string:
            page_title = soup.title.string.strip()
        
        formatted_text = clean_and_format_text(soup)
        
        if formatted_text and len(formatted_text.strip()) > 50:
            return formatted_text, page_title, True
        return None, None, False
        
    except (requests.exceptions.SSLError, ssl.SSLError) as e:
        if verify_ssl:
            # Retry without SSL verification
            return scrape_with_requests(url, verify_ssl=False)
        return None, None, False
    except Exception as e:
        return None, None, False
    

def scrape_with_selenium(urls, use_requests_fallback=True):
    """Scrape URLs using Selenium with better error handling and fallback options."""
    if not urls:
        print("No URLs provided for scraping.")
        return ""
    
    all_text = ""
    driver = None
    
    # Load configuration
    config = config_manager.load_config()
    browser_cfg = config.get("browser_config", {})
    saved_name = browser_cfg.get("browser_name")
    saved_type = browser_cfg.get("browser_type")
    saved_binary = browser_cfg.get("binary_path")

    def get_common_chrome_options(is_edge=False):
        options = EdgeOptions() if is_edge else ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--headless=new')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        options.add_argument('--window-size=1920,1080')
        return options

    # Try different browsers in order of preference
    browsers_to_try = [
        ("Brave", "chrome"),
        ("Chrome", "chrome"),
        ("Edge", "edge"),
        ("Firefox", "firefox")
    ]

    # If we have a saved config, move it to the front
    if saved_name and saved_type:
        # remove it from the list first
        browsers_to_try = [b for b in browsers_to_try if b[0] != saved_name]
        # insert it at the beginning
        browsers_to_try.insert(0, (saved_name, saved_type))

    for browser_name, browser_type in browsers_to_try:
        try:
            if browser_type == "chrome":
                options = get_common_chrome_options(is_edge=False)
                
                # Use saved binary if it matches the browser we are trying
                if browser_name == saved_name and saved_binary and os.path.exists(saved_binary):
                    options.binary_location = saved_binary
                elif browser_name == "Brave":
                    brave_paths = [
                        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'BraveSoftware\\Brave-Browser\\Application\\brave.exe'),
                        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'BraveSoftware\\Brave-Browser\\Application\\brave.exe'),
                        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'BraveSoftware\\Brave-Browser\\Application\\brave.exe'),
                    ]
                    for path in brave_paths:
                        if os.path.exists(path):
                            options.binary_location = path
                            break
                    else:
                        continue # Skip Brave if binary not found
                
                print(f"Attempting to set up {browser_name} driver...")
                service = ChromeService(executable_path=r"..\\chromedriver.exe", log_output=os.devnull)
                driver = webdriver.Chrome(service=service, options=options)
                
            elif browser_type == "edge":
                print("Attempting to set up Edge driver...")
                options = get_common_chrome_options(is_edge=True)
                if browser_name == saved_name and saved_binary and os.path.exists(saved_binary):
                    options.binary_location = saved_binary
                service = EdgeService(executable_path=r"..\\msedgedriver.exe", log_output=os.devnull)
                driver = webdriver.Edge(service=service, options=options)
                
            elif browser_type == "firefox":
                print("Attempting to set up Firefox driver...")
                options = FirefoxOptions()
                options.add_argument('--headless')
                service = FirefoxService(executable_path=r"..\\geckodriver.exe", log_output=os.devnull)
                driver = webdriver.Firefox(service=service, options=options)

            if driver:
                print(f"✓ {browser_name} driver initialized successfully")
                
                # Save configuration if it changed or was empty
                if browser_name != saved_name:
                    binary_path = getattr(options, 'binary_location', None)
                    config["browser_config"] = {
                        "browser_name": browser_name,
                        "browser_type": browser_type,
                        "binary_path": binary_path
                    }
                    config_manager.save_config(config)
                    print(f"  → Saved {browser_name} as preferred browser in config.json")
                
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(10)
                break
                
        except Exception as e:
            # print(f"  ✗ {browser_name} initialization failed: {e}") 
            driver = None
            continue

    driver_failed = driver is None
    if driver_failed:
        print("⚠ All browser drivers failed to initialize. Will use requests-based scraping as fallback.")
    
    successful_scrapes = 0
    total_urls = len(urls)
    
    for i, url in enumerate(urls, 1):
        scraped = False
        formatted_text = None
        page_title = "Untitled Page"
        
        # Try Selenium first if driver is available
        if driver and not driver_failed:
            try:
                print(f"[{i}/{total_urls}] Loading {url} with Selenium...")
                driver.get(url)
                
                # Multiple wait strategies for better content detection
                try:
                    # Wait for body first
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Then wait for common content containers
                    content_selectors = [
                        (By.CSS_SELECTOR, "body > div.main-container > div.resizable-container > div.page.has-right-rail > main"),
                        (By.CSS_SELECTOR, "main, article, #content, .content, #main"),
                        (By.CSS_SELECTOR, "p"),  # At least some paragraphs
                    ]
                    
                    for selector in content_selectors:
                        try:
                            WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located(selector)
                            )
                            break
                        except TimeoutException:
                            continue
                    
                except TimeoutException:
                    print(f"  ⚠ Page load timeout, attempting to extract available content...")
                
                # Wait for dynamic content to load
                time.sleep(2)
                
                # Scroll to trigger lazy loading
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(0.5)
                except:
                    pass
                
                # Get page title
                page_title = driver.title or "Untitled Page"
                
                # Get page source and parse
                page_source = driver.page_source
                
                if page_source and len(page_source) > 500:
                    soup = BeautifulSoup(page_source, 'html.parser')
                    formatted_text = clean_and_format_text(soup)
                    
                    if formatted_text and len(formatted_text.strip()) > 50:
                        scraped = True
                        print(f"  ✓ Selenium scrape successful")
                    else:
                        print(f"  ⚠ Selenium returned empty/minimal content, trying fallback...")
                else:
                    print(f"  ⚠ Selenium returned empty page source, trying fallback...")
                    
            except TimeoutException as e:
                print(f"  ⚠ Selenium timeout: {e}")
            except WebDriverException as e:
                error_msg = str(e).lower()
                if 'handshake' in error_msg or 'ssl' in error_msg or 'certificate' in error_msg:
                    print(f"  ⚠ SSL/TLS error with Selenium, trying fallback...")
                else:
                    print(f"  ⚠ Selenium error: {e}")
            except Exception as e:
                print(f"  ⚠ Selenium error: {e}")
        
        # fallback to requests if Selenium failed or wasn't available
        if not scraped and use_requests_fallback:
            print(f"  → Trying requests-based scraping for {url}...")
            content, req_title, success = scrape_with_requests(url)
            if success and content:
                formatted_text = content
                page_title = req_title
                scraped = True
                print(f"  ✓ Requests fallback successful")
        
        # Add content if we got any
        if scraped and formatted_text:
            all_text += f"\n# {page_title}\n{formatted_text}\n"
            successful_scrapes += 1
            print(f"✓ Successfully scraped: {url}")
        else:
            print(f"✗ Failed to scrape: {url} - No content extracted")
    
    # cleanup
    if driver:
        try:
            driver.quit()
        except:
            pass
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Scraping complete: {successful_scrapes}/{total_urls} URLs successful")
    
    if not all_text.strip():
        print("⚠ Warning: No content was scraped from any URLs")
    
    return all_text

def save_to_file(text, filename="scraped_content.txt"):
    """Save text to a file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Content successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    urls_to_scrape = get_urls()
    if urls_to_scrape:
        scraped_content = scrape_with_selenium(urls_to_scrape)
        if scraped_content.strip():
            save_to_file(scraped_content)
            print("\n--- Preview of Scraped Content ---")
            print(scraped_content[:1000])