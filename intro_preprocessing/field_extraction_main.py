import json
from field_extraction_utils import extract_from_intro

def main():
    input_path = "input.json"
    output_path = "output.json"

    # Read the local input JSON file
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If data is a list, loop over each entry
    if isinstance(data, list):
        for item in data:
            intro = item.get("intro", "")
            
            # Extract structured data from the intro
            extracted_data = extract_from_intro(intro)

            # Fill in the fields
            item["title"] = extracted_data.get("title") or item.get("title")
            item["company"] = extracted_data.get("company") or item.get("company")
            item["skills"] = extracted_data.get("skills") or item.get("skills", [])
            item["location"] = extracted_data.get("location") or item.get("location")
            item["links"] = extracted_data.get("links") or item.get("links", [])

            # Also include discovered_* fields
            item["discovered_title"] = extracted_data.get("title")
            item["discovered_company"] = extracted_data.get("company")
            item["discovered_skills"] = extracted_data.get("skills")
            item["discovered_location"] = extracted_data.get("location")
            item["discovered_links"] = extracted_data.get("links")

    else:
        # If data is a single dictionary
        intro = data.get("intro", "")
        
        # Extract structured data from the intro
        extracted_data = extract_from_intro(intro)

        # Fill in the fields
        data["title"] = extracted_data.get("title") or data.get("title")
        data["company"] = extracted_data.get("company") or data.get("company")
        data["skills"] = extracted_data.get("skills") or data.get("skills", [])
        data["location"] = extracted_data.get("location") or data.get("location")
        data["links"] = extracted_data.get("links") or data.get("links", [])

        # Also include discovered_* fields
        data["discovered_title"] = extracted_data.get("title")
        data["discovered_company"] = extracted_data.get("company")
        data["discovered_skills"] = extracted_data.get("skills")
        data["discovered_location"] = extracted_data.get("location")
        data["discovered_links"] = extracted_data.get("links")

    # Save the results to output.json
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Extraction complete. Results written to {output_path}")

if __name__ == "__main__":
    main()
