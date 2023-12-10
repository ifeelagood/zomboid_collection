# Project Zomboid Mod Configuration Script
The game "Project Zomboid" utilises the steam workshop for mods. However, when hosting a dedicated server, mods are installed via modifying the server's "SERVERNAME.ini" file delimeted by semicolons:

`Mods=` - List of mod IDs to be enabled on the server.

`WorkshopItems=` - List of workshop IDs to be downloaded on the server.

`Map=` - Maps to be loaded, with priority in order of appearance.

Given a steam workshop collection, this script will:

1. Fetch all Mod IDs, Workshop IDs and Map names from the collection.
2. Prompt the user to select which mods to enable, if multiple IDs are available
3. Prompt the user to select which maps to load, if multiple maps are available
4. Generate a "SERVERNAME.ini" file with the selected mods and maps.

## Quick Start

`python3 get_collection.py -c COLLECTION_ID -o SERVERNAME.ini`

## Usage

`--collection, -c` - Steam workshop collection ID. This can be found in the URL of the collection. For example, the collection ID for the collection `https://steamcommunity.com/sharedfiles/filedetails/?id=123456789` is `123456789`.

`--output, -o` - Path to output ini file. Defaults to `servertest.ini` in the current directory.

`--overwrite, -w` - Overwrite fields in output ini file if it already exists. Defaults to `False`.

`--threads, -t` - Number of threads to use when downloading workshop items. Defaults to 16.

`--no-cache` - Do not use cached requests. This will force the script to make requests for mod IDs and workshop items. Use if collection/mods has been updated recently.

`--no-dependencies` - Do not add dependencies for workshop items. Defaults to `False`.

`--help, -h` - Display help message.

## Installation

1. Install Python. This script was developed using Python 3.11.9, but should work with any version of Python 3.
2. Install the required packages using `pip install -r requirements.txt`

## Features

Problems I encountered when using other available scripts:

- Some do not properly handle mods with multiple IDs. This is annoying when not all are meant to be enabled.

- Some do not handle maps at all. This one makes sure "Mauldraugh, KY" is always last in the list.

- Some are very slow. This one uses multithreading to download workshop items.

Additional Features:

- Request caching. As selecting mod ids can be a finicky process (especially when there are a lot of mods), the script will cache the requests for mod IDs and workshop items. This means that if you run the script again with the same collection ID, it will not need to make the requests again.

- Dependency Resolution. If a workshop item has dependencies, the script will automatically and recursively add them to the list.