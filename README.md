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

## Usage

`--collection, -c` - Steam workshop collection ID. This can be found in the URL of the collection. For example, the collection ID for the collection `https://steamcommunity.com/sharedfiles/filedetails/?id=123456789` is `123456789`.

`--servername, -n` - Name of the server. This will be used to name the generated "SERVERNAME.ini" file.

`--threads, -t` - Number of threads to use when downloading workshop items. Defaults to 16.

`--help, -h` - Display help message.

## Features

Problems I encountered when using other available scripts:

- Some do not properly handle mods with multiple IDs. This is annoying when not all are meant to be enabled.

- Some do not handle maps at all. This one makes sure "Mauldraugh, KY" is always last in the list.

- Some are very slow. This one uses multithreading to download workshop items.