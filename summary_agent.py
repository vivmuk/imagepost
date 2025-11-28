"""
Multi-Agent Article Summary System using LangGraph

4-Agent Pipeline:
1. Reconnaissance Scanner - Quick orientation pass
2. Extraction Engine - Deep reading & evidence mapping  
3. Type 2 Challenger - Devil's advocate & bias detection
4. Synthesis Composer - Final summary generation

Venice API Models Used:
- Agent 1 (Scanner): qwen3-235b (fast, efficient)
- Agent 2 (Extractor): qwen3-235b (detailed extraction)
- Agent 3 (Challenger): qwen3-235b-a22b-thinking-2507 (reasoning/critical thinking)
- Agent 4 (Synthesizer): qwen3-235b (clean synthesis)
"""

import json
import re
import asyncio
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console

from config import config

console = Console()


# --- State Definition ---

class SummaryState(TypedDict):
    """State for the summary agent workflow"""
    article_text: str
    article_title: str
    article_url: str
    
    # Agent outputs
    recon_output: str           # Agent 1 output
    extraction_output: str      # Agent 2 output
    challenger_output: str      # Agent 3 output
    synthesis_output: str       # Agent 4 output
    
    # Final outputs
    final_summary: str
    confidence_score: int
    infographic_prompt: str
    infographic_url: str
    
    is_complete: bool


# --- Helper Functions ---

def strip_reasoning_tokens(content: str) -> str:
    """Strip reasoning/thinking tokens from model responses"""
    if not content:
        return content
    
    # Remove <thinking>...</thinking> blocks (including multiline)
    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove <reasoning>...</reasoning> blocks
    content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove <think>...</think> blocks
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove standalone tags
    content = re.sub(r'</?thinking>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?reasoning>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?think>', '', content, flags=re.IGNORECASE)
    
    return content.strip()


# --- Agent Definitions ---

class SummaryAgents:
    def __init__(self):
        self.api_key = config.venice.api_key
        self.base_url = config.venice.base_url
        
        # Agent 1 & 2 & 4: Fast summarization model (10000 token limit per agent)
        self.fast_model = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model="qwen3-235b",
            temperature=0.3,
            max_tokens=10000
        )
        
        # Agent 3: Reasoning model for critical thinking (10000 token limit)
        self.reasoning_model = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=config.venice.reasoning_model,
            temperature=0.4,
            max_tokens=10000
        )
    
    async def reconnaissance_scanner(self, state: SummaryState):
        """
        Agent 1: Reconnaissance Scanner
        Rapid 60-second orientation pass on the article.
        Model: qwen3-235b
        """
        article_text = state["article_text"]
        article_title = state.get("article_title", "Unknown")
        article_url = state.get("article_url", "")
        
        console.print("[bold blue]Agent 1: Reconnaissance Scanner[/bold blue] - Scanning article...")
        
        system_prompt = """You are a Reconnaissance Scanner. Your job is to perform a rapid 60-second orientation pass on an article before deep analysis begins.

Given the following article, extract ONLY these metadata elements:

## SCAN OUTPUT FORMAT

**Source Profile:**
- Publication: [Name and type: mainstream news, trade publication, blog, advocacy org, etc.]
- Author: [Name + brief identifier if discoverable]
- Date: [Publication date + note if outdated >6 months]
- URL credibility signals: [Domain reputation, HTTPS, known outlet]

**Structural Skeleton:**
- Headline: [Exact headline]
- Subheadings: [List all section headers]
- Opening thesis: [First paragraph's main claim in one sentence]
- Closing position: [Final paragraph's conclusion in one sentence]

**Visual/Emphasis Signals:**
- Pull quotes: [Any highlighted quotes]
- Images/graphics: [What visuals are used and what do they emphasize]
- Bold/highlighted text: [Key emphasized phrases]

**Initial Intent Assessment:**
- Article type: [News report / Opinion / Analysis / Advocacy / Sponsored content]
- Apparent purpose: [Inform / Persuade / Sell / Entertain / Alarm]
- Target audience: [Who is this written for]

**Red Flags (if any):**
- [Note any immediate credibility concerns: clickbait headline, emotional language, missing date, anonymous author, etc.]

Be concise but thorough. Do not include any thinking or reasoning tokens in your output."""
        
        user_prompt = f"""ARTICLE TITLE: {article_title}
ARTICLE URL: {article_url}

ARTICLE TO SCAN:
{article_text[:12000]}"""  # Limit to prevent token overflow
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.fast_model.ainvoke(messages)
        recon_output = strip_reasoning_tokens(response.content)
        
        console.print("[green]✓ Reconnaissance scan complete[/green]")
        
        return {"recon_output": recon_output}
    
    async def extraction_engine(self, state: SummaryState):
        """
        Agent 2: Extraction Engine
        Deep reading pass to extract KEY POINTS and map argument structure.
        Model: qwen3-235b
        """
        article_text = state["article_text"]
        recon_output = state["recon_output"]
        
        console.print("[bold blue]Agent 2: Extraction Engine[/bold blue] - Deep analysis...")
        
        system_prompt = """You are an Extraction Engine. Your job is to perform deep analytical reading of an article and extract ALL KEY POINTS before mapping the argument structure.

You will receive an article and the Reconnaissance Scanner's output. Perform a thorough extraction of the following elements:

## EXTRACTION OUTPUT FORMAT

**ARTICLE KEY POINTS SUMMARY:**
[First, provide a comprehensive summary of ALL the main points in the article. List every significant fact, finding, claim, and piece of information. This section should allow someone to understand the full content without reading the original article.]

1. [Key Point 1 - most important finding/claim]
2. [Key Point 2]
3. [Key Point 3]
4. [Key Point 4]
5. [Key Point 5]
6. [Key Point 6]
7. [Key Point 7]
8. [Key Point 8]
9. [Key Point 9]
10. [Key Point 10]
[Continue for ALL significant points in the article - be comprehensive]

---

**Core Claim:**
[The single central argument in one sentence. This is what you'd text a friend to summarize the piece.]

**Argument Structure:**
1. [First supporting point]
   - Evidence provided: [Specific data, quote, or example]
   - Evidence quality: [Primary source / Secondary source / Anecdotal / Unsourced assertion]

2. [Second supporting point]
   - Evidence provided: 
   - Evidence quality: 

3. [Third supporting point]
   - Evidence provided: 
   - Evidence quality: 

[Continue for all major points, up to 5]

**Sources Cited:**
| Source | Type | How Used | Verifiable? |
|--------|------|----------|-------------|
| [e.g., "CDC study"] | [Primary/Secondary/Expert quote] | [Supporting which claim] | [Yes/No/Partially] |

**Assumptions (Unstated):**
- [What does the author take for granted that a skeptic might not accept?]
- [What logical leaps exist between evidence and conclusion?]

**Counterarguments:**
- Addressed by author: [What opposing views does the article acknowledge?]
- Quality of engagement: [Dismissed / Strawmanned / Fairly represented / Strongly rebutted]
- Unaddressed: [What obvious objections are ignored?]

**Stakes & Implications:**
- Explicit: [What does the author say matters about this?]
- Implicit: [What larger implications are suggested but not stated?]

**Emotional Techniques:**
- [List any appeals to fear, outrage, tribalism, urgency, or other emotional levers]
- [Note loaded language or framing choices]

IMPORTANT: The KEY POINTS SUMMARY section must be comprehensive and capture ALL important information from the article. Be thorough and objective. Do not include any thinking or reasoning tokens in your output."""
        
        user_prompt = f"""RECONNAISSANCE SCAN:
{recon_output}

ARTICLE TO ANALYZE:
{article_text[:12000]}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.fast_model.ainvoke(messages)
        extraction_output = strip_reasoning_tokens(response.content)
        
        console.print("[green]✓ Extraction analysis complete[/green]")
        
        return {"extraction_output": extraction_output}
    
    async def type2_challenger(self, state: SummaryState):
        """
        Agent 3: Type 2 Challenger
        Devil's advocate analysis - challenge the article and reactions to it.
        Model: qwen3-235b-a22b-thinking-2507 (reasoning model)
        """
        article_text = state["article_text"]
        recon_output = state["recon_output"]
        extraction_output = state["extraction_output"]
        
        console.print("[bold blue]Agent 3: Type 2 Challenger[/bold blue] - Critical analysis...")
        
        system_prompt = """You are a Type 2 Challenger. Your role is to activate slow, deliberate, critical thinking about an article that has already been scanned and extracted.

You embody the skeptical, disconfirming mindset of a Type 2 thinker. Your job is NOT to debunk, but to stress-test. You are looking for what might be wrong, missing, or manipulative—while remaining fair.

## CHALLENGE OUTPUT FORMAT

**Steelman Opposition:**
[Write the strongest possible 2-3 sentence argument AGAINST this article's thesis. Argue as if you were a thoughtful, informed critic.]

**Disconfirmation Test:**
- What evidence would need to exist to prove this article wrong?
- Does such evidence exist? [Search your knowledge or note if verification needed]
- Has the author addressed this evidence? [Yes / No / Partially]

**Bias Detection:**
*Author/Source Bias:*
- Does the publication have a known ideological leaning?
- Does the author have disclosed or undisclosed conflicts of interest?
- Who benefits if readers believe this article?

*Cognitive Bias Triggers (for readers):*
- Confirmation bias: [Would this article be shared approvingly by a particular ideological group? Which one?]
- Availability heuristic: [Does it rely on vivid examples over statistical reality?]
- Authority bias: [Does it lean heavily on credentials rather than evidence?]
- Anchoring: [Does it establish a frame that makes alternatives seem unreasonable?]

**Missing Perspectives:**
- Who is NOT quoted or represented who has relevant expertise or stake?
- What alternative explanations for the same evidence are not considered?

**Manipulation Check:**
| Technique | Present? | Example |
|-----------|----------|---------|
| False urgency | [Yes/No] | [Example if yes] |
| Fear appeal | [Yes/No] | |
| Tribal signaling (us vs. them) | [Yes/No] | |
| Cherry-picked data | [Yes/No] | |
| Anecdote over data | [Yes/No] | |
| Strawman of opposition | [Yes/No] | |
| Appeal to emotion over logic | [Yes/No] | |

**Confidence Calibration:**
On a scale of 1-10, how confident should a careful reader be in this article's central claim?
- Score: [X/10]
- Reasoning: [2-3 sentences explaining the rating]

**What Would Change Your Mind:**
[If you were inclined to believe this article, what single piece of evidence or argument should make you reconsider?]

Be rigorous but fair. Output your analysis directly without thinking tokens."""
        
        user_prompt = f"""RECONNAISSANCE SCAN:
{recon_output}

EXTRACTION ANALYSIS:
{extraction_output}

ARTICLE:
{article_text[:10000]}"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.reasoning_model.ainvoke(messages)
        challenger_output = strip_reasoning_tokens(response.content)
        
        # Extract confidence score
        confidence_score = 5  # Default
        score_match = re.search(r'Score:\s*(\d+)/10', challenger_output)
        if score_match:
            confidence_score = int(score_match.group(1))
        
        console.print(f"[green]✓ Type 2 challenge complete (Confidence: {confidence_score}/10)[/green]")
        
        return {"challenger_output": challenger_output, "confidence_score": confidence_score}
    
    async def synthesis_composer(self, state: SummaryState):
        """
        Agent 4: Synthesis Composer
        Integrate all analyses into a final, balanced, comprehensive summary.
        Model: qwen3-235b
        """
        article_text = state["article_text"]
        article_title = state.get("article_title", "Unknown")
        recon_output = state["recon_output"]
        extraction_output = state["extraction_output"]
        challenger_output = state["challenger_output"]
        confidence_score = state.get("confidence_score", 5)
        
        console.print("[bold blue]Agent 4: Synthesis Composer[/bold blue] - Composing final summary...")
        
        system_prompt = """You are a Synthesis Composer. You receive the outputs from three prior agents (Reconnaissance Scanner, Extraction Engine, Type 2 Challenger) and compose a final comprehensive summary.

IMPORTANT: Start with ALL KEY POINTS from the article before providing analysis. The reader should understand the full article content first.

Your summary must be:
- Comprehensive (captures ALL key points from the article)
- Balanced (acknowledges both strengths and weaknesses)
- Actionable (reader knows what to think and what to investigate further)

## FINAL SUMMARY OUTPUT FORMAT

### 📰 Article Overview
**Title:** [Headline]
**Source:** [Publication] | **Author:** [Name] | **Date:** [Date]
**Article Type:** [News/Opinion/Analysis/Advocacy]

---

### 📋 Complete Article Summary
[Provide a comprehensive summary of ALL the key points from the article. This should be detailed enough that someone can understand the full article without reading the original. Include all significant facts, findings, statistics, and claims.]

**Key Points:**
1. [Most important finding/claim]
2. [Second key point]
3. [Third key point]
4. [Fourth key point]
5. [Fifth key point]
[Continue for all major points - be thorough]

---

### 🎯 Core Claim
[One sentence capturing the central argument]

---

### 📊 Evidence Summary
**Strongest evidence:**
- [Most compelling supporting point with source quality noted]

**Weakest evidence:**
- [Least supported claim or logical leap]

---

### ⚖️ Critical Assessment
**What the article gets right:**
- [1-2 genuine strengths]

**What the article gets wrong or overstates:**
- [1-2 legitimate weaknesses]

**What's missing:**
- [Key perspective, evidence, or counterargument not addressed]

---

### 🧠 Reader Awareness Notes
**This article may appeal to readers who:** [Profile]
**Readers should be skeptical if they:** [Warning signs of uncritical acceptance]
**Confidence rating:** [X/10] — [One sentence justification]

---

### 📝 SCER Summary
> **Source:** [Publication, author, date, type]
> **Claim:** [One sentence thesis]
> **Evidence:** [2-3 key proof points with quality assessment]
> **Reservations:** [Key weaknesses, biases, or gaps]

---

### 🔍 Suggested Verification Steps
1. [Specific fact or claim worth independently verifying]
2. [Source to consult for opposing view]
3. [Question to research further]

Output only the final summary. Do not include any thinking tokens."""
        
        user_prompt = f"""RECONNAISSANCE SCAN:
{recon_output}

EXTRACTION ANALYSIS:
{extraction_output}

TYPE 2 CHALLENGE:
{challenger_output}

ARTICLE TITLE: {article_title}

Compose the final synthesis summary."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.fast_model.ainvoke(messages)
        synthesis_output = strip_reasoning_tokens(response.content)
        
        console.print("[green]✓ Synthesis complete[/green]")
        
        # Extract key points from extraction output for infographic
        key_points_section = ""
        if "KEY POINTS SUMMARY" in extraction_output:
            # Extract the key points section
            key_points_match = re.search(r'\*\*ARTICLE KEY POINTS SUMMARY:\*\*(.*?)(?=\*\*Core Claim|\*\*---|\Z)', extraction_output, re.DOTALL)
            if key_points_match:
                key_points_section = key_points_match.group(1).strip()
        
        # Generate infographic prompt focusing on ARTICLE CONTENT
        infographic_prompt = f"""Create a comprehensive watercolor-style infographic that SUMMARIZES THE ENTIRE ARTICLE CONTENT.

ARTICLE TITLE: {article_title}

PRIMARY FOCUS (80% of the infographic): THE ARTICLE'S KEY POINTS AND CONTENT
The main purpose of this infographic is to help someone understand the FULL ARTICLE without reading it.

KEY POINTS TO VISUALIZE:
{key_points_section if key_points_section else extraction_output[:2000]}

SECONDARY FOCUS (20% of the infographic): Small analysis section
- Confidence Score: {confidence_score}/10
- Brief note on source credibility

VISUAL STYLE:
- Soft pastel watercolor washes with hand-drawn aesthetic
- Clear, readable text for each key point
- Icons or small illustrations for each main concept
- Organized layout with clear visual hierarchy
- Main content area with key findings prominently displayed
- Small corner section for the {confidence_score}/10 confidence rating
- Muted jewel tones: sage green, dusty rose, soft gold, sky blue, lavender
- Clean and professional but with artistic watercolor touches

LAYOUT REQUIREMENTS:
- Title at the top: "{article_title}"
- Main body: ALL key points from the article with visual representations
- Each key point should have a small icon or visual element
- Use numbered bullets or visual flow to show information hierarchy
- Bottom corner: Small confidence gauge showing {confidence_score}/10

The infographic should allow a reader to understand the ENTIRE article's content at a glance. The critical analysis is secondary."""
        
        return {
            "synthesis_output": synthesis_output,
            "final_summary": synthesis_output,
            "infographic_prompt": infographic_prompt,
            "is_complete": True
        }


# --- Graph Construction ---

def build_summary_graph():
    """Build the LangGraph workflow for article summarization"""
    agents = SummaryAgents()
    
    workflow = StateGraph(SummaryState)
    
    # Add nodes
    workflow.add_node("reconnaissance", agents.reconnaissance_scanner)
    workflow.add_node("extraction", agents.extraction_engine)
    workflow.add_node("challenger", agents.type2_challenger)
    workflow.add_node("synthesis", agents.synthesis_composer)
    
    # Define edges (linear flow)
    workflow.set_entry_point("reconnaissance")
    workflow.add_edge("reconnaissance", "extraction")
    workflow.add_edge("extraction", "challenger")
    workflow.add_edge("challenger", "synthesis")
    workflow.add_edge("synthesis", END)
    
    return workflow.compile()


# --- Convenience Function ---

async def analyze_article(article_text: str, article_title: str = "", article_url: str = "") -> dict:
    """
    Run the full 4-agent analysis pipeline on an article.
    
    Returns a dict with all agent outputs and final summary.
    """
    graph = build_summary_graph()
    
    initial_state = SummaryState(
        article_text=article_text,
        article_title=article_title or "Untitled Article",
        article_url=article_url or "",
        recon_output="",
        extraction_output="",
        challenger_output="",
        synthesis_output="",
        final_summary="",
        confidence_score=5,
        infographic_prompt="",
        infographic_url="",
        is_complete=False
    )
    
    final_state = await graph.ainvoke(initial_state)
    
    return {
        "title": article_title,
        "url": article_url,
        "recon_output": final_state["recon_output"],
        "extraction_output": final_state["extraction_output"],
        "challenger_output": final_state["challenger_output"],
        "synthesis_output": final_state["synthesis_output"],
        "final_summary": final_state["final_summary"],
        "confidence_score": final_state["confidence_score"],
        "infographic_prompt": final_state["infographic_prompt"]
    }

