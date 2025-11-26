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
    """Interactive landing page with professional UI/UX"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executive Summary Report Generator | Venice AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a25 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 2rem 1rem;
            line-height: 1.6;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        header {
            text-align: center;
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid rgba(99, 102, 241, 0.2);
        }
        h1 {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 700;
            background: linear-gradient(135deg, #6366f1, #8b5cf6, #d946ef);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.75rem;
            letter-spacing: -0.02em;
        }
        .subtitle {
            color: #94a3b8;
            font-size: 1.125rem;
            font-weight: 400;
        }
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            background: #12121a;
            padding: 0.5rem;
            border-radius: 12px;
            border: 1px solid #2d2d3a;
        }
        .tab {
            flex: 1;
            padding: 0.875rem 1.5rem;
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 500;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .tab:hover { color: #e2e8f0; background: #1a1a25; }
        .tab.active {
            color: #6366f1;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15));
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .tab-content { display: none; animation: fadeIn 0.3s; }
        .tab-content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .form-card {
            background: #12121a;
            border: 1px solid #2d2d3a;
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .form-group { margin-bottom: 1.75rem; }
        label {
            display: block;
            margin-bottom: 0.625rem;
            color: #e2e8f0;
            font-weight: 600;
            font-size: 0.95rem;
        }
        input[type="text"], input[type="url"], textarea {
            width: 100%;
            padding: 0.875rem 1rem;
            background: #1a1a25;
            border: 2px solid #2d2d3a;
            border-radius: 10px;
            color: #e2e8f0;
            font-size: 1rem;
            font-family: inherit;
            transition: all 0.2s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        textarea {
            min-height: 220px;
            resize: vertical;
            line-height: 1.6;
        }
        input[type="file"] {
            width: 100%;
            padding: 0.875rem;
            background: #1a1a25;
            border: 2px dashed #2d2d3a;
            border-radius: 10px;
            color: #e2e8f0;
            cursor: pointer;
            transition: all 0.2s;
        }
        input[type="file"]:hover { border-color: #6366f1; }
        .checkbox-group {
            display: flex;
            gap: 2rem;
            margin: 1.5rem 0;
            flex-wrap: wrap;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 0.625rem;
            cursor: pointer;
            font-weight: 400;
            margin: 0;
        }
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
            accent-color: #6366f1;
        }
        .btn {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
            border: none;
            padding: 1.125rem 2rem;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }
        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .progress-container {
            margin-top: 1.5rem;
            display: none;
        }
        .progress-container.show { display: block; }
        .progress-stages {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            font-size: 0.875rem;
            color: #94a3b8;
        }
        .stage {
            flex: 1;
            text-align: center;
            padding: 0.5rem;
            position: relative;
        }
        .stage.active { color: #6366f1; font-weight: 600; }
        .stage.completed { color: #10b981; }
        .stage::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100%;
            height: 2px;
            background: #2d2d3a;
            z-index: -1;
        }
        .stage:last-child::after { display: none; }
        .status {
            margin-top: 1.5rem;
            padding: 1.25rem 1.5rem;
            border-radius: 12px;
            display: none;
            border-left: 4px solid;
        }
        .status.show { display: block; animation: slideIn 0.3s; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .status.info {
            background: rgba(59, 130, 246, 0.1);
            border-color: #3b82f6;
            color: #93c5fd;
        }
        .status.success {
            background: rgba(16, 185, 129, 0.1);
            border-color: #10b981;
            color: #6ee7b7;
        }
        .status.error {
            background: rgba(239, 68, 68, 0.1);
            border-color: #ef4444;
            color: #fca5a5;
        }
        .status-content {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .status-icon {
            font-size: 1.25rem;
        }
        .action-buttons {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }
        .btn-secondary {
            background: #1a1a25;
            border: 2px solid #2d2d3a;
            color: #e2e8f0;
            padding: 0.875rem 1.5rem;
            border-radius: 10px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-secondary:hover {
            border-color: #6366f1;
            color: #6366f1;
            transform: translateY(-2px);
        }
        .spinner {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        footer {
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid #2d2d3a;
            color: #94a3b8;
        }
        .link {
            color: #6366f1;
            text-decoration: none;
            transition: color 0.2s;
        }
        .link:hover { color: #8b5cf6; text-decoration: underline; }
        small {
            color: #94a3b8;
            font-size: 0.875rem;
            display: block;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Executive Summary Report Generator</h1>
            <p class="subtitle">Transform content into professional, AI-powered executive summaries with visual insights</p>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="switchTab('url')">🌐 Web Article</button>
            <button class="tab" onclick="switchTab('text')">📝 Text Content</button>
            <button class="tab" onclick="switchTab('file')">📄 Document</button>
        </div>

        <!-- URL Tab -->
        <div id="url-tab" class="tab-content active">
            <div class="form-card">
                <form id="url-form" onsubmit="submitUrl(event)">
                    <div class="form-group">
                        <label for="url-input">Article URL</label>
                        <input type="url" id="url-input" placeholder="https://example.com/article" required>
                        <small>Enter the full URL of the article or webpage you want to summarize</small>
                    </div>
                    <div class="checkbox-group">
                        <label><input type="checkbox" id="url-images" checked> Generate infographic images</label>
                        <label><input type="checkbox" id="url-hero" checked> Include hero banner</label>
                    </div>
                    <button type="submit" class="btn" id="url-btn">Generate Executive Summary</button>
                    <div id="url-progress" class="progress-container"></div>
                    <div id="url-status" class="status"></div>
                </form>
            </div>
        </div>

        <!-- Text Tab -->
        <div id="text-tab" class="tab-content">
            <div class="form-card">
                <form id="text-form" onsubmit="submitText(event)">
                    <div class="form-group">
                        <label for="text-title">Report Title</label>
                        <input type="text" id="text-title" placeholder="Executive Summary: Q4 2024 Analysis">
                        <small>Optional: Provide a title for your report</small>
                    </div>
                    <div class="form-group">
                        <label for="text-content">Content to Analyze</label>
                        <textarea id="text-content" placeholder="Paste or type the content you want to summarize here..." required></textarea>
                        <small>Enter the text content you want to transform into an executive summary</small>
                    </div>
                    <div class="checkbox-group">
                        <label><input type="checkbox" id="text-images" checked> Generate infographic images</label>
                        <label><input type="checkbox" id="text-hero" checked> Include hero banner</label>
                    </div>
                    <button type="submit" class="btn" id="text-btn">Generate Executive Summary</button>
                    <div id="text-progress" class="progress-container"></div>
                    <div id="text-status" class="status"></div>
                </form>
            </div>
        </div>

        <!-- File Tab -->
        <div id="file-tab" class="tab-content">
            <div class="form-card">
                <form id="file-form" onsubmit="submitFile(event)">
                    <div class="form-group">
                        <label for="file-input">Upload Document</label>
                        <input type="file" id="file-input" accept=".pdf,.docx,.txt,.md,.epub" required>
                        <small>Supported formats: PDF, DOCX, TXT, Markdown, EPUB (Max 10MB recommended)</small>
                    </div>
                    <div class="checkbox-group">
                        <label><input type="checkbox" id="file-images" checked> Generate infographic images</label>
                        <label><input type="checkbox" id="file-hero" checked> Include hero banner</label>
                    </div>
                    <button type="submit" class="btn" id="file-btn">Generate Executive Summary</button>
                    <div id="file-progress" class="progress-container"></div>
                    <div id="file-status" class="status"></div>
                </form>
            </div>
        </div>

        <footer>
            <p><a href="/docs" class="link">📚 API Documentation</a> | <a href="/health" class="link">System Status</a></p>
        </footer>
    </div>

    <script>
        const stages = ['Extracting Content', 'Analyzing & Summarizing', 'Generating Visuals', 'Compiling Report'];
        let currentStage = 0;

        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
        }

        function showProgress(formId) {
            const progressEl = document.getElementById(formId + '-progress');
            progressEl.innerHTML = `
                <div class="progress-stages">
                    ${stages.map((stage, i) => `
                        <div class="stage ${i < currentStage ? 'completed' : i === currentStage ? 'active' : ''}">
                            ${i < currentStage ? '✓' : i === currentStage ? '⟳' : '○'} ${stage}
                        </div>
                    `).join('')}
                </div>
            `;
            progressEl.classList.add('show');
        }

        function updateStage(formId, stageIndex) {
            currentStage = stageIndex;
            showProgress(formId);
        }

        function showStatus(formId, message, type, actions = null) {
            const statusEl = document.getElementById(formId + '-status');
            const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
            statusEl.innerHTML = `
                <div class="status-content">
                    <span class="status-icon">${icon}</span>
                    <div style="flex: 1;">
                        <div>${message}</div>
                        ${actions ? `<div class="action-buttons">${actions}</div>` : ''}
                    </div>
                </div>
            `;
            statusEl.className = 'status ' + type + ' show';
        }

        function hideStatus(formId) {
            document.getElementById(formId + '-status').classList.remove('show');
            document.getElementById(formId + '-progress').classList.remove('show');
            currentStage = 0;
        }

        async function submitUrl(event) {
            event.preventDefault();
            const btn = document.getElementById('url-btn');
            const url = document.getElementById('url-input').value;
            const images = document.getElementById('url-images').checked;
            const hero = document.getElementById('url-hero').checked;

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Initiating Analysis...';
            hideStatus('url');
            updateStage('url', 0);

            try {
                const response = await fetch('/api/summarize/url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, generate_images: images, generate_hero: hero })
                });

                const data = await response.json();
                
                if (response.ok) {
                    showStatus('url', 'Analysis pipeline initiated. Processing your content...', 'info');
                    pollStatus(data.report_id, 'url');
                } else {
                    showStatus('url', 'Error: ' + (data.detail || 'Unable to process request'), 'error');
                    btn.disabled = false;
                    btn.textContent = 'Generate Executive Summary';
                }
            } catch (error) {
                showStatus('url', 'Connection error: ' + error.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Generate Executive Summary';
            }
        }

        async function submitText(event) {
            event.preventDefault();
            const btn = document.getElementById('text-btn');
            const text = document.getElementById('text-content').value;
            const title = document.getElementById('text-title').value || 'Executive Summary Report';
            const images = document.getElementById('text-images').checked;
            const hero = document.getElementById('text-hero').checked;

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Initiating Analysis...';
            hideStatus('text');
            updateStage('text', 0);

            try {
                const response = await fetch('/api/summarize/text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, title, generate_images: images, generate_hero: hero })
                });

                const data = await response.json();
                
                if (response.ok) {
                    showStatus('text', 'Analysis pipeline initiated. Processing your content...', 'info');
                    pollStatus(data.report_id, 'text');
                } else {
                    showStatus('text', 'Error: ' + (data.detail || 'Unable to process request'), 'error');
                    btn.disabled = false;
                    btn.textContent = 'Generate Executive Summary';
                }
            } catch (error) {
                showStatus('text', 'Connection error: ' + error.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Generate Executive Summary';
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
                showStatus('file', 'Please select a document to analyze', 'error');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Initiating Analysis...';
            hideStatus('file');
            updateStage('file', 0);

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
                    showStatus('file', 'Analysis pipeline initiated. Processing your document...', 'info');
                    pollStatus(data.report_id, 'file');
                } else {
                    showStatus('file', 'Error: ' + (data.detail || 'Unable to process document'), 'error');
                    btn.disabled = false;
                    btn.textContent = 'Generate Executive Summary';
                }
            } catch (error) {
                showStatus('file', 'Connection error: ' + error.message, 'error');
                btn.disabled = false;
                btn.textContent = 'Generate Executive Summary';
            }
        }

        async function pollStatus(reportId, formId) {
            const maxAttempts = 120;
            let attempts = 0;
            let lastStage = 0;

            const stageMessages = [
                'Extracting and processing content from source...',
                'Analyzing content structure and generating key insights...',
                'Creating visual infographics and imagery...',
                'Compiling final executive summary report...'
            ];

            const checkStatus = async () => {
                try {
                    const response = await fetch('/api/status/' + reportId);
                    const data = await response.json();

                    if (data.status === 'completed') {
                        const actions = `
                            <a href="/api/report/${reportId}" class="btn-secondary" target="_blank">📄 View Report</a>
                            <a href="/api/report/${reportId}/download" class="btn-secondary">💾 Download HTML</a>
                        `;
                        showStatus(formId, 
                            'Executive summary report generated successfully. Your report is ready for review and distribution.',
                            'success', actions);
                        document.getElementById(formId + '-progress').classList.remove('show');
                        document.getElementById(formId + '-btn').disabled = false;
                        document.getElementById(formId + '-btn').textContent = 'Generate Executive Summary';
                    } else if (data.status === 'error') {
                        showStatus(formId, 'Analysis encountered an error: ' + data.message, 'error');
                        document.getElementById(formId + '-btn').disabled = false;
                        document.getElementById(formId + '-btn').textContent = 'Generate Executive Summary';
                    } else {
                        // Update progress stage
                        const stageProgress = Math.min(Math.floor((attempts / maxAttempts) * 4), 3);
                        if (stageProgress !== lastStage) {
                            lastStage = stageProgress;
                            updateStage(formId, stageProgress);
                            showStatus(formId, stageMessages[stageProgress], 'info');
                        }
                        
                        attempts++;
                        if (attempts < maxAttempts) {
                            setTimeout(checkStatus, 3000);
                        } else {
                            showStatus(formId, 
                                'Report generation is taking longer than expected. Your report ID: ' + reportId + '. Please check back shortly or contact support.',
                                'info');
                        }
                    }
                } catch (error) {
                    showStatus(formId, 'Error checking status: ' + error.message, 'error');
                    document.getElementById(formId + '-btn').disabled = false;
                    document.getElementById(formId + '-btn').textContent = 'Generate Executive Summary';
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

