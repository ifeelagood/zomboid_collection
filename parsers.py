import typing
import re

from bs4 import BeautifulSoup

MOD_ID_REGEX = "(?:Mod(?:\s?)ID)(?:\:)(?:[\s+])([\w._&-]+)(?:\r?\n)?"
MAP_FOLDER_REGEX = "(?:Map(?:\s?)Folder)(?:\:)(?:\s+)([^\r\n]+)"

class CollectionParser:
    @staticmethod
    def yield_workshop_ids(soup : BeautifulSoup) -> typing.Iterator[int]:
        for div in soup.find_all("div", class_="collectionItem"):
            item_id = int(div["id"].strip("sharedfiles_"))
            yield item_id
            

class ItemParser:
    @staticmethod
    def parse_description(soup : BeautifulSoup) -> str:
        div = soup.find("div", class_="workshopItemDescription")
        
        # hack: add line breaks <br>
        for br in div.find_all("br"):
            br.replace_with("\n")
        
        return div.text

    @staticmethod
    def parse_dependencies(soup : BeautifulSoup) -> typing.Set[int]:
        dependencies = set()
        
        div = soup.find("div", class_="requiredItemsContainer")
        
        if div is not None:
            for a in div.find_all("a"):
                # get after id=
                dependencies.add(int(a["href"].split("=")[1])) # TODO hacky
                
        return dependencies
    
    @staticmethod
    def parse_mod_ids(description : str) -> typing.Set[str]:
        matches = re.findall(MOD_ID_REGEX, description)
        mod_ids = set()
        
        for m in matches:
            mod_ids.add(m.strip())
                
        return mod_ids
    
    @staticmethod
    def parse_map_folders(description : str) -> typing.Set[str]:
        matches = re.findall(MAP_FOLDER_REGEX, description)
        map_folders = set()
        
        for m in matches:
            map_folders.add(m.strip())
        

        return map_folders