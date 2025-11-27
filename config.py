"""
Configuration for Venice API Summary Tool
"""
import os
from pydantic import BaseModel
from typing import Optional

# Try to load from .env file if available (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required, will use environment variables or defaults


class VeniceConfig(BaseModel):
    """Venice API Configuration"""
    api_key: str = os.getenv("VENICE_API_KEY", "lnWNeSg0pA_rQUooNpbfpPDBaj2vJnWol5WqKWrIEF")
    base_url: str = "https://api.venice.ai/api/v1"
    
    # Model selection for different tasks
    summarization_model: str = "qwen3-235b"  # Venice Large - best for complex summarization
    extraction_model: str = "mistral-31-24b"  # Venice Medium - good for structured extraction, supports vision
    image_model: str = "nano-banana-pro"  # User requested Nano Banana
    
    # Generation parameters
    max_tokens: int = 4096
    temperature: float = 0.3  # Lower for more focused summaries
    

class ScraperConfig(BaseModel):
    """Web scraping configuration"""
    timeout: int = 30
    max_content_length: int = 100000  # Max chars to process
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class ReportConfig(BaseModel):
    """Report generation configuration"""
    images_per_section: int = 1
    image_width: int = 1024
    image_height: int = 768
    image_style: str = "Watercolor Whimsical"  # Style for generated images
    output_dir: str = "reports"


class AppConfig(BaseModel):
    """Main application configuration"""
    venice: VeniceConfig = VeniceConfig()
    scraper: ScraperConfig = ScraperConfig()
    report: ReportConfig = ReportConfig()
    debug: bool = False


# Global config instance
config = AppConfig()

