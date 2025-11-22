import os
import logging
import json
import re
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
        return model_map.get(model, ("openai", "gpt-5"))

    async def generate_response(self, prompt: str, model: str, session_id: str) -> Dict[str, Any]:
        """Generate AI response for user prompt"""
        provider, model_name = self._get_model_config(model)
        
        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message="You are Code Weaver, an expert AI assistant that helps users create professional, production-ready web applications. You understand full-stack development, modern frameworks, and can generate clean, scalable code with backends, frontends, and databases. Always be helpful, creative, and provide clear explanations."
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

    async def generate_complete_project(self, prompt: str, model: str, framework: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        Generate a complete, production-ready project with:
        - Frontend HTML/CSS/JavaScript
        - Python FastAPI backend
        - Database models
        - API endpoints
        - README documentation
        """
        provider, model_name = self._get_model_config(model)
        session_id = f"project_{os.urandom(8).hex()}"
        
        logger.info(f"Starting complete project generation with {provider}/{model_name}")
        logger.info(f"User prompt: {prompt}")
        
        try:
            # Generate frontend
            frontend_result = await self._generate_frontend(prompt, provider, model_name, session_id)
            
            # Generate backend
            backend_result = await self._generate_backend(prompt, provider, model_name, session_id)
            
            # Generate documentation
            readme = await self._generate_readme(prompt, provider, model_name, session_id)
            
            # Compile all files
            files = []
            
            # Frontend files
            if frontend_result.get('html'):
                files.append({
                    "filename": "index.html",
                    "content": frontend_result['html'],
                    "file_type": "html",
                    "description": "Main HTML file with structure and content"
                })
            
            if frontend_result.get('css'):
                files.append({
                    "filename": "styles.css",
                    "content": frontend_result['css'],
                    "file_type": "css",
                    "description": "Stylesheet with modern, responsive design"
                })
            
            if frontend_result.get('js'):
                files.append({
                    "filename": "app.js",
                    "content": frontend_result['js'],
                    "file_type": "js",
                    "description": "JavaScript for interactivity and API calls"
                })
            
            # Backend files
            if backend_result.get('python'):
                files.append({
                    "filename": "server.py",
                    "content": backend_result['python'],
                    "file_type": "python",
                    "description": "FastAPI backend with routes and business logic"
                })
            
            if backend_result.get('requirements'):
                files.append({
                    "filename": "requirements.txt",
                    "content": backend_result['requirements'],
                    "file_type": "txt",
                    "description": "Python dependencies"
                })
            
            if backend_result.get('models'):
                files.append({
                    "filename": "models.py",
                    "content": backend_result['models'],
                    "file_type": "python",
                    "description": "Database models and schemas"
                })
            
            # Documentation
            if readme:
                files.append({
                    "filename": "README.md",
                    "content": readme,
                    "file_type": "md",
                    "description": "Project documentation"
                })
            
            # Package.json for frontend dependencies
            package_json = self._generate_package_json(prompt)
            files.append({
                "filename": "package.json",
                "content": package_json,
                "file_type": "json",
                "description": "Frontend dependencies and scripts"
            })
            
            logger.info(f"Generated complete project with {len(files)} files")
            
            return {
                "html_content": frontend_result.get('html', ''),
                "css_content": frontend_result.get('css', ''),
                "js_content": frontend_result.get('js', ''),
                "python_backend": backend_result.get('python', ''),
                "requirements_txt": backend_result.get('requirements', ''),
                "package_json": package_json,
                "readme": readme,
                "structure": {
                    "frontend": ["index.html", "styles.css", "app.js"],
                    "backend": ["server.py", "models.py", "requirements.txt"],
                    "docs": ["README.md"]
                },
                "files": files
            }
            
        except Exception as e:
            logger.error(f"Complete project generation failed: {str(e)}", exc_info=True)
            # Return basic fallback
            return await self._generate_fallback_project(prompt)

    async def _generate_frontend(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, str]:
        """Generate professional frontend with separated HTML/CSS/JS"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_frontend",
            system_message="""You are an ELITE frontend developer and UI/UX designer who creates STUNNING, visually impressive websites.

🎨 VISUAL DESIGN IS PARAMOUNT - THIS IS YOUR #1 PRIORITY 🎨

DESIGN PHILOSOPHY:
Your designs should rival the best websites on the internet like:
- Stripe.com (clean, modern, subtle gradients)
- Linear.app (sleek, dark themes, smooth animations)
- Vercel.com (minimalist, sharp, excellent typography)
- Apple.com (spacious, elegant, perfect hierarchy)
- Awwwards.com winners (creative, unique, memorable)

═══════════════════════════════════════════════════════════════

🎨 COLOR SCHEME REQUIREMENTS (CRITICAL):

1. CHOOSE A SOPHISTICATED COLOR PALETTE:
   - Primary: One bold, modern color (e.g., #6366f1, #8b5cf6, #0ea5e9, #10b981)
   - Secondary: Complementary accent color
   - Background: Rich gradients, NOT solid colors
   - Use color psychology: Blue=trust, Purple=luxury, Green=growth
   
2. GRADIENT MASTERY:
   - Use multi-stop gradients: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)
   - Subtle mesh gradients for backgrounds
   - Gradient text with background-clip: text
   - Animated gradient effects on hover
   
3. DARK MODE EXCELLENCE:
   - Dark themes: Use #0a0a0a, #111111, #1a1a1a (never pure black)
   - Subtle colored shadows in dark mode
   - Glow effects on interactive elements

═══════════════════════════════════════════════════════════════

📐 LAYOUT & SPACING (CRITICAL):

1. GENEROUS WHITE SPACE:
   - Use 2-3x MORE spacing than you think necessary
   - Section padding: 120px+ vertical, 80px+ horizontal
   - Element gaps: 60px between major sections
   - Component padding: 40-60px
   
2. MODERN LAYOUT PATTERNS:
   - Hero sections: Full viewport height with centered content
   - Asymmetric grids for visual interest
   - Bento box layouts (card grids with varying sizes)
   - Split-screen designs
   - Diagonal sections with clip-path
   
3. VISUAL HIERARCHY:
   - Massive hero headings: 4-6rem (64-96px)
   - Clear size distinctions: h1 → 4rem, h2 → 3rem, h3 → 2rem
   - Use weight variations: 300, 400, 600, 700, 800
   - Strategic use of color to guide eyes

═══════════════════════════════════════════════════════════════

✨ TYPOGRAPHY (MAKE IT SING):

1. FONT SELECTION:
   - Import Google Fonts (2-3 fonts max)
   - Display fonts: Inter, Space Grotesk, Outfit, Manrope, Plus Jakarta Sans
   - Consider variable fonts for smooth weight transitions
   
2. TYPOGRAPHIC DETAILS:
   - Line height: 1.6-1.8 for body text
   - Letter spacing: -0.02em for large headings, normal for body
   - Font smoothing: -webkit-font-smoothing: antialiased
   - Text shadow for depth: text-shadow: 0 2px 4px rgba(0,0,0,0.1)

═══════════════════════════════════════════════════════════════

🌟 VISUAL EFFECTS & POLISH:

1. GLASSMORPHISM:
   - backdrop-filter: blur(12px) saturate(180%)
   - Semi-transparent backgrounds: rgba(255,255,255,0.1)
   - Subtle borders: 1px solid rgba(255,255,255,0.18)
   
2. DEPTH & SHADOWS:
   - Layered shadows: box-shadow: 0 10px 40px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06)
   - Colored shadows matching brand: box-shadow: 0 20px 60px rgba(99,102,241,0.3)
   - Elevation on hover: transform: translateY(-4px)
   
3. SMOOTH ANIMATIONS:
   - Micro-interactions on everything
   - transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
   - Stagger animations for lists
   - Parallax scrolling effects
   - Fade-in on scroll animations
   - Hover scale effects: transform: scale(1.05)
   
4. ADVANCED CSS:
   - CSS custom properties for theming
   - :hover, :focus, :active states for ALL interactive elements
   - clip-path for unique shapes
   - Mix-blend-mode for creative effects
   - filter: for image effects

═══════════════════════════════════════════════════════════════

🎯 COMPONENT DESIGN:

1. BUTTONS (Make them irresistible):
   - Large, pill-shaped with generous padding: 18px 48px
   - Gradient backgrounds or solid with shadow
   - Transform on hover: scale(1.05) + shadow increase
   - Ripple or shimmer effects
   
2. CARDS:
   - Rounded corners: 16-24px
   - Subtle hover elevation
   - Internal padding: 40px
   - Background: white/dark with slight transparency
   
3. NAVIGATION:
   - Sticky/fixed with backdrop blur
   - Smooth scroll behavior
   - Active state indicators
   - Mobile hamburger with smooth animation

═══════════════════════════════════════════════════════════════

📱 RESPONSIVE DESIGN:

- Mobile-first approach
- Breakpoints: 640px, 768px, 1024px, 1280px, 1536px
- Stack layouts gracefully on mobile
- Touch-friendly: 44px minimum tap targets
- Test at all viewport sizes

═══════════════════════════════════════════════════════════════

TECHNICAL REQUIREMENTS:
1. Generate SEPARATE files: HTML, CSS, JavaScript
2. Use semantic HTML5
3. BEM or utility-first CSS methodology
4. Modern ES6+ JavaScript
5. Accessible (ARIA labels, keyboard nav)
6. Performance optimized

OUTPUT FORMAT:
```html
[Complete HTML]
```

```css
[Complete CSS - AT LEAST 500 LINES of beautiful, detailed styling]
```

```javascript
[Complete JavaScript with smooth interactions]
```

REMEMBER: Every pixel matters. Make it BEAUTIFUL, not just functional."""
        )
        chat.with_model(provider, model)
        
        full_prompt = f"""Create a professional, modern frontend for:

{prompt}

Generate THREE separate files:

1. **index.html** - Complete HTML structure with:
   - Semantic HTML5 tags
   - Proper meta tags and SEO
   - Link to styles.css
   - Script tag for app.js at the end
   
2. **styles.css** - Modern CSS with:
   - CSS custom properties (variables)
   - Flexbox/Grid layouts
   - Responsive breakpoints (@media queries)
   - Smooth animations and transitions
   - Professional color scheme
   - Modern typography
   
3. **app.js** - JavaScript with:
   - DOM manipulation
   - Event listeners
   - Form validation (if forms exist)
   - API calls (fetch)
   - Smooth interactions
   - Modern ES6+ syntax

Make it look PROFESSIONAL and MODERN. Think of popular websites like Stripe, Linear, or Vercel.

Format your response with three code blocks:
```html
[HTML CODE]
```

```css
[CSS CODE]
```

```javascript
[JS CODE]
```"""
        
        user_message = UserMessage(text=full_prompt)
        response = await chat.send_message(user_message)
        
        # Extract each file type
        html = self._extract_code_block(response, "html") or ""
        css = self._extract_code_block(response, "css") or ""
        js = self._extract_code_block(response, "javascript") or self._extract_code_block(response, "js") or ""
        
        # If extraction failed, try alternative methods
        if not html and "<!DOCTYPE" in response:
            html = self._extract_html_direct(response)
        
        # Ensure HTML links to CSS and JS
        if html and "<link" not in html:
            head_end = html.find("</head>")
            if head_end > 0:
                html = html[:head_end] + '    <link rel="stylesheet" href="styles.css">\n' + html[head_end:]
        
        if html and "<script" not in html:
            body_end = html.find("</body>")
            if body_end > 0:
                html = html[:body_end] + '    <script src="app.js"></script>\n' + html[body_end:]
        
        logger.info(f"Generated frontend: HTML={len(html)} chars, CSS={len(css)} chars, JS={len(js)} chars")
        
        return {
            "html": html,
            "css": css,
            "js": js
        }

    async def _generate_backend(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, str]:
        """Generate Python FastAPI backend with routes and models"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_backend",
            system_message="""You are an expert backend developer specializing in Python and FastAPI.

Generate production-ready backend code with:
1. FastAPI application with proper structure
2. RESTful API endpoints
3. Pydantic models for validation
4. Database integration (MongoDB with Motor)
5. CORS configuration
6. Error handling
7. Logging
8. Environment variables
9. Security best practices

Make it clean, scalable, and production-ready."""
        )
        chat.with_model(provider, model)
        
        backend_prompt = f"""Create a Python FastAPI backend for:

{prompt}

Generate TWO files:

1. **server.py** - FastAPI application with:
   - Proper imports
   - FastAPI app initialization
   - CORS middleware
   - API routes (GET, POST, PUT, DELETE as needed)
   - Request/response models
   - Error handling
   - MongoDB integration using Motor
   - Environment variable loading
   
2. **models.py** - Pydantic models with:
   - Data validation models
   - Database schemas
   - Type hints
   
3. **requirements.txt** - List all Python dependencies:
   - fastapi
   - uvicorn
   - motor (MongoDB async driver)
   - pydantic
   - python-dotenv
   - Any other needed packages

Format your response:
```python
# server.py
[SERVER CODE]
```

```python
# models.py
[MODELS CODE]
```

```txt
# requirements.txt
[DEPENDENCIES]
```"""
        
        user_message = UserMessage(text=backend_prompt)
        response = await chat.send_message(user_message)
        
        # Extract Python files
        python_code = self._extract_code_block(response, "python")
        
        # Try to separate server.py and models.py
        server_py = ""
        models_py = ""
        
        if "# server.py" in response and "# models.py" in response:
            parts = response.split("# models.py")
            server_part = parts[0]
            models_part = parts[1]
            
            server_py = self._extract_code_block(server_part, "python")
            models_py = self._extract_code_block(models_part, "python")
        elif python_code:
            server_py = python_code
        
        # Extract requirements.txt
        requirements = self._extract_code_block(response, "txt") or self._extract_code_block(response, "text")
        
        if not requirements:
            # Generate default requirements
            requirements = """fastapi==0.104.1
uvicorn==0.24.0
motor==3.3.2
pydantic==2.5.0
python-dotenv==1.0.0
pymongo==4.6.0"""
        
        logger.info(f"Generated backend: server.py={len(server_py)} chars, models.py={len(models_py)} chars")
        
        # Combine or use separate
        full_backend = server_py
        if models_py:
            full_backend += f"\n\n# MODELS (models.py):\n{models_py}"
        
        return {
            "python": full_backend,
            "requirements": requirements,
            "models": models_py
        }

    async def _generate_readme(self, prompt: str, provider: str, model: str, session_id: str) -> str:
        """Generate README documentation"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_docs",
            system_message="You are a technical writer. Create clear, professional documentation."
        )
        chat.with_model(provider, model)
        
        readme_prompt = f"""Create a professional README.md for this project:

{prompt}

Include:
- Project title and description
- Features list
- Installation instructions
- How to run the project
- API endpoints (if backend exists)
- Technologies used
- Project structure
- Future improvements

Format in Markdown."""
        
        user_message = UserMessage(text=readme_prompt)
        response = await chat.send_message(user_message)
        
        readme = self._extract_code_block(response, "markdown") or self._extract_code_block(response, "md") or response
        
        return readme

    def _generate_package_json(self, prompt: str) -> str:
        """Generate package.json for frontend"""
        return json.dumps({
            "name": "generated-website",
            "version": "1.0.0",
            "description": f"Generated website: {prompt[:100]}",
            "scripts": {
                "start": "python -m http.server 8000",
                "dev": "live-server"
            },
            "dependencies": {},
            "devDependencies": {}
        }, indent=2)

    async def _generate_fallback_project(self, prompt: str) -> Dict[str, Any]:
        """Fallback project if generation fails"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Project</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <h1>🚀 Your Project</h1>
        <p>{prompt}</p>
        <button id="actionBtn">Get Started</button>
    </div>
    <script src="app.js"></script>
</body>
</html>"""
        
        css = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.container {
    background: white;
    padding: 60px;
    border-radius: 20px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    text-align: center;
}

button {
    margin-top: 20px;
    padding: 15px 40px;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 50px;
    font-size: 16px;
    cursor: pointer;
    transition: transform 0.3s;
}

button:hover {
    transform: translateY(-2px);
}"""
        
        js = """document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('actionBtn');
    
    btn.addEventListener('click', () => {
        alert('Button clicked! This website is working.');
    });
    
    console.log('Website loaded successfully!');
});"""
        
        backend = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Generated API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.get("/api/data")
async def get_data():
    return {"data": "Sample data"}"""
        
        return {
            "html_content": html,
            "css_content": css,
            "js_content": js,
            "python_backend": backend,
            "requirements_txt": "fastapi==0.104.1\\nuvicorn==0.24.0",
            "package_json": self._generate_package_json(prompt),
            "readme": f"# Generated Project\\n\\n{prompt}",
            "files": [],
            "structure": {}
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

    def _extract_html_direct(self, text: str) -> str:
        """Extract HTML directly from response"""
        try:
            start = text.find("<!DOCTYPE")
            if start == -1:
                start = text.find("<html")
            
            if start != -1:
                end = text.rfind("</html>")
                if end != -1:
                    return text[start:end + 7].strip()
        except:
            pass
        return ""

    async def generate_image(self, prompt: str) -> str:
        """Generate image using Gemini Imagen"""
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
                return f"data:{images[0]['mime_type']};base64,{images[0]['data']}"
            else:
                raise Exception("No image generated")
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
            return "https://via.placeholder.com/800x600?text=Image+Generation+Placeholder"
