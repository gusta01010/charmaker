import requests
import json
import os
from image_handler import ImageHandler
from prompt import INSTRUCTIONS
try:
    from google import generativeai as genai
except ImportError:
    genai = None
    
class APIHandler:
    """Handles all API communications for different providers"""
    
    INSTRUCTIONS = INSTRUCTIONS

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