from pydantic import BaseModel, HttpUrl, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


class ScrapeRequest(BaseModel):
    url: str
    
    @field_validator('url')
    @classmethod
    def validate_url_scheme(cls, v: str) -> str:
        """Validate that URL uses http or https scheme only."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Only http:// and https:// URLs are supported')
        return v


class LinkItem(BaseModel):
    text: str
    href: str


class ImageItem(BaseModel):
    src: str
    alt: str


class SectionContent(BaseModel):
    headings: List[str] = []
    text: str = ""
    links: List[LinkItem] = []
    images: List[ImageItem] = []
    lists: List[List[str]] = []
    tables: List[List[List[str]]] = []


class Section(BaseModel):
    id: str
    type: str
    label: str
    sourceUrl: str
    content: SectionContent
    rawHtml: str
    truncated: bool


class Interactions(BaseModel):
    clicks: List[str] = []
    scrolls: int = 0
    pages: List[str] = []


class ErrorInfo(BaseModel):
    message: str
    phase: str  # fetch | render | parse


class MetaData(BaseModel):
    title: str = ""
    description: str = ""
    language: str = ""
    canonical: Optional[str] = None


class ScrapeResult(BaseModel):
    url: str
    scrapedAt: str
    meta: MetaData
    sections: List[Section]
    interactions: Interactions
    errors: List[ErrorInfo] = []


class ScrapeResponse(BaseModel):
    result: ScrapeResult
