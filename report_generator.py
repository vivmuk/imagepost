"""
HTML Report Generator
Creates beautiful, styled HTML reports with embedded images
"""
import base64
import re
import html
from pathlib import Path
from datetime import datetime
from typing import Optional
from jinja2 import Template
from rich.console import Console

from summarizer import StructuredSummary
from image_generator import GeneratedImage

console = Console()


def markdown_to_html(text: str) -> str:
    """Convert markdown text to HTML"""
    if not text:
        return ""
    
    # Escape HTML entities first to prevent XSS
    # But we need to be careful not to break markdown
    lines = text.split('\n')
    result_lines = []
    in_list = False
    list_type = None
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
                list_type = None
            result_lines.append('')
            continue
        
        # Headers
        if stripped.startswith('### '):
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
            content = html.escape(stripped[4:])
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            result_lines.append(f'<h3>{content}</h3>')
            continue
        elif stripped.startswith('## '):
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
            content = html.escape(stripped[3:])
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            result_lines.append(f'<h2>{content}</h2>')
            continue
        elif stripped.startswith('# '):
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
            content = html.escape(stripped[2:])
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            result_lines.append(f'<h1>{content}</h1>')
            continue
        
        # Horizontal rule
        if stripped == '---' or stripped == '***':
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
            result_lines.append('<hr>')
            continue
        
        # Numbered list items
        num_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if num_match:
            content = html.escape(num_match.group(2))
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            if not in_list or list_type != 'ol':
                if in_list:
                    result_lines.append(f'</{list_type}>')
                result_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            result_lines.append(f'<li>{content}</li>')
            continue
        
        # Bullet list items
        if stripped.startswith('- ') or stripped.startswith('* '):
            content = html.escape(stripped[2:])
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            if not in_list or list_type != 'ul':
                if in_list:
                    result_lines.append(f'</{list_type}>')
                result_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            result_lines.append(f'<li>{content}</li>')
            continue
        
        # Blockquotes
        if stripped.startswith('> '):
            if in_list:
                result_lines.append(f'</{list_type}>')
                in_list = False
            content = html.escape(stripped[2:])
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            result_lines.append(f'<blockquote>{content}</blockquote>')
            continue
        
        # Close list if we're no longer in list items
        if in_list:
            result_lines.append(f'</{list_type}>')
            in_list = False
            list_type = None
        
        # Regular paragraph
        content = html.escape(stripped)
        # Bold
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        # Italic
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        result_lines.append(f'<p>{content}</p>')
    
    # Close any open list
    if in_list:
        result_lines.append(f'</{list_type}>')
    
    return '\n'.join(result_lines)


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
            linkedin_post=summary.linkedin_post,
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

    def _get_linkedin_template(self) -> Template:
        return Template('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ headline }} | LinkedIn Article</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        :root { --accent: #DC2626; --text: #111827; --bg: #ffffff; }
        body { font-family: 'Montserrat', sans-serif; color: var(--text); line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        h1 { font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; line-height: 1.2; }
        h2 { font-size: 1.5rem; font-weight: 700; margin-top: 2rem; margin-bottom: 1rem; color: var(--accent); }
        .intro { font-size: 1.2rem; color: #4b5563; margin-bottom: 2rem; border-left: 4px solid var(--accent); padding-left: 20px; }
        .visual { width: 100%; border-radius: 8px; margin: 2rem 0; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .point { margin-bottom: 2rem; }
        .point-title { font-weight: 700; font-size: 1.2rem; margin-bottom: 0.5rem; }
        .cta { background: #f9fafb; padding: 2rem; border-radius: 8px; margin-top: 3rem; text-align: center; font-weight: 600; border: 1px solid #e5e5e5; }
    </style>
</head>
<body>
    <h1>{{ headline }}</h1>
    
    {% if hero_image %}
    <img src="{{ hero_image }}" class="visual" alt="Article Visual">
    {% endif %}

    <div class="intro">{{ introduction }}</div>
    
    {% for point in key_points %}
    <div class="point">
        <div class="point-title">{{ point.title }}</div>
        <p>{{ point.detail }}</p>
    </div>
    {% endfor %}
    
    <div class="point">
        <h2>Conclusion</h2>
        <p>{{ conclusion }}</p>
    </div>
    
    <div class="cta">
        {{ call_to_action }}
    </div>
</body>
</html>''')

    def generate_linkedin_html(self, article_data: dict, hero_image: Optional[GeneratedImage] = None) -> str:
        hero_src = None
        if hero_image:
            b64 = base64.b64encode(hero_image.image_data).decode('utf-8')
            hero_src = f"data:image/webp;base64,{b64}"
            
        template = self._get_linkedin_template()
        return template.render(
            headline=article_data.get('headline', 'LinkedIn Article'),
            introduction=article_data.get('introduction', ''),
            key_points=article_data.get('key_points', []),
            conclusion=article_data.get('conclusion', ''),
            call_to_action=article_data.get('call_to_action', ''),
            hero_image=hero_src
        )
    
    def _get_learning_template(self) -> Template:
        return Template('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Learning: {{ topic }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #ffffff; --text: #1f2937; --accent: #4f46e5; --light-accent: #e0e7ff; }
        body { 
            font-family: 'Lexend', 'Montserrat', sans-serif; 
            color: var(--text); 
            line-height: 2.0; 
            font-size: 18px; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 40px 20px; 
            background: #fafafa;
        }
        .container { background: white; padding: 60px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        h1 { font-size: 3rem; color: var(--accent); margin-bottom: 1rem; line-height: 1.2; }
        h2 { font-size: 2rem; margin-top: 3rem; margin-bottom: 1.5rem; border-bottom: 3px solid var(--light-accent); padding-bottom: 10px; }
        h3 { font-size: 1.5rem; color: #4b5563; margin-top: 2rem; }
        p { margin-bottom: 1.5rem; }
        ul { margin-bottom: 1.5rem; padding-left: 25px; }
        li { margin-bottom: 10px; }
        
        /* Dyslexia-friendly specifics */
        strong { color: var(--accent); font-weight: 600; }
        .image-wrapper {
            position: relative;
            width: 100%;
            margin-bottom: 2rem;
            background: var(--light-accent);
            border-radius: 12px;
            overflow: hidden;
        }
        .chapter-visual { 
            width: 100%; 
            height: auto; 
            max-height: 600px;
            object-fit: contain; 
            border-radius: 12px; 
            display: block;
            background: var(--light-accent);
        }
        .image-download-btn {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(79, 70, 229, 0.9);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-family: 'Montserrat', sans-serif;
            font-weight: 500;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
            z-index: 10;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .image-download-btn:hover { 
            background: rgba(79, 70, 229, 1); 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .preview-box { background: var(--light-accent); padding: 30px; border-radius: 12px; margin-bottom: 40px; }
        .big-idea { font-size: 1.25rem; font-weight: 500; }
        
        .chapter-card { margin-bottom: 60px; padding: 30px; border: 2px solid #f3f4f6; border-radius: 12px; }
        .chapter-num { text-transform: uppercase; font-weight: 600; color: var(--accent); font-size: 0.9rem; letter-spacing: 1px; margin-bottom: 10px; }
        
        .review-section { background: #fffbeb; border: 2px solid #fcd34d; padding: 30px; border-radius: 12px; margin-top: 60px; }
        
        .print-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--accent);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 30px;
            font-family: 'Montserrat', sans-serif;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
            transition: transform 0.2s;
            z-index: 100;
        }
        .print-btn:hover { transform: translateY(-2px); }
        
        /* Audio Controls */
        .audio-controls {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 20px 0;
            padding: 16px;
            background: #f9fafb;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        .audio-btn {
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-family: 'Montserrat', sans-serif;
            font-weight: 500;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .audio-btn:hover { background: #4338ca; transform: translateY(-1px); }
        .audio-btn:disabled { background: #9ca3af; cursor: not-allowed; transform: none; }
        .audio-btn.generating { background: #f59e0b; }
        .audio-player {
            flex: 1;
            display: none;
            align-items: center;
            gap: 12px;
        }
        .audio-player.active { display: flex; }
        .audio-player audio {
            flex: 1;
            height: 40px;
        }
        .play-pause-btn {
            background: var(--accent);
            color: white;
            border: none;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.2s;
        }
        .play-pause-btn:hover { background: #4338ca; transform: scale(1.05); }
        .audio-loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media print {
            body { background: white; }
            .container { box-shadow: none; padding: 0; margin: 0; max-width: 100%; }
            .chapter-card { page-break-inside: avoid; border: none; padding: 0; margin-bottom: 40px; }
            .print-btn { display: none; }
            .preview-box, .review-section { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Save as PDF</button>
    <div class="container">
        <h1>{{ topic }}</h1>
        
        <div class="preview-box">
            <h2>The Big Idea</h2>
            <p class="big-idea">{{ topic_definition | default("This lesson breaks down " + topic + " into 3 clear chapters to help you master the core concepts quickly.") }}</p>
        </div>

        {% for chapter in chapters %}
        <div class="chapter-card" data-chapter-index="{{ loop.index0 }}">
            <div class="chapter-num">Chapter {{ loop.index }} of {{ loop.length }}</div>
            <h2>{{ chapter.title }}</h2>
            
            {% if chapter.image_url %}
            <div class="image-wrapper">
                <img src="{{ chapter.image_url }}" class="chapter-visual" alt="Visual for {{ chapter.title }}" id="chapter-image-{{ loop.index0 }}">
                <button class="image-download-btn" onclick="downloadImage({{ loop.index0 }}, '{{ chapter.title | replace("'", "\\'") }}')" title="Download Image">
                    ⬇ Download
                </button>
            </div>
            {% endif %}
            
            <div class="audio-controls">
                <button class="audio-btn" onclick="generateAudio({{ loop.index0 }})" id="audio-btn-{{ loop.index0 }}">
                    <span id="audio-btn-text-{{ loop.index0 }}">🎵 Generate Audio</span>
                </button>
                <div class="audio-player" id="audio-player-{{ loop.index0 }}">
                    <button class="play-pause-btn" onclick="toggleAudio({{ loop.index0 }})" id="play-pause-{{ loop.index0 }}">▶</button>
                    <audio id="audio-element-{{ loop.index0 }}" controls></audio>
                </div>
            </div>
            
            <div class="chapter-content">
                {{ chapter.content | safe }}
            </div>
        </div>
        {% endfor %}
        
        <div class="review-section">
            <h2>Smart Review: Key Takeaways</h2>
            {% if chapters[0].review_content %}
                {{ chapters[0].review_content | safe }}
            {% else %}
                <h3>Key Facts to Remember</h3>
                <ul>
                    {% for chapter in chapters %}
                    <li><strong>{{ chapter.title }}:</strong> {{ chapter.description }}</li>
                    {% endfor %}
                </ul>
                <h3>Questions to Ponder</h3>
                <ul>
                    <li>How does this topic connect to your daily life?</li>
                    <li>What questions do you still have about this topic?</li>
                    <li>How would you explain this to someone else?</li>
                </ul>
            {% endif %}
        </div>
    </div>
    <script>
        // Ensure functions are in global scope
        window.audioData = window.audioData || {};
        const chapterCount = {{ chapters | length }};
        
        window.generateAudio = async function(chapterIndex) {
            const btn = document.getElementById(`audio-btn-${chapterIndex}`);
            const btnText = document.getElementById(`audio-btn-text-${chapterIndex}`);
            const player = document.getElementById(`audio-player-${chapterIndex}`);
            const audioElement = document.getElementById(`audio-element-${chapterIndex}`);
            
            if (window.audioData[chapterIndex]) {
                // Audio already generated, just show player
                player.classList.add('active');
                audioElement.src = window.audioData[chapterIndex];
                return;
            }
            
            // Disable button and show loading
            btn.disabled = true;
            btn.classList.add('generating');
            btnText.innerHTML = '<span class="audio-loading"></span> Generating...';
            
            try {
                // Get chapter text (strip HTML tags)
                const chapterCard = document.querySelector(`[data-chapter-index="${chapterIndex}"]`);
                const contentDiv = chapterCard.querySelector('.chapter-content');
                const textContent = contentDiv.innerText || contentDiv.textContent;
                
                // Generate audio
                const formData = new FormData();
                formData.append('text', textContent);
                formData.append('voice', 'af_sky');
                
                const response = await fetch('/api/audio/generate', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Audio generation failed');
                }
                
                const data = await response.json();
                window.audioData[chapterIndex] = data.audio;
                
                // Show player and set audio source
                player.classList.add('active');
                audioElement.src = data.audio;
                
                // Reset button
                btn.disabled = false;
                btn.classList.remove('generating');
                btnText.textContent = '🎵 Audio Ready';
                
            } catch (error) {
                console.error('Error generating audio:', error);
                btn.disabled = false;
                btn.classList.remove('generating');
                btnText.textContent = '❌ Error - Try Again';
                alert('Failed to generate audio. Please try again.');
            }
        }
        
        window.toggleAudio = function(chapterIndex) {
            const audioElement = document.getElementById(`audio-element-${chapterIndex}`);
            const playPauseBtn = document.getElementById(`play-pause-${chapterIndex}`);
            
            if (audioElement.paused) {
                audioElement.play();
                playPauseBtn.textContent = '⏸';
            } else {
                audioElement.pause();
                playPauseBtn.textContent = '▶';
            }
        }
        
        // Update play/pause button when audio state changes
        // Use immediate execution since DOM is already loaded when injected
        (function() {
            for (let index = 0; index < chapterCount; index++) {
                const audioElement = document.getElementById(`audio-element-${index}`);
                const playPauseBtn = document.getElementById(`play-pause-${index}`);
                
                if (audioElement && playPauseBtn) {
                    audioElement.addEventListener('play', () => {
                        if (playPauseBtn) playPauseBtn.textContent = '⏸';
                    });
                    audioElement.addEventListener('pause', () => {
                        if (playPauseBtn) playPauseBtn.textContent = '▶';
                    });
                    audioElement.addEventListener('ended', () => {
                        if (playPauseBtn) playPauseBtn.textContent = '▶';
                    });
                }
            }
        })();
        
        window.downloadImage = function(chapterIndex, chapterTitle) {
            const img = document.getElementById(`chapter-image-${chapterIndex}`);
            if (!img) return;
            
            // Create a temporary anchor element
            const link = document.createElement('a');
            link.href = img.src;
            
            // Clean filename
            const safeTitle = chapterTitle.replace(/[^a-z0-9]/gi, '_').toLowerCase().substring(0, 50);
            link.download = `chapter_${chapterIndex + 1}_${safeTitle}.webp`;
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    </script>
</body>
</html>''')

    def generate_learning_html(self, topic: str, curriculum: list, education_level: str = "High School", topic_definition: str = None) -> str:
        template = self._get_learning_template()
        return template.render(
            topic=topic,
            chapters=curriculum,
            education_level=education_level,
            topic_definition=topic_definition or f"{topic} is a fundamental concept that we'll explore in depth through these three chapters."
        )
    
    def generate_analysis_html(self, analysis_data: dict, infographic_url: str = None) -> str:
        """Generate HTML for the multi-agent article analysis"""
        template = self._get_analysis_template()
        
        # Convert markdown to HTML for all text fields
        final_summary_html = markdown_to_html(analysis_data.get('final_summary', ''))
        recon_html = markdown_to_html(analysis_data.get('recon_output', ''))
        extraction_html = markdown_to_html(analysis_data.get('extraction_output', ''))
        challenger_html = markdown_to_html(analysis_data.get('challenger_output', ''))
        synthesis_html = markdown_to_html(analysis_data.get('synthesis_output', ''))
        
        return template.render(
            title=analysis_data.get('title', 'Article Analysis'),
            url=analysis_data.get('url', ''),
            recon_output=recon_html,
            extraction_output=extraction_html,
            challenger_output=challenger_html,
            synthesis_output=synthesis_html,
            final_summary=final_summary_html,
            confidence_score=analysis_data.get('confidence_score', 5),
            infographic_url=infographic_url or '',
            generated_date=datetime.now().strftime("%B %d, %Y at %H:%M"),
            year=datetime.now().year
        )
    
    def _get_analysis_template(self) -> Template:
        """Returns the Jinja2 HTML template for multi-agent article analysis - Management Consultant Style"""
        return Template('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | Critical Analysis</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #DC2626;
            --primary-dark: #991B1B;
            --text: #111827;
            --text-light: #6b7280;
            --bg: #ffffff;
            --bg-light: #f9fafb;
            --border: #e5e7eb;
            --black: #111827;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            font-size: 16px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 60px 40px;
        }
        
        /* Header */
        header {
            padding-bottom: 40px;
            border-bottom: 3px solid var(--black);
            margin-bottom: 50px;
        }
        
        h1 {
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--black);
            margin-bottom: 16px;
            line-height: 1.3;
        }
        
        .meta {
            color: var(--text-light);
            font-size: 0.9rem;
        }
        
        .meta a { color: var(--primary); text-decoration: none; }
        .meta a:hover { text-decoration: underline; }
        
        /* Infographic Section */
        .infographic-section {
            background: var(--bg-light);
            border: 2px solid var(--border);
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 40px;
            text-align: center;
        }
        
        .infographic-section h2 {
            font-size: 1.2rem;
            color: var(--black);
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .infographic-section img {
            max-width: 100%;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        
        /* Confidence Gauge */
        .confidence-gauge {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 24px;
            background: var(--bg-light);
            border: 2px solid var(--border);
            border-radius: 8px;
            margin-bottom: 40px;
        }
        
        .gauge-label {
            font-weight: 600;
            font-size: 1rem;
            color: var(--black);
        }
        
        .gauge-bar {
            width: 250px;
            height: 20px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .gauge-fill {
            height: 100%;
            border-radius: 4px;
        }
        
        .gauge-fill.low { background: var(--primary); }
        .gauge-fill.medium { background: #f59e0b; }
        .gauge-fill.high { background: #059669; }
        
        .gauge-score {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        /* Section Title */
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--black);
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 10px;
        }
        
        /* Agent Sections */
        .agent-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
            margin-bottom: 50px;
        }
        
        .agent-card {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .agent-header {
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            user-select: none;
            background: var(--bg-light);
            border-bottom: 2px solid var(--primary);
        }
        
        .agent-header:hover {
            background: #f3f4f6;
        }
        
        .agent-icon {
            font-size: 1.3rem;
        }
        
        .agent-title {
            font-size: 0.95rem;
            font-weight: 600;
            flex: 1;
            color: var(--black);
        }
        
        .agent-toggle {
            font-size: 1rem;
            color: var(--text-light);
            transition: transform 0.3s;
        }
        
        .agent-toggle.open { transform: rotate(180deg); }
        
        .agent-content {
            padding: 20px;
            display: none;
            background: var(--bg);
            max-height: 400px;
            overflow-y: auto;
        }
        
        .agent-content.open { display: block; }
        
        .agent-markdown {
            font-family: 'Montserrat', sans-serif;
            font-size: 0.85rem;
            line-height: 1.7;
            color: var(--text);
        }
        
        .agent-markdown h1, .agent-markdown h2, .agent-markdown h3 {
            margin: 16px 0 10px 0;
            color: var(--black);
        }
        
        .agent-markdown h2 { font-size: 1.1rem; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
        .agent-markdown h3 { font-size: 1rem; }
        
        .agent-markdown p { margin-bottom: 10px; }
        .agent-markdown ul, .agent-markdown ol { margin: 10px 0; padding-left: 24px; }
        .agent-markdown li { margin-bottom: 6px; }
        .agent-markdown strong { color: var(--primary); font-weight: 600; }
        .agent-markdown hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
        .agent-markdown blockquote {
            background: var(--bg-light);
            border-left: 3px solid var(--primary);
            padding: 10px 16px;
            margin: 10px 0;
            font-style: italic;
        }
        
        /* Final Summary Section */
        .final-summary {
            background: var(--bg);
            border: 2px solid var(--black);
            border-radius: 8px;
            padding: 40px;
            margin-bottom: 40px;
        }
        
        .final-summary h2 {
            font-size: 1.3rem;
            color: var(--black);
            margin-bottom: 30px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 3px solid var(--primary);
            padding-bottom: 12px;
        }
        
        .summary-content {
            font-size: 0.95rem;
            line-height: 1.9;
        }
        
        .summary-content h3 {
            font-size: 1.1rem;
            color: var(--black);
            margin: 30px 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
        }
        
        .summary-content p {
            margin-bottom: 16px;
        }
        
        .summary-content ul, .summary-content ol {
            margin: 16px 0;
            padding-left: 24px;
        }
        
        .summary-content li {
            margin-bottom: 10px;
        }
        
        .summary-content strong {
            color: var(--primary);
            font-weight: 600;
        }
        
        .summary-content blockquote {
            background: var(--bg-light);
            border-left: 4px solid var(--primary);
            padding: 16px 24px;
            margin: 20px 0;
            font-style: italic;
            color: var(--text);
        }
        
        .summary-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9rem;
        }
        
        .summary-content th, .summary-content td {
            padding: 12px;
            border: 1px solid var(--border);
            text-align: left;
        }
        
        .summary-content th {
            background: var(--bg-light);
            font-weight: 600;
        }
        
        .summary-content hr {
            border: none;
            border-top: 1px solid var(--border);
            margin: 25px 0;
        }
        
        /* Print Button - moved to bottom */
        .print-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-family: 'Montserrat', sans-serif;
            font-weight: 600;
            cursor: pointer;
            z-index: 100;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
        }
        
        .print-btn:hover {
            background: var(--primary-dark);
        }
        
        /* Footer */
        footer {
            text-align: center;
            padding: 30px 0;
            border-top: 1px solid var(--border);
            color: var(--text-light);
            font-size: 0.8rem;
        }
        
        /* Image download button */
        .image-wrapper {
            position: relative;
            display: inline-block;
        }
        
        .image-download-btn {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s ease;
            font-family: 'Montserrat', sans-serif;
        }
        
        .image-wrapper:hover .image-download-btn {
            opacity: 1;
        }
        
        @media print {
            .print-btn { display: none; }
            .agent-content { display: block !important; max-height: none; }
            .agent-toggle { display: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ title }}</h1>
            <p class="meta">
                {% if url %}Source: <a href="{{ url }}" target="_blank">{{ url }}</a> | {% endif %}
                Generated: {{ generated_date }}
            </p>
        </header>
        
        {% if infographic_url %}
        <section class="infographic-section">
            <h2>Article Summary Infographic</h2>
            <div class="image-wrapper">
                <img src="{{ infographic_url }}" alt="Article Summary Infographic" id="infographic-image">
                <button class="image-download-btn" onclick="window.downloadInfographic()">Download</button>
            </div>
        </section>
        {% endif %}
        
        <section class="confidence-gauge">
            <span class="gauge-label">Confidence Rating:</span>
            <div class="gauge-bar">
                <div class="gauge-fill {% if confidence_score <= 3 %}low{% elif confidence_score <= 6 %}medium{% else %}high{% endif %}" 
                     style="width: {{ confidence_score * 10 }}%"></div>
            </div>
            <span class="gauge-score">{{ confidence_score }}/10</span>
        </section>
        
        <section class="final-summary">
            <h2>Executive Summary</h2>
            <div class="summary-content" id="summary-content">{{ final_summary | safe }}</div>
        </section>
        
        <h3 class="section-title">Agent Analysis Details</h3>
        
        <div class="agent-grid">
            <div class="agent-card">
                <div class="agent-header" onclick="window.toggleAgent(this)">
                    <span class="agent-icon">🔎</span>
                    <span class="agent-title">Agent 1: Reconnaissance Scanner</span>
                    <span class="agent-toggle">▼</span>
                </div>
                <div class="agent-content agent-markdown">
                    {{ recon_output | safe }}
                </div>
            </div>
            
            <div class="agent-card">
                <div class="agent-header" onclick="window.toggleAgent(this)">
                    <span class="agent-icon">⛏️</span>
                    <span class="agent-title">Agent 2: Extraction Engine</span>
                    <span class="agent-toggle">▼</span>
                </div>
                <div class="agent-content agent-markdown">
                    {{ extraction_output | safe }}
                </div>
            </div>
            
            <div class="agent-card">
                <div class="agent-header" onclick="window.toggleAgent(this)">
                    <span class="agent-icon">😈</span>
                    <span class="agent-title">Agent 3: Type 2 Challenger</span>
                    <span class="agent-toggle">▼</span>
                </div>
                <div class="agent-content agent-markdown">
                    {{ challenger_output | safe }}
                </div>
            </div>
            
            <div class="agent-card">
                <div class="agent-header" onclick="window.toggleAgent(this)">
                    <span class="agent-icon">🎀</span>
                    <span class="agent-title">Agent 4: Synthesis Composer</span>
                    <span class="agent-toggle">▼</span>
                </div>
                <div class="agent-content agent-markdown">
                    {{ synthesis_output | safe }}
                </div>
            </div>
        </div>
        
        <footer>
            <p>Multi-Agent Critical Analysis | Generated {{ generated_date }} | © {{ year }}</p>
        </footer>
        
        <button class="print-btn" onclick="window.print()">Save as PDF</button>
    </div>
    
    <script>
        // Global functions for interactive elements
        window.toggleAgent = function(header) {
            if (!header) return;
            var content = header.nextElementSibling;
            var toggle = header.querySelector('.agent-toggle');
            
            if (content) {
                content.classList.toggle('open');
            }
            if (toggle) {
                toggle.classList.toggle('open');
            }
        };
        
        window.downloadInfographic = function() {
            var img = document.getElementById('infographic-image');
            if (!img) return;
            
            var link = document.createElement('a');
            link.href = img.src;
            link.download = 'article_summary_infographic.webp';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
    </script>
</body>
</html>''')

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
        
        /* Social Media Card */
        .social-media-card {
            background: #f3f4f6;
            border-radius: 8px;
            padding: 24px;
            border: 1px solid #e5e5e5;
        }
        
        .social-platform {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            font-weight: 600;
            color: #0077b5;
        }
        
        .social-content textarea {
            width: 100%;
            height: 200px;
            padding: 16px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
            margin-bottom: 12px;
            background: white;
        }
        
        .social-content button {
            background: #0077b5;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            transition: background 0.2s;
        }
        
        .social-content button:hover {
            background: #006097;
        }
        
        .social-image {
            margin-top: 20px;
        }
        
        .social-image p {
            font-size: 13px;
            color: #6b7280;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .social-image img {
            max-width: 100%;
            max-height: 400px;
            border-radius: 4px;
            border: 1px solid #e5e5e5;
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
        
        <!-- Social Media Assets -->
        {% if linkedin_post %}
        <section class="section">
            <h2 class="section-title">Social Media Assets</h2>
            <div class="social-media-card">
                <div class="social-platform">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="#0077b5" xmlns="http://www.w3.org/2000/svg">
                        <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                    </svg>
                    <span>LinkedIn Post</span>
                </div>
                <div class="social-content">
                    <textarea readonly onclick="this.select()">{{ linkedin_post }}</textarea>
                    <button onclick="navigator.clipboard.writeText(this.previousElementSibling.value); this.innerText = 'Copied!'; setTimeout(() => this.innerText = 'Copy Text', 2000);">Copy Text</button>
                </div>
                {% if hero_image %}
                <div class="social-image">
                    <p>Recommended Visual:</p>
                    <img src="{{ hero_image }}" alt="Social Media Visual">
                </div>
                {% endif %}
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
