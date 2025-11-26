"""
Summarization Pipeline using Venice API
Uses structured responses for consistent, parseable output
"""
import asyncio
import json
from typing import Optional
from dataclasses import dataclass, field
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import config
from scraper import ExtractedContent

console = Console()


@dataclass
class SectionSummary:
    """Summary for a single section"""
    title: str
    summary: str
    key_points: list[str]
    image_prompt: str  # AI-generated prompt for infographic


@dataclass
class KeyTerm:
    """A key term with definition"""
    term: str
    definition: str
    context: str  # How it's used in this content


@dataclass
class StructuredSummary:
    """Complete structured summary of content"""
    title: str
    executive_summary: str
    key_takeaways: list[str]
    key_terms: list[KeyTerm]  # Key terms and definitions
    sections: list[SectionSummary]
    detailed_analysis: str
    limitations_and_biases: str  # Type 2 thinking: critical analysis of limitations and cognitive biases
    linkedin_post: str  # Viral LinkedIn post text
    source: str
    word_count: int


class VeniceSummarizer:
    """Summarizes content using Venice API with structured responses"""
    
    def __init__(self):
        self.api_key = config.venice.api_key
        self.base_url = config.venice.base_url
        self.model = config.venice.summarization_model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def summarize(self, content: ExtractedContent) -> StructuredSummary:
        """
        Generate a structured summary of the content
        
        Uses a multi-stage pipeline:
        1. Extract key takeaways
        2. Generate section summaries with image prompts
        3. Create executive summary
        """
        console.print(f"\n[bold green]Summarizing:[/bold green] {content.title}")
        console.print(f"[dim]Word count: {content.word_count}[/dim]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Stage 1: Extract key takeaways
            task1 = progress.add_task("Extracting key takeaways...", total=None)
            key_takeaways = await self._extract_key_takeaways(content)
            progress.update(task1, completed=True)
            
            # Stage 2: Generate section summaries
            task2 = progress.add_task("Analyzing sections...", total=None)
            sections = await self._summarize_sections(content, key_takeaways)
            progress.update(task2, completed=True)
            
            # Stage 3: Generate executive summary
            task3 = progress.add_task("Creating executive summary...", total=None)
            executive_summary, detailed_analysis = await self._generate_executive_summary(
                content, key_takeaways, sections
            )
            progress.update(task3, completed=True)
            
            # Stage 4: Extract key terms
            task4 = progress.add_task("Extracting key terms...", total=None)
            key_terms = await self._extract_key_terms(content)
            progress.update(task4, completed=True)
            
            # Stage 5: Generate limitations and biases analysis
            task5 = progress.add_task("Analyzing limitations and biases...", total=None)
            try:
                limitations_and_biases = await self._analyze_limitations_and_biases(
                    content, executive_summary, detailed_analysis
                )
            except Exception as e:
                print(f"Error generating limitations: {e}")
                limitations_and_biases = ""
            progress.update(task5, completed=True)

            # Stage 6: Generate LinkedIn Post
            task6 = progress.add_task("Drafting LinkedIn post...", total=None)
            linkedin_post = await self._generate_linkedin_post(content, executive_summary, key_takeaways)
            progress.update(task6, completed=True)
        
        return StructuredSummary(
            title=content.title,
            executive_summary=executive_summary,
            key_takeaways=key_takeaways,
            key_terms=key_terms,
            sections=sections,
            detailed_analysis=detailed_analysis,
            limitations_and_biases=limitations_and_biases,
            linkedin_post=linkedin_post,
            source=content.source,
            word_count=content.word_count
        )
    
    async def _extract_key_takeaways(self, content: ExtractedContent) -> list[str]:
        """Extract 5-7 key takeaways using structured response"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "key_takeaways",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "takeaways": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "point": {"type": "string"},
                                    "importance": {"type": "string"}
                                },
                                "required": ["point", "importance"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["takeaways"],
                    "additionalProperties": False
                }
            }
        }
        
        prompt = f"""Analyze the following content and extract 5-7 key takeaways.
Each takeaway should be a concise, actionable insight that captures the most important points.

CONTENT TITLE: {content.title}

CONTENT:
{content.text[:12000]}

Extract the most critical insights, findings, or lessons from this content."""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            return [t["point"] for t in data.get("takeaways", [])]
        except (json.JSONDecodeError, KeyError):
            # Fallback: return raw response split into points
            return [response] if response else ["Unable to extract takeaways"]
    
    async def _summarize_sections(
        self, 
        content: ExtractedContent, 
        key_takeaways: list[str]
    ) -> list[SectionSummary]:
        """Generate summaries for each section with image prompts"""
        
        # If we have detected sections, use them; otherwise create logical divisions
        if content.sections and len(content.sections) > 1:
            text_sections = content.sections
        else:
            # Create artificial sections by splitting content
            text_sections = self._create_sections(content.text)
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "section_summaries",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "sections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "summary": {"type": "string"},
                                    "key_points": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "visual_concept": {"type": "string"}
                                },
                                "required": ["title", "summary", "key_points", "visual_concept"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["sections"],
                    "additionalProperties": False
                }
            }
        }
        
        sections_text = "\n\n".join([
            f"SECTION: {s.get('title', 'Untitled')}\n{s.get('content', '')[:2000]}"
            for s in text_sections[:8]  # Limit to 8 sections
        ])
        
        prompt = f"""Analyze these content sections and provide structured summaries.

DOCUMENT TITLE: {content.title}

KEY THEMES: {', '.join(key_takeaways[:3])}

SECTIONS:
{sections_text}

For each section:
1. Create a clear, descriptive title
2. Write a 2-3 sentence summary
3. List 2-3 key points
4. Describe a visual concept for an infographic that would represent this section's main idea 
   (be specific about imagery, metaphors, and visual elements - this will be used to generate an image)"""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            return [
                SectionSummary(
                    title=s["title"],
                    summary=s["summary"],
                    key_points=s["key_points"],
                    image_prompt=self._enhance_image_prompt(s["visual_concept"], s["title"])
                )
                for s in data.get("sections", [])
            ]
        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[yellow]Warning: Could not parse sections: {e}[/yellow]")
            return [SectionSummary(
                title="Overview",
                summary=response[:500] if response else "Summary unavailable",
                key_points=["Content analysis complete"],
                image_prompt="Modern infographic showing data analysis and insights"
            )]
    
    async def _generate_executive_summary(
        self,
        content: ExtractedContent,
        key_takeaways: list[str],
        sections: list[SectionSummary]
    ) -> tuple[str, str]:
        """Generate executive summary and detailed analysis"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "executive_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "executive_summary": {"type": "string"},
                        "detailed_analysis": {"type": "string"},
                        "recommendations": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["executive_summary", "detailed_analysis", "recommendations"],
                    "additionalProperties": False
                }
            }
        }
        
        sections_overview = "\n".join([
            f"- {s.title}: {s.summary[:150]}..."
            for s in sections[:6]
        ])
        
        prompt = f"""Create an executive summary and detailed analysis for this content.

TITLE: {content.title}

KEY TAKEAWAYS:
{chr(10).join(f'• {t}' for t in key_takeaways)}

SECTIONS OVERVIEW:
{sections_overview}

ORIGINAL CONTENT PREVIEW:
{content.text[:4000]}

Generate:
1. An executive summary (3-4 paragraphs) that captures the essence, main arguments, and significance
2. A detailed analysis (4-6 paragraphs) providing deeper insights, implications, and context
3. 3-5 actionable recommendations based on the content"""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            exec_summary = data.get("executive_summary", "")
            detailed = data.get("detailed_analysis", "")
            recommendations = data.get("recommendations", [])
            
            # Append recommendations to detailed analysis
            if recommendations:
                detailed += "\n\n**Recommendations:**\n" + "\n".join(f"• {r}" for r in recommendations)
            
            return exec_summary, detailed
        except (json.JSONDecodeError, KeyError):
            return response[:1000] if response else "Summary unavailable", ""
    
    async def _extract_key_terms(self, content: ExtractedContent) -> list[KeyTerm]:
        """Extract key terms, jargon, and technical vocabulary with definitions"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "key_terms",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "terms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "term": {"type": "string"},
                                    "definition": {"type": "string"},
                                    "context": {"type": "string"}
                                },
                                "required": ["term", "definition", "context"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["terms"],
                    "additionalProperties": False
                }
            }
        }
        
        prompt = f"""Extract 5-10 key terms, technical vocabulary, acronyms, or important concepts from this content that readers should understand.

CONTENT TITLE: {content.title}

CONTENT:
{content.text[:config.scraper.max_content_length]}

For each term, provide:
1. The term itself (exact phrase as used in the content)
2. A clear, concise definition (1-2 sentences, accessible to a general business audience)
3. Context: How this term is specifically used or relevant in this content

Focus on:
- Technical jargon that might be unfamiliar
- Acronyms and abbreviations
- Key concepts central to understanding the content
- Industry-specific terminology

Provide definitions that a management consultant or executive could quickly reference."""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            terms = []
            for t in data.get("terms", []):
                terms.append(KeyTerm(
                    term=t.get("term", ""),
                    definition=t.get("definition", ""),
                    context=t.get("context", "")
                ))
            return terms
        except (json.JSONDecodeError, KeyError):
            return []
    
    async def _analyze_limitations_and_biases(
        self,
        content: ExtractedContent,
        executive_summary: str,
        detailed_analysis: str
    ) -> str:
        """Generate Type 2 thinking analysis: limitations, cognitive biases, and critical evaluation"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "limitations_analysis",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "methodological_limitations": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "cognitive_biases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "bias_name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "impact": {"type": "string"}
                                },
                                "required": ["bias_name", "description", "impact"],
                                "additionalProperties": False
                            }
                        },
                        "missing_perspectives": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "critical_evaluation": {"type": "string"}
                    },
                    "required": ["methodological_limitations", "cognitive_biases", "missing_perspectives", "critical_evaluation"],
                    "additionalProperties": False
                }
            }
        }
        
        prompt = f"""Perform a critical Type 2 thinking analysis of this content. Apply System 2 thinking (slow, deliberate, analytical) to identify limitations, cognitive biases, and potential blind spots.

CONTENT TITLE: {content.title}

EXECUTIVE SUMMARY:
{executive_summary[:1000]}

DETAILED ANALYSIS:
{detailed_analysis[:1500]}

ORIGINAL CONTENT PREVIEW:
{content.text[:3000]}

Analyze from the perspective of a top-tier management consultant who thinks critically about:
1. Methodological limitations (sample size, data quality, research design, generalizability)
2. Cognitive biases present in the content (confirmation bias, availability heuristic, survivorship bias, anchoring, framing effects, etc.)
3. Missing perspectives or alternative viewpoints
4. Critical evaluation of claims and evidence

For each cognitive bias identified, explain:
- The specific bias and how it manifests in the content
- The potential impact on the conclusions drawn
- How to mitigate or account for this bias

Provide a thoughtful, balanced critical analysis that would help decision-makers understand what to be cautious about."""
        
        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            
            limitations = data.get("methodological_limitations", [])
            biases = data.get("cognitive_biases", [])
            missing = data.get("missing_perspectives", [])
            evaluation = data.get("critical_evaluation", "")
            
            # Build HTML output instead of markdown
            result = ""
            
            if limitations:
                result += '<h3>Methodological Limitations</h3><ul>'
                for lim in limitations:
                    result += f'<li>{lim}</li>'
                result += '</ul>'
            
            if biases:
                result += '<h3>Cognitive Biases Identified</h3>'
                for bias in biases:
                    result += f'''<div class="bias-item">
                        <div class="bias-name">{bias['bias_name']}</div>
                        <div class="bias-description">{bias['description']}</div>
                        <div class="bias-impact"><strong>Impact:</strong> {bias['impact']}</div>
                    </div>'''
            
            if missing:
                result += '<h3>Missing Perspectives</h3><ul>'
                for persp in missing:
                    result += f'<li>{persp}</li>'
                result += '</ul>'
            
            if evaluation:
                result += f'<h3>Critical Evaluation</h3><p>{evaluation}</p>'
            
            return result
        except (json.JSONDecodeError, KeyError):
            return "<p>Critical analysis: Unable to parse limitations and biases analysis.</p>"

    async def _generate_linkedin_post(self, content: ExtractedContent, summary: str, takeaways: list[str]) -> str:
        """Generate a viral-style LinkedIn post based on the content"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "linkedin_post",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "post_text": {"type": "string"}
                    },
                    "required": ["post_text"],
                    "additionalProperties": False
                }
            }
        }

        takeaways_text = "\n".join([f"- {t}" for t in takeaways[:3]])
        
        prompt = f"""Write a compelling, viral-style LinkedIn post summarizing this content. 
        
CONTENT TITLE: {content.title}

SUMMARY:
{summary[:500]}

KEY TAKEAWAYS:
{takeaways_text}

Requirements:
- Hook: Start with a provocative question or statement to grab attention.
- Body: Concisely explain the 'Why this matters' and key insights. Use short paragraphs and plenty of white space.
- Structure: Use bullet points for the key takeaways.
- Tone: Professional yet engaging, thought-provoking, and suitable for a management consultant or thought leader.
- Call to Action: End with a question to encourage comments.
- Hashtags: Include 3-5 relevant hashtags at the bottom.
- Length: optimized for LinkedIn (around 150-200 words).

The output should be the raw text of the post, ready to copy-paste."""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            data = json.loads(response)
            return data.get("post_text", "")
        except (json.JSONDecodeError, KeyError):
            return response[:1000] if response else "Could not generate post."

    async def generate_linkedin_article_data(self, content: ExtractedContent) -> dict:
        """Generate a structured LinkedIn Article with a visual concept"""
        
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "linkedin_article",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "introduction": {"type": "string"},
                        "key_points": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "detail": {"type": "string"}
                                },
                                "required": ["title", "detail"],
                                "additionalProperties": False
                            }
                        },
                        "conclusion": {"type": "string"},
                        "call_to_action": {"type": "string"},
                        "visual_concept": {"type": "string"}
                    },
                    "required": ["headline", "introduction", "key_points", "conclusion", "call_to_action", "visual_concept"],
                    "additionalProperties": False
                }
            }
        }

        prompt = f"""Write a high-impact LinkedIn Article (Pulse style) based on this content.

CONTENT TITLE: {content.title}

CONTENT:
{content.text[:config.scraper.max_content_length]}

Requirements:
1. Headline: Catchy, professional, click-worthy.
2. Introduction: engaging hook, context, and thesis statement.
3. Key Points: Extract 3-5 deep insights. For each, provide a "Title" and a "Detail" paragraph (3-4 sentences) explaining the nuance.
4. Conclusion: Synthesize the insights.
5. Call to Action: Engagement prompt.
6. Visual Concept: Describe a single, unified visual metaphor that captures all these key points. This description will be used to generate a "whimsical watercolor" image. Make it artistic and symbolic.

Target Audience: Senior executives and industry leaders."""

        response = await self._call_venice_api(prompt, schema)
        
        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            # Fallback structure
            return {
                "headline": f"Insights from {content.title}",
                "introduction": "Unable to generate structured article.",
                "key_points": [],
                "conclusion": "",
                "call_to_action": "",
                "visual_concept": "Abstract business concept in watercolor"
            }
    
    def _enhance_image_prompt(self, visual_concept: str, section_title: str) -> str:
        """Enhance the visual concept into a proper image generation prompt"""
        return (
            f"Whimsical watercolor illustration: {visual_concept}. "
            f"Dreamy watercolor painting style with soft flowing colors and artistic brush strokes. "
            f"Ethereal and magical atmosphere, pastel color palette with gentle gradients. "
            f"Hand-painted aesthetic, playful and imaginative, organic shapes. "
            f"Theme: {section_title}. "
            f"Delicate watercolor washes, artistic and whimsical, no text overlays."
        )
    
    def _create_sections(self, text: str) -> list[dict]:
        """Create logical sections from continuous text"""
        # Split into roughly equal parts
        words = text.split()
        section_size = len(words) // 4  # Create ~4 sections
        
        sections = []
        section_titles = ["Overview", "Key Concepts", "Analysis", "Conclusions"]
        
        for i, title in enumerate(section_titles):
            start = i * section_size
            end = start + section_size if i < 3 else len(words)
            content = " ".join(words[start:end])
            sections.append({"title": title, "content": content, "level": 1})
        
        return sections
    
    async def _call_venice_api(
        self, 
        prompt: str, 
        response_format: Optional[dict] = None,
        max_retries: int = 3
    ) -> str:
        """Call Venice API with retry logic"""
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert analyst and summarizer. Provide clear, structured, insightful analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": config.venice.temperature,
            "max_completion_tokens": config.venice.max_tokens,
            "venice_parameters": {
                "include_venice_system_prompt": False,
                "strip_thinking_response": True
            }
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 429:
                        wait_time = 2 ** attempt
                        console.print(f"[yellow]Rate limited, waiting {wait_time}s...[/yellow]")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    return data["choices"][0]["message"]["content"]
                    
            except httpx.HTTPStatusError as e:
                console.print(f"[red]API Error: {e.response.status_code}[/red]")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                if attempt == max_retries - 1:
                    raise
        
        return ""


# Convenience function
async def summarize_content(content: ExtractedContent) -> StructuredSummary:
    """Convenience function to summarize content"""
    summarizer = VeniceSummarizer()
    return await summarizer.summarize(content)

