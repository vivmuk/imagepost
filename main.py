"""
Venice AI Summary Report Generator
Main orchestration pipeline for generating AI-powered summaries with images

Usage:
    python main.py --url "https://example.com/article"
    python main.py --text "Your text content here..."
    python main.py --file "document.pdf"
    python main.py --interactive
"""
import asyncio
import argparse
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from config import config
from scraper import ContentScraper, ExtractedContent
from summarizer import VeniceSummarizer, StructuredSummary
from image_generator import VeniceImageGenerator, GeneratedImage
from report_generator import ReportGenerator

console = Console()


class SummaryReportPipeline:
    """
    Main pipeline for generating AI-powered summary reports
    
    Pipeline stages:
    1. Content extraction (URL/text/file)
    2. Summarization with key takeaways
    3. Image generation for each section
    4. HTML report generation
    """
    
    def __init__(self):
        self.scraper = ContentScraper()
        self.summarizer = VeniceSummarizer()
        self.image_generator = VeniceImageGenerator()
        self.report_generator = ReportGenerator()
        self.output_dir = Path(config.report.output_dir)
    
    async def run(
        self,
        source: str,
        output_name: str = None,
        generate_images: bool = True,
        generate_hero: bool = True
    ) -> str:
        """
        Run the complete pipeline
        
        Args:
            source: URL, file path, or raw text
            output_name: Custom name for output files
            generate_images: Whether to generate section images
            generate_hero: Whether to generate a hero banner image
            
        Returns:
            Path to generated HTML report
        """
        self._print_header()
        
        # Stage 1: Extract content
        console.print("\n[bold cyan]Stage 1:[/bold cyan] Content Extraction")
        console.print("─" * 50)
        content = await self.scraper.extract(source)
        self._print_content_info(content)
        
        # Stage 2: Generate summary
        console.print("\n[bold cyan]Stage 2:[/bold cyan] AI Summarization")
        console.print("─" * 50)
        summary = await self.summarizer.summarize(content)
        self._print_summary_preview(summary)
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in content.title)
        safe_title = safe_title.replace(' ', '_').lower()[:40]
        output_name = output_name or f"{safe_title}_{timestamp}"
        
        report_dir = self.output_dir / output_name
        report_dir.mkdir(parents=True, exist_ok=True)
        images_dir = report_dir / "images"
        
        # Stage 3: Generate images
        images = []
        hero_image = None
        
        if generate_images:
            console.print("\n[bold cyan]Stage 3:[/bold cyan] Image Generation")
            console.print("─" * 50)
            images = await self.image_generator.generate_images_for_summary(
                summary, images_dir
            )
            
            if generate_hero:
                console.print("\n[dim]Generating hero banner...[/dim]")
                hero_image = await self.image_generator.generate_hero_image(
                    summary.title,
                    summary.executive_summary,
                    images_dir
                )
        
        # Stage 4: Generate HTML report
        console.print("\n[bold cyan]Stage 4:[/bold cyan] Report Generation")
        console.print("─" * 50)
        
        report_path = report_dir / "report.html"
        html = self.report_generator.generate_report(
            summary=summary,
            images=images,
            hero_image=hero_image,
            output_path=str(report_path),
            embed_images=True  # Embed images for portable HTML
        )
        
        # Print completion summary
        self._print_completion(report_path, summary, len(images))
        
        return str(report_path)
    
    def _print_header(self):
        """Print pipeline header"""
        header = """
╔═══════════════════════════════════════════════════════╗
║     🎨  Venice AI Summary Report Generator  🎨        ║
║                                                       ║
║  Powered by Venice API with Qwen Image               ║
╚═══════════════════════════════════════════════════════╝
"""
        console.print(Panel(header, style="bold magenta", border_style="magenta"))
    
    def _print_content_info(self, content: ExtractedContent):
        """Print extracted content information"""
        console.print(f"\n[green]✓[/green] Content extracted successfully")
        console.print(f"  Title: [bold]{content.title}[/bold]")
        console.print(f"  Source: {content.source_type}")
        console.print(f"  Words: {content.word_count:,}")
        console.print(f"  Sections detected: {len(content.sections)}")
    
    def _print_summary_preview(self, summary: StructuredSummary):
        """Print summary preview"""
        console.print(f"\n[green]✓[/green] Summary generated")
        console.print(f"\n[bold]Key Takeaways:[/bold]")
        for i, takeaway in enumerate(summary.key_takeaways[:3], 1):
            console.print(f"  {i}. {takeaway[:80]}...")
        if len(summary.key_takeaways) > 3:
            console.print(f"  ... and {len(summary.key_takeaways) - 3} more")
        
        console.print(f"\n[bold]Sections:[/bold]")
        for section in summary.sections[:4]:
            console.print(f"  • {section.title}")
        if len(summary.sections) > 4:
            console.print(f"  ... and {len(summary.sections) - 4} more")
    
    def _print_completion(self, report_path: Path, summary: StructuredSummary, image_count: int):
        """Print completion summary"""
        completion_msg = f"""
[bold green]✓ Report Generated Successfully![/bold green]

[bold]Output Location:[/bold]
  {report_path}

[bold]Report Contents:[/bold]
  • Title: {summary.title}
  • Key Takeaways: {len(summary.key_takeaways)}
  • Sections: {len(summary.sections)}
  • Images: {image_count}
  • Word Count: {summary.word_count:,}

[dim]Open the HTML file in your browser to view the report.[/dim]
"""
        console.print(Panel(completion_msg, border_style="green"))


async def interactive_mode():
    """Interactive mode for generating reports"""
    console.print("\n[bold cyan]Interactive Mode[/bold cyan]")
    console.print("─" * 50)
    
    console.print("\nChoose input type:")
    console.print("  1. URL (web page)")
    console.print("  2. File (PDF, DOCX, TXT)")
    console.print("  3. Direct text")
    
    choice = input("\nEnter choice (1/2/3): ").strip()
    
    if choice == "1":
        source = input("Enter URL: ").strip()
    elif choice == "2":
        source = input("Enter file path: ").strip()
    elif choice == "3":
        console.print("Enter text (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "":
                if lines and lines[-1] == "":
                    break
            lines.append(line)
        source = "\n".join(lines)
    else:
        console.print("[red]Invalid choice[/red]")
        return
    
    generate_images = input("\nGenerate images? (y/n, default: y): ").strip().lower() != 'n'
    
    pipeline = SummaryReportPipeline()
    await pipeline.run(source, generate_images=generate_images)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate AI-powered summary reports with Venice API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "https://example.com/article"
  python main.py --file "document.pdf"
  python main.py --text "Your text content..."
  python main.py --interactive
        """
    )
    
    parser.add_argument(
        "--url", "-u",
        help="URL to summarize"
    )
    parser.add_argument(
        "--file", "-f",
        help="File path to summarize (PDF, DOCX, TXT)"
    )
    parser.add_argument(
        "--text", "-t",
        help="Direct text to summarize"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--output", "-o",
        help="Custom output name"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image generation"
    )
    parser.add_argument(
        "--no-hero",
        action="store_true",
        help="Skip hero banner image"
    )
    
    args = parser.parse_args()
    
    # Determine source
    if args.interactive:
        await interactive_mode()
        return
    
    source = args.url or args.file or args.text
    
    if not source:
        # Default demo mode
        console.print("[yellow]No input provided. Running demo with sample text...[/yellow]\n")
        source = """
        # The Future of Artificial Intelligence
        
        ## Introduction
        Artificial Intelligence (AI) has rapidly evolved from a theoretical concept to a 
        transformative technology that impacts virtually every industry. This analysis 
        explores the current state of AI, its potential future developments, and the 
        implications for society.
        
        ## Current State of AI
        Today's AI systems excel at specific tasks like image recognition, natural language 
        processing, and game playing. Machine learning, particularly deep learning, has 
        enabled breakthroughs in autonomous vehicles, medical diagnosis, and creative 
        applications. Companies worldwide are investing billions in AI research and 
        development.
        
        ## Key Technologies
        The most significant AI technologies include:
        - Large Language Models (LLMs) that can understand and generate human-like text
        - Computer vision systems that can analyze images and video
        - Reinforcement learning algorithms that learn through interaction
        - Generative AI that creates new content including images, music, and code
        
        ## Future Predictions
        Experts predict AI will continue to advance rapidly. Within the next decade, we 
        may see artificial general intelligence (AGI) that can perform any intellectual 
        task a human can. This could lead to unprecedented productivity gains but also 
        raises important ethical and safety considerations.
        
        ## Societal Impact
        AI will transform the job market, creating new roles while automating others. 
        Education systems must adapt to prepare students for an AI-driven economy. 
        Governments are beginning to develop regulations to ensure AI is developed and 
        deployed responsibly.
        
        ## Conclusion
        The future of AI holds immense promise and significant challenges. By thoughtfully 
        developing and deploying these technologies, we can harness their benefits while 
        mitigating potential risks. The decisions we make today will shape the AI-driven 
        world of tomorrow.
        """
    
    pipeline = SummaryReportPipeline()
    await pipeline.run(
        source=source,
        output_name=args.output,
        generate_images=not args.no_images,
        generate_hero=not args.no_hero
    )


if __name__ == "__main__":
    asyncio.run(main())

