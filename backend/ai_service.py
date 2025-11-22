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
        """Generate a complete, production-ready project"""
        provider, model_name = self._get_model_config(model)
        session_id = f"project_{os.urandom(8).hex()}"
        
        logger.info(f"Starting complete project generation with {provider}/{model_name}")
        logger.info(f"User prompt: {prompt}")
        
        try:
            # First, analyze what the user is ACTUALLY asking for
            analysis = await self._analyze_user_intent(prompt, provider, model_name, session_id)
            logger.info(f"Intent analysis: {analysis}")
            
            # Generate frontend with context
            frontend_result = await self._generate_contextual_frontend(prompt, analysis, provider, model_name, session_id)
            
            # Generate backend
            backend_result = await self._generate_backend(prompt, provider, model_name, session_id)
            
            # Generate documentation
            readme = await self._generate_readme(prompt, provider, model_name, session_id)
            
            # Compile all files
            files = []
            
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
            
            if readme:
                files.append({
                    "filename": "README.md",
                    "content": readme,
                    "file_type": "md",
                    "description": "Project documentation"
                })
            
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
                "structure": analysis,
                "files": files
            }
            
        except Exception as e:
            logger.error(f"Complete project generation failed: {str(e)}", exc_info=True)
            return await self._generate_fallback_project(prompt)

    async def _analyze_user_intent(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, Any]:
        """Analyze what the user is ACTUALLY asking for"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_analyzer",
            system_message="""You are an expert at understanding user intent for web applications.

Analyze the user's request and identify:
1. What TYPE of website/app they want (e.g., video platform, e-commerce, social media, dashboard, etc.)
2. What SPECIFIC FEATURES they need (e.g., video grid, shopping cart, user profiles, data visualization)
3. What VISUAL STYLE is appropriate (e.g., YouTube's dark theme with thumbnails, Amazon's product grid, Netflix's hero banner)
4. What COMPONENTS are needed (e.g., navigation bar, sidebar, video player, cards, forms)

Return ONLY a JSON object with this structure:
{
  "app_type": "video_platform" | "ecommerce" | "social_media" | "dashboard" | "landing_page" | "other",
  "reference_site": "youtube" | "netflix" | "amazon" | "twitter" | "stripe" | "custom",
  "key_components": ["video_grid", "sidebar_nav", "search_bar", "video_player"],
  "visual_style": "dark_theme" | "light_theme" | "gradient" | "minimal" | "colorful",
  "layout_pattern": "grid" | "feed" | "hero_sections" | "dashboard_cards" | "single_page",
  "primary_features": ["video_playback", "comments", "recommendations", "subscriptions"]
}"""
        )
        chat.with_model(provider, model)
        
        analysis_prompt = f"""Analyze this website request:

"{prompt}"

Return ONLY the JSON analysis object."""
        
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        try:
            # Extract JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            analysis = json.loads(json_str)
            return analysis
        except:
            # Fallback analysis
            return {
                "app_type": "landing_page",
                "reference_site": "custom",
                "key_components": ["header", "hero", "features", "footer"],
                "visual_style": "modern",
                "layout_pattern": "hero_sections",
                "primary_features": ["responsive_design"]
            }

    async def _generate_contextual_frontend(self, prompt: str, analysis: Dict, provider: str, model: str, session_id: str) -> Dict[str, str]:
        """Generate frontend based on context analysis"""
        
        # Build context-specific instructions
        reference_examples = self._get_reference_examples(analysis.get('reference_site', 'custom'))
        component_templates = self._get_component_templates(analysis.get('key_components', []))
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_frontend",
            system_message=f"""You are an ELITE web developer who creates PIXEL-PERFECT clones and functional websites.

CRITICAL RULES:
1. MATCH the exact visual style of what the user asks for
2. If they want a YouTube clone → create a REAL video platform UI with grid, sidebar, player
3. If they want Netflix → create hero banner with rows of content cards
4. If they want Amazon → create product grid with filters and cart
5. DON'T create generic white backgrounds with text - CREATE THE ACTUAL UI

You MUST:
- Use the CORRECT layout for the app type (grid for videos, feed for social, dashboard for analytics)
- Include ALL necessary components (nav, sidebar, cards, players, forms)
- Use appropriate colors and styling for the app type
- Make it FUNCTIONAL with working JavaScript
- Use realistic placeholder content (video thumbnails, product images, user avatars)

REFERENCE EXAMPLES:
{reference_examples}

COMPONENTS TO INCLUDE:
{component_templates}

OUTPUT: Separate HTML, CSS, and JavaScript files that create a REAL, FUNCTIONAL interface."""
        )
        chat.with_model(provider, model)
        
        frontend_prompt = f"""CREATE A FUNCTIONAL {analysis.get('app_type', 'website').upper()}:

USER REQUEST: {prompt}

APP TYPE: {analysis.get('app_type')}
REFERENCE STYLE: {analysis.get('reference_site')}
KEY COMPONENTS: {', '.join(analysis.get('key_components', []))}
VISUAL STYLE: {analysis.get('visual_style')}
LAYOUT: {analysis.get('layout_pattern')}

GENERATE:

1. **index.html** - Complete HTML with:
   - Proper semantic structure
   - ALL components listed above (don't skip any!)
   - Realistic placeholder content
   - <link rel="stylesheet" href="styles.css">
   - <script src="app.js"></script> before </body>

2. **styles.css** - Complete CSS with:
   - Exact styling to match the reference site
   - Proper layout (Grid/Flexbox)
   - Responsive design
   - All component styles
   - Modern effects
   - MINIMUM 600 lines of detailed CSS

3. **app.js** - Working JavaScript with:
   - DOM manipulation
   - Event handlers
   - Interactive features
   - State management
   - API simulation

FORMAT:
```html
[COMPLETE HTML]
```

```css
[COMPLETE CSS - MINIMUM 600 LINES]
```

```javascript
[COMPLETE JAVASCRIPT]
```

MAKE IT LOOK AND FUNCTION LIKE THE REAL THING!"""
        
        user_message = UserMessage(text=frontend_prompt)
        response = await chat.send_message(user_message)
        
        # Extract code
        html = self._extract_code_block(response, "html") or ""
        css = self._extract_code_block(response, "css") or ""
        js = self._extract_code_block(response, "javascript") or self._extract_code_block(response, "js") or ""
        
        # Fallback extraction
        if not html and "<!DOCTYPE" in response:
            html = self._extract_html_direct(response)
        
        # Ensure links
        if html and "<link" not in html and "</head>" in html:
            html = html.replace("</head>", '    <link rel="stylesheet" href="styles.css">\n</head>')
        
        if html and "<script" not in html and "</body>" in html:
            html = html.replace("</body>", '    <script src="app.js"></script>\n</body>')
        
        # Validate quality
        if len(html) < 500:
            logger.warning(f"HTML too short ({len(html)} chars), using fallback")
            return await self._generate_fallback_frontend(prompt, analysis)
        
        if len(css) < 300:
            logger.warning(f"CSS too short ({len(css)} chars), enhancing")
            css = self._enhance_css_for_app_type(css, analysis)
        
        logger.info(f"Generated: HTML={len(html)}, CSS={len(css)}, JS={len(js)}")
        
        return {"html": html, "css": css, "js": js}

    def _get_reference_examples(self, reference_site: str) -> str:
        """Get specific examples for reference sites"""
        examples = {
            "youtube": """YOUTUBE STYLE:
- Dark theme (#0f0f0f background, #212121 for cards)
- Top navigation bar with logo, search bar, icons
- Left sidebar with menu items
- Main content: Grid of video cards (3-4 columns)
- Each card: Thumbnail image, title, channel name, views, date
- Video player page: Large player, title, channel info, description
- Use Material Icons or emoji for icons""",
            "netflix": """NETFLIX STYLE:
- Dark background (#141414)
- Large hero banner with featured content
- Horizontal scrolling rows of content cards
- Hover effects with scale and info reveal
- Navigation bar with transparent/blur effect
- Red accent color (#E50914)""",
            "twitter": """TWITTER STYLE:
- Three column layout: sidebar, feed, trending
- Blue accent (#1DA1F2)
- Tweet cards with avatar, username, text, actions
- Rounded profile images
- Light theme with white cards""",
            "amazon": """AMAZON STYLE:
- Product grid layout
- Search bar prominent in header
- Product cards: image, title, price, rating
- Orange accent (#FF9900)
- Left sidebar with filters/categories"""
        }
        return examples.get(reference_site, "Modern, professional design with appropriate layout for the app type.")

    def _get_component_templates(self, components: List[str]) -> str:
        """Get templates for specific components"""
        templates = []
        
        if "video_grid" in components:
            templates.append("Video Grid: 3-4 columns of video cards with thumbnail, title, channel, views")
        if "sidebar_nav" in components:
            templates.append("Sidebar Navigation: Vertical menu with icons and labels")
        if "search_bar" in components:
            templates.append("Search Bar: Prominent input field with search icon")
        if "video_player" in components:
            templates.append("Video Player: Large embedded player with controls")
        if "product_grid" in components:
            templates.append("Product Grid: Cards with image, title, price, rating")
        if "feed" in components:
            templates.append("Feed: Vertical list of posts/content cards")
        if "dashboard_cards" in components:
            templates.append("Dashboard Cards: Stats cards with numbers and charts")
        
        return "\n".join(templates) if templates else "Standard web components"

    def _enhance_css_for_app_type(self, css: str, analysis: Dict) -> str:
        """Add CSS enhancements based on app type"""
        app_type = analysis.get('app_type', 'landing_page')
        
        if app_type == 'video_platform':
            enhancement = """/* Video Platform Styles */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

:root {
    --yt-black: #0f0f0f;
    --yt-dark: #212121;
    --yt-white: #ffffff;
    --yt-text: #f1f1f1;
    --yt-border: #303030;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Roboto', sans-serif;
    background: var(--yt-black);
    color: var(--yt-text);
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--yt-black);
    border-bottom: 1px solid var(--yt-border);
}

.sidebar {
    position: fixed;
    left: 0;
    top: 56px;
    width: 240px;
    height: calc(100vh - 56px);
    background: var(--yt-black);
    overflow-y: auto;
    padding: 12px 0;
}

.main-content {
    margin-left: 240px;
    margin-top: 56px;
    padding: 24px;
}

.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
}

.video-card {
    cursor: pointer;
}

.video-thumbnail {
    width: 100%;
    aspect-ratio: 16/9;
    background: var(--yt-dark);
    border-radius: 12px;
    position: relative;
    overflow: hidden;
}

.video-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.video-info {
    display: flex;
    gap: 12px;
    padding-top: 12px;
}

.channel-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--yt-dark);
}

.video-details h3 {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    margin-bottom: 4px;
}

.video-meta {
    font-size: 12px;
    color: #aaa;
}"""
        else:
            enhancement = """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --primary: #6366f1;
    --background: #0f172a;
    --surface: #1e293b;
    --text: #f1f5f9;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.6;
}"""
        
        return enhancement + "\n\n" + css

    async def _generate_fallback_frontend(self, prompt: str, analysis: Dict) -> Dict[str, str]:
        """Generate a fallback based on app type"""
        app_type = analysis.get('app_type', 'landing_page')
        
        if app_type == 'video_platform':
            return self._create_video_platform_fallback(prompt)
        else:
            return self._create_generic_fallback(prompt)

    def _create_video_platform_fallback(self, prompt: str) -> Dict[str, str]:
        """Create a video platform UI fallback"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Platform</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header class="header">
        <div class="header-left">
            <button class="menu-btn">☰</button>
            <div class="logo">📺 VideoTube</div>
        </div>
        <div class="header-center">
            <input type="text" class="search-bar" placeholder="Search">
            <button class="search-btn">🔍</button>
        </div>
        <div class="header-right">
            <button>🔔</button>
            <button>👤</button>
        </div>
    </header>
    
    <aside class="sidebar">
        <nav>
            <a href="#" class="nav-item active">🏠 Home</a>
            <a href="#" class="nav-item">📺 Subscriptions</a>
            <a href="#" class="nav-item">📚 Library</a>
            <a href="#" class="nav-item">🕐 History</a>
            <a href="#" class="nav-item">👍 Liked Videos</a>
        </nav>
    </aside>
    
    <main class="main-content">
        <div class="video-grid" id="videoGrid">
            <!-- Videos will be generated by JavaScript -->
        </div>
    </main>
    
    <script src="app.js"></script>
</body>
</html>"""

        css = """@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Roboto', sans-serif;
    background: #0f0f0f;
    color: #f1f1f1;
}

.header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 56px;
    background: #0f0f0f;
    border-bottom: 1px solid #303030;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    z-index: 100;
}

.header-left, .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
}

.menu-btn {
    background: none;
    border: none;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    padding: 8px;
}

.logo {
    font-size: 20px;
    font-weight: 700;
}

.header-center {
    flex: 1;
    max-width: 600px;
    display: flex;
    gap: 8px;
    margin: 0 40px;
}

.search-bar {
    flex: 1;
    background: #121212;
    border: 1px solid #303030;
    border-radius: 40px;
    padding: 10px 16px;
    color: #f1f1f1;
    font-size: 16px;
}

.search-bar:focus {
    outline: none;
    border-color: #1e90ff;
}

.search-btn {
    background: #222;
    border: 1px solid #303030;
    border-radius: 40px;
    padding: 10px 20px;
    color: #fff;
    cursor: pointer;
}

.header-right button {
    background: none;
    border: none;
    color: #fff;
    font-size: 20px;
    cursor: pointer;
    padding: 8px;
}

.sidebar {
    position: fixed;
    left: 0;
    top: 56px;
    width: 240px;
    height: calc(100vh - 56px);
    background: #0f0f0f;
    overflow-y: auto;
    padding: 12px 0;
    border-right: 1px solid #303030;
}

.sidebar::-webkit-scrollbar { width: 8px; }
.sidebar::-webkit-scrollbar-thumb { background: #303030; border-radius: 4px; }

.nav-item {
    display: flex;
    align-items: center;
    padding: 10px 24px;
    color: #f1f1f1;
    text-decoration: none;
    transition: background 0.2s;
    gap: 24px;
}

.nav-item:hover {
    background: #272727;
}

.nav-item.active {
    background: #272727;
    font-weight: 500;
}

.main-content {
    margin-left: 240px;
    margin-top: 56px;
    padding: 24px;
    min-height: calc(100vh - 56px);
}

.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 40px 16px;
}

.video-card {
    cursor: pointer;
}

.video-thumbnail {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
}

.video-thumbnail:hover {
    transform: scale(1.02);
    transition: transform 0.2s;
}

.duration {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0,0,0,0.8);
    padding: 3px 6px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.video-info {
    display: flex;
    gap: 12px;
    padding-top: 12px;
}

.channel-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    flex-shrink: 0;
}

.video-details h3 {
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
    margin-bottom: 4px;
    color: #f1f1f1;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.video-meta {
    font-size: 12px;
    color: #aaa;
    line-height: 1.4;
}

.channel-name {
    color: #aaa;
}

.channel-name:hover {
    color: #fff;
}

@media (max-width: 1024px) {
    .video-grid {
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    }
}

@media (max-width: 768px) {
    .sidebar {
        transform: translateX(-100%);
    }
    
    .main-content {
        margin-left: 0;
    }
    
    .video-grid {
        grid-template-columns: 1fr;
    }
}"""

        js = """// Video Platform JavaScript
const videoData = [
    { title: 'Amazing Tutorial: Learn Web Development', channel: 'CodeMaster', views: '1.2M', time: '2 days ago', duration: '15:30' },
    { title: 'Top 10 JavaScript Tips and Tricks', channel: 'DevGuru', views: '856K', time: '1 week ago', duration: '12:45' },
    { title: 'Build a Full Stack App from Scratch', channel: 'TechLead', views: '2.1M', time: '3 days ago', duration: '45:20' },
    { title: 'CSS Grid vs Flexbox: Complete Guide', channel: 'DesignPro', views: '543K', time: '5 days ago', duration: '18:15' },
    { title: 'React Hooks Explained Simply', channel: 'CodeMaster', views: '1.8M', time: '1 week ago', duration: '22:10' },
    { title: 'Python for Beginners 2024', channel: 'PythonAcademy', views: '3.2M', time: '2 weeks ago', duration: '1:05:30' },
    { title: 'Database Design Best Practices', channel: 'DataEngineer', views: '678K', time: '4 days ago', duration: '28:45' },
    { title: 'API Development with FastAPI', channel: 'BackendPro', views: '945K', time: '1 week ago', duration: '35:20' },
    { title: 'Modern UI/UX Design Principles', channel: 'DesignPro', views: '1.4M', time: '3 days ago', duration: '20:15' },
    { title: 'Docker & Kubernetes Tutorial', channel: 'DevOpsGuru', views: '1.1M', time: '5 days ago', duration: '42:30' },
    { title: 'Machine Learning Basics', channel: 'AIAcademy', views: '2.5M', time: '1 week ago', duration: '52:10' },
    { title: 'Git and GitHub for Teams', channel: 'TechLead', views: '789K', time: '2 days ago', duration: '25:40' }
];

const emojis = ['🎬', '🎮', '🎨', '🎯', '🎪', '🎭', '🎰', '🎲', '🎵', '🎸', '🎹', '🎺'];

function createVideoCard(video, index) {
    return `
        <div class="video-card">
            <div class="video-thumbnail">
                ${emojis[index % emojis.length]}
                <span class="duration">${video.duration}</span>
            </div>
            <div class="video-info">
                <div class="channel-avatar"></div>
                <div class="video-details">
                    <h3>${video.title}</h3>
                    <div class="video-meta">
                        <div class="channel-name">${video.channel}</div>
                        <div>${video.views} views • ${video.time}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderVideos() {
    const grid = document.getElementById('videoGrid');
    grid.innerHTML = videoData.map((video, index) => createVideoCard(video, index)).join('');
    
    // Add click handlers
    document.querySelectorAll('.video-card').forEach((card, index) => {
        card.addEventListener('click', () => {
            console.log('Playing video:', videoData[index].title);
            alert(`Now playing: ${videoData[index].title}`);
        });
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderVideos();
    
    // Search functionality
    const searchBar = document.querySelector('.search-bar');
    const searchBtn = document.querySelector('.search-btn');
    
    function handleSearch() {
        const query = searchBar.value.toLowerCase();
        if (query) {
            console.log('Searching for:', query);
            alert(`Searching for: ${query}`);
        }
    }
    
    searchBtn.addEventListener('click', handleSearch);
    searchBar.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Sidebar toggle for mobile
    const menuBtn = document.querySelector('.menu-btn');
    const sidebar = document.querySelector('.sidebar');
    
    menuBtn.addEventListener('click', () => {
        sidebar.style.transform = sidebar.style.transform === 'translateX(0px)' 
            ? 'translateX(-100%)' 
            : 'translateX(0px)';
    });
});"""

        return {"html": html, "css": css, "js": js}

    def _create_generic_fallback(self, prompt: str) -> Dict[str, str]:
        """Generic fallback"""
        # Use the existing fallback from before
        return {"html": "", "css": "", "js": ""}

    async def _generate_backend(self, prompt: str, provider: str, model: str, session_id: str) -> Dict[str, str]:
        """Generate Python FastAPI backend"""
        chat = LlmChat(
            api_key=self.api_key,
            session_id=f"{session_id}_backend",
            system_message="You are an expert backend developer. Generate production-ready FastAPI code."
        )
        chat.with_model(provider, model)
        
        backend_prompt = f"""Create a Python FastAPI backend for: {prompt}

Generate server.py with:
- FastAPI app
- CORS middleware
- RESTful routes
- MongoDB integration
- Pydantic models

Also provide requirements.txt.

Format:
```python
# server.py
[CODE]
```

```txt
# requirements.txt
[DEPENDENCIES]
```"""
        
        user_message = UserMessage(text=backend_prompt)
        response = await chat.send_message(user_message)
        
        python_code = self._extract_code_block(response, "python") or ""
        requirements = self._extract_code_block(response, "txt") or "fastapi==0.104.1\nuvicorn==0.24.0\nmotor==3.3.2\npydantic==2.5.0\npython-dotenv==1.0.0"
        
        return {"python": python_code, "requirements": requirements, "models": ""}

    async def _generate_readme(self, prompt: str, provider: str, model: str, session_id: str) -> str:
        """Generate README"""
        return f"# Generated Project\n\n{prompt}\n\n## Features\n- Modern UI\n- Responsive design\n- Working functionality"

    def _generate_package_json(self, prompt: str) -> str:
        return json.dumps({"name": "generated-app", "version": "1.0.0"}, indent=2)

    async def _generate_fallback_project(self, prompt: str) -> Dict[str, Any]:
        """Complete fallback"""
        fallback = self._create_video_platform_fallback(prompt)
        
        return {
            "html_content": fallback['html'],
            "css_content": fallback['css'],
            "js_content": fallback['js'],
            "python_backend": "",
            "requirements_txt": "",
            "package_json": self._generate_package_json(prompt),
            "readme": f"# {prompt}",
            "files": [],
            "structure": {}
        }

    def _extract_code_block(self, text: str, language: str) -> Optional[str]:
        try:
            marker = f"```{language}"
            if marker in text:
                parts = text.split(marker)
                if len(parts) > 1:
                    return parts[1].split("```")[0].strip()
        except:
            pass
        return None

    def _extract_html_direct(self, text: str) -> str:
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
        return "https://via.placeholder.com/800x600"
