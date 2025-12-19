import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from parser import extract_meta, detect_sections, should_fallback_to_js


class StaticScraper:
    """Scraper for static HTML content using httpx and BeautifulSoup."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrape static content from URL.
        
        Returns:
            Dict with keys: meta, sections, raw_html, needs_js_fallback
        """
        errors = []
        
        try:
            # Fetch HTML
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                html = response.text
        except httpx.TimeoutException:
            errors.append({
                'message': f'Request timeout after {self.timeout} seconds',
                'phase': 'fetch'
            })
            return {
                'meta': self._empty_meta(),
                'sections': [],
                'raw_html': '',
                'needs_js_fallback': False,
                'errors': errors
            }
        except httpx.HTTPStatusError as e:
            errors.append({
                'message': f'HTTP error: {e.response.status_code}',
                'phase': 'fetch'
            })
            return {
                'meta': self._empty_meta(),
                'sections': [],
                'raw_html': '',
                'needs_js_fallback': False,
                'errors': errors
            }
        except Exception as e:
            errors.append({
                'message': f'Failed to fetch URL: {str(e)}',
                'phase': 'fetch'
            })
            return {
                'meta': self._empty_meta(),
                'sections': [],
                'raw_html': '',
                'needs_js_fallback': False,
                'errors': errors
            }
        
        # Parse HTML
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract metadata
            meta = extract_meta(soup)
            
            # Detect and extract sections
            sections = detect_sections(soup, url)
            
            # Determine if JS rendering is needed
            needs_js = should_fallback_to_js(sections, html)
            
            return {
                'meta': meta,
                'sections': sections,
                'raw_html': html,
                'needs_js_fallback': needs_js,
                'errors': errors
            }
            
        except Exception as e:
            errors.append({
                'message': f'Failed to parse HTML: {str(e)}',
                'phase': 'parse'
            })
            return {
                'meta': self._empty_meta(),
                'sections': [],
                'raw_html': html if 'html' in locals() else '',
                'needs_js_fallback': True,
                'errors': errors
            }
    
    def _empty_meta(self) -> Dict[str, Any]:
        """Return empty metadata structure."""
        return {
            'title': '',
            'description': '',
            'language': '',
            'canonical': None
        }
