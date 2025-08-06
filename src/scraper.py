import time
import re
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
        
        # Quick HEAD request to check if URL is accessible
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code >= 400:
            return False, f"HTTP {response.status_code} error"
        
        return True, "Valid"
    
    except requests.exceptions.ConnectionError:
        return False, "Connection failed - site may be down"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
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
        
        # Validate URL
        print(f"Validating {url}...")
        is_valid, message = is_valid_url(url)
        
        if is_valid:
            urls.append(url)
            print(f"✓ Added: {url}")
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
            alt_text = img.get('alt', '')
            title_text = img.get('title', '')
            
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
            sup_text = sup.get_text()
            if re.search(r'edit|```math\d+```|```mathcitation|^```math\w```$', sup_text, re.I):
                sup.decompose()
        
        # Handle links - preserve meaningful ones
        for link in cell.find_all('a'):
            link_text = link.get_text(strip=True)
            # Remove empty links or edit links
            if not link_text or re.search(r'^(edit|source|citation)$', link_text, re.I):
                link.decompose()
            else:
                # Replace link with its text
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
        if not element.get_text(strip=True):
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
                    table_rows.append(" | ".join(header_texts))
                    table_rows.append("-" * min(len(table_rows[0]), 80))  # Separator line
            
            # Process data rows
            row_count = 0
            empty_row_count = 0
            
            for row in rows[:100]:  # Limit rows to prevent huge tables
                # Skip rows that only contain headers
                if row.find_all('th') and not row.find_all('td'):
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
                    table_rows.append(" | ".join(cells))
                    row_count += 1
                else:
                    empty_row_count += 1
                    
                # Stop if too many empty rows in a row
                if empty_row_count > 3:
                    break
            
            # Only return table if it has meaningful content
            if table_rows and row_count > 0:
                return "\n" + "\n".join(table_rows) + "\n\n"
            else:
                return ""
        
        # Handle pre/code blocks
        if tag_name in ['pre', 'code']:
            code_text = element.get_text(strip=False)
            if code_text.strip():
                if tag_name == 'pre':
                    return f"\n```\n{code_text}\n```\n"
                else:
                    return f"`{code_text}`"
            return ""
        
        # Handle blockquotes
        if tag_name == 'blockquote':
            quote_content = []
            for child in element.children:
                child_text = process_element(child)
                if child_text:
                    quote_content.append(child_text)
            
            if quote_content:
                joined = ' '.join(quote_content)
                return f"\n> {joined}\n"
            return ""
        
        # Process children for other elements
        content = []
        for child in element.children:
            child_content = process_element(child)
            if child_content:  # Only add non-empty content
                content.append(child_content)
        
        if not content:  # Skip if no content after processing
            return ""
            
        joined_content = " ".join(content)
        
        # Format based on tag type
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            # Skip headers that are too short or just numbers
            if len(joined_content) < 2 or re.match(r'^\d+\.?$', joined_content):
                return ""
            return f"\n{'#' * level} {joined_content}\n"
        elif tag_name == 'p':
            # Skip very short paragraphs that might be captions or labels
            return f"{joined_content}\n"
        elif tag_name == 'div': #div newline
                if len(joined_content) > 2:
                    return f"{joined_content}\n"
        elif tag_name == 'li':
            # Check parent to determine list type
            parent = element.find_parent(['ul', 'ol'])
            if parent and parent.name == 'ol':
                return f"• {joined_content}\n"  # Using bullet for both for consistency
            else:
                return f"• {joined_content}\n"
        elif tag_name in ['strong', 'b']:
            return f"**{joined_content}**"
        elif tag_name in ['em', 'i']:
            return f"*{joined_content}*"
        elif tag_name == 'a':
            # Include URL for external links
            href = element.get('href', '')
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                # Only include URL if it's meaningful
                if len(joined_content) > 2 and not re.match(r'^```math\d+```$', joined_content):
                    return f"[{joined_content}]({href})"
            return joined_content
        elif tag_name == 'br':
            return "\n"
        elif tag_name == 'hr':
            return "\n---\n"
        elif tag_name in ['ul', 'ol']:
            # Lists are handled by their li children
            return f"\n{joined_content}"
        else:
            return joined_content

    # Process the main content
    result = process_element(main_content)
    
    # Clean up the final result
    # Remove excessive newlines
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    
    # Remove empty bullets and list items
    result = re.sub(r'^[•·]\s*$', '', result, flags=re.MULTILINE)
    result = re.sub(r'^\d+\.\s*$', '', result, flags=re.MULTILINE)
    
    # Clean up empty headers
    result = re.sub(r'^#+\s*$', '', result, flags=re.MULTILINE)
    
    # Remove multiple spaces
    result = re.sub(r' {2,}', ' ', result)
    
    # Clean up spacing around headers
    result = re.sub(r'\n*(#{1,6}[^\n]+)\n*', r'\n\n\1\n\n', result)
    
    # Remove trailing whitespace on each line
    result = re.sub(r' +$', '', result, flags=re.MULTILINE)
    
    # Final cleanup - remove leading/trailing whitespace
    result = result.strip()
    
    # If result is too short, it's probably not meaningful content
    if len(result.split()) < 10:
        return ""
    
    return result
    

def scrape_with_selenium(urls):
    """Scrape URLs using Selenium with better error handling."""
    if not urls:
        print("No URLs provided for scraping.")
        return ""
    
    all_text = ""
    print("Setting up Edge driver...")
    edge_options = EdgeOptions()
    edge_options.add_argument('--headless')
    edge_options.add_argument('--no-sandbox')
    edge_options.add_argument('--disable-dev-shm-usage')
    edge_options.add_argument('log-level=3')
    edge_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        service = EdgeService(executable_path=r"..\\msedgedriver.exe")
        driver = webdriver.Edge(service=service, options=edge_options)
    except Exception as e:
        print(f"✗ Driver initialization error: {e}")
        return ""
    
    successful_scrapes = 0
    total_urls = len(urls)
    
    for i, url in enumerate(urls, 1):
        try:
            print(f"[{i}/{total_urls}] Loading {url}...")
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # Get the page title
            page_title = driver.title or "Untitled Page"
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            formatted_text = clean_and_format_text(soup)
            
            if formatted_text:
                # Use page title instead of URL in the header
                all_text += f"\n\n{page_title}\n{'-' * len(page_title)}\n{formatted_text}"
                successful_scrapes += 1
                print(f"✓ Successfully scraped: {url}")
            else:
                print(f"⚠ Warning: No main content could be identified for: {url}")
                
        except Exception as e:
            print(f"✗ Error processing {url}: {e}")
    
    driver.quit()
    
    # Summary
    print(f"\nScraping complete: {successful_scrapes}/{total_urls} URLs successful")
    
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