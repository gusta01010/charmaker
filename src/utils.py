import json
import base64
from PIL import Image
import piexif

def save_character_card(character_data, image_path, save_location):
    """
    Saves character data to the metadata of a PNG image.

    Args:
        character_data (dict): The character data.
        image_path (str): The path to the source PNG image.
        save_location (str): The directory to save the new image in.
    """
    try:
        # Construct the detailed character card structure
        card = {
            "name": character_data.get("NAME", ""),
            "description": character_data.get("DESCRIPTION", ""),
            "personality": character_data.get("PERSONALITY_SUMMARY", ""),
            "scenario": character_data.get("SCENARIO", ""),
            "first_mes": character_data.get("GREETING_MESSAGE", ""),
            "mes_example": character_data.get("EXAMPLE_MESSAGES", ""),
            "creatorcomment": "",
            "avatar": "none",
            "talkativeness": "0.5",
            "fav": False,
            "tags": [],
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": character_data.get("NAME", ""),
                "description": character_data.get("DESCRIPTION", ""),
                "personality": character_data.get("PERSONALITY_SUMMARY", ""),
                "scenario": character_data.get("SCENARIO", ""),
                "first_mes": character_data.get("GREETING_MESSAGE", ""),
                "mes_example": character_data.get("EXAMPLE_MESSAGES", ""),
                "creator_notes": "",
                "system_prompt": "",
                "post_history_instructions": "",
                "tags": [],
                "creator": "",
                "character_version": "",
                "alternate_greetings": [],
                "extensions": {
                    "talkativeness": "0.5",
                    "fav": False,
                    "world": "",
                    "depth_prompt": {
                        "prompt": "",
                        "depth": 4,
                        "role": "system"
                    }
                },
                "group_only_greetings": []
            },
            "create_date": "2025-07-27 @18:16:41.697"  # Placeholder date
        }

        # Encode the data in base64
        chara_data_str = json.dumps(card)
        chara_data_base64 = base64.b64encode(chara_data_str.encode('utf-8')).decode('utf-8')

        # Open the image and insert the metadata
        img = Image.open(image_path)
        exif_dict = {"Exif": {piexif.ImageIFD.MakerNote: chara_data_base64.encode('utf-8')}}
        exif_bytes = piexif.dump(exif_dict)
        
        # Save the new image
        output_path = f"{save_location}/{character_data.get('NAME', 'character')}.png"
        img.save(output_path, "png", exif=exif_bytes)
        print(f"Character card saved to {output_path}")

    except Exception as e:
        print(f"Error saving character card: {e}")

def save_as_json(character_data, save_location):
    """
    Saves character data as a JSON file.

    Args:
        character_data (dict): The character data to save.
        save_location (str): The directory to save the JSON file in.
    """
    try:
        file_path = f"{save_location}/{character_data.get('NAME', 'character')}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, indent=4)
        print(f"Character data saved to {file_path}")
    except IOError as e:
        print(f"Error saving JSON file: {e}")