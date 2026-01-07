import time
import re
import ssl
import os
import urllib3
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        'Accept-Encoding': 'gzip, deflate, br',
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
    
    # Remove unwanted elements with expanded list
    for element in soup(["script", "style", "noscript", "meta", "link", "iframe", "svg", "canvas"]):
        element.decompose()

    # Enhanced content selectors with priority ordering
    content_selectors = [
        'main', 'article', '[role="main"]', '[role="article"]',  # Semantic HTML5 first
        '#content', '#main-content', '.main-content', '#mw-body', '.content', '.bodyContent',
        '.post-content', '#vector-body', '#mw-content-text', 'div[role="main"]',
        '.entry-content', '.article-content', '.page-content', '.story-body',
        '.article-body', '.post-body', '[itemprop="articleBody"]'
    ]
    
    main_content = None
    best_score = 0
    
    # Find best content area based on text density
    for selector in content_selectors:
        candidate = soup.select_one(selector)
        if candidate:
            # Calculate content score
            text_length = len(candidate.get_text(strip=True))
            html_length = len(str(candidate))
            if html_length > 0:
                density = text_length / html_length
                word_count = len(candidate.get_text().split())
                
                # Score based on density and word count
                score = (density * 100) + (min(word_count, 1000) / 10)
                
                if score > best_score:
                    best_score = score
                    main_content = candidate

    # Fallback to body if no good content area found
    if not main_content or best_score < 10:
        main_content = soup.body or soup

    if main_content:
        # Expanded list of unwanted elements and patterns
        for element in main_content.find_all(['nav', 'footer', 'aside', 'header'], recursive=True):
            # Check if element contains substantial content before removing
            text_content = element.get_text(strip=True)
            word_count = len(text_content.split())
            if word_count < 50:  # Only remove if it's likely navigation/boilerplate
                element.decompose()
        
        # Enhanced unwanted class patterns
        unwanted_classes = [
            'sidebar', 'advertisement', 'ads', 'menu', 'navigation', 'social', 
            'mw-editsection', 'noprint', 'navbox', 'metadata', 'reference', 
            'reflist', 'external', 'breadcrumb', 'cookie', 'popup', 'modal',
            'overlay', 'banner', 'alert', 'notice', 'warning', 'hidden',
            'offscreen', 'sr-only', 'visually-hidden', 'skip', 'jump'
        ]
        
        for unwanted_class in unwanted_classes:
            for element in main_content.find_all(class_=re.compile(unwanted_class, re.I)):
                # Don't remove if it contains substantial content
                if len(element.get_text(strip=True).split()) < 20:
                    element.decompose()
        
        # Enhanced unwanted ID patterns
        unwanted_ids = [
            'sidebar', 'ad-container', 'comments', 'respond', 'footer',
            'header', 'nav', 'navigation', 'menu', 'search', 'login',
            'signup', 'newsletter', 'subscription', 'share', 'social'
        ]
        
        for unwanted_id in unwanted_ids:
            for element in main_content.find_all(id=re.compile(unwanted_id, re.I)):
                if len(element.get_text(strip=True).split()) < 20:
                    element.decompose()

    def clean_cell_text(cell):
        """
        Clean text from a table cell, handling common issues.
        """
        # Handle images - extract meaningful alt text
        for img in cell.find_all('img'):
            alt_text = img.get('alt', '').strip()
            title_text = img.get('title', '').strip()
            
            # Try alt text first, then title
            img_text = alt_text or title_text
            
            if img_text and not re.search(r'\.(png|jpg|jpeg|gif|svg|webp)$', img_text, re.I):
                # Clean common patterns
                clean_text = re.sub(r'\s*(Icon|Logo|Image|Photo|Picture)\.?\s*$', '', img_text, flags=re.I)
                clean_text = re.sub(r'^\s*(Icon|Logo|Image|Photo|Picture)\s*[:|-]?\s*', '', clean_text, flags=re.I)
                
                if clean_text and len(clean_text) > 1:
                    img.replace_with(f"[{clean_text}]")
                else:
                    img.decompose()
            else:
                img.decompose()
        
        # Remove citations and edit links more thoroughly
        for sup in cell.find_all(['sup', 'small']):
            sup_text = sup.get_text().strip()
            # Remove common citation patterns like [1], [edit], etc.
            if re.search(r'^\[?\d+\]?$|^\[?edit\]?$|^\[?citation needed\]?$', sup_text, re.I):
                sup.decompose()
            elif re.search(r'edit|```math\d+```|```mathcitation|^```math\w```$', sup_text, re.I):
                sup.decompose()
        
        # Handle links - preserve meaningful ones
        for link in cell.find_all('a'):
            link_text = link.get_text(separator=' ', strip=True)
            # Remove empty links or edit links
            if not link_text or re.search(r'^(edit|source|citation|\[\d+\])$', link_text, re.I):
                link.decompose()
            else:
                # Replace link with its text to keep it clean in tables
                link.replace_with(link_text)
        
        # Handle nested tables (flatten them)
        for nested_table in cell.find_all('table'):
            nested_rows = []
            for row in nested_table.find_all('tr'):
                nested_cells = [clean_cell_text(c) for c in row.find_all(['td', 'th'])]
                if any(nested_cells):
                    nested_rows.append(' / '.join(filter(None, nested_cells)))
            
            if nested_rows:
                nested_table.replace_with(' | '.join(nested_rows))
            else:
                nested_table.decompose()
        
        # Handle lists in cells
        lists_text = []
        for list_elem in cell.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in list_elem.find_all('li')]
            if items:
                lists_text.append(', '.join(items))
                list_elem.extract()
        
        # Get clean text
        text = cell.get_text(separator=' ', strip=True)
        
        # Add lists text if any
        if lists_text:
            text = text + ' ' + ' '.join(lists_text) if text else ' '.join(lists_text)
        
        # Clean up whitespace and unwanted patterns
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'KATEX_INLINE_OPEN\s*edit\s*(?:stats?)?\s*KATEX_INLINE_CLOSE', '', text, flags=re.I)
        text = re.sub(r'```math\s*(?:edit|citation needed|dubious|clarification needed)\s*```', '', text, flags=re.I)
        text = re.sub(r'^\s*[·•]\s*', '', text)  # Remove bullet points
        text = re.sub(r'\s*\|\s*$', '', text)  # Remove trailing pipes
        
        # Return empty string for cells with only whitespace or special chars
        if re.match(r'^[\s\-–—·•|]*$', text):
            return ""
        
        return text.strip()

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
            # Include URL for external links
            href = element.get('href', '')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                # Only include URL if it's meaningful and not a citation
                if len(joined_content) > 2 and not re.match(r'^\[\d+\]$', joined_content):
                    # Ensure absolute URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        # We don't have the base URL here easily, but we can try to keep it as is
                        pass
                    return f"[{joined_content}]({href})"
            return joined_content
        elif tag_name == 'br':
            return "\n"
        elif tag_name == 'hr':
            return "\n\n---\n\n"
        elif tag_name in ['ul', 'ol']:
            return f"\n{joined_content}\n"
        else:
            return joined_content

    # Process the main content
    result = process_element(main_content)
    
    # Clean up the final result
    # Remove excessive newlines (more than 2)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Remove empty bullets and list items
    result = re.sub(r'^[•·\-]\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^\d+\.\s*$', '', result, flags=re.MULTILINE)
    
    # Clean up empty headers
    result = re.sub(r'^#+\s*$', '', result, flags=re.MULTILINE)
    
    # Remove multiple spaces (but preserve indentation if any, though we don't use it much)
    result = re.sub(r' {2,}', ' ', result)
    
    # Ensure headers have space around them
    result = re.sub(r'\n*(#{1,6} [^\n]+)\n*', r'\n\n\1\n\n', result)
    
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
    Returns (content, success) tuple.
    """
    try:
        session = create_session_with_retries(retries=3, verify_ssl=verify_ssl)
        response = session.get(url, timeout=30, verify=verify_ssl)
        response.raise_for_status()
        
        # Check if we got actual HTML content
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return None, False
        
        soup = BeautifulSoup(response.text, 'html.parser')
        formatted_text = clean_and_format_text(soup)
        
        if formatted_text and len(formatted_text.strip()) > 50:
            return formatted_text, True
        return None, False
        
    except (requests.exceptions.SSLError, ssl.SSLError) as e:
        if verify_ssl:
            # Retry without SSL verification
            return scrape_with_requests(url, verify_ssl=False)
        return None, False
    except Exception as e:
        return None, False
    

def scrape_with_selenium(urls, use_requests_fallback=True):
    """Scrape URLs using Selenium with better error handling and fallback options."""
    if not urls:
        print("No URLs provided for scraping.")
        return ""
    
    all_text = ""
    print("Setting up Edge driver...")
    edge_options = EdgeOptions()
    
    # Anti-detection settings
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    edge_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent
    edge_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0')
    
    # SSL/TLS and security settings
    edge_options.add_argument('--disable-web-security')
    edge_options.add_argument('--allow-running-insecure-content')
    edge_options.add_argument('--ignore-certificate-errors')
    edge_options.add_argument('--ignore-ssl-errors')
    edge_options.add_argument('--ignore-certificate-errors-spki-list')
    edge_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    
    # Performance and stability
    edge_options.add_argument('--disable-extensions')
    edge_options.add_argument('--disable-gpu')
    edge_options.add_argument('--no-sandbox')
    edge_options.add_argument('--disable-dev-shm-usage')
    edge_options.add_argument('--disable-setuid-sandbox')
    edge_options.add_argument('--headless=new')  # Use new headless mode
    
    # Memory optimization
    edge_options.add_argument('--disable-software-rasterizer')
    edge_options.add_argument('--disable-background-timer-throttling')
    edge_options.add_argument('--disable-backgrounding-occluded-windows')
    edge_options.add_argument('--disable-renderer-backgrounding')
    
    # Suppress console noise
    edge_options.add_argument('--log-level=3')  # Only fatal errors
    edge_options.add_argument('--silent')
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    
    # Window size for proper rendering
    edge_options.add_argument('--window-size=1920,1080')
    
    driver = None
    driver_failed = False
    
    try:
        # Suppress Edge driver stderr output (GPU errors, etc.)
        service = EdgeService(
            executable_path=r"..\\msedgedriver.exe",
            log_output=os.devnull
        )
        driver = webdriver.Edge(service=service, options=edge_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
    except Exception as e:
        print(f"⚠ Driver initialization warning: {e}")
        print("Will use requests-based scraping as fallback.")
        driver_failed = True
    
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
            content, success = scrape_with_requests(url)
            if success and content:
                formatted_text = content
                scraped = True
                # try to get title from the content
                try:
                    session = create_session_with_retries(verify_ssl=False)
                    resp = session.get(url, timeout=15, verify=False)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        page_title = title_tag.get_text(strip=True)
                except:
                    pass
                print(f"  ✓ Requests fallback successful")
        
        # Add content if we got any
        if scraped and formatted_text:
            all_text += f"\n\n# {page_title}\n\n{formatted_text}\n\n---\n"
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