import re
import spacy

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

def extract_from_intro(intro):
    if not intro:
        return {
            "title": None,
            "company": None,
            "skills": [],
            "location": None,
            "links": []
        }

    # Extract links using regex
    links = re.findall(r'https?://\S+', intro)

    # Process the intro text
    doc = nlp(intro.strip())

    # Extract organizations and locations from named entities
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    locations = [ent.text for ent in doc.ents if ent.label_ in {"GPE", "LOC"}]

    # Extract job titles based on keyword-matching in noun chunks
    title_keywords = ["lead", "founder", "ceo", "head", "engineer", "consultant", "developer", "manager", "scientist"]
    noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
    title = next((chunk for chunk in noun_chunks if any(word in chunk for word in title_keywords)), None)

    # Extract possible skills (nouns, proper nouns, adjectives)
    tokens = [
        token.text.lower()
        for token in doc
        if token.pos_ in {"NOUN", "PROPN", "ADJ"} and len(token.text) > 2
    ]
    # Remove organization names from skills
    skills = list(set(tokens) - set(word.lower() for word in orgs))

    # Try matching company using patterns like "at XYZ", "of XYZ", "@XYZ"
    company_match = re.search(r'(?:@|at|of)\s+([a-z0-9_.\-]+)', intro.lower())
    company = company_match.group(1) if company_match else (orgs[0] if orgs else None)

    return {
        "title": title,
        "company": company,
        "skills": skills,
        "location": locations[0] if locations else None,
        "links": links
    }
