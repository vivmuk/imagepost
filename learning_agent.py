"""
Multi-Agent Learning System using LangGraph and Venice API
Orchestrates agents to create dyslexia-friendly learning content
"""
import asyncio
import json
from typing import List, TypedDict, Annotated, Union
import operator
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from rich.console import Console

from config import config
from image_generator import VeniceImageGenerator

console = Console()

# --- State Definition ---

class Chapter(TypedDict):
    title: str
    description: str
    content: str  # The written content
    image_prompt: str
    image_url: str  # Base64 data URL
    review_content: str  # Optional Smart Review content (stored in first chapter)

class LearningState(TypedDict):
    topic: str
    education_level: str  # e.g., "Elementary", "Middle School", "High School", "College", "Adult Learner"
    curriculum: List[Chapter]
    current_chapter_index: int
    final_report: str
    is_complete: bool

# --- Helper Functions ---

def strip_reasoning_tokens(content: str) -> str:
    """Strip reasoning/thinking tokens from model responses"""
    import re
    if not content:
        return content
    
    # Remove <thinking>...</thinking> blocks (including multiline)
    content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove <reasoning>...</reasoning> blocks (including multiline)
    content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove <think>...</think> blocks (including multiline)
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL | re.IGNORECASE)
    # Remove any standalone thinking/reasoning tags
    content = re.sub(r'</?thinking>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?reasoning>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?think>', '', content, flags=re.IGNORECASE)
    
    return content.strip()

# --- Agent Definitions ---

class LearningAgents:
    def __init__(self):
        self.api_key = config.venice.api_key
        self.base_url = config.venice.base_url
        
        # Initialize models - Venice parameters are not supported in LangChain's ChatOpenAI
        # The models will work without them, just with default Venice behavior
        self.reasoning_model = ChatOpenAI(
            model=config.venice.reasoning_model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=0.3
        )
        
        self.writer_model = ChatOpenAI(
            model=config.venice.summarization_model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=0.5
        )
        
        self.designer_model = ChatOpenAI(
            model=config.venice.extraction_model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            temperature=0.7
        )
        
        self.image_generator = VeniceImageGenerator()

    async def planner_agent(self, state: LearningState):
        """
        Agent 1: Planner (Reasoning Model)
        Creates a 3-chapter curriculum based on the topic.
        """
        topic = state["topic"]
        education_level = state.get("education_level", "High School")
        console.print(f"Planner Agent: Designing curriculum for '{topic}' at {education_level} level...")
        
        level_guidance = {
            "Elementary": "Use very simple language, lots of analogies, focus on basic concepts",
            "Middle School": "Use clear explanations, some technical terms with definitions, practical examples",
            "High School": "Use appropriate technical vocabulary, detailed explanations, real-world applications",
            "College": "Use precise terminology, in-depth analysis, academic rigor",
            "Adult Learner": "Use clear, practical language, focus on application and relevance"
        }
        
        guidance = level_guidance.get(education_level, level_guidance["High School"])
        
        system_prompt = f"""You are an expert curriculum designer specializing in Dyslexia and ADHD-friendly learning.
        Create a short, structured 3-chapter overview of the topic provided for {education_level} level learners.
        
        Education Level Guidance: {guidance}
        
        Structure:
        1. Preview (The Big Idea) - Introduction and overview
        2. Core Mechanics (How it works / The details) - Step-by-step explanation
        3. Application/Summary (Why it matters / Review) - Real-world connections and importance
        
        Return ONLY a JSON object with this structure:
        {{
            "chapters": [
                {{"title": "Chapter 1 Title", "description": "Brief description of what this chapter covers"}},
                {{"title": "Chapter 2 Title", "description": "..."}},
                {{"title": "Chapter 3 Title", "description": "..."}}
            ]
        }}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Create a curriculum for: {topic}")
        ]
        
        response = await self.reasoning_model.ainvoke(messages)
        content = strip_reasoning_tokens(response.content)
        
        try:
            # Clean markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Try to find JSON in the content if direct parsing fails
            if not content.strip().startswith("{"):
                # Look for JSON object in the text
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    content = json_match.group(0)
                else:
                    raise ValueError("No JSON object found in response")
                
            data = json.loads(content)
            chapters = []
            for ch in data.get("chapters", []):
                chapters.append({
                    "title": ch.get("title", "Chapter"),
                    "description": ch.get("description", ""),
                    "content": "",
                    "image_prompt": "",
                    "image_url": "",
                    "review_content": ""
                })
            
            if not chapters:
                raise ValueError("No chapters found in response")
            
            return {"curriculum": chapters, "current_chapter_index": 0}
        except Exception as e:
            console.print(f"Planner Error: {e}")
            console.print(f"Response content: {content[:200]}...")
            # Fallback curriculum based on topic
            return {
                "curriculum": [
                    {"title": f"Introduction to {topic}", "description": "Overview of the concept", "content": "", "image_prompt": "", "image_url": "", "review_content": ""},
                    {"title": f"Understanding {topic}", "description": "Core details and mechanics", "content": "", "image_prompt": "", "image_url": "", "review_content": ""},
                    {"title": f"Applying {topic}", "description": "Summary and practical application", "content": "", "image_prompt": "", "image_url": "", "review_content": ""}
                ],
                "current_chapter_index": 0
            }

    async def researcher_writer_agent(self, state: LearningState):
        """
        Agent 2 & 3: Researcher & Writer (Combined for efficiency)
        Researches and writes the content for the current chapter.
        """
        index = state["current_chapter_index"]
        chapters = state["curriculum"]
        current_chapter = chapters[index]
        topic = state["topic"]
        education_level = state.get("education_level", "High School")
        
        console.print(f"Writer Agent: Researching and writing '{current_chapter['title']}'...")
        
        level_guidance = {
            "Elementary": "Use very simple words, lots of analogies (like 'plants are like factories'), short sentences (5-8 words), focus on 'what' and 'why'",
            "Middle School": "Use clear explanations, define technical terms when first used, use examples from daily life, sentences can be 10-15 words",
            "High School": "Use appropriate technical vocabulary with brief definitions, detailed explanations, real-world applications, sentences 12-20 words",
            "College": "Use precise terminology, in-depth analysis, assume some background knowledge, sentences can be longer but still clear",
            "Adult Learner": "Use clear, practical language, focus on application and relevance, avoid unnecessary jargon, sentences 10-18 words"
        }
        
        guidance = level_guidance.get(education_level, level_guidance["High School"])
        
        system_prompt = f"""You are an expert educational content writer specializing in accessible, multi-sensory learning for people with Dyslexia and ADHD.
        
        Your goal: Write a short, engaging chapter for a lesson on the given topic at {education_level} level.
        
        Education Level Guidance: {guidance}
        
        Guidelines (MUST FOLLOW):
        1. **Big Idea**: Start with a 1-sentence summary of the chapter at the very beginning.
        2. **Chunking**: Keep paragraphs short (2-3 sentences). Use bullet points frequently.
        3. **Clear Language**: {guidance.split(',')[0]} - no jargon without definition.
        4. **Active Processing**: Include a "Think about this" prompt or a simple question for engagement.
        5. **Visual Structure**: Use <h3> headers for sections. Use <strong> for key terms.
        6. **Multi-sensory**: Describe what visuals would show (even though we can't embed them), mention hands-on activities.
        
        Output Format: Return strictly HTML body content (no <html> tags, just the inner content).
        """
        
        user_prompt = f"""
        Topic: {topic}
        Education Level: {education_level}
        Chapter Title: {current_chapter['title']}
        Chapter Description: {current_chapter['description']}
        
        Write the content for this chapter. Use web search to find the latest and most accurate information.
        Make it engaging, clear, and appropriate for {education_level} learners.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.writer_model.ainvoke(messages)
        
        # Strip reasoning tokens and update state
        chapters[index]["content"] = strip_reasoning_tokens(response.content)
        return {"curriculum": chapters}

    async def designer_agent(self, state: LearningState):
        """
        Agent 4: Graphic Designer
        Creates a detailed, instructional visual for the top of the chapter.
        """
        index = state["current_chapter_index"]
        chapters = state["curriculum"]
        current_chapter = chapters[index]
        topic = state["topic"]
        education_level = state.get("education_level", "High School")
        
        console.print(f"Designer Agent: Creating visual for '{current_chapter['title']}'...")
        
        # 1. Generate Detailed Instructional Prompt
        prompt_gen_msg = [
            SystemMessage(content="""You are a visual thinking expert specializing in educational illustrations. 
            Create a detailed, instructional image generation prompt that shows HOW the concept works, not just what it is.
            
            The image should be:
            - Detailed and instructional, showing processes, steps, or mechanisms
            - Educational and informative, like a diagram or illustration from a textbook
            - In whimsical watercolor style but still clear and explanatory
            - Include labels, arrows, or visual elements that explain the concept
            - Show the actual process or mechanism being discussed
            
            Return ONLY the image prompt text, nothing else."""),
            HumanMessage(content=f"""Topic: {topic}
            Education Level: {education_level}
            Chapter Title: {current_chapter['title']}
            Chapter Description: {current_chapter['description']}
            Chapter Content Summary: {current_chapter['content'][:800]}
            
            Create a detailed, instructional image prompt that illustrates HOW {current_chapter['title']} works.
            The image should be educational, showing the process, mechanism, or concept in detail.
            Use whimsical watercolor style but make it clear and informative like a scientific illustration.
            Include visual elements that help explain the concept (arrows, labels, steps, etc.).""")
        ]
        
        prompt_response = await self.designer_model.ainvoke(prompt_gen_msg)
        image_prompt = strip_reasoning_tokens(prompt_response.content)
        
        # Clean up the prompt if it has extra text
        if "prompt:" in image_prompt.lower():
            image_prompt = image_prompt.split("prompt:")[-1].strip()
        if image_prompt.startswith('"') and image_prompt.endswith('"'):
            image_prompt = image_prompt[1:-1]
        
        # 2. Generate Image
        image_obj = await self.image_generator.generate_image(
            prompt=image_prompt,
            section_title=current_chapter['title'],
            style="Watercolor Whimsical"
        )
        
        if image_obj:
            b64_img = self.image_generator.get_image_as_base64(image_obj)
            image_url = f"data:image/webp;base64,{b64_img}"
            chapters[index]["image_url"] = image_url
            chapters[index]["image_prompt"] = image_prompt
        
        return {"curriculum": chapters}

    async def iterator_node(self, state: LearningState):
        """Controls the loop through chapters"""
        next_index = state["current_chapter_index"] + 1
        if next_index < len(state["curriculum"]):
            return {"current_chapter_index": next_index}
        else:
            return {"is_complete": True}

    async def integrator_agent(self, state: LearningState):
        """
        Agent 5: Integrator
        Creates a Smart Review with key facts and questions.
        """
        console.print("Integrator Agent: Creating Smart Review...")
        topic = state["topic"]
        education_level = state.get("education_level", "High School")
        chapters = state["curriculum"]
        
        # Generate Smart Review content
        review_prompt = f"""Based on the following chapters about {topic}, create a Smart Review section with:
        
        1. Key Facts to Remember (3-5 bullet points of the most important facts)
        2. Questions to Ponder (3-4 thoughtful questions that help the learner reflect and apply what they learned)
        
        Education Level: {education_level}
        
        Chapters:
        {chr(10).join([f"- {ch['title']}: {ch['description']}" for ch in chapters])}
        
        Return the review in HTML format with:
        - <h3>Key Facts to Remember</h3> followed by a <ul> list
        - <h3>Questions to Ponder</h3> followed by a <ul> list of questions
        
        Make it concise, memorable, and appropriate for {education_level} level."""
        
        messages = [
            SystemMessage(content="You are an expert educational content creator. Create concise, memorable review content."),
            HumanMessage(content=review_prompt)
        ]
        
        response = await self.writer_model.ainvoke(messages)
        review_content = strip_reasoning_tokens(response.content)
        
        # Store review in the first chapter
        if chapters and review_content:
            if "review_content" not in chapters[0]:
                chapters[0]["review_content"] = ""
            chapters[0]["review_content"] = review_content
        
        return {"curriculum": chapters, "final_report": "Compiled"}

# --- Graph Construction ---

def build_learning_graph():
    agents = LearningAgents()
    
    workflow = StateGraph(LearningState)
    
    # Add nodes
    workflow.add_node("planner", agents.planner_agent)
    workflow.add_node("research_write", agents.researcher_writer_agent)
    workflow.add_node("designer", agents.designer_agent)
    workflow.add_node("iterator", agents.iterator_node)
    workflow.add_node("integrator", agents.integrator_agent)
    
    # Define edges
    workflow.set_entry_point("planner")
    
    workflow.add_edge("planner", "research_write")
    workflow.add_edge("research_write", "designer")
    workflow.add_edge("designer", "iterator")
    
    # Conditional edge from iterator
    def check_completion(state: LearningState):
        if state.get("is_complete"):
            return "integrator"
        return "research_write"
    
    workflow.add_conditional_edges(
        "iterator",
        check_completion,
        {
            "research_write": "research_write",
            "integrator": "integrator"
        }
    )
    
    workflow.add_edge("integrator", END)
    
    return workflow.compile()

# --- Convenience Function ---

async def generate_learning_path(topic: str, education_level: str = "High School"):
    """Run the learning graph for a topic"""
    graph = build_learning_graph()
    
    initial_state = LearningState(
        topic=topic,
        education_level=education_level,
        curriculum=[],
        current_chapter_index=0,
        final_report="",
        is_complete=False
    )
    
    final_state = await graph.ainvoke(initial_state)
    return final_state["curriculum"]


