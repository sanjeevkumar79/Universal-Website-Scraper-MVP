from datetime import datetime
from typing import Dict, Any
from static_scraper import StaticScraper
from js_scraper import JavaScriptScraper
from models import (
    ScrapeResponse, ScrapeResult, MetaData, Section, 
    SectionContent, LinkItem, ImageItem, Interactions, ErrorInfo
)
import asyncio


class UniversalScraper:
    """Main scraper orchestrator that coordinates static and JS scraping."""
    
    def __init__(self):
        self.static_scraper = StaticScraper(timeout=10)
        self.js_scraper = JavaScriptScraper(page_timeout=30000, interaction_timeout=5000)
        self.total_timeout = 120  # 2 minutes total
    
    async def scrape(self, url: str) -> ScrapeResponse:
        """
        Main scraping entry point. Tries static first, falls back to JS if needed.
        """
        try:
            # Run with total timeout
            result = await asyncio.wait_for(
                self._scrape_internal(url),
                timeout=self.total_timeout
            )
            return result
        except asyncio.TimeoutError:
            # Return partial result with timeout error
            return ScrapeResponse(
                result=ScrapeResult(
                    url=url,
                    scrapedAt=datetime.utcnow().isoformat() + 'Z',
                    meta=MetaData(),
                    sections=[],
                    interactions=Interactions(),
                    errors=[ErrorInfo(
                        message=f'Total scrape timeout after {self.total_timeout} seconds',
                        phase='fetch'
                    )]
                )
            )
    
    async def _scrape_internal(self, url: str) -> ScrapeResponse:
        """Internal scraping logic with static/JS fallback."""
        all_errors = []
        
        # Step 1: Try static scraping
        static_result = await self.static_scraper.scrape(url)
        all_errors.extend(static_result.get('errors', []))
        
        # Step 2: Decide if we need JS rendering
        needs_js = static_result.get('needs_js_fallback', False)
        
        if needs_js:
            # Use JavaScript scraper
            js_result = await self.js_scraper.scrape(url)
            all_errors.extend(js_result.get('errors', []))
            
            # Use JS results
            meta = js_result.get('meta', {})
            sections = js_result.get('sections', [])
            interactions = js_result.get('interactions', {
                'clicks': [],
                'scrolls': 0,
                'pages': [url]
            })
        else:
            # Use static results
            meta = static_result.get('meta', {})
            sections = static_result.get('sections', [])
            interactions = {
                'clicks': [],
                'scrolls': 0,
                'pages': [url]
            }
        
        # Step 3: Ensure we have at least one section with content
        if not sections:
            all_errors.append({
                'message': 'No sections detected in page',
                'phase': 'parse'
            })
            # Create a fallback section
            sections = self._create_fallback_section(url)
        
        # Step 4: Format response
        return self._format_response(url, meta, sections, interactions, all_errors)
    
    def _create_fallback_section(self, url: str) -> list:
        """Create a minimal fallback section when no content is detected."""
        return [{
            'id': 'fallback-0',
            'type': 'unknown',
            'label': 'Unable to extract structured content',
            'sourceUrl': url,
            'content': {
                'headings': [],
                'text': 'No content could be extracted from this page.',
                'links': [],
                'images': [],
                'lists': [],
                'tables': []
            },
            'rawHtml': '<div>No content</div>',
            'truncated': False
        }]
    
    def _format_response(
        self, 
        url: str, 
        meta: Dict[str, Any], 
        sections: list, 
        interactions: Dict[str, Any],
        errors: list
    ) -> ScrapeResponse:
        """Format raw data into ScrapeResponse model."""
        
        # Convert sections to Section models
        section_models = []
        for s in sections:
            content_data = s.get('content', {})
            
            section_models.append(Section(
                id=s.get('id', ''),
                type=s.get('type', 'unknown'),
                label=s.get('label', ''),
                sourceUrl=s.get('sourceUrl', url),
                content=SectionContent(
                    headings=content_data.get('headings', []),
                    text=content_data.get('text', ''),
                    links=[LinkItem(**link) for link in content_data.get('links', [])],
                    images=[ImageItem(**img) for img in content_data.get('images', [])],
                    lists=content_data.get('lists', []),
                    tables=content_data.get('tables', [])
                ),
                rawHtml=s.get('rawHtml', ''),
                truncated=s.get('truncated', False)
            ))
        
        # Convert interactions
        interactions_model = Interactions(
            clicks=interactions.get('clicks', []),
            scrolls=interactions.get('scrolls', 0),
            pages=interactions.get('pages', [url])
        )
        
        # Convert errors
        error_models = [ErrorInfo(**err) for err in errors]
        
        # Build result
        result = ScrapeResult(
            url=url,
            scrapedAt=datetime.utcnow().isoformat() + 'Z',
            meta=MetaData(**meta),
            sections=section_models,
            interactions=interactions_model,
            errors=error_models
        )
        
        return ScrapeResponse(result=result)
