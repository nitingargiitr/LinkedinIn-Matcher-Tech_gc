import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse
import time
import logging
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer
import numpy as np
from search.google_custom_search_api import GoogleCustomSearch

class LinkedInSearch:
    def __init__(self):
        self.google_search = GoogleCustomSearch()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.logger = logging.getLogger(__name__)
        
    def build_search_query(self, persona: Dict) -> str:
        """Build comprehensive queries using ALL available persona data"""
        query_parts = []
        
        # 1. Name (with variants)
        name = persona.get('name', '')
        if name:
            query_parts.append(f'"{name}"')  # Start with exact name match
        
        # 2. Professional info
        if persona.get('job_title'):
            query_parts.append(persona['job_title'])
        if persona.get('company'):
            query_parts.append(persona['company'])
        
        # 3. Location (handle both location and timezone)
        location = persona.get('location')
        if not location and persona.get('timezone'):
            location = persona['timezone'].split('/')[-1].replace('_', ' ')
        if location:
            query_parts.append(location)
        
        # 4. Company metadata
        if persona.get('company_industry'):
            query_parts.append(persona['company_industry'])
        if persona.get('company_size'):
            query_parts.append(
                persona['company_size'].replace('employees', '').strip()
            )
        
        # 5. Social profile hints
        social_keywords = []
        for profile in persona.get('social_profile', []):
            if 'twitter.com' in profile:
                social_keywords.append('twitter')
            elif 'github.com' in profile:
                social_keywords.append('github')
        if social_keywords:
            query_parts.extend(social_keywords)
        
        # Construct base query
        base_query = ' '.join(query_parts)
        
        # Generate multiple query formulations
        queries = [
            f'site:linkedin.com/in/ {base_query}',  # Most comprehensive
            f'"{name}" {persona.get("company", "")} LinkedIn',  # Name + company
            f'"{name}" {location or ""} LinkedIn',  # Name + location
            base_query  # Fallback
        ]
        
        # Log the actual query used (for debugging)
        print(f"Generated queries: {queries}")
        return queries[0]  # Return the most comprehensive query
    
    def extract_linkedin_username(self, url: str) -> Optional[str]:
        """More robust LinkedIn username extraction"""
        try:
            # Handle both http and https, with or without www
            url = url.lower().replace('https://', '').replace('http://', '').replace('www.', '')
            
            # Extract the path after linkedin.com/in/
            if 'linkedin.com/in/' in url:
                path = url.split('linkedin.com/in/')[1]
                # Take everything before the next slash or question mark
                username = path.split('/')[0].split('?')[0]
                return username if username else None
        except Exception as e:
            self.logger.error(f"Error extracting username from {url}: {str(e)}")
        return None
    
    def calculate_similarity(self, persona: Dict, profile: Dict) -> float:
        try:
            # Prepare persona text
            persona_name = persona.get('name', '').lower().strip()
            persona_fields = [
                persona.get('job_title', ''),
                persona.get('company', ''),
                persona.get('location', '').split('/')[-1].replace('_', ' ')
            ]
            persona_text = ' '.join([f for f in persona_fields if f]).lower()
            
            # Prepare profile text
            profile_title = profile.get('title', '').lower()
            profile_snippet = profile.get('snippet', '').lower()
            profile_text = f"{profile_title} {profile_snippet}"
            
            # Name matching is most important
            name_score = 0
            if persona_name:
                # Check if persona name appears in profile (all parts)
                name_parts = persona_name.split()
                if all(part in profile_text for part in name_parts):
                    name_score = 1.0
                else:
                    # Use fuzzy matching as fallback
                    name_score = fuzz.partial_ratio(persona_name, profile_text) / 100
            
            # Other fields matching
            field_score = 0
            if persona_text:
                field_score = fuzz.token_set_ratio(persona_text, profile_text) / 100
            
            # Combined score (weighted heavily toward name match)
            return 0.8 * name_score + 0.2 * field_score
            
        except Exception as e:
            self.logger.error(f"Error in similarity calculation: {str(e)}")
            return 0.0
    
    def search_profiles(self, query: str, num_results: int = 5) -> List[Dict]:
        """More inclusive profile search"""
        try:
            self.logger.info(f"Searching with query: {query}")
            results = self.google_search.search(query, num=num_results)
            
            linkedin_profiles = []
            for result in results:
                if not result.get('link'):
                    continue
                    
                # Accept any LinkedIn URL variation
                if any(domain in result['link'].lower() 
                    for domain in ['linkedin.com/in/', 'linkedin.com/pub/']):
                    
                    username = self.extract_linkedin_username(result['link'])
                    if username:
                        linkedin_profiles.append({
                            'url': result['link'],
                            'username': username,
                            'title': result.get('title', ''),
                            'snippet': result.get('snippet', ''),
                            'source': 'google_custom_search'
                        })
                        # Stop if we have enough results
                        if len(linkedin_profiles) >= num_results:
                            break
            
            self.logger.info(f"Found {len(linkedin_profiles)} profiles for query: {query}")
            return linkedin_profiles
        except Exception as e:
            self.logger.error(f"Error in search_profiles: {str(e)}")
            return []
        
    def search_linkedin_profiles(self, persona: Dict, num_results: int = 5) -> List[Dict]:
        """Main search method with fallback name-only searches"""
        try:
            # Step 1: Try comprehensive search first
            query = self.build_search_query(persona)
            profiles = self.search_profiles(query, num_results)
            
            # Step 2: If no results, try name-only fallbacks
            if not profiles:
                name = persona.get('name', '').strip()
                if name:
                    # Fallback 1: Exact full name match
                    fallback_queries = [
                        f'site:linkedin.com/in/ "{name}"',  # Exact full name
                        f'"{name}" LinkedIn',               # Loose full name
                    ]
                    
                    # Fallback 2: First name only if compound name
                    if ' ' in name:
                        first_name = name.split()[0]
                        fallback_queries.extend([
                            f'site:linkedin.com/in/ "{first_name}"',  # Exact first name
                            f'"{first_name}" LinkedIn'                # Loose first name
                        ])
                    
                    # Execute fallback queries in order
                    for fq in fallback_queries:
                        if len(profiles) >= num_results:
                            break
                        profiles.extend(self.search_profiles(fq, num_results - len(profiles)))
                        time.sleep(0.5)  # Rate limiting
            
            # Score and sort results
            scored_profiles = []
            for profile in profiles[:num_results]:  # Ensure we don't exceed num_results
                score = self.calculate_similarity(persona, profile)
                scored_profiles.append({
                    **profile,
                    'match_score': min(score,0.9),
                    'query_used': query if score > 0 else fq,  # Track which query worked
                    'persona_name': persona['name']
                })
            
            return sorted(scored_profiles, key=lambda x: x['match_score'], reverse=True)
        
        except Exception as e:
            self.logger.error(f"Search error: {str(e)}")
            return []

def search_linkedin_profiles(persona: Dict, num_results: int = 5) -> List[Dict]:
    """Public interface with error handling"""
    try:
        searcher = LinkedInSearch()
        return searcher.search_linkedin_profiles(persona, num_results)
    except Exception as e:
        logging.error(f"Error in search_linkedin_profiles: {str(e)}")
        return []