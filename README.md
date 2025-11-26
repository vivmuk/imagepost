# 🎨 Venice AI Summary Report Generator

Generate beautiful, AI-powered summary reports with infographic images using the Venice API.

![Pipeline](https://img.shields.io/badge/Pipeline-Multi--Stage-6366f1)
![Venice API](https://img.shields.io/badge/Powered%20by-Venice%20AI-d946ef)
![Python](https://img.shields.io/badge/Python-3.10+-22d3ee)

## ✨ Features

- **Multi-Source Input**: Process URLs, text, PDFs, DOCX, EPUB, and more
- **Smart Summarization**: Uses Venice's Qwen3-235B for intelligent content analysis
- **Visual Generation**: Creates infographic images for each section using Qwen Image
- **Structured Output**: Uses Venice's structured response format for consistent results
- **Beautiful Reports**: Generates stunning HTML reports with modern design
- **REST API**: Optional FastAPI server for integration

## 🔄 Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        INPUT SOURCES                         │
├─────────────┬─────────────┬─────────────────────────────────┤
│    URL      │    Text     │    Uploaded File (PDF/DOCX)     │
└──────┬──────┴──────┬──────┴────────────────┬────────────────┘
       │             │                        │
       └─────────────┴────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │        SCRAPER          │
              │  Extract & Clean Text   │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │      SUMMARIZER         │
              │  Venice API (qwen3-235b)│
              │  • Key Takeaways        │
              │  • Section Analysis     │
              │  • Executive Summary    │
              │  • Image Prompts        │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │    IMAGE GENERATOR      │
              │  Venice API (qwen-image)│
              │  • Section Infographics │
              │  • Hero Banner          │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │    REPORT GENERATOR     │
              │  • HTML Templating      │
              │  • Embedded Images      │
              │  • Modern Styling       │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │      HTML REPORT        │
              │   Beautiful, Portable   │
              └─────────────────────────┘
```

## 🚀 Quick Start

### Installation

```bash
# Clone or create the project
cd "Image Report"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### Command Line

```bash
# Summarize a URL
python main.py --url "https://example.com/article"

# Summarize a file
python main.py --file "document.pdf"

# Summarize text directly
python main.py --text "Your long text content here..."

# Interactive mode
python main.py --interactive

# Skip image generation (faster)
python main.py --url "https://example.com" --no-images
```

#### API Server

```bash
# Start the server
uvicorn server:app --reload

# Or
python server.py
```

Then visit:
- Landing page: http://localhost:8000
- API docs: http://localhost:8000/docs

#### API Endpoints

```bash
# Summarize URL
curl -X POST http://localhost:8000/api/summarize/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Summarize text
curl -X POST http://localhost:8000/api/summarize/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your content...", "title": "My Report"}'

# Check status
curl http://localhost:8000/api/status/{report_id}

# Get report
curl http://localhost:8000/api/report/{report_id}
```

## 📁 Project Structure

```
Image Report/
├── main.py              # Main CLI pipeline orchestration
├── server.py            # FastAPI REST server
├── config.py            # Configuration settings
├── scraper.py           # Content extraction module
├── summarizer.py        # Venice API summarization
├── image_generator.py   # Venice API image generation
├── report_generator.py  # HTML report generation
├── requirements.txt     # Python dependencies
└── reports/             # Generated reports output
    └── {report_name}/
        ├── report.html
        └── images/
            ├── hero_banner.webp
            ├── img_00_section1.webp
            └── ...
```

## ⚙️ Configuration

Edit `config.py` to customize:

```python
class VeniceConfig:
    api_key: str = "your-api-key"
    summarization_model: str = "qwen3-235b"  # Venice Large
    image_model: str = "qwen-image"          # Qwen Image

class ReportConfig:
    image_width: int = 1024
    image_height: int = 768
    image_style: str = "Infographic"
    output_dir: str = "reports"
```

## 🎨 Venice API Models Used

| Task | Model | Description |
|------|-------|-------------|
| Summarization | `qwen3-235b` | Venice Large - Best for complex analysis |
| Extraction | `mistral-31-24b` | Venice Medium - Supports vision |
| Images | `qwen-image` | Fast image generation |

## 📊 Structured Response Format

The summarizer uses Venice's structured response feature for consistent output:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "summary_output",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "key_takeaways": {...},
        "sections": {...},
        "executive_summary": {...}
      },
      "required": [...],
      "additionalProperties": false
    }
  }
}
```

## 🖼️ Generated Report Features

- **Hero Banner**: Custom generated banner representing the content theme
- **Executive Summary**: AI-generated overview of the content
- **Key Takeaways**: Numbered cards with critical insights
- **Section Analysis**: Each section with:
  - Summary text
  - Key bullet points
  - AI-generated infographic image
- **Detailed Analysis**: In-depth breakdown with recommendations
- **Modern Dark Theme**: Beautiful, professional styling
- **Responsive Design**: Works on desktop and mobile
- **Self-Contained**: All images embedded as base64

## 🔧 Requirements

- Python 3.10+
- Venice API key
- Internet connection (for API calls and URL scraping)

## 📝 License

MIT License - Feel free to use and modify!

## 🙏 Credits

- Powered by [Venice.ai](https://venice.ai) API
- Built with FastAPI, httpx, Beautiful Soup, Jinja2

