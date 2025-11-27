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

class LearningState(TypedDict):
    topic: str
    curriculum: List[Chapter]
    current_chapter_index: int
    final_report: str
    is_complete: bool

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
        console.print(f"[bold blue]Planner Agent:[/bold blue] Designing curriculum for '{topic}'...")
        
        system_prompt = """You are an expert curriculum designer specializing in Dyslexia and ADHD-friendly learning.
        Create a short, structured 3-chapter overview of the topic provided.
        
        Structure:
        1. Preview (The Big Idea)
        2. Core Mechanics (How it works / The details)
        3. Application/Summary (Why it matters / Review)
        
        Return ONLY a JSON object with this structure:
        {
            "chapters": [
                {"title": "Chapter 1 Title", "description": "Brief description of what this chapter covers"},
                {"title": "Chapter 2 Title", "description": "..."},
                {"title": "Chapter 3 Title", "description": "..."}
            ]
        }
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Create a curriculum for: {topic}")
        ]
        
        response = await self.reasoning_model.ainvoke(messages)
        content = response.content
        
        try:
            # Clean markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            data = json.loads(content)
            chapters = []
            for ch in data.get("chapters", []):
                chapters.append({
                    "title": ch["title"],
                    "description": ch["description"],
                    "content": "",
                    "image_prompt": "",
                    "image_url": ""
                })
            
            return {"curriculum": chapters, "current_chapter_index": 0}
        except Exception as e:
            console.print(f"[red]Planner Error:[/red] {e}")
            # Fallback curriculum
            return {
                "curriculum": [
                    {"title": "Introduction", "description": "Overview of the concept", "content": "", "image_prompt": "", "image_url": ""},
                    {"title": "Key Concepts", "description": "Core details and mechanics", "content": "", "image_prompt": "", "image_url": ""},
                    {"title": "Conclusion", "description": "Summary and application", "content": "", "image_prompt": "", "image_url": ""}
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
        
        console.print(f"[bold green]Writer Agent:[/bold blue] Researching and writing '{current_chapter['title']}'...")
        
        system_prompt = """You are an expert educational content writer specializing in accessible, multi-sensory learning for people with Dyslexia and ADHD.
        
        Your goal: Write a short, engaging chapter for a lesson on the given topic.
        
        Guidelines (MUST FOLLOW):
        1. **Chunking**: Keep paragraphs short (2-3 sentences). Use bullet points frequently.
        2. **Clear Language**: Simple words, no jargon without definition.
        3. **Active Processing**: Include a "Think about this" prompt or a simple question.
        4. **Visual Structure**: Use <h3> headers for sections. Use <strong> for key terms.
        5. **Big Idea**: Start with a 1-sentence summary of the chapter.
        
        Output Format: Return strictly HTML body content (no <html> tags, just the inner content).
        """
        
        user_prompt = f"""
        Topic: {topic}
        Chapter Title: {current_chapter['title']}
        Chapter Description: {current_chapter['description']}
        
        Write the content for this chapter. 
        Enable web search to find the latest and most accurate information.
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.writer_model.ainvoke(messages)
        
        # Update state
        chapters[index]["content"] = response.content
        return {"curriculum": chapters}

    async def designer_agent(self, state: LearningState):
        """
        Agent 4: Graphic Designer
        Creates a visual for the top of the chapter.
        """
        index = state["current_chapter_index"]
        chapters = state["curriculum"]
        current_chapter = chapters[index]
        
        console.print(f"[bold magenta]Designer Agent:[/bold magenta] Creating visual for '{current_chapter['title']}'...")
        
        # 1. Generate Prompt
        prompt_gen_msg = [
            SystemMessage(content="You are a visual thinking expert. Create a specific image generation prompt for a header visual that summarizes this chapter concept. Use 'whimsical watercolor' style."),
            HumanMessage(content=f"Chapter: {current_chapter['title']}\nContent Summary: {current_chapter['content'][:500]}")
        ]
        
        prompt_response = await self.designer_model.ainvoke(prompt_gen_msg)
        image_prompt = prompt_response.content
        
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
        Compiles the final report.
        """
        console.print("[bold yellow]Integrator Agent:[/bold yellow] Compiling final report...")
        # In a real scenario, this might do more synthesis.
        # For now, the state 'curriculum' holds the compiled data.
        return {"final_report": "Compiled"}

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

async def generate_learning_path(topic: str):
    """Run the learning graph for a topic"""
    graph = build_learning_graph()
    
    initial_state = LearningState(
        topic=topic,
        curriculum=[],
        current_chapter_index=0,
        final_report="",
        is_complete=False
    )
    
    final_state = await graph.ainvoke(initial_state)
    return final_state["curriculum"]


