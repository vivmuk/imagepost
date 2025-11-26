"""
FastAPI Server for Venice Summary Report Generator
Provides REST API endpoints for generating reports

Run with: uvicorn server:app --reload
"""
import asyncio
import base64
from pathlib import Path
from typing import Optional
from datetime import datetime
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

app = FastAPI(
    title="Venice Summary Report API",
    description="Generate AI-powered summary reports with images using Venice API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Startup event handler - verify critical imports"""
    try:
        # Test that critical modules can be imported
        from config import config
        print(f"✓ Config loaded successfully")
        print(f"✓ API Key configured: {'Yes' if config.venice.api_key else 'No'}")
    except Exception as e:
        print(f"⚠ Warning during startup: {e}")
        # Don't fail startup if config has issues


class URLInput(BaseModel):
    """URL input for summarization"""
    url: HttpUrl
    generate_images: bool = True
    generate_hero: bool = True


class TextInput(BaseModel):
    """Text input for summarization"""
    text: str
    title: str = "Document Summary"
    generate_images: bool = True
    generate_hero: bool = True


class ReportStatus(BaseModel):
    """Report generation status"""
    status: str
    report_id: str
    message: str
    report_url: Optional[str] = None


# Store for background tasks
report_store = {}


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint to prevent 404 errors"""
    return JSONResponse(content={}, status_code=204)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page with API documentation link"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Venice Summary Report API</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #0a0a0f;
                color: #e2e8f0;
            }
            h1 { 
                background: linear-gradient(135deg, #6366f1, #d946ef);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            a { color: #6366f1; }
            code { 
                background: #1a1a25;
                padding: 2px 8px;
                border-radius: 4px;
            }
            .endpoint {
                background: #12121a;
                border: 1px solid #2d2d3a;
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
            }
        </style>
    </head>
    <body>
        <h1>🎨 Venice Summary Report API</h1>
        <p>Generate AI-powered summary reports with images using Venice API.</p>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <h3>POST /api/summarize/url</h3>
            <p>Summarize content from a URL</p>
            <code>{"url": "https://example.com/article"}</code>
        </div>
        
        <div class="endpoint">
            <h3>POST /api/summarize/text</h3>
            <p>Summarize raw text content</p>
            <code>{"text": "Your content here...", "title": "Optional title"}</code>
        </div>
        
        <div class="endpoint">
            <h3>POST /api/summarize/file</h3>
            <p>Upload and summarize a file (PDF, DOCX, TXT)</p>
        </div>
        
        <div class="endpoint">
            <h3>GET /api/report/{report_id}</h3>
            <p>Get the generated HTML report</p>
        </div>
        
        <p><a href="/docs">📚 Interactive API Documentation</a></p>
    </body>
    </html>
    """


@app.post("/api/summarize/url", response_model=ReportStatus)
async def summarize_url(input_data: URLInput, background_tasks: BackgroundTasks):
    """
    Generate a summary report from a URL
    
    The report is generated in the background. Use the returned report_id
    to check status and retrieve the report.
    """
    report_id = f"url_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_store[report_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(
        generate_report_task,
        report_id=report_id,
        source=str(input_data.url),
        generate_images=input_data.generate_images,
        generate_hero=input_data.generate_hero
    )
    
    return ReportStatus(
        status="processing",
        report_id=report_id,
        message="Report generation started. Check /api/status/{report_id} for progress."
    )


@app.post("/api/summarize/text", response_model=ReportStatus)
async def summarize_text(input_data: TextInput, background_tasks: BackgroundTasks):
    """Generate a summary report from text content"""
    report_id = f"text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_store[report_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(
        generate_report_task,
        report_id=report_id,
        source=input_data.text,
        generate_images=input_data.generate_images,
        generate_hero=input_data.generate_hero,
        title=input_data.title
    )
    
    return ReportStatus(
        status="processing",
        report_id=report_id,
        message="Report generation started. Check /api/status/{report_id} for progress."
    )


@app.post("/api/summarize/file", response_model=ReportStatus)
async def summarize_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    generate_images: bool = Form(True),
    generate_hero: bool = Form(True)
):
    """Upload and generate a summary report from a file"""
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt', '.md', '.epub']
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file temporarily
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / file.filename
    
    content = await file.read()
    temp_path.write_bytes(content)
    
    report_id = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_store[report_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(
        generate_report_task,
        report_id=report_id,
        source=str(temp_path),
        generate_images=generate_images,
        generate_hero=generate_hero
    )
    
    return ReportStatus(
        status="processing",
        report_id=report_id,
        message="Report generation started. Check /api/status/{report_id} for progress."
    )


@app.get("/api/status/{report_id}", response_model=ReportStatus)
async def get_status(report_id: str):
    """Check the status of a report generation task"""
    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")
    
    data = report_store[report_id]
    
    if data["status"] == "completed":
        return ReportStatus(
            status="completed",
            report_id=report_id,
            message="Report ready",
            report_url=f"/api/report/{report_id}"
        )
    elif data["status"] == "error":
        return ReportStatus(
            status="error",
            report_id=report_id,
            message=data.get("error", "Unknown error")
        )
    else:
        return ReportStatus(
            status="processing",
            report_id=report_id,
            message="Report is being generated..."
        )


@app.get("/api/report/{report_id}", response_class=HTMLResponse)
async def get_report(report_id: str):
    """Retrieve the generated HTML report"""
    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")
    
    data = report_store[report_id]
    
    if data["status"] != "completed":
        raise HTTPException(status_code=202, detail="Report not ready yet")
    
    return HTMLResponse(content=data["result"])


@app.get("/api/report/{report_id}/download")
async def download_report(report_id: str):
    """Download the report as an HTML file"""
    if report_id not in report_store:
        raise HTTPException(status_code=404, detail="Report not found")
    
    data = report_store[report_id]
    
    if data["status"] != "completed":
        raise HTTPException(status_code=202, detail="Report not ready yet")
    
    return HTMLResponse(
        content=data["result"],
        headers={
            "Content-Disposition": f"attachment; filename=report_{report_id}.html"
        }
    )


async def generate_report_task(
    report_id: str,
    source: str,
    generate_images: bool = True,
    generate_hero: bool = True,
    title: str = None
):
    """Background task to generate the report"""
    # Lazy imports to avoid blocking app startup
    from scraper import ContentScraper
    from summarizer import VeniceSummarizer
    from image_generator import VeniceImageGenerator
    from report_generator import ReportGenerator
    
    try:
        scraper = ContentScraper()
        summarizer = VeniceSummarizer()
        image_generator = VeniceImageGenerator()
        report_generator = ReportGenerator()
        
        # Stage 1: Extract content
        content = await scraper.extract(source)
        if title:
            content.title = title
        
        # Stage 2: Summarize
        summary = await summarizer.summarize(content)
        
        # Stage 3: Generate images
        images = []
        hero_image = None
        
        if generate_images:
            images = await image_generator.generate_images_for_summary(summary)
            
            if generate_hero:
                hero_image = await image_generator.generate_hero_image(
                    summary.title,
                    summary.executive_summary
                )
        
        # Stage 4: Generate HTML
        html = report_generator.generate_report(
            summary=summary,
            images=images,
            hero_image=hero_image,
            embed_images=True
        )
        
        report_store[report_id] = {
            "status": "completed",
            "result": html
        }
        
    except Exception as e:
        report_store[report_id] = {
            "status": "error",
            "error": str(e)
        }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint - no imports required"""
    return {"status": "healthy", "api": "Venice Summary Report Generator"}


@app.get("/test")
async def test():
    """Simple test endpoint to verify server is running"""
    return {"message": "Server is running!", "status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

