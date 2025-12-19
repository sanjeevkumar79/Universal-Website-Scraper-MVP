from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Tuple
import hashlib
import re


def normalize_url(base_url: str, url: str) -> str:
    """Convert relative URLs to absolute URLs."""
    if not url:
        return ""
    # Handle protocol-relative URLs
    if url.startswith("//"):
        parsed_base = urlparse(base_url)
        return f"{parsed_base.scheme}:{url}"
    return urljoin(base_url, url)


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def generate_section_id(element: Tag, index: int) -> str:
    """Generate a stable ID for a section."""
    # Use tag name + class + index for stability
    classes = ' '.join(element.get('class', []))
    id_str = f"{element.name}-{classes}-{index}"
    return hashlib.md5(id_str.encode()).hexdigest()[:12]


def classify_section_type(element: Tag, first_heading: str = "") -> str:
    """Classify section type based on content and structure."""
    tag_name = element.name.lower()
    classes = ' '.join(element.get('class', [])).lower()
    id_attr = (element.get('id') or '').lower()
    text = clean_text(element.get_text()).lower()
    
    # Check tag-based types
    if tag_name == 'nav':
        return 'nav'
    if tag_name == 'footer':
        return 'footer'
    if tag_name == 'header':
        return 'hero'
    
    # Check class/id-based types
    if any(keyword in classes or keyword in id_attr for keyword in ['hero', 'banner', 'jumbotron']):
        return 'hero'
    if any(keyword in classes or keyword in id_attr for keyword in ['pricing', 'price', 'plan']):
        return 'pricing'
    if any(keyword in classes or keyword in id_attr for keyword in ['faq', 'question', 'accordion']):
        return 'faq'
    if any(keyword in classes or keyword in id_attr for keyword in ['grid', 'cards', 'features']):
        return 'grid'
    if 'list' in classes or 'list' in id_attr:
        return 'list'
    
    # Check for list-heavy content
    lists = element.find_all(['ul', 'ol'], recursive=True)
    if len(lists) >= 2:
        return 'list'
    
    return 'section'


def generate_label(element: Tag, first_heading: str = "") -> str:
    """Generate a human-readable label for a section."""
    if first_heading:
        return first_heading[:60]  # Truncate if too long
    
    # Use aria-label or title
    aria_label = element.get('aria-label')
    if aria_label:
        return clean_text(aria_label)[:60]
    
    # Use first 5-7 words of text content
    text = clean_text(element.get_text())
    if text:
        words = text.split()[:7]
        label = ' '.join(words)
        if len(words) == 7 and len(text.split()) > 7:
            label += '...'
        return label[:60]
    
    # Fallback
    return f"Section {element.name}"


def extract_headings(element: Tag) -> List[str]:
    """Extract all headings from an element."""
    headings = []
    for tag in element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=True):
        text = clean_text(tag.get_text())
        if text:
            headings.append(text)
    return headings


def extract_text(element: Tag) -> str:
    """Extract cleaned text content from an element."""
    # Remove script and style tags
    for script in element.find_all(['script', 'style']):
        script.decompose()
    
    text = element.get_text(separator=' ', strip=True)
    return clean_text(text)


def extract_links(element: Tag, base_url: str) -> List[Dict[str, str]]:
    """Extract all links from an element."""
    links = []
    seen_hrefs = set()
    
    for a_tag in element.find_all('a', href=True):
        href = a_tag['href']
        absolute_href = normalize_url(base_url, href)
        
        # Skip duplicates and empty/anchor-only links
        if not absolute_href or absolute_href in seen_hrefs or absolute_href.startswith('#'):
            continue
        
        seen_hrefs.add(absolute_href)
        text = clean_text(a_tag.get_text())
        
        links.append({
            'text': text or absolute_href,
            'href': absolute_href
        })
    
    return links


def extract_images(element: Tag, base_url: str) -> List[Dict[str, str]]:
    """Extract all images from an element."""
    images = []
    seen_srcs = set()
    
    for img_tag in element.find_all('img', src=True):
        src = img_tag['src']
        absolute_src = normalize_url(base_url, src)
        
        if not absolute_src or absolute_src in seen_srcs:
            continue
        
        seen_srcs.add(absolute_src)
        alt = clean_text(img_tag.get('alt', ''))
        
        images.append({
            'src': absolute_src,
            'alt': alt
        })
    
    return images


def extract_lists(element: Tag) -> List[List[str]]:
    """Extract all lists from an element."""
    lists = []
    
    for list_tag in element.find_all(['ul', 'ol'], recursive=True):
        items = []
        for li in list_tag.find_all('li', recursive=False):
            text = clean_text(li.get_text())
            if text:
                items.append(text)
        if items:
            lists.append(items)
    
    return lists


def extract_tables(element: Tag) -> List[List[List[str]]]:
    """Extract all tables from an element."""
    tables = []
    
    for table_tag in element.find_all('table', recursive=True):
        rows = []
        for tr in table_tag.find_all('tr'):
            cells = []
            for cell in tr.find_all(['td', 'th']):
                text = clean_text(cell.get_text())
                cells.append(text)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    
    return tables


def truncate_html(html: str, max_length: int = 500) -> Tuple[str, bool]:
    """Truncate HTML to a maximum length."""
    if len(html) <= max_length:
        return html, False
    return html[:max_length] + '...', True


def extract_meta(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract meta information from HTML."""
    meta = {
        'title': '',
        'description': '',
        'language': '',
        'canonical': None
    }
    
    # Title
    title_tag = soup.find('title')
    if title_tag:
        meta['title'] = clean_text(title_tag.get_text())
    
    # Meta description
    desc_tag = soup.find('meta', attrs={'name': 'description'})
    if desc_tag and desc_tag.get('content'):
        meta['description'] = clean_text(desc_tag['content'])
    
    # Language
    html_tag = soup.find('html')
    if html_tag and html_tag.get('lang'):
        meta['language'] = html_tag['lang']
    
    # Canonical URL
    canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
    if canonical_tag and canonical_tag.get('href'):
        meta['canonical'] = canonical_tag['href']
    
    return meta


def detect_sections(soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
    """Detect and extract sections from HTML."""
    sections = []
    
    # Find semantic landmarks and sections
    landmarks = soup.find_all(['header', 'nav', 'main', 'section', 'article', 'aside', 'footer'])
    
    # If no landmarks, try to group by headings
    if not landmarks:
        landmarks = []
        body = soup.find('body')
        if body:
            # Find top-level content containers
            for child in body.find_all(['div'], recursive=False):
                if len(clean_text(child.get_text())) > 50:
                    landmarks.append(child)
    
    for index, element in enumerate(landmarks):
        # Extract content
        headings = extract_headings(element)
        text = extract_text(element)
        
        # Skip if section has no meaningful content
        if not text or len(text) < 10:
            continue
        
        first_heading = headings[0] if headings else ""
        
        section_data = {
            'id': generate_section_id(element, index),
            'type': classify_section_type(element, first_heading),
            'label': generate_label(element, first_heading),
            'sourceUrl': base_url,
            'content': {
                'headings': headings,
                'text': text,
                'links': extract_links(element, base_url),
                'images': extract_images(element, base_url),
                'lists': extract_lists(element),
                'tables': extract_tables(element)
            },
            'rawHtml': '',
            'truncated': False
        }
        
        # Add truncated HTML
        raw_html = str(element)
        truncated_html, is_truncated = truncate_html(raw_html)
        section_data['rawHtml'] = truncated_html
        section_data['truncated'] = is_truncated
        
        sections.append(section_data)
    
    return sections


def should_fallback_to_js(sections: List[Dict[str, Any]], html: str) -> bool:
    """Determine if we should fallback to JS rendering."""
    # Check if we have meaningful content
    total_text_length = sum(len(s['content']['text']) for s in sections)
    
    if total_text_length < 100:
        return True
    
    # Check for heavy JS frameworks
    html_lower = html.lower()
    js_frameworks = ['react', 'vue', 'angular', 'next.js', '__next', 'nuxt']
    
    for framework in js_frameworks:
        if framework in html_lower:
            # Additional check: if framework detected but we have content, don't fallback
            if total_text_length > 500:
                return False
            return True
    
    return False
