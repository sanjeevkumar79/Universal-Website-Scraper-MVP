# Design Notes - Universal Website Scraper

## Architecture Overview

The scraper uses a **two-tier approach**:

1. **Static Scraping** (First attempt) - Fast extraction using `httpx` + `BeautifulSoup`
2. **JavaScript Rendering** (Fallback) - Playwright-based browser automation when needed

This design prioritizes speed while ensuring completeness.

## Static vs JavaScript Fallback Heuristic

### Decision Logic

The scraper decides to fall back to JavaScript rendering based on:

1. **Content threshold**: If total text extracted from all sections < 100 characters
2. **Framework detection**: If heavy JavaScript frameworks are detected (React, Vue, Angular, Next.js, Nuxt)
   - Additional check: If framework detected BUT content > 500 chars, no fallback (server-side rendered content)

### Rationale

- Most modern websites serve some content in static HTML even if they use JS frameworks
- Threshold of 100 chars catches "empty" pages that need JS
- Framework detection helps identify client-side rendered apps
- 500 char exception handles SSR (Server-Side Rendered) frameworks like Next.js

### Trade-offs

- **False positives**: Some static pages with minimal content may trigger JS rendering unnecessarily
- **False negatives**: Some JS-heavy sites with SSR may not trigger fallback
- **Mitigation**: Conservative thresholds chosen based on testing

## Wait Strategies

### Static Scraping

- **Network timeout**: 10 seconds
- **Follow redirects**: Enabled
- **No wait for JS**: Does not execute JavaScript

### JavaScript Rendering

- **Page load**: `wait_until='networkidle'` with 30-second timeout
  - Waits for network to be idle (no requests for 500ms)
  - Ensures most dynamic content has loaded
  
- **Interaction waits**: 5 seconds timeout per interaction
  - Tab clicks: 500ms delay after each click
  - Load more: 1 second delay after click
  - Scroll: 1 second delay + wait for scroll height change
  - Pagination: Wait for `networkidle` after navigation

### Rationale

- `networkidle` is reliable for most SPAs (Single Page Apps)
- Short delays prevent race conditions
- Timeouts prevent hanging on broken pages

## Interaction Logic

### 1. Tab Clicks

**Selectors tried** (in order):
- `[role="tab"]` - ARIA standard
- `.tab:not(.active)` - Common class pattern
- `[data-tab]` - Data attribute pattern
- `button[aria-selected="false"]` - ARIA button tabs

**Behavior**:
- Click up to 3 tabs per selector
- 500ms delay between clicks
- Silently fail if selector not found

**Why this works**:
- Most tab implementations use ARIA roles or standard classes
- Limited to 3 to avoid excessive scraping
- Delay allows content to render

### 2. Load More / Show More Clicks

**Selectors tried** (in order):
- `button:has-text("Load more")` - Playwright text matching
- `button:has-text("Show more")`
- `a:has-text("Load more")` - Sometimes implemented as links
- `a:has-text("Show more")`
- `[class*="load-more"]` - Class name patterns
- `[class*="show-more"]`

**Behavior**:
- Try all selectors until one succeeds
- Click up to depth 3 (repeat 3 times)
- 1-second delay after each click
- Stop if button not found or not visible

**Why this works**:
- Text-based matching catches most variations
- Class patterns catch custom implementations
- Depth limit prevents infinite loops

### 3. Infinite Scroll

**Algorithm**:
```
for depth in range(3):
    1. Record current scroll height
    2. Scroll to bottom
    3. Wait for scroll height to increase (5s timeout)
    4. If no change, break
```

**Behavior**:
- Maximum 3 scrolls
- 1-second initial delay
- Wait for DOM change before continuing
- Stop if no new content loads

**Why this works**:
- Scroll height change is reliable indicator of new content
- Timeout prevents waiting forever
- Depth limit keeps scraping bounded

### 4. Pagination

**Selectors tried** (in order):
- `a[aria-label*="Next"]` - ARIA labeled
- `a:has-text("Next")` - Text matching
- `a:has-text("→")` - Arrow symbol
- `[class*="next"]` - Class pattern
- `[rel="next"]` - HTML5 standard

**Behavior**:
- Follow up to depth 3 (visit 4 pages total including initial)
- Wait for `networkidle` after each navigation
- Record each URL in `interactions.pages`
- Stop if link not found or not visible

**Why this works**:
- Multiple selector strategies catch most pagination styles
- `networkidle` ensures page fully loaded
- Depth limit prevents crawling entire site

## Section Grouping Algorithm

### Detection Strategy

1. **Semantic landmarks** (preferred):
   - `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`, `<footer>`
   
2. **Fallback** (if no landmarks):
   - Top-level `<div>` elements with > 50 characters of text

### Content Extraction Per Section

- **Headings**: `h1` through `h6`
- **Text**: All text nodes, cleaned of scripts/styles
- **Links**: All `<a>` tags with `href`, converted to absolute URLs
- **Images**: All `<img>` tags with `src`, converted to absolute URLs
- **Lists**: All `<ul>` and `<ol>` with their `<li>` items
- **Tables**: All `<table>` with row/cell structure preserved

### Section Classification

**Types assigned**:
- `nav` - Navigation elements
- `footer` - Footer elements
- `hero` - Hero/banner sections (header tag or class/id keywords)
- `pricing` - Pricing sections (class/id keywords)
- `faq` - FAQ sections (class/id keywords)
- `grid` - Grid/card layouts (class/id keywords)
- `list` - List-heavy sections (2+ lists)
- `section` - Default/generic section

**Classification logic**:
1. Check tag name (`nav`, `footer`, `header`)
2. Check classes/IDs for keywords
3. Check content structure (e.g., number of lists)
4. Default to `section`

### Label Generation

**Priority order**:
1. First heading in section
2. `aria-label` attribute
3. First 5-7 words of text content
4. Fallback: "Section {tagname}"

**Rationale**:
- Headings are most semantically meaningful
- ARIA labels are intended for description
- Text preview better than nothing
- Always provide a label (never empty)

## Noise Filtering

### What is filtered out:

- **Empty sections**: Less than 10 characters of text
- **Script/style tags**: Removed before text extraction
- **Duplicate links**: Same `href` within a section
- **Duplicate images**: Same `src` within a section
- **Empty strings**: All empty values filtered from lists/arrays
- **Anchor-only links**: Links starting with `#` (internal anchors)

### What is preserved:

- **All raw HTML**: Stored in `rawHtml` (truncated to 500 chars)
- **Original structure**: Lists and tables maintain nesting
- **Partial data**: If errors occur, return what was extracted

### Rationale

- Balance between cleanliness and completeness
- Truncate HTML to prevent huge payloads
- Never return completely empty result if any data exists

## Error Handling Philosophy

### Principles

1. **Never crash** - Always return a response, even if partial
2. **Record errors** - Populate `errors[]` array with details
3. **Phase tracking** - Tag each error with phase: `fetch | render | parse`
4. **Continue on partial failure** - Extract what's possible

### Error Types

- **Fetch errors**: Network issues, timeouts, HTTP errors
- **Render errors**: Playwright failures, page load timeouts
- **Parse errors**: HTML parsing issues, malformed content

### Timeout Hierarchy

```
Total scrape: 120s
├── Static fetch: 10s
└── JS rendering: 30s page load
    ├── Tab clicks: 5s each
    ├── Load more: 5s each
    ├── Scroll wait: 5s each
    └── Pagination: 30s per page
```

### Graceful Degradation

1. If static scraping fails → Try JS rendering
2. If JS rendering fails → Return static results (if any)
3. If all fails → Return error response with empty sections
4. If timeout → Return partial results collected so far

## Performance Considerations

### Static Scraping

- **Speed**: ~1-3 seconds typical
- **Memory**: Low (~10-50 MB)
- **CPU**: Minimal

### JavaScript Rendering

- **Speed**: ~5-30 seconds typical
- **Memory**: High (~200-500 MB for browser)
- **CPU**: Moderate to high

### Optimization Strategies

1. **Try static first** - Avoid browser overhead when possible
2. **Headless mode** - No GUI rendering saves resources
3. **Single browser instance** - Reuse context within scrape
4. **Truncate HTML** - Limit response size
5. **Timeout limits** - Prevent runaway scraping

## Known Edge Cases

### Handled

- Sites with no semantic structure → Fallback to div grouping
- Sites blocking User-Agent → Returns error (scraper is identifiable)
- Infinite scroll pages → Limited to depth 3
- Client-side routing → Pagination navigation works
- Lazy-loaded images → Captured after interactions

### Not Handled

- CAPTCHA challenges → Returns error
- Login-required content → Only scrapes public content
- iframes → Not traversed (main page only)
- Shadow DOM → Not fully supported
- Dynamic content triggered by mouse hover → Not triggered

## Future Improvements

Potential enhancements not in MVP:

1. **Custom wait conditions** - User-specified selectors to wait for
2. **Screenshot capture** - Visual proof of scraping
3. **Retry logic** - Automatic retry on transient failures
4. **Rate limiting** - Built-in delays for ethical scraping
5. **Cookie support** - Handle cookie consent banners
6. **Proxy support** - Rotate IPs for large scrapes
7. **Sitemap integration** - Structured multi-page scraping
8. **Content filtering** - User-specified include/exclude patterns

## Testing Strategy

### Unit Testing

Not implemented in MVP, but recommended tests:

- URL validation logic
- Section classification algorithm
- Text cleaning functions
- URL normalization

### Integration Testing

Manual testing performed with:

- Static sites (example.com, info.cern.ch)
- JS-rendered sites (quotes.toscrape.com/js)
- Infinite scroll (quotes.toscrape.com/scroll)
- Pagination (quotes.toscrape.com)

### Load Testing

Not performed in MVP. For production:

- Test with concurrent requests
- Monitor memory usage with browser instances
- Test timeout handling under load
