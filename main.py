from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from models import ScrapeRequest, ScrapeResponse
from scraper import UniversalScraper
from pydantic import ValidationError
import os


app = FastAPI(title="Universal Website Scraper", version="1.0.0")

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scraper
scraper = UniversalScraper()


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    """
    Scrape a website and return structured JSON.
    
    Request body:
        {
            "url": "https://example.com"
        }
    
    Returns structured JSON with sections, meta, and interactions.
    """
    try:
        result = await scraper.scrape(request.url)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Return error in standard format
        return JSONResponse(
            status_code=500,
            content={
                "result": {
                    "url": request.url,
                    "scrapedAt": "",
                    "meta": {
                        "title": "",
                        "description": "",
                        "language": "",
                        "canonical": None
                    },
                    "sections": [],
                    "interactions": {
                        "clicks": [],
                        "scrolls": 0,
                        "pages": []
                    },
                    "errors": [{
                        "message": f"Internal error: {str(e)}",
                        "phase": "fetch"
                    }]
                }
            }
        )


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    return FileResponse("static/index.html")


# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
