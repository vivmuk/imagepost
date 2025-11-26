"""
HTML Report Generator
Creates beautiful, styled HTML reports with embedded images
"""
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional
from jinja2 import Template
from rich.console import Console

from summarizer import StructuredSummary
from image_generator import GeneratedImage

console = Console()


class ReportGenerator:
    """Generates styled HTML reports from structured summaries"""
    
    def __init__(self):
        self.template = self._get_template()
    
    def generate_report(
        self,
        summary: StructuredSummary,
        images: list[GeneratedImage],
        hero_image: Optional[GeneratedImage] = None,
        output_path: Optional[str] = None,
        embed_images: bool = True
    ) -> str:
        """
        Generate a complete HTML report
        
        Args:
            summary: Structured summary data
            images: List of generated images for sections
            hero_image: Optional hero/banner image
            output_path: Path to save the HTML file
            embed_images: If True, embed images as base64; otherwise use file paths
        """
        console.print("\n[bold blue]Generating HTML Report[/bold blue]")
        
        # Prepare image data
        image_map = {}
        for img in images:
            if embed_images:
                b64 = base64.b64encode(img.image_data).decode('utf-8')
                image_map[img.section_title] = f"data:image/webp;base64,{b64}"
            else:
                image_map[img.section_title] = img.filename
        
        hero_src = None
        if hero_image:
            if embed_images:
                b64 = base64.b64encode(hero_image.image_data).decode('utf-8')
                hero_src = f"data:image/webp;base64,{b64}"
            else:
                hero_src = hero_image.filename
        
        # Render template
        html = self.template.render(
            title=summary.title,
            executive_summary=summary.executive_summary,
            key_takeaways=summary.key_takeaways,
            key_terms=summary.key_terms,
            sections=summary.sections,
            detailed_analysis=summary.detailed_analysis,
            limitations_and_biases=summary.limitations_and_biases,
            source=summary.source,
            word_count=summary.word_count,
            image_map=image_map,
            hero_image=hero_src,
            generated_date=datetime.now().strftime("%B %d, %Y at %H:%M"),
            year=datetime.now().year
        )
        
        # Save if path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(html, encoding='utf-8')
            console.print(f"[green]✓[/green] Report saved: {output_path}")
        
        return html
    
    def _get_template(self) -> Template:
        """Return the Jinja2 HTML template"""
        return Template('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | Executive Summary</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #ffffff;
            color: #1a1a1a;
            line-height: 1.8;
            font-size: 16px;
            font-weight: 400;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 80px 40px;
        }
        
        /* Header */
        header {
            border-bottom: 1px solid #e5e5e5;
            padding-bottom: 40px;
            margin-bottom: 60px;
        }
        
        .header-meta {
            font-size: 13px;
            font-weight: 500;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }
        
        h1 {
            font-family: 'Montserrat', sans-serif;
            font-size: 42px;
            font-weight: 600;
            line-height: 1.2;
            color: #111827;
            margin-bottom: 20px;
            letter-spacing: -0.5px;
        }
        
        .subtitle {
            font-size: 15px;
            color: #6b7280;
            font-weight: 400;
        }
        
        /* Executive Summary */
        .section {
            margin-bottom: 70px;
        }
        
        .section-title {
            font-family: 'Montserrat', sans-serif;
            font-size: 28px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid #f3f4f6;
        }
        
        .executive-summary {
            font-size: 17px;
            line-height: 1.85;
            color: #374151;
        }
        
        .executive-summary p {
            margin-bottom: 20px;
        }
        
        /* Key Takeaways */
        .takeaways {
            display: grid;
            gap: 20px;
            margin-top: 30px;
        }
        
        .takeaway {
            padding: 24px;
            background: #f9fafb;
            border-left: 3px solid #4b5563;
            border-radius: 2px;
        }
        
        .takeaway-number {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .takeaway-text {
            font-size: 15px;
            line-height: 1.7;
            color: #374151;
        }
        
        /* Key Terms */
        .key-terms {
            display: grid;
            gap: 16px;
        }
        
        .key-term {
            padding: 20px;
            background: #f9fafb;
            border-left: 3px solid #6366f1;
            border-radius: 2px;
        }
        
        .term-name {
            font-size: 16px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 8px;
        }
        
        .term-definition {
            font-size: 14px;
            line-height: 1.7;
            color: #374151;
            margin-bottom: 8px;
        }
        
        .term-context {
            font-size: 13px;
            color: #6b7280;
            line-height: 1.6;
        }
        
        .term-context em {
            color: #4b5563;
            font-style: normal;
            font-weight: 500;
        }
        
        /* Sections */
        .section-item {
            margin-bottom: 50px;
        }
        
        .section-item-title {
            font-size: 22px;
            font-weight: 600;
            color: #111827;
            margin-bottom: 16px;
        }
        
        .section-item-summary {
            font-size: 15px;
            line-height: 1.75;
            color: #4b5563;
            margin-bottom: 16px;
        }
        
        .section-points {
            list-style: none;
            margin-top: 16px;
        }
        
        .section-points li {
            font-size: 14px;
            line-height: 1.7;
            color: #6b7280;
            padding-left: 20px;
            position: relative;
            margin-bottom: 10px;
        }
        
        .section-points li::before {
            content: '—';
            position: absolute;
            left: 0;
            color: #9ca3af;
        }
        
        .section-image {
            margin: 24px 0;
            border-radius: 4px;
            overflow: hidden;
            background: #f9fafb;
        }
        
        .section-image img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        /* Detailed Analysis */
        .detailed-analysis {
            font-size: 15px;
            line-height: 1.8;
            color: #374151;
        }
        
        .detailed-analysis p {
            margin-bottom: 18px;
        }
        
        .detailed-analysis strong {
            color: #111827;
            font-weight: 600;
        }
        
        /* Limitations and Biases */
        .limitations-section {
            background: #fef3f2;
            border: 1px solid #fee2e2;
            border-left: 4px solid #dc2626;
            padding: 32px;
            border-radius: 4px;
            margin-top: 50px;
        }
        
        .limitations-section .section-title {
            color: #991b1b;
            border-bottom-color: #fecaca;
        }
        
        .limitations-content {
            font-size: 14px;
            line-height: 1.8;
            color: #7f1d1d;
        }
        
        .limitations-content h3 {
            font-size: 18px;
            font-weight: 600;
            color: #991b1b;
            margin-top: 24px;
            margin-bottom: 12px;
        }
        
        .limitations-content h3:first-child {
            margin-top: 0;
        }
        
        .limitations-content ul {
            list-style: none;
            margin: 12px 0;
        }
        
        .limitations-content li {
            padding-left: 20px;
            position: relative;
            margin-bottom: 10px;
        }
        
        .limitations-content li::before {
            content: '•';
            position: absolute;
            left: 0;
            color: #dc2626;
            font-weight: bold;
        }
        
        .bias-item {
            margin: 16px 0;
            padding: 16px;
            background: #fff;
            border-radius: 2px;
        }
        
        .bias-name {
            font-weight: 600;
            color: #991b1b;
            margin-bottom: 6px;
        }
        
        .bias-description {
            color: #7f1d1d;
            margin-bottom: 6px;
        }
        
        .bias-impact {
            font-style: italic;
            color: #991b1b;
            font-size: 13px;
        }
        
        /* Footer */
        footer {
            margin-top: 80px;
            padding-top: 40px;
            border-top: 1px solid #e5e5e5;
            font-size: 13px;
            color: #9ca3af;
            text-align: center;
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
            }
            
            .container {
                padding: 40px 20px;
            }
            
            .section {
                page-break-inside: avoid;
            }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 40px 24px;
            }
            
            h1 {
                font-size: 32px;
            }
            
            .section-title {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-meta">Executive Summary Report</div>
            <h1>{{ title }}</h1>
            <div class="subtitle">
                Generated {{ generated_date }} • {{ word_count | default(0) }} words analyzed
            </div>
        </header>
        
        <!-- Executive Summary -->
        <section class="section">
            <h2 class="section-title">Executive Summary</h2>
            <div class="executive-summary">
                {% for paragraph in executive_summary.split('\n\n') %}
                <p>{{ paragraph }}</p>
                {% endfor %}
            </div>
        </section>
        
        <!-- Key Takeaways -->
        <section class="section">
            <h2 class="section-title">Key Takeaways</h2>
            <div class="takeaways">
                {% for takeaway in key_takeaways %}
                <div class="takeaway">
                    <div class="takeaway-number">Takeaway {{ loop.index }}</div>
                    <div class="takeaway-text">{{ takeaway }}</div>
                </div>
                {% endfor %}
            </div>
        </section>
        
        <!-- Key Terms -->
        {% if key_terms %}
        <section class="section">
            <h2 class="section-title">Key Terms &amp; Definitions</h2>
            <div class="key-terms">
                {% for term in key_terms %}
                <div class="key-term">
                    <div class="term-name">{{ term.term }}</div>
                    <div class="term-definition">{{ term.definition }}</div>
                    <div class="term-context"><em>Context:</em> {{ term.context }}</div>
                </div>
                {% endfor %}
            </div>
        </section>
        {% endif %}
        
        <!-- Detailed Sections -->
        <section class="section">
            <h2 class="section-title">Detailed Analysis</h2>
            {% for section in sections %}
            <div class="section-item">
                <h3 class="section-item-title">{{ section.title }}</h3>
                <div class="section-item-summary">{{ section.summary }}</div>
                {% if section.key_points %}
                <ul class="section-points">
                    {% for point in section.key_points %}
                    <li>{{ point }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% if section.title in image_map %}
                <div class="section-image">
                    <img src="{{ image_map[section.title] }}" alt="Visual for {{ section.title }}">
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        
        <!-- In-Depth Analysis -->
        {% if detailed_analysis %}
        <section class="section">
            <h2 class="section-title">In-Depth Analysis</h2>
            <div class="detailed-analysis">
                {% for paragraph in detailed_analysis.split('\n\n') %}
                <p>{{ paragraph | replace('**', '<strong>') | replace('**', '</strong>') | safe }}</p>
                {% endfor %}
            </div>
        </section>
        {% endif %}
        
        <!-- Limitations and Cognitive Biases -->
        {% if limitations_and_biases %}
        <section class="section">
            <div class="limitations-section">
                <h2 class="section-title">Critical Analysis: Limitations and Cognitive Biases</h2>
                <div class="limitations-content">
                    {{ limitations_and_biases | safe }}
                </div>
            </div>
        </section>
        {% endif %}
        
        <footer>
            <p>Source: {{ source }}</p>
            <p>Generated with Venice AI • {{ year }}</p>
        </footer>
    </div>
</body>
</html>

''')

def generate_html_report(
    summary: StructuredSummary,
    images: list[GeneratedImage],
    hero_image: Optional[GeneratedImage] = None,
    output_path: Optional[str] = None
) -> str:
    """Convenience function to generate an HTML report"""
    generator = ReportGenerator()
    return generator.generate_report(summary, images, hero_image, output_path)

