# Handles fuzzy and semantic matching between persona and profile
import json
import re
import time
import random
from difflib import SequenceMatcher
import logging
import requests
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInProfileMatcher:
    def __init__(self, dataset_path):
        """Initialize the LinkedIn Profile Matcher with a dataset path and SERP API key."""
        self.dataset = self.load_dataset(dataset_path)
        
        # Weights for profile attributes
        self.weights = {
            'name': 0.5,           # Name is the most important attribute
            'company_role': 0.2,   # Company and role information
            'industry_size': 0.15, # Industry and company size
            'location': 0.3,       # Location/timezone information
            'social': 0.05         # Social profile links
        }
    
    def load_dataset(self, dataset_path):
        """Load and parse the dataset from the given path."""
        try:
            with open(dataset_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            return []

    def get_search_queries(self, persona):
        """Generate exhaustive search queries using all persona attributes"""
        queries = []
        name = persona.get('name', '')
        if not name:
            return queries
        
        # Base name queries
        queries.append(f"{name} linkedin")
        queries.append(f'"{name}"')
        
        # Professional context queries
        professional_terms = []
        if persona.get('job_title'):
            professional_terms.extend(persona['job_title'].split())
        if persona.get('company'):
            professional_terms.append(persona['company'])
        
        if professional_terms:
            queries.append(f"{name} {' '.join(professional_terms)} linkedin")
        
        # Company metadata queries
        metadata_terms = []
        if persona.get('company_industry'):
            metadata_terms.append(persona['company_industry'])
        if persona.get('company_size'):
            metadata_terms.append(
                persona['company_size'].replace('employees', '').strip()
            )
        
        if metadata_terms:
            queries.append(f"{name} {' '.join(metadata_terms)} linkedin")
        
        # Location-based queries
        location = persona.get('location') or self.timezone_to_location(
            persona.get('timezone')
        )
        if location:
            queries.append(f"{name} {location} linkedin")
            if professional_terms:
                queries.append(f"{name} {' '.join(professional_terms)} {location}")
        
        # Social profile enhanced queries
        social_terms = []
        for profile in persona.get('social_profile', []):
            if 'twitter.com' in profile:
                social_terms.append('twitter')
            elif 'github.com' in profile:
                social_terms.append('github')
        
        if social_terms:
            queries.append(f"{name} {' '.join(social_terms)}")
        
        # URL-based queries
        if persona.get('website'):
            domain = re.search(r'https?://([^/]+)', persona['website'])
            if domain:
                queries.append(f"{name} {domain.group(1)}")
        
        # Remove duplicates and empty queries
        return list(set(q.strip() for q in queries if q.strip()))

    def timezone_to_location(self, timezone):
        """Convert timezone to a general location."""
        timezone_map = {
            'America/New_York': 'New York',
            'America/Chicago': 'Chicago',
            'America/Los_Angeles': 'California',
            'Europe/London': 'UK',
            'Europe/Brussels': 'Belgium',
            'Asia/Kolkata': 'India',
            'Asia/Jerusalem': 'Israel',
            'Africa/Monrovia': 'Liberia'
        }
        return timezone_map.get(timezone)

    def extract_profile_info(self, linkedin_url):
        """
        Extract basic information from LinkedIn URL.
        
        In a real-world scenario, you would use LinkedIn's API or a service like
        Proxycurl or Phantombuster to get detailed profile information.
        For this example, we'll extract what we can from the URL and structure.
        """
        profile_info = {'url': linkedin_url}
        
        # Extract name from URL
        name_match = re.search(r'linkedin\.com/in/([^/]+)', linkedin_url)
        if name_match:
            slug = name_match.group(1)
            # Convert slug to a name (e.g., "john-doe" to "John Doe")
            name = slug.replace('-', ' ').title()
            profile_info['name'] = name
        
        # Note: In a real implementation, you would fetch the actual profile page
        # and extract more details like company, role, location, etc.
        
        return profile_info

    def calculate_name_similarity(self, persona_name, profile_name):
        if not persona_name or not profile_name:
            return 0.0

        persona_name = persona_name.strip().lower()
        profile_name = profile_name.strip().lower()

        if persona_name == profile_name:
            return 1.0
        if persona_name in profile_name or profile_name in persona_name:
            return 0.9

        name_variations = {
            'bob': ['robert', 'rob', 'bobby'],
            'mike': ['michael', 'mick'],
            'dave': ['david'],
            'jim': ['james', 'jimmy'],
            'chris': ['christopher', 'christoph'],
            'zach': ['zachary'],
            'jeff': ['jeffrey', 'geoffrey'],
        }

        try:
            persona_first = persona_name.split()[0]
            profile_first = profile_name.split()[0]
        except IndexError:
            return 0.0

        for base, variations in name_variations.items():
            if (persona_first == base or persona_first in variations) and \
            (profile_first == base or profile_first in variations):
                return 0.85

        return SequenceMatcher(None, persona_name, profile_name).ratio()

    def calculate_match_score(self, persona, profile):
        scores = {}

        name_similarity = self.calculate_name_similarity(
            persona.get('name', ''), 
            profile.get('name', '')
        )
        scores['name'] = name_similarity * self.weights['name']

        intro = persona.get('intro', '')
        company_industry = persona.get('company_industry', '')
        company_size = persona.get('company_size', '')
        timezone = persona.get('timezone', '')
        social_profiles = persona.get('social_profile', [])

        # Company/role score
        company_role_score = 0.5
        if intro and profile.get('url'):
            intro_keywords = re.findall(r'\b\w{4,}\b', intro.lower())
            url_lower = profile.get('url', '').lower()
            matches = sum(1 for keyword in intro_keywords if keyword in url_lower)
            if matches > 0:
                company_role_score = min(0.5 + (matches * 0.1), 1.0)
        scores['company_role'] = company_role_score * self.weights['company_role']

        scores['industry_size'] = 0.6 * self.weights['industry_size']
        scores['location'] = 0.5 * self.weights['location']
        scores['social'] = 0.5 * self.weights['social']

        total_score = sum(scores.values())
        total_score = min(total_score,0.9)

        return total_score, scores


    def find_top_matches(self, persona, max_results=3):
        """Find top LinkedIn profile matches for a persona."""
        logger.info(f"Finding matches for: {persona.get('name', 'Unknown')}")
        
        # Get search queries for this persona
        queries = self.get_search_queries(persona)
        
        # Track unique LinkedIn URLs we find
        all_linkedin_urls = set()
        
        # Search using SERP API for each query
        for query in queries:
            logger.info(f"Searching for query: {query}")
            linkedin_urls = self.search_with_serpapi(query)
            all_linkedin_urls.update(linkedin_urls)
            
            # Avoid hitting API rate limits
            time.sleep(random.uniform(1, 2))
        
        # Extract information from LinkedIn profiles
        profile_scores = []
        
        for url in all_linkedin_urls:
            profile = self.extract_profile_info(url)
            score, component_scores = self.calculate_match_score(persona, profile)
            
            profile_scores.append({
                'url': url,
                'profile': profile,
                'total_score': min(score,0.9),
                'component_scores': component_scores
            })
        
        # Sort by total score in descending order
        profile_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Return top matches
        return profile_scores[:max_results]

    def process_dataset(self):
        """Process entire dataset and find matches for each persona."""
        results = []
        for persona in self.dataset:
            top_matches = self.find_top_matches(persona, max_results=5)  # Changed to 5 matches
            results.append({
                'persona': persona,
                'matches': top_matches
            })
            # Avoid hitting API rate limits
            time.sleep(random.uniform(2, 3))
        return results
    
# Usage example
if __name__ == "__main__":
    matcher = LinkedInProfileMatcher("D:\Fortran_Recepto_Linkedin_matcher\RECEPTO-FINALLLL\Recepto-linkedin-matcher_final\Recepto-linkedin-matcher\recepto-linkedin-matcher\output\matches_type_new.json")
    results = matcher.process_dataset()
    
    # Print top matches for each persona
    for result in results:
        persona = result['persona']
        matches = result['matches']
        
        # Print persona info with image URL
        print(f"\nPersona: {persona.get('name', 'Unknown')}")
        print(f"Input Image: {persona.get('image', 'No image available')}\n")
        
        # Print all matches (up to 5)
        if matches:
            for i, match in enumerate(matches, 1):
                print(f"Match {i}:")
                print(f"  - URL: {match['url']}")
                print(f"  - Query Used: {match.get('query_used', 'Unknown')}")
                print(f"  - Match Score: {match['total_score']:.2f}")
                print("  - Component Scores:")
                for component, score in match['component_scores'].items():
                    print(f"    * {component}: {score:.2f}")
                print()  # Add space between matches
        else:
            print("No matches found")