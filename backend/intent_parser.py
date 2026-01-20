"""
Intent Parser - Converts natural language messages to structured task intents
Uses OpenAI to understand user requests and map them to task types
"""

import os
import json
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class IntentParser:
    """
    Parses natural language messages into structured task intents
    """
    
    TASK_TYPES = {
        "copy_change": "Text or copy modifications",
        "section_reorder": "Reorder page sections",
        "color_change": "Update color tokens/themes",
        "seo_update": "Modify SEO tags (title, meta, etc.)",
        "component_edit": "General component changes",
        "style_change": "CSS/styling modifications",
        "add_content": "Add new content to existing components",
        "remove_content": "Remove content from components"
    }
    
    # Files that are commonly edited
    COMMON_SCOPES = {
        "hero": ["app/components/Hero.tsx", "components/Hero.tsx", "src/components/Hero.tsx"],
        "header": ["app/components/Header.tsx", "components/Header.tsx", "src/components/Header.tsx"],
        "footer": ["app/components/Footer.tsx", "components/Footer.tsx", "src/components/Footer.tsx"],
        "cta": ["app/components/CTA.tsx", "components/CTA.tsx", "src/components/CTA.tsx"],
        "nav": ["app/components/Nav.tsx", "components/Navigation.tsx", "src/components/Nav.tsx"],
        "pricing": ["app/components/Pricing.tsx", "components/Pricing.tsx"],
        "features": ["app/components/Features.tsx", "components/Features.tsx"],
        "seo": ["app/layout.tsx", "pages/_document.tsx", "src/app/layout.tsx"],
        "colors": ["tailwind.config.js", "tailwind.config.ts", "styles/globals.css"],
    }
    
    SYSTEM_PROMPT = """You are an intent parser for a website change automation system.
    
Your job is to analyze user messages and extract:
1. The type of change they want
2. A clear description of the change
3. Which files should be modified
4. Safety rules to prevent unwanted changes

Available task types:
- copy_change: Text/copy modifications (buttons, headings, paragraphs)
- section_reorder: Reorder page sections
- color_change: Update color tokens/themes
- seo_update: Modify SEO tags (title, meta, og tags)
- component_edit: General component changes
- style_change: CSS/styling modifications
- add_content: Add new content
- remove_content: Remove content

Common file locations:
- Hero sections: app/components/Hero.tsx, components/Hero.tsx
- Header: app/components/Header.tsx, components/Header.tsx
- Footer: app/components/Footer.tsx
- CTA buttons: Usually in Hero.tsx or CTA.tsx
- SEO: app/layout.tsx, pages/_document.tsx
- Colors: tailwind.config.js, tailwind.config.ts

Respond ONLY with a valid JSON object (no markdown, no explanation):
{
    "type": "task_type",
    "description": "Clear description of what to change",
    "scope": ["file1.tsx", "file2.tsx"],
    "rules": ["Rule 1", "Rule 2"],
    "auto_commit": true/false,
    "confidence": 0.0-1.0
}

Set auto_commit to true only for:
- Simple text changes
- Color token updates
- SEO tag changes
- Safe, reversible changes

Set auto_commit to false for:
- Layout changes
- Adding new components
- Complex logic changes
- Anything that could break the site

If the message is unclear or not a valid change request, set confidence below 0.5.
"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None
            print("Warning: OPENAI_API_KEY not set. Using rule-based parsing only.")
    
    async def parse(self, message: str) -> dict:
        """
        Parse a natural language message into a structured task intent
        """
        # Try OpenAI first if available
        if self.client:
            try:
                return await self._parse_with_openai(message)
            except Exception as e:
                print(f"OpenAI parsing failed: {e}")
        
        # Fallback to rule-based parsing
        return self._parse_with_rules(message)
    
    async def _parse_with_openai(self, message: str) -> dict:
        """Use OpenAI to parse the intent"""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            intent = json.loads(content)
            return self._validate_intent(intent)
        except json.JSONDecodeError:
            return self._parse_with_rules(message)
    
    def _parse_with_rules(self, message: str) -> dict:
        """
        Rule-based fallback parsing for when OpenAI is unavailable
        """
        message_lower = message.lower()
        
        # Detect task type
        task_type = "component_edit"  # default
        
        if any(word in message_lower for word in ["change text", "change button", "change cta", "rename", "update text", "modify text"]):
            task_type = "copy_change"
        elif any(word in message_lower for word in ["reorder", "move section", "swap"]):
            task_type = "section_reorder"
        elif any(word in message_lower for word in ["color", "theme", "background"]):
            task_type = "color_change"
        elif any(word in message_lower for word in ["seo", "meta", "title tag", "description tag"]):
            task_type = "seo_update"
        elif any(word in message_lower for word in ["style", "css", "padding", "margin"]):
            task_type = "style_change"
        
        # Detect scope
        scope = []
        for key, files in self.COMMON_SCOPES.items():
            if key in message_lower:
                scope.extend(files[:1])  # Add first matching file
        
        if not scope:
            scope = ["app/components/Hero.tsx"]  # Default
        
        # Generate rules based on task type
        rules = self._generate_rules(task_type)
        
        # Determine auto_commit
        auto_commit = task_type in ["copy_change", "color_change", "seo_update"]
        
        # Calculate confidence
        confidence = 0.6 if scope else 0.4
        
        return {
            "type": task_type,
            "description": message,
            "scope": list(set(scope)),
            "rules": rules,
            "auto_commit": auto_commit,
            "confidence": confidence
        }
    
    def _generate_rules(self, task_type: str) -> list[str]:
        """Generate safety rules based on task type"""
        base_rules = [
            "Do not change layout structure",
            "Do not remove existing functionality",
            "Preserve all existing imports"
        ]
        
        type_rules = {
            "copy_change": [
                "Only modify text content",
                "Do not touch styles or classes",
                "Keep the same element types"
            ],
            "color_change": [
                "Only modify color values",
                "Keep the same variable names",
                "Do not change other style properties"
            ],
            "seo_update": [
                "Only modify meta tags",
                "Keep valid HTML structure",
                "Do not change page content"
            ],
            "section_reorder": [
                "Only change component order",
                "Do not modify component internals",
                "Keep all props intact"
            ],
            "style_change": [
                "Only modify style properties",
                "Keep responsive breakpoints",
                "Do not change structure"
            ]
        }
        
        return base_rules + type_rules.get(task_type, [])
    
    def _validate_intent(self, intent: dict) -> dict:
        """Validate and normalize the parsed intent"""
        # Ensure required fields
        if "type" not in intent:
            intent["type"] = "component_edit"
        
        if "description" not in intent:
            intent["description"] = "No description provided"
        
        if "scope" not in intent or not intent["scope"]:
            intent["scope"] = ["app/components/Hero.tsx"]
        
        if "rules" not in intent:
            intent["rules"] = self._generate_rules(intent["type"])
        
        if "auto_commit" not in intent:
            intent["auto_commit"] = intent["type"] in ["copy_change", "color_change", "seo_update"]
        
        if "confidence" not in intent:
            intent["confidence"] = 0.7
        
        # Validate task type
        if intent["type"] not in self.TASK_TYPES:
            intent["type"] = "component_edit"
        
        return intent
