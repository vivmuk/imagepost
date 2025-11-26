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
            sections=summary.sections,
            detailed_analysis=summary.detailed_analysis,
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
    <title>{{ title }} - Summary Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,500;0,9..144,700;1,9..144,400&family=DM+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
    <style>
        :root {
            --color-bg: #0a0a0f;
            --color-surface: #12121a;
            --color-surface-alt: #1a1a25;
            --color-accent: #6366f1;
            --color-accent-glow: rgba(99, 102, 241, 0.3);
            --color-secondary: #22d3ee;
            --color-text: #e2e8f0;
            --color-text-muted: #94a3b8;
            --color-border: #2d2d3a;
            --color-success: #10b981;
            --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
            --gradient-glow: radial-gradient(ellipse at center, var(--color-accent-glow) 0%, transparent 70%);
            --font-display: 'Fraunces', Georgia, serif;
            --font-body: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            --shadow-glow: 0 0 60px var(--color-accent-glow);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html {
            scroll-behavior: smooth;
        }
        
        body {
            font-family: var(--font-body);
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.7;
            font-size: 16px;
            min-height: 100vh;
        }
        
        /* Noise texture overlay */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0.03;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
            z-index: 1000;
        }
        
        /* Hero Section */
        .hero {
            position: relative;
            min-height: 70vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 4rem 2rem;
        }
        
        .hero-bg {
            position: absolute;
            inset: 0;
            background: var(--gradient-glow);
            opacity: 0.5;
        }
        
        .hero-image {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0.15;
            filter: blur(2px);
        }
        
        .hero-content {
            position: relative;
            z-index: 10;
            max-width: 900px;
            text-align: center;
        }
        
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--color-surface-alt);
            border: 1px solid var(--color-border);
            border-radius: 100px;
            font-size: 0.85rem;
            color: var(--color-text-muted);
            margin-bottom: 2rem;
        }
        
        .hero-badge::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--color-success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        h1 {
            font-family: var(--font-display);
            font-size: clamp(2.5rem, 6vw, 4rem);
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .hero-meta {
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
            color: var(--color-text-muted);
            font-size: 0.9rem;
        }
        
        .hero-meta span {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Main Content */
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        /* Executive Summary */
        .executive-summary {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 24px;
            padding: 3rem;
            margin: -4rem auto 4rem;
            position: relative;
            z-index: 20;
            max-width: 900px;
            box-shadow: var(--shadow-lg), var(--shadow-glow);
        }
        
        .section-label {
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--color-accent);
            margin-bottom: 1rem;
        }
        
        .executive-summary p {
            font-size: 1.1rem;
            color: var(--color-text);
            margin-bottom: 1rem;
        }
        
        /* Key Takeaways */
        .takeaways {
            padding: 4rem 0;
        }
        
        .takeaways h2 {
            font-family: var(--font-display);
            font-size: 2rem;
            font-weight: 500;
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .takeaways-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        
        .takeaway-card {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .takeaway-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }
        
        .takeaway-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient-primary);
            border-radius: 16px 16px 0 0;
        }
        
        .takeaway-number {
            font-family: var(--font-display);
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--color-surface-alt);
            margin-bottom: 0.5rem;
        }
        
        .takeaway-card p {
            color: var(--color-text);
            font-size: 0.95rem;
        }
        
        /* Sections */
        .sections {
            padding: 4rem 0;
        }
        
        .sections h2 {
            font-family: var(--font-display);
            font-size: 2rem;
            font-weight: 500;
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .section-card {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 3rem;
            align-items: center;
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 24px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            transition: box-shadow 0.3s ease;
        }
        
        .section-card:hover {
            box-shadow: var(--shadow-lg);
        }
        
        .section-card:nth-child(even) {
            direction: rtl;
        }
        
        .section-card:nth-child(even) > * {
            direction: ltr;
        }
        
        .section-content h3 {
            font-family: var(--font-display);
            font-size: 1.5rem;
            font-weight: 500;
            margin-bottom: 1rem;
            color: var(--color-text);
        }
        
        .section-content p {
            color: var(--color-text-muted);
            margin-bottom: 1.5rem;
        }
        
        .section-points {
            list-style: none;
        }
        
        .section-points li {
            position: relative;
            padding-left: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--color-text);
            font-size: 0.95rem;
        }
        
        .section-points li::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0.5rem;
            width: 6px;
            height: 6px;
            background: var(--color-accent);
            border-radius: 50%;
        }
        
        .section-image {
            border-radius: 16px;
            overflow: hidden;
            aspect-ratio: 4/3;
            background: var(--color-surface-alt);
        }
        
        .section-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.5s ease;
        }
        
        .section-card:hover .section-image img {
            transform: scale(1.05);
        }
        
        /* Detailed Analysis */
        .analysis {
            padding: 4rem 0;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .analysis h2 {
            font-family: var(--font-display);
            font-size: 2rem;
            font-weight: 500;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .analysis-content {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: 24px;
            padding: 3rem;
        }
        
        .analysis-content p {
            margin-bottom: 1.5rem;
            color: var(--color-text);
        }
        
        .analysis-content strong {
            color: var(--color-accent);
        }
        
        /* Footer */
        footer {
            background: var(--color-surface);
            border-top: 1px solid var(--color-border);
            padding: 3rem 2rem;
            margin-top: 4rem;
        }
        
        .footer-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .footer-brand {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 500;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .footer-meta {
            color: var(--color-text-muted);
            font-size: 0.875rem;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .section-card {
                grid-template-columns: 1fr;
            }
            
            .section-card:nth-child(even) {
                direction: ltr;
            }
            
            .executive-summary {
                margin: -2rem 1rem 2rem;
                padding: 2rem;
            }
            
            .takeaways-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
                color: black;
            }
            
            .hero {
                min-height: auto;
                padding: 2rem;
            }
            
            .section-card {
                break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <section class="hero">
        <div class="hero-bg"></div>
        {% if hero_image %}
        <img src="{{ hero_image }}" alt="Report banner" class="hero-image">
        {% endif %}
        <div class="hero-content">
            <div class="hero-badge">
                <span>AI-Generated Summary Report</span>
            </div>
            <h1>{{ title }}</h1>
            <div class="hero-meta">
                <span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                    {{ generated_date }}
                </span>
                <span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                    </svg>
                    {{ word_count | default(0) }} words analyzed
                </span>
            </div>
        </div>
    </section>
    
    <!-- Executive Summary -->
    <div class="container">
        <div class="executive-summary">
            <div class="section-label">Executive Summary</div>
            {% for paragraph in executive_summary.split('\\n\\n') %}
            <p>{{ paragraph }}</p>
            {% endfor %}
        </div>
    </div>
    
    <!-- Key Takeaways -->
    <section class="takeaways">
        <div class="container">
            <h2>Key Takeaways</h2>
            <div class="takeaways-grid">
                {% for takeaway in key_takeaways %}
                <div class="takeaway-card">
                    <div class="takeaway-number">{{ loop.index }}</div>
                    <p>{{ takeaway }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </section>
    
    <!-- Detailed Sections -->
    <section class="sections">
        <div class="container">
            <h2>Detailed Analysis by Section</h2>
            {% for section in sections %}
            <div class="section-card">
                <div class="section-content">
                    <h3>{{ section.title }}</h3>
                    <p>{{ section.summary }}</p>
                    <ul class="section-points">
                        {% for point in section.key_points %}
                        <li>{{ point }}</li>
                        {% endfor %}
                    </ul>
                </div>
                <div class="section-image">
                    {% if section.title in image_map %}
                    <img src="{{ image_map[section.title] }}" alt="Visual for {{ section.title }}">
                    {% else %}
                    <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:var(--color-text-muted);">
                        <span>Image unavailable</span>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </section>
    
    <!-- Detailed Analysis -->
    {% if detailed_analysis %}
    <section class="analysis">
        <div class="container">
            <h2>In-Depth Analysis</h2>
            <div class="analysis-content">
                {% for paragraph in detailed_analysis.split('\\n\\n') %}
                <p>{{ paragraph | replace('**', '<strong>') | replace('**', '</strong>') | safe }}</p>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}
    
    <!-- Footer -->
    <footer>
        <div class="footer-content">
            <div class="footer-brand">Summary Report</div>
            <div class="footer-meta">
                <p>Source: {{ source }}</p>
                <p>Generated with Venice AI • {{ year }}</p>
            </div>
        </div>
    </footer>
</body>
</html>''')


def generate_html_report(
    summary: StructuredSummary,
    images: list[GeneratedImage],
    hero_image: Optional[GeneratedImage] = None,
    output_path: Optional[str] = None
) -> str:
    """Convenience function to generate an HTML report"""
    generator = ReportGenerator()
    return generator.generate_report(summary, images, hero_image, output_path)

