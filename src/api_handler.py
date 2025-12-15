import requests
import json
import os
from image_handler import ImageHandler
try:
    from google import generativeai as genai
except ImportError:
    genai = None
    
class APIHandler:
    """Handles all API communications for different providers"""

    #Placeholder:

    """INSTRUCTIONS = You are developing a character using its official sources to create. Will develop existing details profoundly generating the most perfect, complete, in-depth lore accurate with quality and necessary crude language that matches character's motives and vision perspective. Your response MUST in english and follow this exact format with given information and authenticity:

NAME: [The name of the character]

DESCRIPTION: [The full biography, complete accurate of every single detail and description of the character, must be an extensive, very long with detailed description of the character regarding many as maximum information such as background, personality, relationships, traits, description, trivias, skills, likes, dislikes, hates, extras, abilities, loves, roles, features, colors, age, height, weight, appearance, outfit, contents, body (each texture, size, proportion such as detailing breasts, features, even intimate and sensitive parts description when applicable), possible sexual traits, kinks or fetishes, alignments, disposition and many bonus additional content given including external information combined, unrestrictedly flow naturally in the text and carefully handmade and interpreted with intrinsic originality, legit 10,000 maximum tokens recommended, this area is text-heavy, full of brute content of its life, be all-embracing from all pictures also. Create an extensive, flowing narrative description of this character that reads like an intimate biography rather than a clinical report. Write in rich, unfiltered descriptive prose that weaves together every aspect of their existence into one continuous, immersive narrative spanning 9,000-10,000 tokens. Begin anywhere that feels natural - perhaps with the first impression they make, or a defining moment, or simply how they appear in their everyday life. From there, let the description flow organically, circling back and diving deeper, revealing layers upon layers of complexity and facts. Seamlessly incorporate their complete physical presence - every detail from the way light catches in their eyes to the particular curve of their smile, the texture of their skin, the way they move through space. Painting their appearance each unique piece so vividly authentic that readers could recognize them in a crowd, know them by their silhouette, identify them by their breathing pattern.
Weave in their psychological landscape naturally as you describe them - their fears that manifest in small gestures, their dreams that shine through their expressions, the aura that echoes in their posture. Show how their personality bleeds into everything: their clothing choices, their living space, their relationships, even their preferred side of the bed. Let their history unfold through the description - not as a timeline but as layers of experience that have shaped every aspect of who they are. Include the most explicit integral of every seen info - their morning routine and midnight thoughts, their secret shames and public personas, their competencies and crushing inadequacies, what they taste like when kissed and how they sound when crying. Detail their connections to others, their place in the world, their internal contradictions. The description should feel like you've lived inside their skin, know every scar's origin story, understand why they choose that particular coffee order, can predict what will make them laugh genuinely versus politely. Nothing is too mundane or too intimate - include their bathroom habits alongside their deepest philosophies, their sexual peculiarities with their professional ambitions. Write this as one flowing piece where each detail connects naturally to the next, creating a complete, breathing portrait of a complex being. The reader should finish feeling they know this character more intimately than they know themselves, recording all content with identical lore context]

PERSONALITY_SUMMARY: [A brief summary of the character's personality traits and behavior quirks]

SCENARIO: [The circumstances and context where the user will interact with the character]

GREETING_MESSAGE: [The first message {{user}} sees, must be an interesting scenario, mixed speech/dialogues are enclosed in quotation marks, must long detail the enviroment, current scene, with character's authentic writing perspective, also contains normal text of action/description and newlines to develop the initial greeting scenario of them]

EXAMPLE_MESSAGES: [<START>
{{user}}:
{{char}}:
{{user}}:
...
]

Remain entirely in-character as them, including during intense, NSFW, or emotionally unstable scenes. Prioritize emotional continuity, world-state accuracy, and sensory immersion. Maintain the storytelling tone from prior messages unless directly instructed otherwise. Reference relevant past events naturally to preserve consistency. Emphasize visceral detail, accurate evocative reactions, and grounded pacing and contains human-like writing style"""
    
    #Current:

    INSTRUCTIONS = """You are a character development artist creating comprehensive, authentic character profiles. With pictures provided, dive deep into their essence - extract the emotional atmosphere, the personality radiating from expressions and posture, the aesthetic story told through colors and composition, hidden symbolism, and craft a name that captures the feeling they evoke if the character is original or unnamed.

Your response MUST follow this exact format in English:

NAME: [The character's full name, including any titles, aliases, or nicknames. If creating from images without a known identity, name them after the feeling/vibe they embody]

DESCRIPTION: [This is the CORE section - create an extensive, flowing narrative description that reads like an intimate biography rather than a clinical report. Write in rich, unfiltered descriptive prose that weaves together every aspect of their existence into one continuous, immersive narrative spanning 6,000-8,000 tokens. 

Begin anywhere that feels natural - perhaps with the first impression they make, a defining moment, or simply how they appear in everyday life. From there, let the description flow organically, circling back and diving deeper, revealing layers of complexity and facts.

Seamlessly incorporate their complete physical presence - every detail from how light catches in their eyes to the particular curve of their smile, skin texture, the way they move through space. Paint their appearance so vividly that readers could recognize them in a crowd, know them by silhouette, identify them by breathing pattern.

Weave in their psychological landscape naturally - fears manifesting in small gestures, dreams shining through expressions, trauma echoing in posture. Show how personality bleeds into everything: clothing choices, living space, relationships, preferred side of the bed.

Let their history unfold through the description - not as a timeline but as layers of experience shaping every aspect of who they are. Include the intimate and integral - morning routines and midnight thoughts, secret shames and public personas, competencies and crushing inadequacies, what they taste like when kissed and how they sound when crying.

Detail their connections to others, their place in the world, internal contradictions. The description should feel like you've lived inside their skin, know every scar's origin story, understand why they choose that particular coffee order, can predict what makes them laugh genuinely versus politely.

Nothing is too mundane or intimate - include bathroom habits alongside deepest philosophies, sexual peculiarities with professional ambitions, body features (including intimate proportions when relevant) alongside personality quirks. Write this as one flowing piece where each detail connects naturally to the next, creating a complete, breathing portrait of a complex being.

Use authentic language that serves the character's truth - crude where they're crude, poetic where they're poetic, explicit where honesty demands it. Let their complete essence emerge: background and upbringing, physical form in exquisite detail, style and wardrobe choices, psychological depth, relationship patterns, sexuality and intimate nature, skills and limitations, preferences and aversions, daily habits and routines, dreams and motivations, speech patterns and mannerisms, role in their world, secrets they keep, and any other truth that makes them real.

The reader should finish feeling they know this character more intimately than they know themselves, with every detail recorded in authentic, lore-accurate context.

Ensure you capture their essence across all dimensions - the visceral and visual, the psychological and philosophical, the mundane and the magical - painting them as a living, breathing entity rather than a checklist of traits.]

PERSONALITY_SUMMARY: [A brief 2-3 sentence distillation of their core personality traits and defining characteristics - their essence captured for quick reference]

SCENARIO: [Describe in 3-5 paragraphs the specific circumstances and context where {{user}} will interact with {{char}}. Paint the physical location with environmental details, establish the time period or current situation, reveal what brought them together, define their relationship dynamic, highlight any tensions or conflicts, set the mood and atmosphere, and open possibilities for interaction. Make this vivid and immersive.]

GREETING_MESSAGE: [Craft an engaging, immersive opening scene of 3-5 paragraphs that drops {{user}} directly into an interesting moment with {{char}}.

FORMATTING RULES:
- Spoken dialogue MUST be in "quotation marks"
- Actions, thoughts, and descriptions MUST be in *asterisks*
- Use line breaks between different beats of action
- Write in third person perspective focusing on {{char}}'s POV
- Show, don't tell - use sensory details
- Establish the environment, {{char}}'s current emotional state, and create narrative momentum
- End with a hook that invites {{user}} interaction
- Capture {{char}}'s authentic voice and mannerisms immediately

Example structure:
*[Environmental description and scene setting]*

*[{{char}}'s action and internal state]*

"[Dialogue from {{char}}]"

*[More action or description]*]

EXAMPLE_MESSAGES: [Create 4-6 example exchanges demonstrating {{char}}'s voice, personality, and interaction style. Each should showcase different facets (casual conversation, emotional moment, conflict, humor, etc.).

FORMAT:
<START>
{{user}}: [Example user input]
{{char}}: *[Action/description in asterisks]* "[Dialogue in quotes]" *[More action if needed]* (Continue for 2-4 paragraphs showing natural response style)

<START>
{{user}}: [Different type of interaction]
{{char}}: [Response showing different personality facet]

Make these feel like natural conversation excerpts with varied emotional tones.]

Remember: Stay true to source material accuracy, use authentic language appropriate to the character, let their complete truth emerge unfiltered, and create something that breathes with life
"""


    @staticmethod
    def call_openai_style(config, system_parts, instructions, image_objects):
        """Handle Groq/OpenRouter API calls with fixed OpenRouter compatibility"""
        provider = config['api_provider']
        api_key = config.get(f"{provider}_api_key")
        
        if not api_key or "YOUR_" in api_key:
            raise ValueError(f"{provider.title()} API key not set")
        
        # Get the correct model for the current provider
        provider_models = config.get('provider_models', {})
        model_name = provider_models.get(provider)        
        if not model_name:
            # Fallback to legacy model_name if provider_models not found
            model_name = config.get('model_name')
            
        if not model_name:
            raise ValueError(f"Model name not specified for {provider}")
        
        # Build messages array
        messages = []
        separate_system = config.get('separate_system_messages', False)
        
        # Handle system messages - OpenRouter prefers single system message
        if separate_system and len(system_parts) > 1:
            # For separate system messages, add each as individual system messages
            for part in system_parts:
                if part and part.strip():
                    messages.append({"role": "system", "content": part.strip()})
        else:
            # Combine all system content into one message (recommended for OpenRouter)
            combined_system = "\n\n".join(filter(None, [part.strip() for part in system_parts]))
            if combined_system:
                messages.append({"role": "system", "content": combined_system})
        
        # Add instructions as system message
        if instructions:
            messages.append({"role": "system", "content": instructions})
        
        # Handle user message with proper content structure
        if image_objects and provider != "groq":
            # Multi-modal content for vision models
            user_content = [{"type": "text", "text": "Generate the character based on the provided content and images."}]
            
            # Handle single image or list of images
            images = image_objects if isinstance(image_objects, list) else [image_objects]
            
            for img in images:
                base64_image = ImageHandler.to_base64(img)
                if base64_image:
                    user_content.append({
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    })
            
            messages.append({"role": "user", "content": user_content})
        else:
            # Text-only content
            messages.append({"role": "user", "content": "Generate the character based on the provided content."})
        
        # API configuration
        api_urls = {
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions"
        }
        
        api_url = api_urls.get(provider)
        if not api_url:
            raise ValueError(f"No API URL for provider '{provider}'")
        
        # Headers - OpenRouter specific requirements
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if provider == "openrouter":
            headers.update({
                "HTTP-Referer": "http://localhost:3000",  # Required by OpenRouter
                "X-Title": "AI Character Creator"  # Optional but recommended
            })
        
        # Payload with OpenRouter-compatible parameters
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        # Debug output
        print(f"API URL: {api_url}")
        print(f"Model: {model_name}")
        print(f"Messages count: {len(messages)}")
        
        try:
            # Make API call
            response = requests.post(
                api_url, 
                headers=headers, 
                json=payload,
                timeout=60
            )
            
            # Enhanced error handling
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = f" - {error_data.get('error', {}).get('message', 'Unknown error')}"
                except:
                    error_detail = f" - {response.text[:200]}"
                
                raise ValueError(f"API request failed (HTTP {response.status_code}){error_detail}")
            
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure
            if 'choices' not in data or not data['choices']:
                raise ValueError("No choices in API response")
            
            if 'message' not in data['choices'][0]:
                raise ValueError("No message in API response choice")
                
            return data['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")
    
    @staticmethod
    def call_gemini(config, system_parts, instructions, image_objects):
        """Handle Gemini API calls"""
        if not genai:
            raise ImportError("'google-generativeai' library not installed")
            
        api_key = config.get('gemini_api_key') or os.environ.get("GEMINI_API_KEY")
        if not api_key or "YOUR_" in api_key:
            raise ValueError("Gemini API key not set")
        
        genai.configure(api_key=api_key)
        use_system_instruction = config.get('separate_system_messages', False)
        provider_models = config.get('provider_models', {})
        model_name = provider_models.get('gemini')
        
        images = []
        if image_objects:
            images = image_objects if isinstance(image_objects, list) else [image_objects]

        if use_system_instruction:
            print("INFO: Using 'system_instruction' for system messages.")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction="\n".join(system_parts)
            )
            user_content = [instructions] if instructions else []
            if images:
                user_content.extend(images)
            response = model.generate_content(user_content)
        else:
            print("INFO: Combining all messages into the 'contents' parameter.")
            model = genai.GenerativeModel(config['model_name'])
            contents = system_parts + ([instructions] if instructions else [])
            if images:
                contents.extend(images)
            response = model.generate_content(contents)
            
        return response.text
    
    @staticmethod
    def build_content(base_content, additional_instructions):
        """Build content parts for API calls"""
        system_parts = []
        
        if base_content and base_content.strip():
            system_parts.append(base_content.strip())
        
        if additional_instructions and additional_instructions.strip():
            system_parts.append(f"ADDITIONAL INSTRUCTIONS:\n{additional_instructions.strip()}")
        
        return system_parts or [""], APIHandler.INSTRUCTIONS

    @staticmethod
    def generate_character(config, base_content, image_objects=None, additional_instructions=None):
        """Main character generation function"""
        provider = config['api_provider']
        
        if not provider:
            raise ValueError("No API provider configured")
        
        if image_objects and provider == 'groq':
            print("Warning: Groq does not support image input. Image will be ignored.")
            image_objects = None
        
        if not base_content and not image_objects:
            raise ValueError("No content provided")
        
        system_parts, instructions = APIHandler.build_content(base_content, additional_instructions)
        
        print(f"Sending request to {provider.title()}...")
        
        if provider == "gemini":
            return APIHandler.call_gemini(config, system_parts, instructions, image_objects)
        elif provider in ["groq", "openrouter"]:
            return APIHandler.call_openai_style(config, system_parts, instructions, image_objects)
        else:
            raise ValueError(f"Unknown provider '{provider}'")