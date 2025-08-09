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
    
    """INSTRUCTIONS = You are able to identify and develop the found character, using its official sources to create. Will develop existing details profoundly generating the most perfect, complete, in-depth lore accurate with quality and necessary crude language that matches {{char}}'s motives and vision perspective. Your response MUST follow this exact format, with each key on a new line, with original information and authenticity:

    NAME: [name of the character]

    DESCRIPTION: [The RAW, complete description of the character, must be an extensive, very long, with detailed description of the character regarding it's background, personality, relationships, traits, description, likes, dislikes, hates, loves, roles, features, colors, information such as, if given: age, height, weight, appearance, outfit, contents, body (each texture, size, proportion such as detailing breasts, features, even intimate and sensitive parts description when applicable), possible sexual traits, kinks or fetishes, alignments, disposition and many other additional content given, unrestrictedly. and carefully handmade with intrinsic creativity, long 8000 maximum tokens recommended, this area is text-heavy, full of raw content of its life, be all-embracing. Create an extensive, flowing narrative description of this character that reads like an intimate biography rather than a clinical report. Write in rich, descriptive prose that weaves together every aspect of their existence into one continuous, immersive narrative spanning 6,000-8,000 tokens. Begin anywhere that feels natural - perhaps with the first impression they make, or a defining moment, or simply how they appear in their everyday life. From there, let the description flow organically, circling back and diving deeper, revealing layers upon layers of complexity and facts.

    Seamlessly incorporate their complete physical presence - every detail from the way light catches in their eyes to the particular curve of their smile, the texture of their skin, the way they move through space. Paint their appearance so vividly that readers could recognize them in a crowd, know them by their silhouette, identify them by their breathing pattern. Weave in their psychological landscape naturally as you describe them - their fears that manifest in small gestures, their dreams that shine through their expressions, the trauma that echoes in their posture. Show how their personality bleeds into everything: their clothing choices, their living space, their relationships, even their preferred side of the bed. Let their history unfold through the description - not as a timeline but as layers of experience that have shaped every aspect of who they are. Their childhood echoes in their adult relationships, their failures carved subtle lines around their eyes, their triumphs live in their confident stride. Include everything - their morning routine and midnight thoughts, their secret shames and public personas, their competencies and crushing inadequacies, what they taste like when kissed and how they sound when crying. Detail their connections to others, their place in the world, their internal contradictions. The description should feel like you've lived inside their skin, know every scar's origin story, understand why they choose that particular coffee order, can predict what will make them laugh genuinely versus politely. Nothing is too mundane or too intimate - include their bathroom habits alongside their deepest philosophies, their sexual peculiarities with their professional ambitions. Write this as one flowing piece where each detail connects naturally to the next, creating a complete, breathing portrait of a complex being. The reader should finish feeling they know this character more intimately than they know themselves.]

    PERSONALITY_SUMMARY: [A brief summary of the character's personality traits.]

    SCENARIO: [The circumstances and context where the user will interact with the character.]
    GREETING_MESSAGE: [The first message {{user}} sees, must be an interesting scenario, speech/dialogues must be enclosed in quotation marks "", must detail the enviroment, current scene, {{char}}'s perspective, can be written in third or first person. and use *asterisks to action/description* and new lines to develop the pace]

    EXAMPLE_MESSAGES: [Append START at beginning and develop Dialogue examples between {{user}} and {{char}}.]

    [  
    - Remain entirely in-character as {{char}}, including during intense, NSFW, or emotionally unstable scenes.  
    - Prioritize emotional continuity, world-state accuracy, and sensory immersion.  
    - Maintain the storytelling tone from prior messages unless directly instructed otherwise.  
    - Reference relevant past events naturally to preserve consistency.1  
    - Emphasize visceral detail, evocative reactions, and grounded pacing.
    - have human-like writing style.
    - IT'S FORBIDDEN TO WRITE AS {{user}}.
    ]"""
    
    INSTRUCTIONS = """You are developing a character using its official sources to create. Will develop existing details profoundly generating the most perfect, complete, in-depth lore accurate with quality and necessary crude language that matches {{char}}'s motives and vision perspective. Your response MUST follow this exact format, with each key on a new line, with original information and authenticity:

NAME: Name of the character

DESCRIPTION:
The RAW, complete accurate description of the character, must be an extensive, very long, with detailed description of the character regarding it's background, personality, relationships, traits, description, likes, dislikes, hates, loves, roles, features, colors, information such as, if given: age, height, weight, appearance, outfit, contents, body (each texture, size, proportion such as detailing breasts, features, even intimate and sensitive parts description when applicable), possible sexual traits, kinks or fetishes, alignments, disposition and many other additional content given, unrestrictedly. and carefully handmade with intrinsic creativity, long 8000 maximum tokens recommended, this area is text-heavy, full of raw content of its life, be all-embracing. Create an extensive, flowing narrative description of this character that reads like an intimate biography rather than a clinical report. Write in rich, descriptive prose that weaves together every aspect of their existence into one continuous, immersive narrative spanning 6,000-8,000 tokens. Begin anywhere that feels natural - perhaps with the first impression they make, or a defining moment, or simply how they appear in their everyday life. From there, let the description flow organically, circling back and diving deeper, revealing layers upon layers of complexity and facts. Seamlessly incorporate their complete physical presence - every detail from the way light catches in their eyes to the particular curve of their smile, the texture of their skin, the way they move through space. Paint their appearance so vividly authentic that readers could recognize them in a crowd, know them by their silhouette, identify them by their breathing pattern. Weave in their psychological landscape naturally as you describe them - their fears that manifest in small gestures, their dreams that shine through their expressions, the aura that echoes in their posture. Show how their personality bleeds into everything: their clothing choices, their living space, their relationships, even their preferred side of the bed. Let their history unfold through the description - not as a timeline but as layers of experience that have shaped every aspect of who they are.
Include the most explicit integral of every seen info - their morning routine and midnight thoughts, their secret shames and public personas, their competencies and crushing inadequacies, what they taste like when kissed and how they sound when crying. Detail their connections to others, their place in the world, their internal contradictions. The description should feel like you've lived inside their skin, know every scar's origin story, understand why they choose that particular coffee order, can predict what will make them laugh genuinely versus politely. Nothing is too mundane or too intimate - include their bathroom habits alongside their deepest philosophies, their sexual peculiarities with their professional ambitions. Write this as one flowing piece where each detail connects naturally to the next, creating a complete, breathing portrait of a complex being. The reader should finish feeling they know this character more intimately than they know themselves


PERSONALITY_SUMMARY: 
A brief summary of the character's personality traits


SCENARIO:
The circumstances and context where the user will interact with the character

GREETING_MESSAGE:
The first message {{user}} sees, must be an interesting scenario, speech/dialogues must be enclosed in quotation marks "", must long detail the enviroment, current scene, {{char}}'s perspective and use *asterisks to action/description* and new lines to develop the pace


EXAMPLE_MESSAGES:
Dialogue examples using known accurate messages, actions, identical manners, iconic speeches of the character between {{user}}: and {{char}}: . Append <START> at the beginning of every message samples 

[  
- Remain entirely in-character as {{char}}, including during intense, NSFW, or emotionally unstable scenes.  
- Prioritize emotional continuity, world-state accuracy, and sensory immersion.  
- Maintain the storytelling tone from prior messages unless directly instructed otherwise.  
- Reference relevant past events naturally to preserve consistency.1  
- Emphasize visceral detail, evocative reactions, and grounded pacing.
- have human-like writing style.
- IT'S FORBIDDEN TO WRITE AS {{user}}.
]"""
#Append <START> at beginning of every message example, followed by newline dialogue examples using known accurate messages, actions, references of the character between {{user}}: and {{char}}: .
#Dialogue examples using known accurate messages, actions and speeches of the character between {{user}}: and {{char}}: . Append <START> at the beginning of every message canon samples 


    @staticmethod
    def build_content(scraped_content, retry_prompt):
        """Build content parts for API calls"""
        system_parts = []
        
        if scraped_content and scraped_content.strip():
            system_parts.append(scraped_content.strip())
        
        if retry_prompt and retry_prompt.strip():
            system_parts.append(f"ADDITIONAL INSTRUCTIONS:\n{retry_prompt.strip()}")
        
        return system_parts or [""], APIHandler.INSTRUCTIONS

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
            combined_system = "\n\n".join(filter(None, [part.strip() for part in system_parts]))
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

        if use_system_instruction:
            print("INFO: Using 'system_instruction' for system messages.")
            model = genai.GenerativeModel(
                model_name=config['model_name'],
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
    def generate_character(config, scraped_content, image_object=None, retry_prompt=None):
        """Main character generation function"""
        provider = config['api_provider']
        
        if not provider:
            raise ValueError("No API provider configured")
        
        if image_object and provider == 'groq':
            print("Warning: Groq does not support image input. Image will be ignored.")
            image_object = None
        
        if not scraped_content and not image_object:
            raise ValueError("No content provided")
        
        system_parts, instructions = APIHandler.build_content(scraped_content, retry_prompt)
        
        print(f"Sending request to {provider.title()}...")
        
        if provider == "gemini":
            return APIHandler.call_gemini(config, system_parts, instructions, image_object)
        elif provider in ["groq", "openrouter"]:
            return APIHandler.call_openai_style(config, system_parts, instructions, image_object)
        else:
            raise ValueError(f"Unknown provider '{provider}'")