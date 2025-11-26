"""
Content Scraper and Extractor Module
Handles URL scraping, text input, and file uploads (PDF, DOCX, EPUB)
"""
import asyncio
import re
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


@dataclass
class ExtractedContent:
    """Container for extracted content"""
    title: str
    text: str
    source_type: str  # 'url', 'text', 'pdf', 'docx', 'epub'
    source: str  # Original URL or filename
    word_count: int
    sections: list[dict]  # Detected sections with headers


class ContentScraper:
    """Scrapes and extracts content from various sources"""
    
    def __init__(self, timeout: int = 30, max_length: int = 100000):
        self.timeout = timeout
        self.max_length = max_length
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def extract(self, source: str) -> ExtractedContent:
        """
        Main extraction method - auto-detects source type
        
        Args:
            source: URL, file path, or raw text
        """
        # Check if it's a URL
        if source.startswith(('http://', 'https://')):
            return await self.extract_from_url(source)
        
        # Check if it's likely a file path (short enough)
        if len(source) < 255:
            try:
                path = Path(source)
                if path.exists():
                    return await self.extract_from_file(path)
            except OSError:
                # If Path creation fails (e.g. invalid chars), treat as text
                pass
        
        # Assume it's raw text
        return self.extract_from_text(source)
    
    async def extract_from_url(self, url: str) -> ExtractedContent:
        """Extract content from a URL"""
        console.print(f"[cyan]Scraping URL:[/cyan] {url}")
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            html = response.text
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            tag.decompose()
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        if not title:
            h1 = soup.find('h1')
            title = h1.get_text(strip=True) if h1 else "Untitled"
        
        # Try to find main content area
        main_content = None
        for selector in ['article', 'main', '[role="main"]', '.content', '.post-content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body or soup
        
        # Extract sections based on headers
        sections = self._extract_sections(main_content)
        
        # Get full text
        text = main_content.get_text(separator='\n', strip=True)
        text = self._clean_text(text)
        
        # Truncate if needed
        if len(text) > self.max_length:
            text = text[:self.max_length] + "\n\n[Content truncated...]"
        
        return ExtractedContent(
            title=title.strip(),
            text=text,
            source_type='url',
            source=url,
            word_count=len(text.split()),
            sections=sections
        )
    
    def extract_from_text(self, text: str, title: str = "Direct Input") -> ExtractedContent:
        """Extract content from raw text"""
        console.print("[cyan]Processing text input[/cyan]")
        
        text = self._clean_text(text)
        
        # If title is default, try to extract from first line
        if title == "Direct Input":
            first_line = text.split('\n')[0].strip()
            # If first line looks like a title (not too long, has content)
            if first_line and len(first_line) < 150:
                title = first_line
        
        sections = self._extract_sections_from_text(text)
        
        if len(text) > self.max_length:
            text = text[:self.max_length] + "\n\n[Content truncated...]"
        
        return ExtractedContent(
            title=title,
            text=text,
            source_type='text',
            source='direct_input',
            word_count=len(text.split()),
            sections=sections
        )
    
    async def extract_from_file(self, filepath: Path) -> ExtractedContent:
        """Extract content from a file (PDF, DOCX, EPUB, TXT)"""
        console.print(f"[cyan]Processing file:[/cyan] {filepath.name}")
        
        suffix = filepath.suffix.lower()
        
        if suffix == '.pdf':
            return await self._extract_pdf(filepath)
        elif suffix == '.docx':
            return await self._extract_docx(filepath)
        elif suffix == '.epub':
            return await self._extract_epub(filepath)
        elif suffix in ['.txt', '.md']:
            return await self._extract_text_file(filepath)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    async def _extract_pdf(self, filepath: Path) -> ExtractedContent:
        """Extract text from PDF"""
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("PyPDF2 required for PDF extraction. Install with: pip install PyPDF2")
        
        reader = PdfReader(str(filepath))
        text_parts = []
        
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        
        text = "\n\n".join(text_parts)
        text = self._clean_text(text)
        
        title = filepath.stem.replace('_', ' ').replace('-', ' ').title()
        sections = self._extract_sections_from_text(text)
        
        return ExtractedContent(
            title=title,
            text=text[:self.max_length],
            source_type='pdf',
            source=str(filepath),
            word_count=len(text.split()),
            sections=sections
        )
    
    async def _extract_docx(self, filepath: Path) -> ExtractedContent:
        """Extract text from DOCX"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx required for DOCX extraction. Install with: pip install python-docx")
        
        doc = Document(str(filepath))
        text_parts = []
        
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        
        text = "\n\n".join(text_parts)
        text = self._clean_text(text)
        
        title = filepath.stem.replace('_', ' ').replace('-', ' ').title()
        sections = self._extract_sections_from_text(text)
        
        return ExtractedContent(
            title=title,
            text=text[:self.max_length],
            source_type='docx',
            source=str(filepath),
            word_count=len(text.split()),
            sections=sections
        )
    
    async def _extract_epub(self, filepath: Path) -> ExtractedContent:
        """Extract text from EPUB"""
        try:
            import ebooklib
            from ebooklib import epub
        except ImportError:
            raise ImportError("ebooklib required for EPUB extraction. Install with: pip install ebooklib")
        
        book = epub.read_epub(str(filepath))
        text_parts = []
        title = book.get_metadata('DC', 'title')
        title = title[0][0] if title else filepath.stem
        
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'lxml')
            text_parts.append(soup.get_text(separator='\n', strip=True))
        
        text = "\n\n".join(text_parts)
        text = self._clean_text(text)
        sections = self._extract_sections_from_text(text)
        
        return ExtractedContent(
            title=title,
            text=text[:self.max_length],
            source_type='epub',
            source=str(filepath),
            word_count=len(text.split()),
            sections=sections
        )
    
    async def _extract_text_file(self, filepath: Path) -> ExtractedContent:
        """Extract text from plain text or markdown file"""
        text = filepath.read_text(encoding='utf-8')
        text = self._clean_text(text)
        
        title = filepath.stem.replace('_', ' ').replace('-', ' ').title()
        sections = self._extract_sections_from_text(text)
        
        return ExtractedContent(
            title=title,
            text=text[:self.max_length],
            source_type='text',
            source=str(filepath),
            word_count=len(text.split()),
            sections=sections
        )
    
    def _extract_sections(self, soup_element) -> list[dict]:
        """Extract sections based on HTML headers"""
        sections = []
        current_section = {"title": "Introduction", "content": [], "level": 0}
        
        for element in soup_element.descendants:
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                if current_section["content"]:
                    current_section["content"] = " ".join(current_section["content"])
                    sections.append(current_section)
                
                level = int(element.name[1])
                current_section = {
                    "title": element.get_text(strip=True),
                    "content": [],
                    "level": level
                }
            elif element.name == 'p' and element.string:
                text = element.get_text(strip=True)
                if text and len(text) > 20:
                    current_section["content"].append(text)
        
        if current_section["content"]:
            current_section["content"] = " ".join(current_section["content"])
            sections.append(current_section)
        
        return sections if sections else [{"title": "Content", "content": "", "level": 1}]
    
    def _extract_sections_from_text(self, text: str) -> list[dict]:
        """Extract sections from plain text based on patterns"""
        sections = []
        
        # Try to detect markdown-style headers or numbered sections
        lines = text.split('\n')
        current_section = {"title": "Introduction", "content": [], "level": 0}
        
        header_pattern = re.compile(r'^(#{1,4})\s+(.+)$|^(\d+\.)\s+(.+)$|^([A-Z][A-Z\s]{5,})$')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            match = header_pattern.match(line)
            if match:
                if current_section["content"]:
                    current_section["content"] = " ".join(current_section["content"])
                    sections.append(current_section)
                
                # Determine header level and text
                if match.group(1):  # Markdown header
                    level = len(match.group(1))
                    title = match.group(2)
                elif match.group(3):  # Numbered section
                    level = 1
                    title = match.group(4)
                else:  # All caps header
                    level = 1
                    title = match.group(5).title()
                
                current_section = {"title": title, "content": [], "level": level}
            else:
                if len(line) > 20:
                    current_section["content"].append(line)
        
        if current_section["content"]:
            current_section["content"] = " ".join(current_section["content"])
            sections.append(current_section)
        
        return sections if sections else [{"title": "Content", "content": text[:2000], "level": 1}]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
        
        # Remove common artifacts
        text = re.sub(r'cookie[s]?\s*(policy|consent|notice)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(accept|reject)\s+all\s+cookies?', '', text, flags=re.IGNORECASE)
        
        return text.strip()


# Convenience function for direct use
async def scrape_content(source: str) -> ExtractedContent:
    """Convenience function to scrape content from any source"""
    scraper = ContentScraper()
    return await scraper.extract(source)

