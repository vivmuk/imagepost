
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

