"""
Image Generation Module using Venice API with Qwen Image
Generates infographics and visual representations for report sections
"""
import asyncio
import base64
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import httpx
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn

from config import config
from summarizer import SectionSummary, StructuredSummary

console = Console()


@dataclass
class GeneratedImage:
    """Container for generated image data"""
    section_title: str
    prompt: str
    image_data: bytes  # Raw image bytes
    format: str
    filename: str


class VeniceImageGenerator:
    """Generates images using Venice API with Qwen Image model"""
    
    def __init__(self):
        self.api_key = config.venice.api_key
        self.base_url = config.venice.base_url
        self.model = config.venice.image_model  # qwen-image
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.width = config.report.image_width
        self.height = config.report.image_height
    
    async def generate_images_for_summary(
        self, 
        summary: StructuredSummary,
        output_dir: Optional[Path] = None
    ) -> list[GeneratedImage]:
        """Generate images for all sections in the summary"""
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"\n[bold magenta]Generating images for {len(summary.sections)} sections[/bold magenta]")
        
        images = []
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Generating images...", total=len(summary.sections))
            
            for i, section in enumerate(summary.sections):
                try:
                    image = await self.generate_image(
                        prompt=section.image_prompt,
                        section_title=section.title,
                        index=i
                    )
                    
                    if image and output_dir:
                        # Save to disk
                        filepath = output_dir / image.filename
                        filepath.write_bytes(image.image_data)
                        console.print(f"  [green]✓[/green] Saved: {image.filename}")
                    
                    if image:
                        images.append(image)
                    
                except Exception as e:
                    console.print(f"  [red]✗[/red] Failed for '{section.title}': {e}")
                
                progress.update(task, advance=1)
                
                # Small delay between requests to avoid rate limiting
                if i < len(summary.sections) - 1:
                    await asyncio.sleep(1)
        
        console.print(f"\n[green]Generated {len(images)} images successfully[/green]")
        return images
    
    async def generate_image(
        self,
        prompt: str,
        section_title: str = "section",
        index: int = 0,
        style: Optional[str] = None
    ) -> Optional[GeneratedImage]:
        """Generate a single image using Venice API"""
        
        # Clean the section title for filename
        safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in section_title)
        safe_title = safe_title.replace(' ', '_').lower()[:30]
        filename = f"img_{index:02d}_{safe_title}.webp"
        
        # Enhance prompt for better infographic generation
        enhanced_prompt = self._enhance_prompt(prompt, style or config.report.image_style)
        
        payload = {
            "model": self.model,
            "prompt": enhanced_prompt,
            "width": self.width,
            "height": self.height,
            # "steps": 20,  # Let the API use the model's default
            "format": "webp",
            "safe_mode": True,
            "hide_watermark": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/image/generate",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 429:
                    console.print("[yellow]Rate limited, waiting...[/yellow]")
                    await asyncio.sleep(5)
                    # Retry once
                    response = await client.post(
                        f"{self.base_url}/image/generate",
                        headers=self.headers,
                        json=payload
                    )
                
                response.raise_for_status()
                data = response.json()
                
                # Venice returns base64 encoded images in the 'images' array
                if "images" in data and data["images"]:
                    image_b64 = data["images"][0]
                    image_bytes = base64.b64decode(image_b64)
                    
                    return GeneratedImage(
                        section_title=section_title,
                        prompt=enhanced_prompt,
                        image_data=image_bytes,
                        format="webp",
                        filename=filename
                    )
                
        except httpx.HTTPStatusError as e:
            console.print(f"[red]HTTP Error {e.response.status_code}: {e.response.text[:200]}[/red]")
        except Exception as e:
            console.print(f"[red]Error generating image: {e}[/red]")
        
        return None
    
    async def generate_hero_image(
        self, 
        title: str, 
        summary: str,
        output_dir: Optional[Path] = None
    ) -> Optional[GeneratedImage]:
        """Generate a hero/banner image for the report"""
        
        # Create a prompt that represents the overall theme in watercolor whimsical style
        prompt = (
            f"Whimsical watercolor hero banner illustration representing: {title}. "
            f"Dreamy watercolor painting with soft flowing colors and artistic brush strokes. "
            f"Ethereal and magical atmosphere, pastel color palette with gentle gradients. "
            f"Hand-painted aesthetic, playful and imaginative, organic flowing shapes. "
            f"Conceptual visualization of: {summary[:200]}. "
            f"Wide format, artistic watercolor style, high quality, no text."
        )
        
        # Use wider dimensions for hero
        original_height = self.height
        self.height = int(self.width * 0.5)  # 2:1 aspect ratio
        
        image = await self.generate_image(
            prompt=prompt,
            section_title="hero_banner",
            index=0
        )
        
        self.height = original_height
        
        if image and output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            filepath = output_dir / "hero_banner.webp"
            filepath.write_bytes(image.image_data)
            image.filename = "hero_banner.webp"
        
        return image
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Enhance prompt with style and quality keywords"""
        
        style_modifiers = {
            "Watercolor Whimsical": (
                "watercolor painting style, whimsical and dreamy, soft flowing colors, "
                "artistic brush strokes, ethereal and magical atmosphere, "
                "pastel color palette with gentle gradients, hand-painted aesthetic, "
                "playful and imaginative, organic shapes and forms, "
                "delicate watercolor washes, artistic illustration"
            ),
            "Infographic": (
                "infographic style, data visualization, clean modern design, "
                "icons and symbols, professional business graphics"
            ),
            "Cinematic": (
                "cinematic composition, dramatic lighting, movie poster style, "
                "atmospheric, professional photography look"
            ),
            "Digital Art": (
                "digital art, vibrant colors, creative illustration, "
                "modern artistic style, detailed rendering"
            ),
            "Minimalist": (
                "minimalist design, simple shapes, clean lines, "
                "limited color palette, elegant and sophisticated"
            ),
            "Photographic": (
                "photorealistic, high quality photography style, "
                "professional lighting, sharp details"
            ),
            "3D Model": (
                "3D rendered, isometric view, modern 3D graphics, "
                "clean materials, professional product visualization"
            )
        }
        
        modifier = style_modifiers.get(style, style_modifiers["Watercolor Whimsical"])
        
        return f"{prompt}. Style: {modifier}. High quality, detailed, artistic."
    
    def get_image_as_base64(self, image: GeneratedImage) -> str:
        """Convert image to base64 string for embedding in HTML"""
        return base64.b64encode(image.image_data).decode('utf-8')


# Convenience functions
async def generate_report_images(
    summary: StructuredSummary,
    output_dir: Optional[str] = None
) -> list[GeneratedImage]:
    """Generate all images for a report"""
    generator = VeniceImageGenerator()
    path = Path(output_dir) if output_dir else None
    return await generator.generate_images_for_summary(summary, path)


async def generate_single_image(prompt: str, filename: str = "output.webp") -> Optional[bytes]:
    """Generate a single image from a prompt"""
    generator = VeniceImageGenerator()
    image = await generator.generate_image(prompt, filename.replace('.webp', ''))
    return image.image_data if image else None

