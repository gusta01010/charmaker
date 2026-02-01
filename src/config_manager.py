import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
DEFAULT_CONFIG = {
    "save_location": "saved_characters",
    "api_provider": "groq",
    "groq_api_key": "YOUR_GROQ_API_KEY_HERE",
    "openrouter_api_key": "YOUR_OPENROUTER_API_KEY_HERE",
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "separate_system_messages": False,
    "browser_config": {
        "browser_type": None,
        "binary_path": None
    },
    # Provider-specific model configurations
    "provider_models": {
        "groq": "llama-3.1-70b-versatile",
        "openrouter": "openai/gpt-4o-mini",
        "gemini": "gemini-2.0-flash-exp"
    }
}

def load_config():
    """Loads config from config.json, creating it if it doesn't exist."""
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file not found. Creating '{CONFIG_FILE}' with default values.")
        config = DEFAULT_CONFIG.copy()
        save_config(config)
    else:
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            for key, value in DEFAULT_CONFIG.items():
                if key not in config and key != "model_name":
                    config[key] = value
            
            # Migration: Convert old model_name to provider-specific models
            if "model_name" in config and "provider_models" not in config:
                print("Migrating configuration to provider-specific models...")
                config["provider_models"] = DEFAULT_CONFIG["provider_models"].copy()
                # Try to preserve the old model for the current provider
                current_provider = config.get("api_provider", "groq")
                if current_provider in config["provider_models"]:
                    config["provider_models"][current_provider] = config["model_name"]
                
                print("Removing legacy model_name field after migration.")
                del config["model_name"]
                save_config(config)
                
            if "provider_models" in config:
                for provider in DEFAULT_CONFIG["provider_models"]:
                    if provider not in config["provider_models"]:
                        config["provider_models"][provider] = DEFAULT_CONFIG["provider_models"][provider]
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading config file: {e}. Loading default config.")
            config = DEFAULT_CONFIG.copy()

    return config

def save_config(config_data):
    """Saves the given configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        print("Configuration saved successfully.")
    except IOError as e:
        print(f"Error saving config file: {e}")

def get_current_model(config):
    """Get the model name for the current provider."""
    current_provider = config.get("api_provider", "groq")
    provider_models = config.get("provider_models", {})
    
    # Return provider-specific model if available
    if current_provider in provider_models:
        return provider_models[current_provider]
    
    # Fallback to legacy model_name
    return config.get("model_name", DEFAULT_CONFIG["provider_models"].get(current_provider, ""))

def set_provider_model(config, provider, model_name):
    """Set the model name for a specific provider."""
    if "provider_models" not in config:
        config["provider_models"] = DEFAULT_CONFIG["provider_models"].copy()
    
    config["provider_models"][provider] = model_name
    save_config(config)
    print(f"Model for {provider} set to: {model_name}")

def change_provider(config, new_provider):
    """Change the current provider while preserving all API keys and models."""
    if new_provider not in ["groq", "openrouter", "gemini"]:
        print(f"Invalid provider: {new_provider}")
        return False
    
    old_provider = config.get("api_provider")
    config["api_provider"] = new_provider
    
    current_model = get_current_model(config)
    print(f"Switched from {old_provider} to {new_provider}")
    print(f"Using model: {current_model}")
    
    # Check if API key is configured
    api_key = config.get(f"{new_provider}_api_key", "")
    if not api_key or "YOUR_" in api_key:
        print(f"WARNING: API key for {new_provider} is not configured!")
        return False
    
    save_config(config)
    return True

def get_provider_info(config):
    """Get comprehensive information about all providers."""
    current_provider = config.get("api_provider", "groq")
    provider_models = config.get("provider_models", {})
    
    info = {
        "current_provider": current_provider,
        "current_model": get_current_model(config),
        "providers": {}
    }
    
    for provider in ["groq", "openrouter", "gemini"]:
        api_key = config.get(f"{provider}_api_key", "")
        has_key = api_key and "YOUR_" not in api_key
        model = provider_models.get(provider, "Not set")
        
        info["providers"][provider] = {
            "has_api_key": has_key,
            "model": model,
            "is_current": provider == current_provider
        }
    
    return info

# Backward compatibility functions
def get_model_name(config):
    """Legacy function for backward compatibility."""
    return get_current_model(config)