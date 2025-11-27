# AI Prompts Documentation

This document contains all the prompts used in the Image Report generation system.

---

## System Configuration

- **Summarization Model**: `qwen3-235b` (Venice Large)
- **Image Model**: `nano-banana-pro`
- **Temperature**: `0.3` (lower for focused summaries)
- **Max Tokens**: `4096`
- **Venice Parameters**: 
  - `include_venice_system_prompt: False`
  - `strip_thinking_response: True`

---

## 1. System Prompt

**Location**: `summarizer.py` line 673-674  
**Used For**: All API calls to Venice API

```
You are an expert analyst and summarizer. Provide clear, structured, insightful analysis.
```

---

## 2. Key Takeaways Extraction

**Location**: `summarizer.py` lines 161-169  
**Purpose**: Extract 5-7 key takeaways from content  
**Output Format**: JSON schema with `takeaways` array containing `point` and `importance`

```
Analyze the following content and extract 5-7 key takeaways.
Each takeaway should be a concise, actionable insight that captures the most important points.

CONTENT TITLE: {content.title}

CONTENT:
{content.text[:12000]}

Extract the most critical insights, findings, or lessons from this content.
```

---

## 3. Section Summaries with Image Prompts

**Location**: `summarizer.py` lines 231-245  
**Purpose**: Generate summaries for each section with visual concepts  
**Output Format**: JSON schema with `sections` array containing `title`, `summary`, `key_points`, and `visual_concept`

```
Analyze these content sections and provide structured summaries.

DOCUMENT TITLE: {content.title}

KEY THEMES: {', '.join(key_takeaways[:3])}

SECTIONS:
{sections_text}

For each section:
1. Create a clear, descriptive title
2. Write a 2-3 sentence summary
3. List 2-3 key points
4. Describe a visual concept for an infographic that would represent this section's main idea 
   (be specific about imagery, metaphors, and visual elements - this will be used to generate an image)
```

---

## 4. Executive Summary and Detailed Analysis

**Location**: `summarizer.py` lines 303-319  
**Purpose**: Generate executive summary and detailed analysis with recommendations  
**Output Format**: JSON schema with `executive_summary`, `detailed_analysis`, and `recommendations` array

```
Create an executive summary and detailed analysis for this content.

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
3. 3-5 actionable recommendations based on the content
```

---

## 5. Key Terms Extraction

**Location**: `summarizer.py` lines 368-386  
**Purpose**: Extract key terms, technical vocabulary, and definitions  
**Output Format**: JSON schema with `terms` array containing `term`, `definition`, and `context`

```
Extract 5-10 key terms, technical vocabulary, acronyms, or important concepts from this content that readers should understand.

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

Provide definitions that a management consultant or executive could quickly reference.
```

---

## 6. Limitations and Biases Analysis (Type 2 Thinking)

**Location**: `summarizer.py` lines 448-472  
**Purpose**: Critical analysis of limitations, cognitive biases, and blind spots  
**Output Format**: JSON schema with `methodological_limitations`, `cognitive_biases`, `missing_perspectives`, and `critical_evaluation`

```
Perform a critical Type 2 thinking analysis of this content. Apply System 2 thinking (slow, deliberate, analytical) to identify limitations, cognitive biases, and potential blind spots.

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

Provide a thoughtful, balanced critical analysis that would help decision-makers understand what to be cautious about.
```

---

## 7. LinkedIn Post (For Executive Report)

**Location**: `summarizer.py` lines 536-555  
**Purpose**: Generate a viral-style LinkedIn post for the executive report  
**Output Format**: JSON schema with `post_text` string

```
Write a compelling, viral-style LinkedIn post summarizing this content. 
        
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

The output should be the raw text of the post, ready to copy-paste.
```

---

## 8. LinkedIn Article/Post (Separate Pipeline)

**Location**: `summarizer.py` lines 600-616  
**Purpose**: Generate a high-impact LinkedIn post (long-form status update)  
**Output Format**: JSON schema with `headline`, `introduction`, `key_points`, `conclusion`, `call_to_action`, and `visual_concept`

```
Write a high-impact, viral LinkedIn Post (long-form status update) based on this content. Do NOT write a blog article; write a social media post.

CONTENT TITLE: {content.title}

CONTENT:
{content.text[:config.scraper.max_content_length]}

Requirements:
1. Headline: A catchy first line/hook for the post (this will be the bold opening).
2. Introduction: The setup and context (keep it punchy and engaging).
3. Key Points: Extract 3-5 deep insights. For each, provide a "Title" (as a bold header) and a "Detail" (short, insightful explanation).
4. Conclusion: A powerful closing thought.
5. Call to Action: A question to drive engagement in comments.
6. Visual Concept: Describe a single, unified visual metaphor that captures all these key points. This description will be used to generate a "whimsical watercolor" image. Make it artistic and symbolic.

Style: Use emojis, short paragraphs, extra whitespace, and conversational tone suitable for a thought leader.
Target Audience: Senior executives and industry leaders.
```

---

## 9. Image Generation Prompts

### 9.1 Hero Image Prompt

**Location**: `image_generator.py` lines 174-181  
**Purpose**: Generate hero/banner image for reports

```
Whimsical watercolor hero banner illustration representing: {title}. 
Dreamy watercolor painting with soft flowing colors and artistic brush strokes. 
Ethereal and magical atmosphere, pastel color palette with gentle gradients. 
Hand-painted aesthetic, playful and imaginative, organic flowing shapes. 
Conceptual visualization of: {summary[:200]}. 
Wide format, artistic watercolor style, high quality, no text.
```

### 9.2 Section Image Prompt Enhancement

**Location**: `summarizer.py` lines 633-642  
**Purpose**: Enhance visual concepts into image generation prompts

```
Whimsical watercolor illustration: {visual_concept}. 
Dreamy watercolor painting style with soft flowing colors and artistic brush strokes. 
Ethereal and magical atmosphere, pastel color palette with gentle gradients. 
Hand-painted aesthetic, playful and imaginative, organic shapes. 
Theme: {section_title}. 
Delicate watercolor washes, artistic and whimsical, no text overlays.
```

### 9.3 Image Style Modifiers

**Location**: `image_generator.py` lines 207-214  
**Purpose**: Style enhancement for "Watercolor Whimsical" images

```
watercolor painting style, whimsical and dreamy, soft flowing colors, 
artistic brush strokes, ethereal and magical atmosphere, 
pastel color palette with gentle gradients, hand-painted aesthetic, 
playful and imaginative, organic shapes and forms, 
delicate watercolor washes, artistic illustration
```

**Additional Style Options Available**:
- Infographic
- Cinematic
- Digital Art
- Minimalist
- Photographic
- 3D Model

---

## Prompt Engineering Notes

### Content Truncation Limits
- Key Takeaways: First 12,000 characters
- Executive Summary: First 4,000 characters
- Limitations Analysis: Executive summary (1,000 chars), Detailed analysis (1,500 chars), Original content (3,000 chars)
- LinkedIn Post (Executive): Summary (500 chars), Top 3 takeaways
- LinkedIn Article: Full content up to `max_content_length` (100,000 chars)
- Key Terms: Full content up to `max_content_length`

### Structured Response Format
All prompts use Venice API's `response_format` with `json_schema` to ensure consistent, parseable JSON output. Each schema includes:
- `strict: True` - Enforces exact schema compliance
- `additionalProperties: False` - Prevents extra fields
- Required fields explicitly marked

### Error Handling
- All prompts have fallback error handling for JSON parsing failures
- Graceful degradation to raw text responses when structured parsing fails
- Error messages logged but don't crash the pipeline

---

## Usage Flow

1. **Content Input** → Scraper extracts content
2. **Key Takeaways** → Extract main insights
3. **Section Summaries** → Analyze sections with visual concepts
4. **Executive Summary** → Generate high-level overview
5. **Key Terms** → Extract technical vocabulary
6. **Limitations Analysis** → Critical Type 2 thinking evaluation
7. **LinkedIn Post** → Generate social media content
8. **Image Generation** → Create visuals using enhanced prompts

---

*Last Updated: Based on current codebase as of latest commit*

