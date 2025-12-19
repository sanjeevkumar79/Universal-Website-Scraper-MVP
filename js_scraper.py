from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from parser import extract_meta, detect_sections
import asyncio


class JavaScriptScraper:
    """Scraper for JavaScript-rendered content using Playwright."""
    
    def __init__(self, page_timeout: int = 30000, interaction_timeout: int = 5000):
        self.page_timeout = page_timeout
        self.interaction_timeout = interaction_timeout
        self.max_depth = 3
    
    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrape JavaScript-rendered content from URL with interactions.
        
        Returns:
            Dict with keys: meta, sections, interactions, errors
        """
        errors = []
        interactions = {
            'clicks': [],
            'scrolls': 0,
            'pages': [url]
        }
        
        async with async_playwright() as p:
            browser = None
            try:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                page.set_default_timeout(self.page_timeout)
                
                # Navigate to URL
                try:
                    await page.goto(url, wait_until='networkidle', timeout=self.page_timeout)
                except PlaywrightTimeout:
                    errors.append({
                        'message': 'Page load timeout',
                        'phase': 'render'
                    })
                except Exception as e:
                    errors.append({
                        'message': f'Failed to load page: {str(e)}',
                        'phase': 'render'
                    })
                    return await self._error_result(browser, errors)
                
                # Perform interactions
                await self._perform_interactions(page, interactions, errors)
                
                # Get final HTML
                html = await page.content()
                
                # Parse
                try:
                    soup = BeautifulSoup(html, 'lxml')
                    meta = extract_meta(soup)
                    sections = detect_sections(soup, url)
                    
                    return {
                        'meta': meta,
                        'sections': sections,
                        'interactions': interactions,
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
                        'interactions': interactions,
                        'errors': errors
                    }
                
            except Exception as e:
                errors.append({
                    'message': f'Browser error: {str(e)}',
                    'phase': 'render'
                })
                return {
                    'meta': self._empty_meta(),
                    'sections': [],
                    'interactions': interactions,
                    'errors': errors
                }
            finally:
                if browser:
                    await browser.close()
    
    async def _perform_interactions(self, page: Page, interactions: Dict, errors: List[Dict]):
        """Perform interactions to reveal more content."""
        try:
            # 1. Click tabs to reveal hidden content
            await self._click_tabs(page, interactions, errors)
            
            # 2. Click "Load More" / "Show More" buttons
            await self._click_load_more(page, interactions, errors)
            
            # 3. Infinite scroll to depth 3
            await self._infinite_scroll(page, interactions, errors)
            
            # 4. Follow pagination links to depth 3
            await self._follow_pagination(page, interactions, errors)
            
        except Exception as e:
            errors.append({
                'message': f'Interaction error: {str(e)}',
                'phase': 'render'
            })
    
    async def _click_tabs(self, page: Page, interactions: Dict, errors: List[Dict]):
        """Detect and click tab elements."""
        try:
            # Common tab selectors
            tab_selectors = [
                '[role="tab"]',
                '.tab:not(.active)',
                '[data-tab]',
                'button[aria-selected="false"]'
            ]
            
            for selector in tab_selectors:
                try:
                    tabs = await page.query_selector_all(selector)
                    for i, tab in enumerate(tabs[:3]):  # Click up to 3 tabs
                        try:
                            await tab.click(timeout=self.interaction_timeout)
                            interactions['clicks'].append(f'Tab: {selector} (index {i})')
                            await asyncio.sleep(0.5)  # Wait for content to load
                        except:
                            pass
                except:
                    pass
        except Exception as e:
            pass  # Silently fail for tabs
    
    async def _click_load_more(self, page: Page, interactions: Dict, errors: List[Dict]):
        """Click 'Load More' / 'Show More' buttons."""
        try:
            load_more_selectors = [
                'button:has-text("Load more")',
                'button:has-text("Show more")',
                'a:has-text("Load more")',
                'a:has-text("Show more")',
                '[class*="load-more"]',
                '[class*="show-more"]'
            ]
            
            for depth in range(self.max_depth):
                clicked = False
                for selector in load_more_selectors:
                    try:
                        button = await page.query_selector(selector)
                        if button and await button.is_visible():
                            await button.click(timeout=self.interaction_timeout)
                            interactions['clicks'].append(f'Load More: {selector}')
                            await asyncio.sleep(1)  # Wait for content
                            clicked = True
                            break
                    except:
                        pass
                
                if not clicked:
                    break
        except Exception as e:
            pass  # Silently fail
    
    async def _infinite_scroll(self, page: Page, interactions: Dict, errors: List[Dict]):
        """Perform infinite scroll to depth 3."""
        try:
            for depth in range(self.max_depth):
                # Get current scroll height
                prev_height = await page.evaluate('document.body.scrollHeight')
                
                # Scroll to bottom
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                interactions['scrolls'] += 1
                
                # Wait for new content
                try:
                    await asyncio.sleep(1)
                    await page.wait_for_function(
                        f'document.body.scrollHeight > {prev_height}',
                        timeout=self.interaction_timeout
                    )
                except:
                    # No new content loaded
                    break
        except Exception as e:
            pass  # Silently fail
    
    async def _follow_pagination(self, page: Page, interactions: Dict, errors: List[Dict]):
        """Follow pagination links to depth 3."""
        try:
            pagination_selectors = [
                'a[aria-label*="Next"]',
                'a:has-text("Next")',
                'a:has-text("→")',
                '[class*="next"]',
                '[rel="next"]'
            ]
            
            for depth in range(self.max_depth - 1):  # -1 because we already have initial page
                clicked = False
                for selector in pagination_selectors:
                    try:
                        link = await page.query_selector(selector)
                        if link and await link.is_visible():
                            # Get href before clicking
                            href = await link.get_attribute('href')
                            
                            await link.click(timeout=self.interaction_timeout)
                            await page.wait_for_load_state('networkidle', timeout=self.page_timeout)
                            
                            current_url = page.url
                            interactions['pages'].append(current_url)
                            clicked = True
                            break
                    except:
                        pass
                
                if not clicked:
                    break
        except Exception as e:
            pass  # Silently fail
    
    async def _error_result(self, browser: Browser, errors: List[Dict]) -> Dict[str, Any]:
        """Return error result and close browser."""
        if browser:
            await browser.close()
        return {
            'meta': self._empty_meta(),
            'sections': [],
            'interactions': {'clicks': [], 'scrolls': 0, 'pages': []},
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
