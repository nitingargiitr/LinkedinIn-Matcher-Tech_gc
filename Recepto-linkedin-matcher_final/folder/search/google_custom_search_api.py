import requests
from typing import Optional, TypedDict, List
import logging
import time 

class GoogleCustomSearchResponse(TypedDict):
    link: str
    title: Optional[str]
    snippet: Optional[str]

class GoogleCustomSearch:
    def __init__(self):
        self.api_key = "AIzaSyBhoMDnst3_JoK5TziGClgS27bhX0dQNFk"
        self.search_engine_id = "c307652d3fbc44ec8"
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.last_response = None

    def _search(self, query: str, num=10, start=1) -> Optional[dict]:
        params = {
            "q": query,
            "key": self.api_key,
            "cx": self.search_engine_id,
            "num": min(num, 10),  # Google typically limits to 10
        }
        
        print(f"DEBUG: Sending query: {query}")  # Debug output
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            self.last_response = response.json()  # Store for debugging
            print(f"DEBUG: API Response: {self.last_response}")  # Debug output
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"API Exception: {str(e)}")
            return None
        
    def _parse_results(self, response: dict) -> List[GoogleCustomSearchResponse]:
        """
        More robust parsing of google search response.
        """
        if not response or "items" not in response:
            return []

        results = []
        for item in response.get("items", []):
            link = item.get("link", "")
            if link and "linkedin.com/in/" in link:
                results.append({
                    "title": item.get("title", ""),
                    "link": link,
                    "snippet": item.get("snippet", ""),
                })
        return results

    def search(self, query: str, num=10, start=1) -> List[GoogleCustomSearchResponse]:
        """
        Get formatted search results from Google with retry logic.
        """
        max_retries = 2
        for attempt in range(max_retries):
            response = self._search(query, num, start)
            if response:
                return self._parse_results(response)
            time.sleep(1)  # Simple backoff
            
        return []