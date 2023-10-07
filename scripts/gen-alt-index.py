import json

with open("../index.json", "r") as file:
    data = json.loads(file.read())

entries = data.get('entries')

index = {}

for entry in entries:
    trimmed_uri = entries[entry].replace('/game-soundtracks/album/', '')
    try:
        with open(f"../albums/{trimmed_uri}.json", "r") as file:
            album = json.loads(file.read())
            meta = { 's': trimmed_uri, 'm': False, 'f': False }
            if album['total']['filesize_mp3_bytes'] > 0:
                meta['m'] = True
            if album['total']['filesize_flac_bytes'] > 0:
                meta['f'] = True
            if 'year' in album.keys():
                meta['y'] = album['year']
            if 'genres' in album.keys() and len(album['genres']) >= 1:
                meta['g'] = list(album['genres'].keys())[0]
            if 'tracks' in album.get('total', {}):
                meta['c'] = album['total']['tracks']
            if album['tracks'][-1]['disc_number'] is not None:
                meta['d'] = album['tracks'][-1]['disc_number']

            index[entry] = meta
    except Exception as ex:
        # pass
        print(f"Issue with {trimmed_uri}: {ex}")

with open("../index-alt.json", "w") as file:
    json.dump(index, file)