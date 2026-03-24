import tiktoken
import os
import re
import requests
import tempfile
from image_handler import ImageHandler
from api_handler import APIHandler
from scraper import scrape_with_selenium, is_valid_url_format
from character_card import save_character_card
import config_manager
import file_dialogs 

def parse_ai_response(ai_response):
    """Extract character fields from AI response"""
    character_details = {}
    keys = ["NAME", "DESCRIPTION", "PERSONALITY_SUMMARY", "SCENARIO", "GREETING_MESSAGE", "EXAMPLE_MESSAGES"]
    pattern = re.compile(r'(' + '|'.join(keys) + r')\s*:(.*?)(?=\n(?:' + '|'.join(keys) + r')\s*:|\Z)', re.DOTALL | re.IGNORECASE)
    
    for key, value in pattern.findall(ai_response):
        val = value.strip().replace('**', '').replace('*', '').strip()
        if key.upper().strip() == "NAME":
            val = val[:100]
        character_details[key.upper().strip()] = val
    
    return character_details

def get_inputs_from_user():
    """Get URLs and image from user input with improved validation"""
    urls_to_scrape, image_object = [], None
    print("\n--- Content Input ---")
    print("Enter URLs to scrape, image URLs, or '!' for local file.")
    print("Type 'done' when finished, or press Enter on empty line.")
    
    while True:
        user_input = input("URL, image URL, or command (!): ").strip()
        
        # Check for exit conditions
        if not user_input or user_input.lower() == 'done':
            break
            
        if user_input == '!':
            image_object = ImageHandler.load_image(user_input)
        elif ImageHandler.is_image_url(user_input):
            image_object = ImageHandler.load_image(user_input)
            if image_object:
                print("✓ Image loaded from URL")
        else:
            # process as regular URL
            url = user_input if user_input.startswith('http') else 'https://' + user_input
            
            # use validation from scraper.py
            if is_valid_url_format(url):
                urls_to_scrape.append(url)
                print(f"✓ Added '{url}' to scrape")
            else:
                print(f"✗ Invalid URL format: '{user_input}'")
    return urls_to_scrape, image_object

def get_character_image():
    """Get image for character card with improved handling"""
    while True:
        print("\nSelect image for character card:")
        print("1. Default template (./template.png)")
        print("2. Choose custom image file")
        print("3. Download from URL")
        
        choice = input("> ").strip()
        
        if choice == '1':
            return './template.png'
        elif choice == '2':
            return file_dialogs.open_image_dialog()
        elif choice == '3':
            url = input("Enter image URL: ").strip()
            if not url:
                continue
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                temp_path = ImageHandler.save_temp_image(response.content)
                if temp_path:
                    print("✓ Image downloaded successfully")
                    return temp_path
                    
            except Exception as e:
                print(f"✗ Error downloading image: {e}")
        else:
            print("Invalid choice.")

def handle_save(character_details, save_location):
    """Handle character saving with image selection"""
    image_path = get_character_image()
    if image_path and os.path.exists(image_path):
        save_character_card(character_details, image_path, save_location)
        # Clean up temp file if it was created
        ImageHandler.cleanup_temp_file(image_path)
        print("✓ Character saved successfully!")
    else:
        print("✗ No valid image path. Save cancelled.")

def count_tokens(text, model="gpt-4"):
    """Count tokens using tiktoken"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

def run_character_creation_flow(config):
    """Main character creation workflow"""
    urls, initial_image_object = get_inputs_from_user()
    if not urls and not initial_image_object:
        print("No content provided. Returning to menu.")
        return
    
    # scrape content if urls provided
    scraped_content = ""
    if urls:
        scraped_content = scrape_with_selenium(urls)
        if not scraped_content or not scraped_content.strip():
            print("Warning: No text content scraped.")
    
    if not scraped_content and not initial_image_object:
        print("✗ Scraping failed and no image provided.")
        return
    
    # shows content summary
    content_info = []
    if scraped_content:
        token_count = count_tokens(scraped_content)
        content_info.append(f"text (~{token_count} tokens)")
    if initial_image_object:
        content_info.append("image")
    
    if content_info:
        print(f"\n✓ Content ready: {' + '.join(content_info)}")
    
    initial_instructions = input("\nEnter any additional instructions for the AI (optional, press Enter to skip):\n> ").strip()

    if input("Proceed with AI generation? (yes/no): ").lower() not in ['yes', 'y', '1']:
        return
        

    # these variables hold the state for the current generation attempt
    content_for_generation = scraped_content
    image_for_generation = initial_image_object
    instructions_for_generation = initial_instructions

    while True:
        try:
            response_text = APIHandler.generate_character(
                config, 
                content_for_generation, 
                image_for_generation, 
                instructions_for_generation
            )
            
            character_details = parse_ai_response(response_text)
            
            if not character_details or not character_details.get("NAME"):
                raise ValueError("No character data generated")
            
            print("\n--- Generated Character ---")
            colors = {
                "NAME": "\033[93m",           # Yellow
                "DESCRIPTION": "\033[92m",    # Green  
                "PERSONALITY_SUMMARY": "\033[94m",  # Blue
                "SCENARIO": "\033[94m",       # Blue
                "GREETING_MESSAGE": "\033[93m"  # Orange (using yellow-orange)
            }
            reset_color = "\033[0m"  # Reset to default
            
            for key in ["NAME", "DESCRIPTION", "PERSONALITY_SUMMARY", "SCENARIO", "GREETING_MESSAGE"]:
                value = character_details.get(key, 'N/A')
                color = colors.get(key, "")
                print(f"{color}{key}:{reset_color}")
                print(f"{color}{value}{reset_color}")
                print()  # Add blank line between sections
            
            action = input("\n1. Save  2. Retry (with feedback)  3. Discard\n> ").strip()
            
            if action == '1':
                handle_save(character_details, config['save_location'])
                break
            elif action == '2':                
                content_for_generation = response_text
                
                instructions_for_generation = input("\nEnter feedback to refine the text above:\n> ").strip()
                
                image_for_generation = None
                
                print("\n✓ Ready to refine. The previous text will be used as the new context.")
            else:
                print("Character discarded.")
                break
                
        except Exception as e:
            print(f"✗ Generation failed: {e}")
            if input("Retry? (yes/no): ").lower() not in ['y', 'yes', '1']:
                return

def update_config_setting(config, setting_key, prompt, valid_values=None):
    """Unified config updater - returns None to stay in menu"""
    if setting_key == 'provider_change':
        current = config.get('api_provider', 'groq')
        providers = ['groq', 'openrouter', 'gemini']
        print(f"\nCurrent provider: {current}\nAvailable providers:")
        for p in providers:
            key = config.get(f'{p}_api_key', '')
            status = '✓' if key and 'YOUR_' not in key else '✗'
            current_mark = ' (current)' if p == current else ''
            print(f"  {status} {p}{current_mark}")

        new = input(f"Enter new provider ({'/'.join(providers)}): ").lower().strip()
        if new in providers:
            if config_manager.change_provider(config, new):
                print(f"✓ Provider changed to {new}")
                return None  # Stay in menu
            print("Provider change failed. Please configure the API key first.")
        else:
            print("Invalid provider selection.")

    elif setting_key == 'model_change':
        provider = config.get('api_provider', 'groq')
        model = config_manager.get_current_model(config)
        print(f"Current provider: {provider}\nCurrent model: {model}")
        new_model = input(f"Enter new model name for {provider}: ").strip()
        if new_model:
            config_manager.set_provider_model(config, provider, new_model)
            print(f"✓ Model changed to {new_model}")
            return None  # Stay in menu
        print("No model name provided.")

    elif setting_key == 'api_key_setup':
        provider = input("Enter provider to configure API key (groq/openrouter/gemini): ").lower().strip()
        if provider in ['groq', 'openrouter', 'gemini']:
            api_key = input(f"Enter API key for {provider}: ").strip()
            if api_key:
                config[f'{provider}_api_key'] = api_key
                config_manager.save_config(config)
                print(f"✓ API key for {provider} configured successfully!")
                return None  # Stay in menu
            print("No API key provided.")
        else:
            print("Invalid provider.")

    elif valid_values:
        value = input(f"{prompt} ({'/'.join(valid_values)}): ").lower().strip()
        if value in valid_values:
            config[setting_key] = value
            config_manager.save_config(config)
            print(f"✓ {setting_key} updated to {value}")
            return None  # Stay in menu
    else:
        value = input(f"{prompt}: ").strip()
        if value:
            config[setting_key] = value
            config_manager.save_config(config)
            print(f"✓ {setting_key} updated to {value}")
            return None  # Stay in menu
    
    return None  # Always stay in menu

def _is_provider_ready(config):
    """Check if current provider is configured"""
    provider = config.get('api_provider', 'groq')
    api_key = config.get(f'{provider}_api_key', '')
    if not api_key or 'YOUR_' in api_key:
        print(f"✗ ERROR: API key for {provider} is not configured!")
        print("Please configure your API key first (option 5).")
        return False
    return True

def _change_save_location(config):
    """Change save location - returns None to stay in menu"""
    new_path = file_dialogs.open_folder_dialog(config['save_location'])
    if new_path:
        config['save_location'] = new_path
        config_manager.save_config(config)
        print(f"✓ Save location updated to: '{new_path}'")
    return None  # Stay in menu

def _toggle_separate_system_messages(config):
    """Toggle separate system messages setting - returns None to stay in menu"""
    current = config.get('separate_system_messages', False)
    config['separate_system_messages'] = not current
    config_manager.save_config(config)
    status = "enabled" if config['separate_system_messages'] else "disabled"
    print(f"✓ Separate system messages is now {status}.")
    return None  # Stay in menu

def _exit_program():
    """Exit the program - returns True to break the loop"""
    print("Exiting program.")
    return True

def _toggle_gemini_grounding(config):
    current = config.get('gemini_grounding', False)
    config['gemini_grounding'] = not current
    config_manager.save_config(config)
    status = "enabled" if config['gemini_grounding'] else "disabled"
    print(f"✓ Gemini Grounding with Google Search is now {status}.")
    return None

def _scraping_options_menu(config):
    while True:
        print(f"\n{'-'*40}")
        print("\t Scraping Options")
        print(f"{'-'*40}")
        
        engine = config.get('scraper_engine', 'legacy')
        headless = "enabled" if config.get('crawl4ai_headless', True) else "disabled"
        
        print(f"  Current Engine: {engine}")
        if engine == 'crawl4ai':
            print(f"  Headless Mode: {headless}")
        print(f"{'-'*40}")
        
        options = [
            "Switch Scraper Engine (legacy / crawl4ai)",
            "Toggle Crawl4AI Headless Mode",
            "Back to Settings"
        ]
        
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")
            
        choice = input("\nSelect option > ").strip()
        
        if choice == '1':
            update_config_setting(config, 'scraper_engine', 'Select Engine', ['legacy', 'crawl4ai'])
        elif choice == '2':
            current_h = config.get('crawl4ai_headless', True)
            config['crawl4ai_headless'] = not current_h
            config_manager.save_config(config)
            print(f"✓ Headless mode is now {'enabled' if not current_h else 'disabled'}.")
        elif choice == '3':
            break

def _settings_menu(config):
    """Settings submenu loop"""
    while True:
        print(f"\n{'-'*60}")
        print("\t\t\t Settings")
        print(f"{'-'*60}")
        
        provider = config.get('api_provider', 'groq')
        model = config_manager.get_current_model(config)
        api_key = config.get(f'{provider}_api_key', '')
        key_status = '✓ Configured' if (api_key and 'YOUR_' not in api_key) else '✗ Not Set'
        
        print(f"  Provider: {provider.upper()} | Model: {model}")
        print(f"  API Key: {key_status}")
        print(f"  Save Location: '{config['save_location']}'")
        separate_status = "enabled" if config.get('separate_system_messages', False) else "disabled"
        print(f"  Separate System Messages: {separate_status}")
        
        # display Gemini grounding status if provider is gemini
        if provider == 'gemini':
            grounding_status = "enabled" if config.get('gemini_grounding', False) else "disabled"
            print(f"  Gemini Grounding: {grounding_status}")
            
        print(f"  Preset: {config.get('preset', 'Preset 3')}")
        print(f"  Scraper Engine: {config.get('scraper_engine', 'legacy')}")
        print(f"{'-'*60}")

        settings_options = [
            "Change Save Location",
            "Switch Provider",
            "Change Model (Current Provider)",
            "Configure API Keys",
            "Toggle Separate System Messages",
            "Preset Selection"
        ]
        
        if provider == 'gemini':
            settings_options.append("Toggle Gemini Grounding (Google Search)")
            
        settings_options.append("Scraping Options")
        settings_options.append("Back to Main Menu")

        for i, opt in enumerate(settings_options, 1):
            print(f"{i}. {opt}")

        choice = input("\nSelect option > ").strip()
        
        try:
            choice_idx = int(choice) - 1
            if choice_idx < 0 or choice_idx >= len(settings_options):
                raise ValueError()
            selected_opt = settings_options[choice_idx]
        except ValueError:
            print("Invalid option. Please try again.")
            continue

        if selected_opt == "Change Save Location":
            _change_save_location(config)
        elif selected_opt == "Switch Provider":
            update_config_setting(config, 'provider_change', 'Switch provider')
        elif selected_opt == "Change Model (Current Provider)":
            update_config_setting(config, 'model_change', 'Change model')
        elif selected_opt == "Configure API Keys":
            update_config_setting(config, 'api_key_setup', 'Configure API keys')
        elif selected_opt == "Toggle Separate System Messages":
            _toggle_separate_system_messages(config)
        elif selected_opt == "Preset Selection":
            update_config_setting(config, 'preset', 'Select Preset', ['preset 1', 'preset 2', 'preset 3'])
        elif selected_opt == "Toggle Gemini Grounding (Google Search)":
            _toggle_gemini_grounding(config)
        elif selected_opt == "Scraping Options":
            _scraping_options_menu(config)
        elif selected_opt == "Back to Main Menu":
            break

def main():
    """Main application loop"""
    config = config_manager.load_config()

    menu_actions = {
        '0': lambda: os.system('python interface.py') or _exit_program(),
        '1': lambda: run_character_creation_flow(config) if _is_provider_ready(config) else None,
        '2': lambda: _settings_menu(config),
        '3': _exit_program
    }

    while True:
        os.makedirs(config['save_location'], exist_ok=True)

        print(f"\n{'='*60}")
        print("\t\t\t CharMaker")
        print(f"{'='*60}")

        menu_options = [
            "🪟  (NEW!) Switch to GUI Mode",
            "🚀 Start Character Creation",
            "⚙️ Settings",
            "❌ Exit"
        ]

        for i, opt in enumerate(menu_options, 0):
            print(f"{i}. {opt}")

        choice = input("\nSelect option > ").strip()

        if choice in menu_actions:
            result = menu_actions[choice]()
            if result is True:  # Only exit if explicitly returning True
                break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()