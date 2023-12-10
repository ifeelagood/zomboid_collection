import argparse
import dataclasses
import datetime
import logging
import typing
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import requests_cache
import tqdm
from bs4 import BeautifulSoup

from pick import pick

from fetchers import Fetcher
from parsers import CollectionParser, ItemParser
from ini import zINI

MAP_BASE = "Muldraugh, KY"
WORKSHOP_FILE_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

DELIMITER = ";"
        


def get_args():
    parser = argparse.ArgumentParser(description="Generate server configuration for a Project Zomboid workshop collection")
    
    parser.add_argument("--collection-id", "-c", type=int, help="Workshop collection ID", required=True)
    parser.add_argument("--output", "-o", help="Output zomboid ini file", default="servertest.ini")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output fields if they already exist")
    parser.add_argument("--threads", "-t", type=int, help="Number of threads to use", default=16)
    parser.add_argument("--no-cache", action="store_true", help="Disable requests cache. Useful if collection was updated recently")
    parser.add_argument("--no-dependencies", action="store_true", help="Do not add unresolved mod dependencies")


    return parser.parse_args()

@dataclasses.dataclass
class WorkshopItem:
    workshop_id : int
    dependencies : typing.Set[int]
    mod_ids : typing.Set[str]
    map_folders : typing.Set[str]
    
    def __hash__(self):
        return hash(self.workshop_id)

    def __str__(self):
        return WORKSHOP_FILE_URL.format(self.workshop_id)
    
    def __repr__(self):
        return str(self)

def scrape_workshop_items(fetcher : Fetcher, threads : int, workshop_ids : typing.Set[int]) -> typing.Set[WorkshopItem]:
    def process_item(item_id):
        soup = fetcher.fetch_soup(item_id)
        
        desc = ItemParser.parse_description(soup)
        
        item = WorkshopItem(
            workshop_id=item_id,
            dependencies=ItemParser.parse_dependencies(soup),
            mod_ids=ItemParser.parse_mod_ids(desc),
            map_folders=ItemParser.parse_map_folders(desc)
        )
        
        return item
        
    workshop_items = set()
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for item_id in workshop_ids:
            futures.append(executor.submit(process_item, item_id))
            
        for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
            workshop_items.add(future.result())
            
    return workshop_items

def select_mods_maps(workshop_items : typing.Set[WorkshopItem]):
    for item in workshop_items:
        if len(item.mod_ids) == 0:
            print(f"Warning: Workshop item {item} has no mod IDs")
        
        if len(item.mod_ids) > 1:
            selected_mod_ids = pick(list(item.mod_ids), f"Select mods for workshop item {WORKSHOP_FILE_URL.format(item.workshop_id)}", multiselect=True, min_selection_count=1)
            item.mod_ids = set(t[0] for t in selected_mod_ids)
            
        if len(item.map_folders) > 1:
            selected_map_folders = pick(list(item.map_folders), f"Select map folders for workshop item {WORKSHOP_FILE_URL.format(item.workshop_id)}", multiselect=True, min_selection_count=1)
            item.map_folders = set(t[0] for t in selected_map_folders)

def gather_unresolved_dependencies(workshop_items : typing.Set[WorkshopItem]):
    workshop_ids = set(item.workshop_id for item in workshop_items)
    
    # gather dependencies
    dependencies = set()
    for item in workshop_items:
        for dependency in item.dependencies:
            dependencies.add(dependency)
            
            if dependency not in workshop_ids:
                logging.warning(f"Found unresolved dependency {dependency} for workshop item {item}")

    unresolved = dependencies - workshop_ids
    return unresolved

def resolve_dependencies(fetcher : Fetcher, threads : int, workshop_items : typing.Set[WorkshopItem]):
    workshop_ids = set(item.workshop_id for item in workshop_items)
    
    unresolved = gather_unresolved_dependencies(workshop_items)    

    # resolve dependencies
    dependencies = set()
    while len(unresolved) > 0:
        logging.info(f"Resolving {len(unresolved)} unresolved dependencies")
        for item in scrape_workshop_items(fetcher, threads, unresolved):
            workshop_items.add(item)
            workshop_ids.add(item.workshop_id)
            
            for dependency in item.dependencies:
                dependencies.add(dependency)
                
                if dependency not in workshop_ids:
                    logging.warning(f"Found unresolved dependency {dependency} for workshop item {item}")
                    
        unresolved = dependencies - workshop_ids

def write_config(ini_path : os.PathLike, workshop_items : typing.Set[WorkshopItem], overwrite : bool):
    if os.path.exists(ini_path):
        if not overwrite:
            logging.error(f"File {ini_path} already exists. Use --overwrite to overwrite")
            return

        ini = zINI.load(ini_path)
    else:
        ini = zINI()
    
    workshop_ids = set(str(item.workshop_id) for item in workshop_items)
    mod_ids = set(mod_id for item in workshop_items for mod_id in item.mod_ids)
    map_folders = set(map_folder for item in workshop_items for map_folder in item.map_folders)
    
    ini["WorkshopItems"] = DELIMITER.join(workshop_ids)
    ini["Mods"] = DELIMITER.join(mod_ids)
    ini["Map"] = DELIMITER.join(map_folders) + DELIMITER + MAP_BASE
    
    ini.save(ini_path)

def main():
    args = get_args()

    # create requests cache session
    session = requests.Session() if args.no_cache else requests_cache.CachedSession(".requests_cache", expire_after=datetime.timedelta(minutes=30))
    fetcher = Fetcher(session)

    # scrape workshop items
    workshop_ids = set(CollectionParser.yield_workshop_ids(fetcher.fetch_soup(args.collection_id)))
    workshop_items = scrape_workshop_items(fetcher, args.threads, workshop_ids)
    select_mods_maps(workshop_items)
    
    # resolve dependencies
    if not args.no_dependencies:
        resolve_dependencies(fetcher, args.threads, workshop_items)
        
    
    write_config(args.output, workshop_items, args.overwrite)
        
if __name__ == "__main__":
    main()