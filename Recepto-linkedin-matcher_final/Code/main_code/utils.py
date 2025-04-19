import json
import os
import re
import requests
from io import BytesIO
from PIL import Image
import spacy
from urllib.parse import urlparse, urlunparse
from typing import Optional


nlp = spacy.load("en_core_web_sm")


def clean_name(name):
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(r'\([^)]*\)', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name.strip())
    return name.title()


def clean_timezone(timezone):
    if not timezone:
        return None
    timezone = re.sub(r'[^\w\s/,]', '', timezone).split(',')[0].strip()
    return timezone


def clean_company_industry(company_industry):
    if not company_industry or str(company_industry).strip().lower() == "null":
        return None
    industry = str(company_industry).strip()
    industry = re.sub(r'[^\w\s&/-]', '', industry)
    industry = ' '.join(industry.split())
    return industry.title() if len(industry.split()) > 1 else industry.capitalize()


def clean_roles(intro_text):
    if not intro_text:
        return []
    segments = re.split(r'\.(?!\w)', intro_text)
    return [seg.strip() for seg in segments if seg.strip()]


def clean_website(intro_text):
    if not intro_text:
        return None
    match = re.search(r'\((https?://[^\s)]+)\)', intro_text)
    return match.group(1) if match else None


def extract_company_size(text):
    if not text:
        return None
    return re.sub(r"\s*employees\s*", "", text, flags=re.IGNORECASE).strip()


def extract_job_company(text):
    if not text:
        return None, None
    doc = nlp(text)
    job = next((ent.text for ent in doc.ents if ent.label_ == "TITLE"), None)
    company = next((ent.text for ent in doc.ents if ent.label_ == "ORG"), None)
    return job, company


def standardize_country_name(location: Optional[str]) -> Optional[str]:
    if not location:
        return None
    
    # Convert to string and clean
    location = str(location).strip().upper()
    
    # Country mappings
    country_map = {
        "UK": "United Kingdom",
        "U.K.": "United Kingdom",
        "GB": "United Kingdom",
        "GREAT BRITAIN": "United Kingdom",
        "ENGLAND": "United Kingdom",
        "SCOTLAND": "United Kingdom",
        "WALES": "United Kingdom",
        "US": "United States",
        "U.S.": "United States",
        "USA": "United States",
        "UNITED STATES OF AMERICA": "United States",
        "CA": "Canada",
        "CAN": "Canada",
        "AU": "Australia",
        "AUS": "Australia",
        "DE": "Germany",
        "GER": "Germany",
        "FR": "France",
        "FRA": "France",
        "IN": "India",
        "IND": "India",
        "JP": "Japan",
        "JPN": "Japan",
        "SG": "Singapore",
        "SGP": "Singapore"
    }
    
    # Check if location matches any country code
    standardized = country_map.get(location, None)
    if standardized:
        return standardized
    
    # Check if location is in values (case-insensitive)
    for code, name in country_map.items():
        if location == name.upper():
            return name
    
    # If no match, return original location capitalized
    return location.title()


def clean_social_profile(profiles):
    if not profiles:
        return []
    
    # Handle cases where profiles is a string instead of list
    if isinstance(profiles, str):
        profiles = [profiles]
    
    cleaned = []
    for profile in profiles:
        if not profile or not isinstance(profile, str) or profile.isspace():
            continue
        
        profile = profile.strip()
    
        if not re.match(r'^https?://', profile, re.IGNORECASE) and '@' not in profile:
            profile = f'https://{profile}'
        
        try:
            parsed = urlparse(profile)
            if not parsed.netloc:  
                continue
                
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip('/')
            cleaned_url = urlunparse((
                'https',
                netloc,
                path,
                '',  
                '', 
                ''   
            ))
            
            if 'linkedin.com' in netloc:
                if not re.match(r'^/in/[a-z0-9-]+$', path, re.IGNORECASE):
                    path = re.sub(r'^/in/', '/', path)
                cleaned_url = f'https://www.linkedin.com{path}'
            
            elif 'twitter.com' in netloc:
                cleaned_url = f'https://twitter.com{path.split("?")[0]}'
            
            cleaned.append(cleaned_url)
        except:
            continue
    
    seen = set()
    return [x for x in cleaned if not (x in seen or seen.add(x))]


def save_image_from_drive(drive_url, save_path):
    try:
        file_id = drive_url.split('/file/d/')[1].split('/')[0]
        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(direct_url)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        save_path = os.path.splitext(save_path)[0] + f".{img.format.lower()}"
        img.save(save_path)
        return save_path
    except Exception as e:
        print(f"[⚠️] Failed to save image from {drive_url}: {e}")
        return None


def process_persona(persona):
    name = clean_name(persona.get("name", ""))
    job, company = extract_job_company(persona.get("intro", ""))
    
    # Get location with priority: existing location > timezone > None
    location = persona.get("location") or clean_timezone(persona.get("timezone"))
    location = standardize_country_name(location) if location else None
    
    cleaned = {
        "name": name,
        "location": location,
        "company_industry": clean_company_industry(persona.get("company_industry")),
        "company_size": extract_company_size(persona.get("company_size")),
        "roles": clean_roles(persona.get("intro")),
        "website": clean_website(persona.get("intro")),
        "job_title": job,
        "company": company,
        "social_profile": clean_social_profile(persona.get("social_profile")),
        "image_url": persona.get("image")
    }
    return cleaned