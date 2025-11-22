import os
import logging
import json
import base64
from typing import Dict, Any, List, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get_model_config(self, model: str) -> tuple:
        """Map model ID to provider and model name"""
        model_map = {
            "claude-sonnet-4": ("anthropic", "claude-4-sonnet-20250514"),
            "gpt-5": ("openai", "gpt-5"),
            "gpt-5-mini": ("openai", "gpt-5-mini"),
            "gemini-2.5-pro": ("gemini", "gemini-2.5-pro")
        }
        return model_map.get(model, ("anthropic", "claude-4-sonnet-20250514"))

    async def generate_response(self, prompt: str, model: str, session_id: str) -> Dict[str, Any]:
        """
        Generate AI response for user prompt
        """
        provider, model_name = self._get_model_config(model)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message="You are Code Weaver, an expert AI assistant that helps users create professional websites. You understand web design, modern frameworks, and can generate clean, production-ready code. Always be helpful, creative, and provide clear explanations."
            )
            chat.with_model(provider, model_name)
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            return {
                "content": response,
                "website_data": None,
                "image_urls": None
            }
        except Exception as e:
            logger.error(f"AI response generation failed: {str(e)}")
            return {
                "content": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "website_data": None,
                "image_urls": None
            }

    async def generate_website(self, prompt: str, model: str, framework: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        Multi-agent website generation process:
        1. Requirement Planner Agent - Creates structured plan
        2. Code Generation Agent - Generates actual code
        3. Design & Styling Agent - Creates visual assets
        """
        provider, model_name = self._get_model_config(model)
        session_id = f"gen_{os.urandom(8).hex()}"
        
        try:
            # Step 1: Planning Agent
            planning_result = await self._planning_agent(prompt, provider, model_name, session_id)
            
            # Step 2: Code Generation Agent
            code_result = await self._code_generation_agent(planning_result, provider, model_name, session_id, framework)
            
            # Step 3: Design & Styling Agent (optional - for hero images)
            # For now, we'll skip image generation in basic flow
            
            return code_result
        except Exception as e:
            logger.error(f"Website generation failed: {str(e)}")
            raise

    async def _planning_agent(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """
        Requirement Planner Agent - Analyzes prompt and creates structured plan
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_planner",
            system_message="""You are a website planning expert. Analyze user requirements and create a detailed JSON structure.
Output ONLY valid JSON with this structure:
{
  "pages": ["Home", "About", "Contact"],
  "sections": {
    "Home": ["Hero", "Features", "CTA"],
    "About": ["Story", "Team"],
    "Contact": ["Form", "Info"]
  },
  "style": {
    "theme": "modern/minimal/corporate/creative",
    "colors": {"primary": "#color", "secondary": "#color"},
    "typography": "font-family"
  },
  "features": ["responsive", "animations", "forms"]
}"""
        )
        chat.with_model(provider, model)
        
        user_message = UserMessage(
            text=f"Analyze this website request and create a JSON plan: {prompt}"
        )
        
        response = await chat.send_message(user_message)
        
        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            plan = json.loads(json_str)
            return plan
        except:
            # Fallback plan if JSON parsing fails
            return {
                "pages": ["Home"],
                "sections": {"Home": ["Hero", "Features", "About", "Contact"]},
                "style": {"theme": "modern", "colors": {"primary": "#3b82f6", "secondary": "#8b5cf6"}},
                "features": ["responsive"]
            }

    async def _code_generation_agent(self, plan: Dict, provider: str, model: str, session_id: str, framework: str) -> Dict[str, Any]:
        """
        Code Generation Agent - Generates actual HTML/CSS/JS code
        """
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_coder",
            system_message=f"""You are an expert web developer. Generate clean, modern, production-ready code for {framework}.
Create a complete, responsive website based on the provided plan.
Use modern best practices, semantic HTML, and beautiful design.
For styling, use inline styles or embedded CSS.
Make it visually appealing with proper spacing, colors, and typography."""
        )
        chat.with_model(provider, model)
        
        prompt = f"""Create a complete website based on this plan:
{json.dumps(plan, indent=2)}

Generate:
1. Complete HTML (including embedded CSS)
2. Any necessary JavaScript
3. Make it beautiful, modern, and fully responsive

Format your response as:
HTML:
```html
[your html code]
```

CSS:
```css
[any additional css]
```

JS:
```javascript
[any js code]
```
"""
        
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Extract code sections
        html_content = self._extract_code_block(response, "html") or "<html><body><h1>Website</h1></body></html>"
        css_content = self._extract_code_block(response, "css") or ""
        js_content = self._extract_code_block(response, "javascript") or ""
        
        return {
            "html_content": html_content,
            "css_content": css_content,
            "js_content": js_content,
            "structure": plan
        }

    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        """Extract code from markdown code blocks"""
        try:
            marker = f"```{language}"
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    code = parts[1].split("```")[0].strip()
                    return code
            return None
        except:
            return None

    async def generate_image(self, prompt: str) -> str:
        """
        Generate image using Gemini Imagen (nano-banana)
        """
        session_id = f"img_{os.urandom(8).hex()}"
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message="You are a helpful AI assistant that generates images."
            )
            chat.with_model("gemini", "gemini-2.5-flash-image-preview").with_params(modalities=["image", "text"])
            
            msg = UserMessage(text=f"Create an image: {prompt}")
            text, images = await chat.send_message_multimodal_response(msg)
            
            if images and len(images) > 0:
                # Return base64 encoded image
                return f"data:{images[0]['mime_type']};base64,{images[0]['data']}"
            else:
                raise Exception("No image generated")
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            # Return placeholder
            return "https://via.placeholder.com/800x600?text=Image+Generation+Placeholder"