import json
from google.cloud import language_v1
import os

# Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:\RECEPTO-FINAL-SUBMISSION\Intro_processing\service-account.json"

# Expanded keywords for roles and skills
role_keywords = [
    "co-founder", "cto", "ceo", "chief", "engineer", "developer", "scientist",
    "director", "manager", "head", "lead", "founder", "president", "vp", "architect",
    "consultant", "specialist", "strategist", "analyst", "advisor", "product manager",
    "designer", "developer", "software engineer", "product owner", "researcher",
    "teacher", "professor", "marketer", "administrator", "trainer", "entrepreneur",
    "sales", "director", "executive", "coach", "brand manager", "content creator",
    "author", "speaker", "developer advocate", "business analyst", "system architect"
]

skill_keywords = [
    "python", "java", "javascript", "sql", "html", "css", "react", "node", "angular", 
    "docker", "aws", "azure", "ml", "ai", "data science", "cloud", "devops", "cybersecurity", 
    "machine learning", "artificial intelligence", "data analysis", "deep learning", "pytorch", 
    "tensorflow", "ruby", "swift", "c++", "golang", "kubernetes", "hadoop", "spark", "scala",
    "r", "sas", "vba", "c#", "typescript", "matlab", "git", "jira", "tableau", "excel", "power bi", 
    "excel macros", "tensorflow", "keras", "computer vision", "nlp", "unity", "game development", 
    "vr", "ar", "blockchain", "cryptography", "iot", "networking", "kotlin", "flutter", "docker-compose",
    "postgreSQL", "mongodb", "firebase", "elasticsearch", "redis", "ci/cd", "automation", "salesforce", 
    "sap", "agile", "scrum", "lean", "usability", "seo", "content marketing", "digital marketing",
    "user experience", "user interface", "branding", "advertising"
]

def extract_info(text):
    client = language_v1.LanguageServiceClient()

    if not text.strip():
        return {}

    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)

    try:
        response = client.analyze_entities(request={"document": document})
    except Exception as e:
        print(f"[ERROR] Failed to analyze text: {e}")
        return {}

    extracted = {
        "roles": [],
        "organization": None,
        "skills": [],
        "location": None,
        "others": []  # New field for other relevant information
    }

    for entity in response.entities:
        name = entity.name.lower()
        type_ = language_v1.Entity.Type(entity.type_).name
        salience = entity.salience

        # Check for roles based on predefined keywords
        if any(role_keyword in name for role_keyword in role_keywords):
            extracted["roles"].append(entity.name)

        # Extract organization information (previously "company")
        if type_ == "ORGANIZATION" and not extracted["organization"]:
            extracted["organization"] = entity.name

        # Extract location information
        if type_ == "LOCATION" and not extracted["location"]:
            extracted["location"] = entity.name

        # Skills should only be added if the entity is not a role, organization, or location
        if type_ == "OTHER" and name not in ["years", "experience"] and name not in extracted["skills"]:
            if any(skill_keyword in name for skill_keyword in skill_keywords):
                extracted["skills"].append(entity.name)
            else:
                extracted["others"].append(entity.name)

    return extracted

def enrich_profiles(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    enriched = []

    for profile in profiles:
        if not isinstance(profile, dict):
            print("[SKIP] Malformed entry:", profile)
            continue

        intro = (profile.get("intro") or "").strip()
        if not intro:
            print(f"[SKIP] No intro for user: {profile.get('name', 'Unknown')}")
            enriched.append(profile)
            continue

        print(f"[INFO] Processing: {profile.get('name', 'Unknown')}")
        extracted = extract_info(intro)

        # Make sure the extracted fields are added to the profile, even if they are None
        enriched_profile = {**profile, **extracted}
        enriched.append(enriched_profile)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"[DONE] Enriched data written to: {output_path}")

if __name__ == "__main__":
    enrich_profiles("input.json", "enriched_output.json")
