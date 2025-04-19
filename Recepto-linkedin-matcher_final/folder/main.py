import os
import sys
# Add this line RIGHT AT THE TOP (before any other imports)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Then keep your existing imports
from utils import process_persona, save_image_from_drive, clean_name
from search.search_engine import search_linkedin_profiles

from utils import process_persona, save_image_from_drive, clean_name
from search.search_engine import search_linkedin_profiles
import json
import os
import time
import os

import sys
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TensorFlow warning suppression
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
tf.get_logger().setLevel('ERROR')

def run_type1_preprocessing(input_path, output_path, image_folder):
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    cleaned_data = []

    for persona in raw_data:
        cleaned = process_persona(persona)

        # Save image
        global image_url
        img_url = persona.get("image")
        if img_url:
            name = clean_name(persona.get("name"))
            img_path = os.path.join(image_folder, f"{name}.jpg")
            save_image_from_drive(img_url, img_path)

        cleaned_data.append(cleaned)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2)

    print(f"✅ Preprocessing done! {len(cleaned_data)} personas processed.")
    return cleaned_data


def run_linkedin_search(personas, output_file, num_results=5):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    all_matches = []

    for i, persona in enumerate(personas):
        print(f"\n🔍 Searching for persona {i+1}/{len(personas)}: {persona['name']}")
        
        try:
            matches = search_linkedin_profiles(persona, num_results=num_results)
            
            all_matches.append({
                "persona_name": persona["name"],
                "query_used": f'{persona["name"]} {persona.get("job_title", "")} {persona.get("company", "")} {persona.get("location", "")}',
                "user_image_url":persona["image_url"],
                "matches": matches
            })
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error searching for {persona['name']}: {str(e)}")
            all_matches.append({
                "persona_name": persona["name"],
                "user_image_url":persona["image_url"],
                "error": str(e),
                "matches": []
            })

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_matches, f, indent=2)

    print(f"\n✅ Search complete! Results saved to: {output_file}")


if __name__ == "__main__":
    input_path = "D:\Fortran_Recepto_Linkedin_matcher\RECEPTO-FINALLLL\Recepto-linkedin-matcher_final\enriched_output.json"
    cleaned_output_path = "data/cleaned/cleaned_dataset_new.json"
    image_folder = "data/persona_images"
    matches_output_path = "output/matches_type_new.json"

    # Step 1: Preprocess all personas
    cleaned_personas = run_type1_preprocessing(input_path, cleaned_output_path, image_folder)

    # Step 2: Search for LinkedIn profiles
    run_linkedin_search(cleaned_personas, matches_output_path)

