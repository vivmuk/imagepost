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
    """Interactive landing page with input forms"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Venice Summary Report Generator</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: system-ui, -apple-system, sans-serif;
                background: #0a0a0f;
                color: #e2e8f0;
                min-height: 100vh;
                padding: 2rem;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
            }
            header {
                text-align: center;
                margin-bottom: 3rem;
            }
            h1 {
                font-size: 2.5rem;
                background: linear-gradient(135deg, #6366f1, #d946ef);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.5rem;
            }
            .subtitle {
                color: #94a3b8;
                font-size: 1.1rem;
            }
            .tabs {
                display: flex;
                gap: 1rem;
                margin-bottom: 2rem;
                border-bottom: 2px solid #2d2d3a;
            }
            .tab {
                padding: 1rem 2rem;
                background: none;
                border: none;
                color: #94a3b8;
                cursor: pointer;
                font-size: 1rem;
                border-bottom: 3px solid transparent;
                transition: all 0.3s;
            }
            .tab:hover {
                color: #e2e8f0;
            }
            .tab.active {
                color: #6366f1;
                border-bottom-color: #6366f1;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .form-card {
                background: #12121a;
                border: 1px solid #2d2d3a;
                border-radius: 16px;
                padding: 2rem;
                margin-bottom: 2rem;
            }
            .form-group {
                margin-bottom: 1.5rem;
            }
            label {
                display: block;
                margin-bottom: 0.5rem;
                color: #e2e8f0;
                font-weight: 500;
            }
            input[type="text"],
            input[type="url"],
            textarea {
                width: 100%;
                padding: 0.75rem;
                background: #1a1a25;
                border: 1px solid #2d2d3a;
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 1rem;
                font-family: inherit;
            }
            input[type="text"]:focus,
            input[type="url"]:focus,
            textarea:focus {
                outline: none;
                border-color: #6366f1;
            }
            textarea {
                min-height: 200px;
                resize: vertical;
            }
            input[type="file"] {
                width: 100%;
                padding: 0.75rem;
                background: #1a1a25;
                border: 1px solid #2d2d3a;
                border-radius: 8px;
                color: #e2e8f0;
                cursor: pointer;
            }
            .checkbox-group {
                display: flex;
                gap: 1rem;
                margin-top: 1rem;
            }
            .checkbox-group label {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                cursor: pointer;
            }
            input[type="checkbox"] {
                width: 18px;
                height: 18px;
                cursor: pointer;
            }
            .btn {
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                color: white;
                border: none;
                padding: 1rem 2rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
            }
            .btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }
            .status {
                margin-top: 1.5rem;
                padding: 1rem;
                border-radius: 8px;
                display: none;
            }
            .status.info {
                background: #1e3a5f;
                border: 1px solid #3b82f6;
                color: #93c5fd;
            }
            .status.success {
                background: #064e3b;
                border: 1px solid #10b981;
                color: #6ee7b7;
            }
            .status.error {
                background: #7f1d1d;
                border: 1px solid #ef4444;
                color: #fca5a5;
            }
            .status.show {
                display: block;
            }
            .spinner {
                display: inline-block;
                width: 16px;
                height: 16px;
                border: 2px solid #6366f1;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.6s linear infinite;
                margin-right: 0.5rem;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
            .link {
                color: #6366f1;
                text-decoration: none;
            }
            .link:hover {
                text-decoration: underline;
            }
            footer {
                text-align: center;
                margin-top: 3rem;
                padding-top: 2rem;
                border-top: 1px solid #2d2d3a;
                color: #94a3b8;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🎨 Venice Summary Report Generator</h1>
                <p class="subtitle">Generate AI-powered summary reports with images</p>
            </header>

            <div class="tabs">
                <button class="tab active" onclick="switchTab('url')">🌐 From URL</button>
                <button class="tab" onclick="switchTab('text')">📝 From Text</button>
                <button class="tab" onclick="switchTab('file')">📄 From File</button>
            </div>

            <!-- URL Tab -->
            <div id="url-tab" class="tab-content active">
                <div class="form-card">
                    <form id="url-form" onsubmit="submitUrl(event)">
                        <div class="form-group">
                            <label for="url-input">Article URL</label>
                            <input type="url" id="url-input" placeholder="https://example.com/article" required>
                        </div>
                        <div class="checkbox-group">
                            <label>
                                <input type="checkbox" id="url-images" checked>
                                Generate images
                            </label>
                            <label>
                                <input type="checkbox" id="url-hero" checked>
                                Generate hero banner
                            </label>
                        </div>
                        <button type="submit" class="btn" id="url-btn">Generate Report</button>
                        <div id="url-status" class="status"></div>
                    </form>
                </div>
            </div>

            <!-- Text Tab -->
            <div id="text-tab" class="tab-content">
                <div class="form-card">
                    <form id="text-form" onsubmit="submitText(event)">
                        <div class="form-group">
                            <label for="text-title">Title (Optional)</label>
                            <input type="text" id="text-title" placeholder="My Article Title">
                        </div>
                        <div class="form-group">
                            <label for="text-content">Content</label>
                            <textarea id="text-content" placeholder="Paste or type your content here..." required></textarea>
                        </div>
                        <div class="checkbox-group">
                            <label>
                                <input type="checkbox" id="text-images" checked>
                                Generate images
                            </label>
                            <label>
                                <input type="checkbox" id="text-hero" checked>
                                Generate hero banner
                            </label>
                        </div>
                        <button type="submit" class="btn" id="text-btn">Generate Report</button>
                        <div id="text-status" class="status"></div>
                    </form>
                </div>
            </div>

            <!-- File Tab -->
            <div id="file-tab" class="tab-content">
                <div class="form-card">
                    <form id="file-form" onsubmit="submitFile(event)">
                        <div class="form-group">
                            <label for="file-input">Upload File</label>
                            <input type="file" id="file-input" accept=".pdf,.docx,.txt,.md,.epub" required>
                            <small style="color: #94a3b8; margin-top: 0.5rem; display: block;">
                                Supported formats: PDF, DOCX, TXT, MD, EPUB
                            </small>
                        </div>
                        <div class="checkbox-group">
                            <label>
                                <input type="checkbox" id="file-images" checked>
                                Generate images
                            </label>
                            <label>
                                <input type="checkbox" id="file-hero" checked>
                                Generate hero banner
                            </label>
                        </div>
                        <button type="submit" class="btn" id="file-btn">Generate Report</button>
                        <div id="file-status" class="status"></div>
                    </form>
                </div>
            </div>

            <footer>
                <p><a href="/docs" class="link">📚 API Documentation</a> | <a href="/health" class="link">Health Check</a></p>
            </footer>
        </div>

        <script>
            function switchTab(tabName) {
                // Hide all tabs and content
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // Show selected tab and content
                event.target.classList.add('active');
                document.getElementById(tabName + '-tab').classList.add('active');
            }

            function showStatus(formId, message, type) {
                const statusEl = document.getElementById(formId + '-status');
                statusEl.textContent = message;
                statusEl.className = 'status ' + type + ' show';
            }

            function hideStatus(formId) {
                document.getElementById(formId + '-status').classList.remove('show');
            }

            async function submitUrl(event) {
                event.preventDefault();
                const btn = document.getElementById('url-btn');
                const url = document.getElementById('url-input').value;
                const images = document.getElementById('url-images').checked;
                const hero = document.getElementById('url-hero').checked;

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner"></span>Generating...';
                hideStatus('url');

                try {
                    const response = await fetch('/api/summarize/url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url, generate_images: images, generate_hero: hero })
                    });

                    const data = await response.json();
                    
                    if (response.ok) {
                        showStatus('url', 'Report generation started! Report ID: ' + data.report_id + '. Checking status...', 'info');
                        pollStatus(data.report_id, 'url');
                    } else {
                        showStatus('url', 'Error: ' + (data.detail || 'Unknown error'), 'error');
                    }
                } catch (error) {
                    showStatus('url', 'Error: ' + error.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Generate Report';
                }
            }

            async function submitText(event) {
                event.preventDefault();
                const btn = document.getElementById('text-btn');
                const text = document.getElementById('text-content').value;
                const title = document.getElementById('text-title').value || 'Document Summary';
                const images = document.getElementById('text-images').checked;
                const hero = document.getElementById('text-hero').checked;

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner"></span>Generating...';
                hideStatus('text');

                try {
                    const response = await fetch('/api/summarize/text', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text, title, generate_images: images, generate_hero: hero })
                    });

                    const data = await response.json();
                    
                    if (response.ok) {
                        showStatus('text', 'Report generation started! Report ID: ' + data.report_id + '. Checking status...', 'info');
                        pollStatus(data.report_id, 'text');
                    } else {
                        showStatus('text', 'Error: ' + (data.detail || 'Unknown error'), 'error');
                    }
                } catch (error) {
                    showStatus('text', 'Error: ' + error.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Generate Report';
                }
            }

            async function submitFile(event) {
                event.preventDefault();
                const btn = document.getElementById('file-btn');
                const fileInput = document.getElementById('file-input');
                const file = fileInput.files[0];
                const images = document.getElementById('file-images').checked;
                const hero = document.getElementById('file-hero').checked;

                if (!file) {
                    showStatus('file', 'Please select a file', 'error');
                    return;
                }

                btn.disabled = true;
                btn.innerHTML = '<span class="spinner"></span>Generating...';
                hideStatus('file');

                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('generate_images', images);
                    formData.append('generate_hero', hero);

                    const response = await fetch('/api/summarize/file', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    
                    if (response.ok) {
                        showStatus('file', 'Report generation started! Report ID: ' + data.report_id + '. Checking status...', 'info');
                        pollStatus(data.report_id, 'file');
                    } else {
                        showStatus('file', 'Error: ' + (data.detail || 'Unknown error'), 'error');
                    }
                } catch (error) {
                    showStatus('file', 'Error: ' + error.message, 'error');
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Generate Report';
                }
            }

            async function pollStatus(reportId, formId) {
                const maxAttempts = 60; // 5 minutes max
                let attempts = 0;

                const checkStatus = async () => {
                    try {
                        const response = await fetch('/api/status/' + reportId);
                        const data = await response.json();

                        if (data.status === 'completed') {
                            showStatus(formId, 'Report ready! <a href="/api/report/' + reportId + '" class="link" target="_blank">View Report</a>', 'success');
                        } else if (data.status === 'error') {
                            showStatus(formId, 'Error: ' + data.message, 'error');
                        } else {
                            attempts++;
                            if (attempts < maxAttempts) {
                                setTimeout(checkStatus, 5000); // Check every 5 seconds
                            } else {
                                showStatus(formId, 'Timeout: Report is still processing. Check back later with report ID: ' + reportId, 'info');
                            }
                        }
                    } catch (error) {
                        showStatus(formId, 'Error checking status: ' + error.message, 'error');
                    }
                };

                checkStatus();
            }
        </script>
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

