import requests
import json
import os
import sys
import importlib.util
from image_handler import ImageHandler

def load_instructions():
    """
    loads INSTRUCTIONS from an external prompt.py file if it exists 
    next to the executable/script, otherwise falls back to internal version.
    """
    # get the directory where the EXE (if frozen) or script is located
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    prompt_path = os.path.join(base_path, 'prompt.py')
    
    # Try to load from the external file if it exists
    if os.path.exists(prompt_path):
        try:
            # use importlib to dynamically load the python file as a module
            spec = importlib.util.spec_from_file_location("prompt_external", prompt_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'INSTRUCTIONS'):
                return module.INSTRUCTIONS
        except Exception as e:
            print(f" Warning: Found external prompt.py but failed to load it: {e}")
            print("  Falling back to internal prompt...")
    
    # fallback to internal prompt
    try:
        from prompt import INSTRUCTIONS
        return INSTRUCTIONS
    except ImportError:
        return "Error: Could not find character generation instructions."

try:
    from google import genai
    from google.genai.types import GoogleSearch
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None
    
class APIHandler:
    """Handles all API communications for different providers"""
    
    INSTRUCTIONS = load_instructions()

    @staticmethod
    def _normalize_images(image_input):
        """Normalize image input to a list for multi-image support."""
        if image_input is None:
            return []
        if isinstance(image_input, list):
            return [img for img in image_input if img is not None]
        return [image_input]

    @staticmethod
    def _combine_same_roles(messages):
        """Combine adjacent messages with the same role (system-system, user-user)."""
        if not messages:
            return messages

        combined = [messages[0]]
        for msg in messages[1:]:
            last = combined[-1]
            if msg.get("role") == last.get("role") and isinstance(msg.get("content"), str) and isinstance(last.get("content"), str):
                last["content"] = f"{last['content']}\n\n{msg['content']}"
            else:
                combined.append(msg)
        return combined

    @staticmethod
    def call_openai_style(config, content_text, instructions, image_objects):
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
        content_role = 'system'

        # Preset/prompt message must be first system message
        if instructions:
            messages.append({"role": "system", "content": instructions})

        # Add scraped/assembled content as selected role
        if content_text and content_text.strip():
            messages.append({"role": content_role, "content": content_text.strip()})
        
        # Handle user message with proper content structure
        images = APIHandler._normalize_images(image_objects)
        if images and provider != "groq":
            # Multi-modal content for vision models
            user_content = [
                {"type": "text", "text": "Generate the character based on the provided content and images."}
            ]

            added_images = 0
            for img in images:
                base64_image = ImageHandler.to_base64(img)
                if base64_image:
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    )
                    added_images += 1

            if added_images > 0:
                messages.append({"role": "user", "content": user_content})
            else:
                # Fallback if image processing fails
                messages.append({"role": "user", "content": "Generate the character based on the provided content."})
        else:
            # Text-only content
            messages.append({"role": "user", "content": "Generate the character based on the provided content."})

        # If separate message mode is disabled, combine adjacent same-role messages
        if not separate_system:
            messages = APIHandler._combine_same_roles(messages)
        
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
    def call_gemini(config, content_text, instructions, image_objects):
        """Handle Gemini API calls"""
        if not genai:
            raise ImportError("'google-genai' library not installed")
            
        api_key = config.get('gemini_api_key') or os.environ.get("GEMINI_API_KEY")
        if not api_key or "YOUR_" in api_key:
            raise ValueError("Gemini API key not set")
        
        client = genai.Client(api_key=api_key)
        content_role = 'system'

        provider_models = config.get('provider_models', {})
        model_name = provider_models.get('gemini')
        # Preset/prompt must be first system content.
        system_chunks = [instructions] if instructions else []
        user_content = []

        if content_text and content_text.strip():
            if content_role == 'system':
                system_chunks.append(content_text.strip())
            else:
                user_content.append(content_text.strip())

        images = APIHandler._normalize_images(image_objects)

        if images:
            user_content.append("Generate the character based on the provided content and image.")
            user_content.extend(images)
        else:
            user_content.append("Generate the character based on the provided content.")

        use_grounding = config.get('gemini_grounding', False)
        tools = [GoogleSearch] if use_grounding else None

        response = client.models.generate_content(
            model=model_name,
            config=genai_types.GenerateContentConfig(
                system_instruction="\n\n".join([chunk for chunk in system_chunks if chunk]),
                tools=tools
            ),
            contents=user_content
        )
            
        return response.text
    
    @staticmethod
    def build_content(base_content, additional_instructions):
        """Build content payload and preset instructions for API calls."""
        content_chunks = []

        if base_content and base_content.strip():
            content_chunks.append(base_content.strip())

        if additional_instructions and additional_instructions.strip():
            content_chunks.append(f"ADDITIONAL INSTRUCTIONS:\n{additional_instructions.strip()}")

        content_text = "\n\n".join(content_chunks)
        return content_text, APIHandler.INSTRUCTIONS

    @staticmethod
    def generate_character(config, base_content, image_object=None, additional_instructions=None):
        """Main character generation function"""
        provider = config['api_provider']
        images = APIHandler._normalize_images(image_object)
        
        if not provider:
            raise ValueError("No API provider configured")
        
        if images and provider == 'groq':
            print("Warning: Groq does not support image input. Images will be ignored.")
            images = []
        
        if not base_content and not images:
            raise ValueError("No content provided")
        
        content_text, instructions = APIHandler.build_content(base_content, additional_instructions)
        
        print(f"Sending request to {provider.title()}...")
        
        if provider == "gemini":
            return APIHandler.call_gemini(config, content_text, instructions, images)
        elif provider in ["groq", "openrouter"]:
            return APIHandler.call_openai_style(config, content_text, instructions, images)
        else:
            raise ValueError(f"Unknown provider '{provider}'")