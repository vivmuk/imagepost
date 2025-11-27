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
        
        # Test optional imports (don't fail if they don't work)
        try:
            from learning_agent import generate_learning_path
            print(f"✓ Learning agent module loaded")
        except Exception as e:
            print(f"⚠ Learning agent not available: {e}")
            
    except Exception as e:
        print(f"⚠ Warning during startup: {e}")
        import traceback
        traceback.print_exc()
        # Don't fail startup if config has issues


class URLInput(BaseModel):
    """URL input for summarization"""
    url: HttpUrl
    generate_images: bool = True
    generate_hero: bool = True
    report_type: str = "executive"  # "executive" or "linkedin"


class TextInput(BaseModel):
    """Text input for summarization"""
    text: str
    title: Optional[str] = None
    generate_images: bool = True
    generate_hero: bool = True
    report_type: str = "executive"  # "executive" or "linkedin"


class LearnInput(BaseModel):
    """Input for learning path generation"""
    topic: str


class ReportStatus(BaseModel):
    """Report generation status"""
    status: str
    report_id: str
    message: str
    report_url: Optional[str] = None


# Store for background tasks
report_store = {}


@app.get("/favicon.ico", status_code=204)
async def favicon():
    """Favicon endpoint to prevent 404 errors"""
    return None


@app.get("/health")
async def health():
    """Health check endpoint for Railway deployment"""
    return JSONResponse(content={"status": "healthy", "service": "venice-summary-api"})


@app.get("/", response_class=HTMLResponse)
async def root():
    """Interactive landing page with professional UI/UX"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Venice Summary | Executive Intelligence</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #ffffff;
            --text: #0f0f0f;
            --accent: #DC2626; /* Red */
            --accent-dark: #991b1b;
            --surface: #f8f8f8;
            --border: #e0e0e0;
            --font: 'Montserrat', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--font);
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Innovative Background */
        .bg-grid {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(var(--border) 1px, transparent 1px),
                linear-gradient(90deg, var(--border) 1px, transparent 1px);
            background-size: 40px 40px;
            opacity: 0.3;
            z-index: -1;
            pointer-events: none;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 4rem 2rem;
            width: 100%;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        /* Header */
        header {
            margin-bottom: 4rem;
            position: relative;
        }

        h1 {
            font-size: clamp(3rem, 8vw, 5rem);
            font-weight: 800;
            line-height: 0.9;
            letter-spacing: -0.04em;
            text-transform: uppercase;
            color: var(--text);
            margin-bottom: 1rem;
        }

        h1 span {
            color: var(--accent);
        }

        .subtitle {
            font-size: 1.2rem;
            font-weight: 400;
            color: #666;
            max-width: 600px;
            border-left: 3px solid var(--accent);
            padding-left: 1rem;
        }

        /* Tab System - Innovative Style */
        .input-section {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border: 1px solid var(--text);
            padding: 0;
            position: relative;
            box-shadow: 10px 10px 0px var(--text);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .tabs {
            display: flex;
            border-bottom: 1px solid var(--text);
        }

        .tab {
            flex: 1;
            padding: 1.5rem;
            text-align: center;
            background: transparent;
            border: none;
            border-right: 1px solid var(--text);
            font-family: var(--font);
            font-weight: 700;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
            letter-spacing: 1px;
        }

        .tab:last-child { border-right: none; }

        .tab:hover {
            background: #f0f0f0;
        }

        .tab.active {
            background: var(--accent);
            color: white;
        }

        .tab-content {
            padding: 3rem;
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: slideUp 0.4s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Inputs */
        .input-group {
            margin-bottom: 2rem;
        }

        label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        input[type="url"], textarea, input[type="text"] {
            width: 100%;
            padding: 1rem;
            font-family: var(--font);
            font-size: 1rem;
            border: 2px solid var(--border);
            background: #fff;
            transition: border-color 0.2s;
        }

        input[type="url"]:focus, textarea:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--accent);
        }

        textarea {
            min-height: 150px;
            resize: vertical;
        }

        /* Radio Cards */
        .radio-cards {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .radio-card {
            flex: 1;
            background: #fff;
            border: 2px solid var(--border);
            padding: 1.5rem;
            cursor: pointer;
            position: relative;
            display: flex;
            align-items: flex-start;
            gap: 12px;
            transition: all 0.2s;
        }
        .radio-card:hover { border-color: #999; }
        .radio-card.selected { border-color: var(--accent); background: rgba(220, 38, 38, 0.03); }
        .radio-card input { display: none; }
        .card-content { display: flex; flex-direction: column; }
        .card-title { font-weight: 800; font-size: 0.95rem; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
        .card-desc { font-size: 0.85rem; color: #666; line-height: 1.5; font-weight: 400; }

        /* Checkbox */
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
        }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: var(--accent);
        }

        /* Generate Button */
        .btn-generate {
            width: 100%;
            padding: 1.2rem;
            background: var(--text);
            color: white;
            border: none;
            font-family: var(--font);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 1.1rem;
            letter-spacing: 2px;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }

        .btn-generate:hover {
            background: var(--accent);
        }

        .btn-generate:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        /* Loading State - Artistic Animation */
        .loading-container {
            display: none;
            text-align: center;
            padding: 4rem 0;
        }

        .artistic-loader {
            width: 80px;
            height: 80px;
            border: 8px solid var(--text);
            border-top-color: var(--accent);
            border-radius: 50%;
            margin: 0 auto 2rem;
            animation: spin 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
        }
        
        .loading-text {
            font-size: 1.5rem;
            font-weight: 300;
            margin-bottom: 1rem;
        }

        .progress-bar {
            width: 100%;
            height: 4px;
            background: var(--border);
            margin-top: 1rem;
            position: relative;
            overflow: hidden;
        }

        .progress-fill {
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background: var(--accent);
            width: 0%;
            transition: width 0.5s ease;
        }

        @keyframes spin {
            0% { transform: rotate(0deg) scale(1); }
            50% { transform: rotate(180deg) scale(1.2); }
            100% { transform: rotate(360deg) scale(1); }
        }

        /* Status Steps */
        .status-steps {
            display: flex;
            justify-content: space-between;
            margin-top: 2rem;
            font-size: 0.8rem;
            color: #999;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .step {
            position: relative;
            padding-top: 1rem;
        }
        
        .step.active { color: var(--text); }
        .step.active::before { background: var(--accent); }
        
        .step::before {
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 8px;
            height: 8px;
            background: var(--border);
            border-radius: 50%;
        }

        /* Result Actions */
        .result-actions {
            display: none;
            gap: 1rem;
            margin-top: 2rem;
            animation: slideUp 0.5s ease;
        }

        .btn-secondary {
            flex: 1;
            padding: 1rem;
            background: transparent;
            border: 2px solid var(--text);
            color: var(--text);
            font-family: var(--font);
            font-weight: 600;
            text-transform: uppercase;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .btn-secondary:hover {
            background: var(--text);
            color: white;
        }

        .error-message {
            color: var(--accent);
            margin-top: 1rem;
            padding: 1rem;
            border: 1px solid var(--accent);
            background: rgba(220, 38, 38, 0.05);
            display: none;
        }

    </style>
</head>
<body>
    <div class="bg-grid"></div>

    <div class="container">
        <header>
            <h1>Venice <span>Summary</span></h1>
            <div class="subtitle">Advanced AI Executive Reporting & Visual Synthesis</div>
        </header>

        <div class="input-section" id="inputSection">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('url')">URL / Web</button>
                <button class="tab" onclick="switchTab('text')">Direct Text</button>
                <button class="tab" onclick="switchTab('learn')">Learn Topic</button>
            </div>

            <div id="url-tab" class="tab-content active">
                <div class="input-group">
                    <label>Article URL</label>
                    <input type="url" id="urlInput" placeholder="https://example.com/article">
                </div>

                <div class="input-group">
                    <label>Output Format</label>
                    <div class="radio-cards">
                        <label class="radio-card selected" onclick="selectRadio(this)">
                            <input type="radio" name="reportTypeUrl" value="executive" checked>
                            <div class="card-content">
                                <span class="card-title">Executive Report</span>
                                <span class="card-desc">Deep-dive analysis with multiple sections & visuals.</span>
                            </div>
                        </label>
                        <label class="radio-card" onclick="selectRadio(this)">
                            <input type="radio" name="reportTypeUrl" value="linkedin">
                            <div class="card-content">
                                <span class="card-title">LinkedIn Article</span>
                                <span class="card-desc">Viral article format with one consolidated visual.</span>
                            </div>
                        </label>
                    </div>
                </div>
                
                <div class="checkbox-group">
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="urlImages" checked>
                        <span>Generate Visuals</span>
                    </label>
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="urlHero" checked>
                        <span>Hero Image</span>
                    </label>
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="urlLinkedin" checked>
                        <span>Social Media Assets (LinkedIn)</span>
                    </label>
                </div>

                <button class="btn-generate" onclick="generateReport('url')">Generate Executive Report</button>
            </div>

            <div id="text-tab" class="tab-content">
                <div class="input-group">
                    <label>Content</label>
                    <textarea id="textContent" placeholder="Paste article text, report content, or notes here..."></textarea>
                </div>

                <div class="input-group">
                    <label>Output Format</label>
                    <div class="radio-cards">
                        <label class="radio-card selected" onclick="selectRadio(this)">
                            <input type="radio" name="reportTypeText" value="executive" checked>
                            <div class="card-content">
                                <span class="card-title">Executive Report</span>
                                <span class="card-desc">Deep-dive analysis with multiple sections & visuals.</span>
                            </div>
                        </label>
                        <label class="radio-card" onclick="selectRadio(this)">
                            <input type="radio" name="reportTypeText" value="linkedin">
                            <div class="card-content">
                                <span class="card-title">LinkedIn Article</span>
                                <span class="card-desc">Viral article format with one consolidated visual.</span>
                            </div>
                        </label>
                    </div>
                </div>

                <div class="checkbox-group">
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="textImages" checked>
                        <span>Generate Visuals</span>
                    </label>
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="textHero" checked>
                        <span>Hero Image</span>
                    </label>
                    <label class="checkbox-wrapper">
                        <input type="checkbox" id="textLinkedin" checked>
                        <span>Social Media Assets (LinkedIn)</span>
                    </label>
                </div>

                <button class="btn-generate" onclick="generateReport('text')">Generate Executive Report</button>
            </div>

            <div id="learn-tab" class="tab-content">
                <div class="input-group">
                    <label>What do you want to learn?</label>
                    <input type="text" id="learnInput" placeholder="e.g., Quantum Computing, French Revolution, Photosynthesis">
                </div>
                <p style="margin-bottom: 2rem; color: #666; font-size: 0.9rem;">
                    Creates a 3-chapter, multi-sensory lesson designed for Dyslexia & ADHD. Orchestrated by autonomous AI agents.
                </p>
                <button class="btn-generate" onclick="generateReport('learn')">Start Learning Journey</button>
            </div>
        </div>

        <div class="loading-container" id="loadingSection">
            <div class="artistic-loader"></div>
            <div class="loading-text" id="statusMessage">Initializing AI Agents...</div>
            
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>

            <div class="status-steps">
                <div class="step" id="step1">Plan</div>
                <div class="step" id="step2">Research</div>
                <div class="step" id="step3">Write</div>
                <div class="step" id="step4">Visuals</div>
            </div>
        </div>

        <div class="result-actions" id="resultSection">
            <a href="#" id="viewBtn" target="_blank" class="btn-secondary">View Lesson</a>
            <a href="#" id="downloadBtn" download class="btn-secondary">Download HTML</a>
            <button onclick="resetUI()" class="btn-secondary">Learn Something Else</button>
        </div>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        function selectRadio(label) {
            const groupName = label.querySelector('input').name;
            document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                input.closest('.radio-card').classList.remove('selected');
            });
            label.classList.add('selected');
            label.querySelector('input').checked = true;
        }

        function switchTab(type) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            if (type === 'url') {
                document.querySelector('.tab:nth-child(1)').classList.add('active');
                document.getElementById('url-tab').classList.add('active');
            } else if (type === 'text') {
                document.querySelector('.tab:nth-child(2)').classList.add('active');
                document.getElementById('text-tab').classList.add('active');
            } else {
                document.querySelector('.tab:nth-child(3)').classList.add('active');
                document.getElementById('learn-tab').classList.add('active');
            }
        }

        async function generateReport(type) {
            const inputSection = document.getElementById('inputSection');
            const loadingSection = document.getElementById('loadingSection');
            const errorMessage = document.getElementById('errorMessage');
            
            errorMessage.style.display = 'none';
            inputSection.style.display = 'none';
            loadingSection.style.display = 'block';
            
            try {
                let endpoint = '';
                let body = {};
                
                if (type === 'url') {
                    endpoint = '/api/summarize/url';
                    const url = document.getElementById('urlInput').value;
                    if (!url) throw new Error("Please enter a URL");
                    
                    body = {
                        url: url,
                        generate_images: document.getElementById('urlImages').checked,
                        generate_hero: document.getElementById('urlHero').checked,
                        report_type: document.querySelector('input[name="reportTypeUrl"]:checked').value
                    };
                } else if (type === 'text') {
                    endpoint = '/api/summarize/text';
                    const text = document.getElementById('textContent').value;
                    if (!text) throw new Error("Please enter text content");
                    
                    body = {
                        text: text,
                        generate_images: document.getElementById('textImages').checked,
                        generate_hero: document.getElementById('textHero').checked,
                        report_type: document.querySelector('input[name="reportTypeText"]:checked').value
                    };
                } else if (type === 'learn') {
                    endpoint = '/api/learn';
                    const topic = document.getElementById('learnInput').value;
                    if (!topic) throw new Error("Please enter a topic");
                    body = { topic: topic };
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                if (!response.ok) throw new Error('Failed to start generation');
                
                const data = await response.json();
                pollStatus(data.report_id);

            } catch (error) {
                showError(error.message);
            }
        }

        async function pollStatus(reportId) {
            const statusMsg = document.getElementById('statusMessage');
            const progressFill = document.getElementById('progressFill');
            const steps = [
                document.getElementById('step1'),
                document.getElementById('step2'),
                document.getElementById('step3'),
                document.getElementById('step4')
            ];

            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/status/${reportId}`);
                    if (!res.ok) throw new Error("Status check failed");
                    
                    const data = await res.json();
                    
                    // Update UI based on message
                    statusMsg.textContent = data.message;
                    
                    // Progress logic
                    if (data.message.includes("Extracting") || data.message.includes("Planning")) {
                        progressFill.style.width = '25%';
                        steps[0].classList.add('active');
                    } else if (data.message.includes("Summarizing") || data.message.includes("Researching") || data.message.includes("Writing")) {
                        progressFill.style.width = '50%';
                        steps[1].classList.add('active');
                    } else if (data.message.includes("Visual") || data.message.includes("Designing")) {
                        progressFill.style.width = '75%';
                        steps[2].classList.add('active');
                    } else if (data.message.includes("Compiling") || data.message.includes("Report")) {
                        progressFill.style.width = '90%';
                        steps[3].classList.add('active');
                    }

                    if (data.status === 'completed') {
                        clearInterval(interval);
                        progressFill.style.width = '100%';
                        steps.forEach(s => s.classList.add('active'));
                        showResult(data.report_url);
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        showError(data.message);
                    }
                } catch (e) {
                    console.error(e);
                }
            }, 2000);
        }

        function showResult(url) {
            const loadingSection = document.getElementById('loadingSection');
            const resultSection = document.getElementById('resultSection');
            const viewBtn = document.getElementById('viewBtn');
            const downloadBtn = document.getElementById('downloadBtn');

            loadingSection.style.display = 'none';
            resultSection.style.display = 'flex';
            
            viewBtn.href = url;
            downloadBtn.href = url + '/download';
        }

        function showError(msg) {
            const loadingSection = document.getElementById('loadingSection');
            const inputSection = document.getElementById('inputSection');
            const errorMessage = document.getElementById('errorMessage');

            loadingSection.style.display = 'none';
            inputSection.style.display = 'block';
            errorMessage.style.display = 'block';
            errorMessage.textContent = msg;
        }

        function resetUI() {
            document.getElementById('resultSection').style.display = 'none';
            document.getElementById('inputSection').style.display = 'block';
            document.getElementById('urlInput').value = '';
            document.getElementById('textContent').value = '';
            document.getElementById('learnInput').value = '';
        }
    </script>
</body>
</html>
"""


@app.post("/api/summarize/url", response_model=ReportStatus)
async def summarize_url(input_data: URLInput, background_tasks: BackgroundTasks):
    """
    Generate a summary report from a URL
    """
    report_id = f"url_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_store[report_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(
        generate_report_task,
        report_id=report_id,
        source=str(input_data.url),
        generate_images=input_data.generate_images,
        generate_hero=input_data.generate_hero,
        report_type=input_data.report_type
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
        title=input_data.title,
        report_type=input_data.report_type
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
    generate_hero: bool = Form(True),
    report_type: str = Form("executive")
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
        generate_hero=generate_hero,
        report_type=report_type
    )
    
    return ReportStatus(
        status="processing",
        report_id=report_id,
        message="Report generation started. Check /api/status/{report_id} for progress."
    )


@app.post("/api/learn", response_model=ReportStatus)
async def learn_topic(input_data: LearnInput, background_tasks: BackgroundTasks):
    """Generate a learning path for a topic"""
    report_id = f"learn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report_store[report_id] = {"status": "processing", "result": None}
    
    background_tasks.add_task(
        generate_learning_task,
        report_id=report_id,
        topic=input_data.topic
    )
    
    return ReportStatus(
        status="processing",
        report_id=report_id,
        message="Learning agents engaged. Check /api/status/{report_id} for progress."
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
            message=data.get("message", "Processing...")
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
    title: str = None,
    report_type: str = "executive"
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
        report_store[report_id]["message"] = "Extracting content..."
        
        content = await scraper.extract(source)
        if title:
            content.title = title
            
        html = ""
        
        if report_type == "linkedin":
            # --- LinkedIn Article Pipeline ---
            
            # Stage 2: Generate Article Content
            report_store[report_id]["message"] = "Drafting LinkedIn Article..."
            article_data = await summarizer.generate_linkedin_article_data(content)
            
            # Stage 3: Generate 1 Focused Visual
            hero_image = None
            if generate_images:
                report_store[report_id]["message"] = "Creating Viral Visual..."
                # Use the specific visual concept from the article generation
                visual_prompt = article_data.get("visual_concept", f"Whimsical watercolor illustration of {content.title}")
                hero_image = await image_generator.generate_hero_image(
                    content.title,
                    visual_prompt
                )
            
            # Stage 4: Generate HTML Page
            report_store[report_id]["message"] = "Compiling Article..."
            html = report_generator.generate_linkedin_html(article_data, hero_image)
            
        else:
            # --- Standard Executive Report Pipeline ---
            
            # Stage 2: Summarize
            report_store[report_id]["message"] = "Analyzing & Summarizing..."
            summary = await summarizer.summarize(content)
            
            # Stage 3: Generate images
            images = []
            hero_image = None
            
            if generate_images:
                report_store[report_id]["message"] = "Generating Visuals..."
                images = await image_generator.generate_images_for_summary(summary)
                
                if generate_hero:
                    hero_image = await image_generator.generate_hero_image(
                        summary.title,
                        summary.executive_summary
                    )
            
            # Stage 4: Generate HTML
            report_store[report_id]["message"] = "Compiling Report..."
            html = report_generator.generate_report(
                summary=summary,
                images=images,
                hero_image=hero_image,
                embed_images=True
            )
        
        report_store[report_id] = {
            "status": "completed",
            "result": html,
            "message": "Generation Complete!"
        }
        
    except Exception as e:
        print(f"Error in generation: {e}")
        report_store[report_id] = {
            "status": "error",
            "error": str(e),
            "message": f"Error: {str(e)}"
        }


async def generate_learning_task(report_id: str, topic: str):
    """Background task for learning path generation"""
    from learning_agent import generate_learning_path
    from report_generator import ReportGenerator
    
    try:
        report_store[report_id]["message"] = "Planning curriculum..."
        
        # Execute LangGraph workflow
        # Note: Monitoring detailed progress from inside the graph is harder without a callback,
        # so we update generic messages or use a custom callback handler if needed.
        # For now, we just let it run.
        
        # We could update status periodically if we had a way to peek into the graph execution
        # but awaiting the whole thing is simpler.
        
        curriculum = await generate_learning_path(topic)
        
        report_store[report_id]["message"] = "Compiling lesson..."
        
        generator = ReportGenerator()
        html = generator.generate_learning_html(topic, curriculum)
        
        report_store[report_id] = {
            "status": "completed",
            "result": html,
            "message": "Lesson Ready!"
        }
        
    except Exception as e:
        print(f"Error in learning generation: {e}")
        report_store[report_id] = {
            "status": "error",
            "error": str(e),
            "message": f"Error: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
