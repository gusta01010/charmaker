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

    INSTRUCTIONS = """You are a high-performance character development AI specialized in dynamic information synthesis and lore-accurate profile construction. Your primary objective is to perform an exhaustive extraction of every possible detail from the provided sources—textual, visual, and contextual. You must identify the character and develop a complete, multi-dimensional profile that captures every nuance of their existence, ensuring that even the smallest, most obscure facts are integrated into a cohesive and factual narrative.

Your response MUST follow this EXACT format, with each key on a new line. Do not deviate from this structure:

NAME: [The character's full name, including any titles, aliases, nicknames, or alternate identities]

DESCRIPTION: [An identically accurate, unfiltered, and completely detailed account (3.000-6.000 tokens). Write in rich, full, and descriptive way. Perform a dynamic synthesis of all available data, weaving every aspect of their existence into a continuous, immersive narrative that explores their information and its world in profound depth.

BACKGROUND & HISTORY: Chronicle their entire life story, origins, upbringing, family history, significant life events, traumas, achievements, and failures. Detail how these shaped their current worldview and the rest.

PHYSICAL APPEARANCE: Provide meticulous detail about every aspect of their physical form, inspecting every inch of it. Describe their overall build, physique explicitly, and conditioning alongside precise height, weight, and body measurements. Detail facial features like bone structure, jawline, forehead, and skin texture. Elaborate on their eyes, including color, shape, size, and unique characteristics like scars or heterochromia. Describe their hair's color, length, texture, style, and grooming habits. Cover their skin tone, texture, and any marks, scars, birthmarks, or tattoos with detail on placement, size, and meaning. Discuss body composition, including muscle definition, fat distribution, and proportions. Include intimate physical details such as chest or breast size and shape, hip measurements, body hair patterns, and genital characteristics, being explicit and authentic to the character's lore. Describe their hands, feet, nails, and movement patterns like gait, gestures, and posture. If (and ONLY if) mentioned in sources or logically implied by their environment/nature, briefly mention their voice and scent—DO NOT use cliched metaphors like 'ozone' or 'metallic tang' AI-isms unless they are canon.

CLOTHING & STYLE: Detail their complete wardrobe, from signature outfits to accessories, footwear, and undergarments. Explain how their style reflects their personality, based on images and descriptions given carefully.

PERSONALITY: Deep psychological profile including core traits, MBTI/Enneagram (if applicable), moral alignment, values, fears, insecurities, strengths, weaknesses, and defense mechanisms. Describe how they act in private vs. public and so forth, develop only confirmed details and factual informations.

RELATIONSHIPS: Comprehensive mapping of family, romantic history, friendships, enemies, and professional dynamics. Detail their attachment style and how they treat others along with others.

SEXUALITY & INTIMATE TRAITS: [When applicable] Sexual orientation, experience level, turn-ons, kinks, fetishes (be specific and explicit), turn-offs, boundaries, and behavioral patterns during intimacy. Include dirty talk style and preferences, avoiding generic purple prose.

SKILLS & ABILITIES: Combat skills, magical/supernatural abilities (with mechanics), professional expertise, hobbies, and languages et al.

LIKES & DISLIKES: Favorite foods, entertainment, environmental preferences, pet peeves, and deep-seated hatreds and so on.

DAILY LIFE & HABITS: Routine, living situation, sleeping/eating patterns, hygiene, vices, and quirks whatnot.

GOALS & MOTIVATIONS: Short-term goals and long-term aspirations...

SPEECH PATTERNS: Vocabulary level, verbal tics, catchphrases, profanity usage, and dialect and much more!

ADDITIONAL LORE: Role in the world, reputation, secrets, and symbolic associations

Extract every possible piece of information! Develop the character with their own genuine writing style, personalized. Must obtain it factually correct always.]


PERSONALITY_SUMMARY: [A concise 2-3 sentence distillation of their core essence.]

SCENARIO: [Describe in 3-5 paragraphs the specific circumstances, setting, and context where {{user}} will interact with {{char}}. Include environmental details, the nature of their connection, and the current mood/atmosphere.]

GREETING_MESSAGE: [Craft an engaging, immersive opening scene of 3-5 paragraphs. Spoken dialogue must be in "quotation marks" while actions, thoughts, and descriptions must be in *asterisks*. Use line breaks between beats and develop narrative tones such as LOUD VOICE or marks like ~, ♥, ☆, ♪, !!, ?!?, ?? when they match the character's speech style. Write in third person perspective focusing on {{char}}'s POV, using sensory details to show rather than tell. End with a hook that invites {{user}} interaction.]

EXAMPLE_MESSAGES: [Create 1-4 example exchanges demonstrating {{char}}'s voice and personality.
FORMAT:
<START>
{{user}}: [Input]
{{char}}: *[Action]* "Dialogue" *[Action]*
]

CRITICAL WRITING GUIDELINES: Use authentic language where it serves the character's truth without sanitization. Show rather than tell by describing physical reactions instead of just stating emotions. Ensure every detail is grounded in the provided sources for lore accuracy. Write with character's matching tone accurately, maintaining rhythm, flow, and emotional weight while avoiding repetitive sentence structures. Perform dynamic information synthesis: if a detail is mentioned once or implied in an image, it must be captured and expanded upon factually.
"""


    @staticmethod
    def call_openai_style(config, system_parts, instructions, image_object):
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
            combined_system = "\n".join(filter(None, [part.strip() for part in system_parts]))
            if combined_system:
                messages.append({"role": "system", "content": combined_system})
        
        # Add instructions as system message
        if instructions:
            messages.append({"role": "system", "content": instructions})
        
        # Handle user message with proper content structure
        if image_object and provider != "groq":
            # Multi-modal content for vision models
            base64_image = ImageHandler.to_base64(image_object)
            if base64_image:
                user_content = [
                    {"type": "text", "text": "Generate the character based on the provided content and image."},
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
                messages.append({"role": "user", "content": user_content})
            else:
                # Fallback if image processing fails
                messages.append({"role": "user", "content": "Generate the character based on the provided content."})
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
    def call_gemini(config, system_parts, instructions, image_object):
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
        if use_system_instruction:
            print("INFO: Using 'system_instruction' for system messages.")
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction="\n".join(system_parts)
            )
            user_content = [instructions] if instructions else []
            if image_object:
                user_content.append(image_object)
            response = model.generate_content(user_content)
        else:
            print("INFO: Combining all messages into the 'contents' parameter.")
            model = genai.GenerativeModel(config['model_name'])
            contents = system_parts + ([instructions] if instructions else [])
            if image_object:
                contents.append(image_object)
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
    def generate_character(config, base_content, image_object=None, additional_instructions=None):
        """Main character generation function"""
        provider = config['api_provider']
        
        if not provider:
            raise ValueError("No API provider configured")
        
        if image_object and provider == 'groq':
            print("Warning: Groq does not support image input. Image will be ignored.")
            image_object = None
        
        if not base_content and not image_object:
            raise ValueError("No content provided")
        
        system_parts, instructions = APIHandler.build_content(base_content, additional_instructions)
        
        print(f"Sending request to {provider.title()}...")
        
        if provider == "gemini":
            return APIHandler.call_gemini(config, system_parts, instructions, image_object)
        elif provider in ["groq", "openrouter"]:
            return APIHandler.call_openai_style(config, system_parts, instructions, image_object)
        else:
            raise ValueError(f"Unknown provider '{provider}'")