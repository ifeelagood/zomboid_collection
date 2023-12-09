import requests
import argparse
import re
import typing
from bs4 import BeautifulSoup
import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import dataclasses

from pick import pick

MOD_ID_REGEX = "(?:Mod(?:\s?)ID)(?:\:)(?:[\s+])([\w._&-]+)(?:\r?\n)?"
MAP_FOLDER_REGEX = "(?:Map(?:\s?)Folder)(?:\:)(?:[\s+])([\w._&-]+)(?:\r?\n)?"

MAP_BASE = "Muldraugh, KY"

def yield_workshop_ids(collection_id : int) -> int:
    try:
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
        response = requests.get(url)

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return
    

    soup = BeautifulSoup(response.text, "html.parser")
    for div in soup.find_all("div", class_="collectionItem"):
        item_id = int(div["id"].strip("sharedfiles_"))
        yield item_id

def get_workshop_description(item_id : int) -> str:
    try:
        url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
        response = requests.get(url)

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return
    
    soup = BeautifulSoup(response.text, "html.parser")
    div = soup.find("div", class_="workshopItemDescription")
    
    # hack: add line breaks <br>
    for br in div.find_all("br"):
        br.replace_with("\n")
    
    return div.text

def get_mod_ids(description : str) -> typing.List[str]:
    matches = re.findall(MOD_ID_REGEX, description)
    mod_ids = set(m.strip() for m in matches)
        
    return mod_ids

def get_map_folders(description : str) -> typing.List[str]:
    matches = re.findall(MAP_FOLDER_REGEX, description)
    map_folders = set(m.strip() for m in matches)

    return map_folders

def get_args():
    parser = argparse.ArgumentParser(description="Generate server configuration for a Project Zomboid workshop collection")
    
    parser.add_argument("--collection-id", "-c", type=int, help="Workshop collection ID", required=True)
    parser.add_argument("--server-name", "-n", help="Server name", required=True)
    parser.add_argument("--threads", "-t", type=int, help="Number of threads to use", default=16)

    return parser.parse_args()

@dataclasses.dataclass
class WorkshopItem:
    workshop_id : int
    mod_ids : typing.List[str]
    map_folders : typing.List[str]
    
    def __hash__(self):
        return hash(self.workshop_id)
    
def main():
    args = get_args()

    workshop_items = set()
    
    # worker function to process a single workshop item
    def process_item(item_id):        
        description = get_workshop_description(item_id) 
        item_mod_ids = get_mod_ids(description)
        item_map_folders = get_map_folders(description) 

        workshop_items.add(WorkshopItem(item_id, item_mod_ids, item_map_folders))
        
    # process workshop items in parallel
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for item_id in yield_workshop_ids(args.collection_id):
            futures.append(executor.submit(process_item, item_id))
            
        for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
            future.result()

    # extract mod IDs and map folders
    # prompt user to select mods and map folders
    workshop_ids = set()
    mod_ids = set()
    map_folders = set()
    
    for item in workshop_items:
        if len(item.mod_ids) == 0:
            print(f"Warning: Workshop item {item.workshop_id} has no mod IDs")
        
        if len(item.mod_ids) > 1:
            selected_mod_ids = pick(item.mod_ids, "Select mods for workshop item", multiselect=True, min_selection_count=1)
            item.mod_ids = selected_mod_ids
            
        if len(item.map_folders) > 1:
            selected_map_folders = pick(item.map_folders, "Select map folders for workshop item", multiselect=True, min_selection_count=1)
            item.map_folders = selected_map_folders

        workshop_ids.add(item.workshop_id)
        mod_ids.update(item.mod_ids)
        map_folders.update(item.map_folders)
        
    

    # write result to ini file
    ini_path = f"{args.server_name}.ini"
    
    with open(ini_path, "w") as f:
        f.write("WorkshopItems=" + ";".join(map(str, workshop_ids)) + "\n")
        f.write("Mods=" + ";".join(mod_ids) + "\n")
        f.write("Map=" + ";".join(map_folders) + ";" + MAP_BASE + "\n")
    
    print("Done")
        
if __name__ == "__main__":
    main()