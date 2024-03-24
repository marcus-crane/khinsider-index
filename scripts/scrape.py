import json
import os
from pathlib import Path
import urllib.parse

from bs4 import BeautifulSoup
import pendulum
from pytimeparse.timeparse import timeparse
import requests

BASE_URL = 'https://downloads.khinsider.com/'

Path('../albums').mkdir(exist_ok=True)

# TODO: Error out when file is malformed so it can be handled properly. Probably write a log in a directory for me to review
# TODO: Convert string numbers to proper integers
# TODO: Add totals for runtime and file sizes

SYMBOLS = {
    'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
    'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
                       'zetta', 'iotta'),
    'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
    'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
                       'zebi', 'yobi'),
}

# Nicked from https://code.activestate.com/recipes/578019-bytes-to-human-human-to-bytes-converter/
def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.

      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776

      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])

def parse_album_metadata(album, msoup):
    content = msoup.find("p", {"align": "left"}).contents
    platforms = {}
    developers = {}
    publishers = {}
    genres = {}
    uploaders = {}
    global inCategory
    inCategory = ''
    for entry in content:
        if ":" in entry:
            inCategory = entry.strip().replace(":", "").lower()
            continue
        if entry.name == 'br':
            inCategory = ''
            continue
        if inCategory == 'platforms' and entry.name == 'a':
            platforms[entry.text.strip()] = urllib.parse.urljoin(BASE_URL, entry.attrs['href'])
        if inCategory == 'year':
            album['year'] = int(entry.text.strip())
        if inCategory == 'catalog number' and entry.name == 'b':
            if entry.text.strip().lower() == 'n/a':
                album['catalog_number'] = None
            else:
                album['catalog_number'] = entry.text.strip()
        if inCategory == 'developed by' and entry.name == 'a':
            developers[entry.text.strip()] = urllib.parse.urljoin(BASE_URL, entry.attrs['href'])
        if inCategory == 'published by' and entry.name == 'a':
            publishers[entry.text.strip()] = urllib.parse.urljoin(BASE_URL, entry.attrs['href'])
        if inCategory == 'date added' and entry.name == 'b':
            album['date_added'] = pendulum.from_format(entry.text.strip(), "MMM Do, YYYY", tz="UTC").to_rfc3339_string()
        if inCategory == 'album type' and entry.name == 'b':
            genres[entry.a.text.strip()] = urllib.parse.urljoin(BASE_URL, entry.a.attrs['href'])
        if inCategory == 'uploaded by' and entry.name == 'a':
            uploaders[entry.text.strip()] = urllib.parse.urljoin(BASE_URL, entry.attrs['href'])
    album['platforms'] = platforms
    album['developers'] = developers
    album['publishers'] = publishers
    album['genres'] = genres
    return album
        

def parse_album_tracks(album, msoup):
    track_rows = msoup.find("table", id="songlist").find_all("tr")[1:]
    table_headers = msoup.find("table", id="songlist").find("tr", id="songlist_header").find_all("th")
    headers = {}

    print(f"Found {len(track_rows)} tracks")

    track_el_reached = False
    for i, x in enumerate(table_headers):
        title = x.text.strip()
        if track_el_reached:
            # Needed because there is no actual header for track length but there is
            # a column
            headers[i+1] = title
        else:
            headers[i] = title
        if title == 'Song Name':
            track_el_reached = True
            headers[i+1] = 'Track Length'

    tracks = []

    for row in track_rows:
        rowsoup = row.find_all("td")
        track_metadata = {'disc_number': None, 'filesize_flac_bytes': None, 'filesize_mp3_bytes': None}
        track_url = None
        for idx, entry in enumerate(rowsoup):
            if idx == 0:
                # Skip table header
                continue
            if idx == len(rowsoup):
                # Skip table footer
                continue
            if idx in headers.keys() and headers[idx] == 'CD':
                track_metadata['disc_number'] = int(entry.text.strip())
            if idx in headers.keys() and headers[idx] == 'Track Length':
                track_metadata['runtime'] = timeparse(entry.text.strip())
            if idx in headers.keys() and headers[idx] == '#':
                try:
                    track_metadata['track_number'] = int(entry.text.strip().replace(".", ""))
                except ValueError:
                    track_metadata['track_number'] = 0
            if idx in headers.keys() and headers[idx] == 'Song Name':
                track_metadata['title'] = entry.text.strip()
            if idx in headers.keys() and headers[idx] == 'MP3':
                track_metadata['filesize_mp3_bytes'] = human2bytes(entry.text.strip()[:-1])
                track_url = f"https://downloads.khinsider.com{entry.find('a')['href']}"
            if idx in headers.keys() and headers[idx] == 'FLAC':
                track_metadata['filesize_flac_bytes'] = human2bytes(entry.text.strip()[:-1])
                # It's probably possible to only have a FLAC file and no MP3s
                track_url = f"https://downloads.khinsider.com{entry.find('a')['href']}"
        
        if track_url is not None:
            track_sources = get_real_tracks(track_url)
            for source in track_sources:
                if '.mp3' in source:
                    track_metadata['source_mp3'] = source
                if '.flac' in source:
                    track_metadata['source_flac'] = source

            track_metadata['track_url'] = track_url
            tracks.append(track_metadata)
    
    album['tracks'] = tracks

    total_runtime = 0
    total_mp3_size = 0
    total_flac_size = 0

    for track in tracks:
        total_runtime += track['runtime']
        if 'filesize_mp3_bytes' in track.keys() and 'source_mp3' in track.keys():
            total_mp3_size += track['filesize_mp3_bytes']
        if 'filesize_flac_bytes' in track.keys() and 'source_flac' in track.keys():
            total_flac_size += track['filesize_flac_bytes']

    album['total'] = {
        'runtime': total_runtime,
        'filesize_mp3_bytes': total_mp3_size,
        'filesize_flac_bytes': total_flac_size,
        'tracks': len(tracks)
    }
    return album

def get_real_tracks(url):
    tr = requests.get(url)
    rsoup = BeautifulSoup(tr.text, 'html.parser')
    rlinks = rsoup.find_all('span', {'class': 'songDownloadLink'})
    return [link.parent['href'] for link in rlinks]

letter = os.getenv("LETTER")

if letter:
    with open(f"../letters/{letter}.json", "r") as file:
        data = json.loads(file.read())
        links = list(data.values())
else:
    with open("../index.json", "r") as file:
        data = json.loads(file.read())
        links = list(data['entries'].values())

links.sort()

processed_links = [x.replace('.json', '') for x in os.listdir("../albums")]

letter = os.getenv("LETTER")

with open("../failure.log", "r") as file:
    failures = file.read()

for link in links:
    slug = link.replace('/game-soundtracks/album/', '').replace('https://downloads.khinsider.com', '')
    if slug in processed_links or slug in failures: # We skip failures for now but will handle them when sync is complete
        # print(f"Skipping {slug}")
        continue
    try:
        url = urllib.parse.urljoin(BASE_URL, link)
        mr = requests.get(url)
        msoup = BeautifulSoup(mr.text, 'html.parser')
        title = msoup.css.select("#pageContent h2")[0].text

        print(f"Processing {slug}")

        images = []

        for image in msoup.find("div", {"class": "albumImage"}).find_all("a"):
            images.append(image['href'])
            

        album = {
            "title": title,
            "titles_alternative": [],
            "crawled_at": pendulum.now(tz='UTC').to_rfc3339_string(),
            "slug": slug,
            "url": url,
            "platforms": [],
            "images": images
        }

        alt_titles = msoup.find("p", {"class": "albuminfoAlternativeTitles"})
        if alt_titles is not None:
            album['titles_alternative'] = alt_titles.text.split("\r\n")

        album = parse_album_metadata(album, msoup)
        album = parse_album_tracks(album, msoup)

        with open(f"../albums/{slug}.json", 'w') as file:
            json.dump(album, file, indent=2)
    except Exception:
        with open("../failure.log", "a") as file:
            file.write(f"{slug}\n")
