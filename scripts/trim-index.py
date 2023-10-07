import json

with open("../index.json", "r") as file:
    data = json.loads(file.read())

entries = data.get('entries')

index = {}

for entry in entries:
    trimmed_uri = entries[entry].replace('/game-soundtracks/album/', '')
    index[entry] = trimmed_uri

with open("../index-alt.json", "w") as file:
    json.dump(index, file)