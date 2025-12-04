import asyncio
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# The Expert Rubric provided by the user
RUBRIC_PROMPT = """
You are an expert summarizer using a research-backed protocol to generate high-quality summaries.
Your goal is to create a "Visual Map Summary" text that can be visualized.

Follow these steps for your analysis (internal process):
1. Do a "10% Pass" - identify the macrostructure (Problem -> Causes -> Solutions).
2. Use the 4-Box Summary method (Main Idea, Key Points, Evidence, So What?).
3. Apply Progressive Compression (Sentence -> Paragraph -> Bullets).
4. Answer key questions: "What problem is this solving?", "What is the core claim?".
5. Apply the "Feynman Mini-Explainer" - explain it simply.

OUTPUT FORMAT:
Produce a structured summary suitable for an infographic. 
The output should be clear, concise, and broken down into these exact sections:

# TITLE: [Engaging Title]

## 🎯 CORE MESSAGE
[1-2 sentences capturing the main idea]

## 🔑 KEY POINTS
* [Point 1]
* [Point 2]
* [Point 3]
* [Point 4]
* [Point 5]

## 🧠 EVIDENCE & EXAMPLES
* [Key statistic, study, or example]
* [Key statistic, study, or example]

## 🚀 WHY IT MATTERS
* [Implication 1]
* [Implication 2]

## 🛠️ ACTIONABLE TAKEAWAY
[1 sentence on how to apply this]

Keep the tone engaging but professional.
"""

IMAGE_PROMPT_TEMPLATE = """
Create a prompt for an AI image generator to create a "Watercolor Whimsical Infographic" based on the following summary.
The image should be a visual summary of the content.

SUMMARY:
{summary}

STYLE REQUIREMENTS:
- Whimsical watercolor style
- Soft pastel washes
- Hand-drawn aesthetic
- Organic shapes
- Muted jewel tones (sage, dusty rose, soft gold, sky blue, lavender)
- Text should be minimal and legible if generated, but focus on visual metaphors.
- Layout: Central concept with branches or structured flow.

OUTPUT:
Provide ONLY the prompt text for the image generator.
"""

async def generate_rubric_summary(
    article_text: str, 
    model_id: str = "llama-3.3-70b",
    api_key: Optional[str] = None,
    base_url: str = "https://api.venice.ai/api/v1"
) -> str:
    """
    Generates a summary using the expert rubric.
    """
    llm = ChatOpenAI(
        model=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3
    )
    
    messages = [
        SystemMessage(content=RUBRIC_PROMPT),
        HumanMessage(content=f"Here is the article to summarize:\n\n{article_text[:15000]}")
    ]
    
    response = await llm.ainvoke(messages)
    return response.content

async def generate_image_prompt(
    summary_text: str,
    model_id: str = "llama-3.3-70b",
    api_key: Optional[str] = None,
    base_url: str = "https://api.venice.ai/api/v1"
) -> str:
    """
    Generates an image prompt based on the summary.
    """
    llm = ChatOpenAI(
        model=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=0.7
    )
    
    messages = [
        HumanMessage(content=IMAGE_PROMPT_TEMPLATE.format(summary=summary_text))
    ]
    
    response = await llm.ainvoke(messages)
    return response.content


