import glob
import json
import os

albums = glob.glob("../albums/*.json")
letters = glob.glob("../letters/*.json")

with open("../index.json", "r") as file:
    data = json.loads(file.read())

entries = [f"{x.replace('/game-soundtracks/album/', '')}.json" for x in data['entries'].values()]

with open("../failure.log", "r") as file:
    failures = file.read().split("\n")

for album in albums:
    filename = album.replace('../albums/', '')
    if filename not in entries:
        os.remove(album)
        print(f"Deleted {album}")
    # if filename in failures:
    #     print(f"{filename} should be removed from the failure tracker")
