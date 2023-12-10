import logging

from bs4 import BeautifulSoup
import requests
import requests_cache

WORKSHOP_FILE_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

class Fetcher:
    def __init__(self, session : requests.Session | requests_cache.CachedSession):
        self.session = session
        
    def fetch_soup(self, item_id : int) -> BeautifulSoup:
        url = WORKSHOP_FILE_URL.format(item_id)
        try:
            response = self.session.get(url)

            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error(f"Error fetching {url}: {e}")
            return
        
        return BeautifulSoup(response.text, "html.parser")
