import json
import base64
import os
import re
from PIL import Image
from PIL.PngImagePlugin import PngInfo

def sanitize_filename(name):
    """Takes a string and returns a valid filename."""
    if not name:
        return "unnamed_character"
    name = name.strip().replace('**', '').replace('*', '')
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:100]

def save_character_card(character_data, image_path, save_location):
    """Saves character data to a tEXt chunk in a PNG image."""
    try:
        card = {
            "name": character_data.get("NAME", ""),
            "description": character_data.get("DESCRIPTION", ""),
            "personality": character_data.get("PERSONALITY_SUMMARY", ""),
            "scenario": character_data.get("SCENARIO", ""),
            "first_mes": character_data.get("GREETING_MESSAGE", ""),
            "mes_example": character_data.get("EXAMPLE_MESSAGES", ""),
            "spec": "chara_card_v2"
        }

        chara_data_str = json.dumps(card)
        chara_data_base64 = base64.b64encode(chara_data_str.encode('utf-8')).decode('utf-8')

        img = Image.open(image_path)
        metadata = PngInfo()
        metadata.add_text("chara", chara_data_base64)
        
        clean_name = sanitize_filename(character_data.get('NAME'))
        output_path = os.path.join(save_location, f"{clean_name}.png")

        img.save(output_path, "png", pnginfo=metadata)
        print(f"\nCharacter card saved successfully to {output_path}")

    except FileNotFoundError:
        print(f"Error: The image path '{image_path}' was not found.")
    except Exception as e:
        print(f"\nError saving character card: {e}")