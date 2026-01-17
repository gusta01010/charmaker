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
    """Saves character data to a tEXt chunk in a PNG image using V3 format."""
    try:
        char_name = character_data.get("NAME", "")[:100]
        card = {
            "data": {
                "name": char_name,
                "description": character_data.get("DESCRIPTION", ""),
                "personality": character_data.get("PERSONALITY_SUMMARY", ""),
                "first_mes": character_data.get("GREETING_MESSAGE", ""),
                "avatar": "none",
                "mes_example": character_data.get("EXAMPLE_MESSAGES", ""),
                "scenario": character_data.get("SCENARIO", ""),
                "creator_notes": "",
                "system_prompt": "",
                "post_history_instructions": "",
                "alternate_greetings": [],
                "tags": [],
                "creator": "Anonymous",
                "character_version": "",
                "extensions": {
                    "depth_prompt": {
                        "prompt": "",
                        "depth": 0,
                        "role": "system"
                    },
                    "fav": False,
                    "talkativeness": "0.5",
                    "world": ""
                },
                "group_only_greetings": []
            },
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            # these are duplicated at the root level for compatibility
            "name": char_name,
            "fav": False,
            "description": character_data.get("DESCRIPTION", ""),
            "personality": character_data.get("PERSONALITY_SUMMARY", ""),
            "scenario": character_data.get("SCENARIO", ""),
            "first_mes": character_data.get("GREETING_MESSAGE", ""),
            "mes_example": character_data.get("EXAMPLE_MESSAGES", "")
        }

        chara_data_str = json.dumps(card, ensure_ascii=False)
        chara_data_base64 = base64.b64encode(chara_data_str.encode('utf-8')).decode('utf-8')

        img = Image.open(image_path)
        metadata = PngInfo()
        metadata.add_text("chara", chara_data_base64)
        
        clean_name = sanitize_filename(char_name)
        output_path = os.path.join(save_location, f"{clean_name}.png")

        img.save(output_path, "png", pnginfo=metadata)
        print(f"\nCharacter card saved successfully to {output_path}")

    except FileNotFoundError:
        print(f"Error: The image path '{image_path}' was not found.")
    except Exception as e:
        print(f"\nError saving character card: {e}")