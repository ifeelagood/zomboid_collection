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
MAP_FOLDER_REGEX = "(?:Map(?:\s?)Folder)(?:\:)(?:\s+)([^\r\n]+)"

MAP_BASE = "Muldraugh, KY"

WORKSHOP_FILE_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id={}"

def yield_workshop_ids(collection_id : int) -> int:
    try:
        url = WORKSHOP_FILE_URL.format(collection_id)
        response = requests.get(url)

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return
    

    soup = BeautifulSoup(response.text, "html.parser")
    for div in soup.find_all("div", class_="collectionItem"):
        item_id = int(div["id"].strip("sharedfiles_"))
        yield item_id

def get_workshop_soup(item_id : int) -> BeautifulSoup:
    try:
        url = WORKSHOP_FILE_URL.format(item_id)
        response = requests.get(url)

        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
        return
    
    return BeautifulSoup(response.text, "html.parser")


def parse_workshop_description(soup : BeautifulSoup) -> str:
    div = soup.find("div", class_="workshopItemDescription")
    
    # hack: add line breaks <br>
    for br in div.find_all("br"):
        br.replace_with("\n")
    
    return div.text

def parse_dependencies(soup : BeautifulSoup) -> typing.Set[int]:
    dependencies = set()
    
    div = soup.find("div", class_="requiredItemsContainer")
    
    if div is not None:
        for a in div.find_all("a"):
            # get after id=
            dependencies.add(int(a["href"].split("=")[1])) # TODO hacky
            
    return dependencies

def parse_mod_ids(description : str) -> typing.Set[str]:
    matches = re.findall(MOD_ID_REGEX, description)
    mod_ids = set()
    
    for m in matches:
        mod_ids.add(m.strip())
            
    return mod_ids

def parse_map_folders(description : str) -> typing.Set[str]:
    matches = re.findall(MAP_FOLDER_REGEX, description)
    map_folders = set()
    
    for m in matches:
        map_folders.add(m.strip())
    

    return map_folders


def prompt_yn(prompt : str) -> bool:
    while True:
        response = input(prompt + " [y/n] ").lower()
        if response == "y":
            return True
        elif response == "n":
            return False
        else:
            print("Invalid response")
            
        

def get_args():
    parser = argparse.ArgumentParser(description="Generate server configuration for a Project Zomboid workshop collection")
    
    parser.add_argument("--collection-id", "-c", type=int, help="Workshop collection ID", required=True)
    parser.add_argument("--server-name", "-n", help="Server name", required=True)
    parser.add_argument("--threads", "-t", type=int, help="Number of threads to use", default=16)

    return parser.parse_args()

@dataclasses.dataclass
class WorkshopItem:
    workshop_id : int
    dependencies : typing.Set[int]
    mod_ids : typing.Set[str]
    map_folders : typing.Set[str]
    
    def __hash__(self):
        return hash(self.workshop_id)


def scrape_workshop_items(args : argparse.Namespace, workshop_ids : typing.Set[int]) -> typing.Set[WorkshopItem]:
    workshop_items = set()
    
    def process_item(item_id):
        soup = get_workshop_soup(item_id)
        
        workshop_items.add(WorkshopItem(
            workshop_id=item_id,
            dependencies=parse_dependencies(soup),
            mod_ids=parse_mod_ids(parse_workshop_description(soup)),
            map_folders=parse_map_folders(parse_workshop_description(soup))
        ))    
        
        
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for item_id in workshop_ids:
            futures.append(executor.submit(process_item, item_id))
            
        for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
            future.result()
            
    return workshop_items

def select_mods_maps(workshop_items : typing.Set[WorkshopItem]):
    for item in workshop_items:
        if len(item.mod_ids) == 0:
            print(f"Warning: Workshop item {item.workshop_id} has no mod IDs")
        
        if len(item.mod_ids) > 1:
            selected_mod_ids = pick(list(item.mod_ids), f"Select mods for workshop item {WORKSHOP_FILE_URL.format(item.workshop_id)}", multiselect=True, min_selection_count=1)
            item.mod_ids = set(t[0] for t in selected_mod_ids)
            
        if len(item.map_folders) > 1:
            selected_map_folders = pick(list(item.map_folders), f"Select map folders for workshop item {WORKSHOP_FILE_URL.format(item.workshop_id)}", multiselect=True, min_selection_count=1)
            item.map_folders = set(t[0] for t in selected_map_folders)

def main():
    args = get_args()

    workshop_items = scrape_workshop_items(args, set(yield_workshop_ids(args.collection_id)))
    
    select_mods_maps(workshop_items) # this modifies workshop_items
    
    # extract mod IDs and map folders
    # prompt user to select mods and map folders
    workshop_ids = set()
    dependencies = set()
    mod_ids = set()
    map_folders = set()
    
    for item in workshop_items:
        workshop_ids.add(item.workshop_id)
        dependencies.update(item.dependencies)
        mod_ids.update(item.mod_ids)
        map_folders.update(item.map_folders)
    
    missing_dependencies = dependencies - workshop_ids
    if len(missing_dependencies) > 0:
        print(f"Warning: {len(missing_dependencies)} dependencies are missing from the collection")
        
        for item_id in missing_dependencies:
            print(f"Mising: {WORKSHOP_FILE_URL.format(item_id)}")
            
        if prompt_yn("Add missing dependencies?"):
            dependency_items = scrape_workshop_items(args, missing_dependencies)
            select_mods_maps(dependency_items)
            
            for item in dependency_items:
                workshop_ids.add(item.workshop_id)
                dependencies.update(item.dependencies)
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