from bs4 import BeautifulSoup
from pytimeparse.timeparse import timeparse

import json
import requests

BASE_URL = 'https://downloads.khinsider.com/'

# r = requests.get("https://downloads.khinsider.com/console-list")

# soup = BeautifulSoup(r.text, 'html.parser')

# platforms = {}

# platformList = soup.find(id='pageContent').find_all('a')

# for item in platformList:
#     name = item.text
#     slug = item.attrs['href'].replace('/game-soundtracks/', '')
#     platforms[name] = slug

# with open('platforms.json', 'w') as file:
#     json.dump(platforms, file, indent=2, sort_keys=True)

# TODO: Error out when file is malformed so it can be handled properly. Probably write a log in a directory for me to review
# TODO: Convert string numbers to proper integers
# TODO: Add totals for runtime and file sizes

def parse_album_tracks(soup):
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
    
    print(headers)

    tracks = []

    total_duration = 0
    total_mp3_size = 0
    total_flac_size = 0

    for row in track_rows:
        rowsoup = row.find_all("td")
        track_metadata = {}
        track_url = None
        for idx, entry in enumerate(rowsoup):
            if idx == 0:
                # Skip table header
                continue
            if idx == len(rowsoup):
                # Skip table footer
                continue
            if idx in headers.keys() and headers[idx] == 'CD':
                track_metadata['disc_number'] = entry.text.strip()
            if idx in headers.keys() and headers[idx] == 'Track Length':
                track_metadata['runtime'] = timeparse(entry.text.strip())
            if idx in headers.keys() and headers[idx] == '#':
                track_metadata['track_number'] = entry.text.strip().replace(".", "")
            if idx in headers.keys() and headers[idx] == 'Song Name':
                track_metadata['title'] = entry.text.strip()
            if idx in headers.keys() and headers[idx] == 'MP3':
                track_metadata['filesize_mp3_bytes'] = entry.text.strip()
                track_metadata['mp3_available'] = True
                track_url = f"https://downloads.khinsider.com{entry.find('a')['href']}"
            if idx in headers.keys() and headers[idx] == 'FLAC':
                track_metadata['filesize_flac_bytes'] = entry.text.strip()
                track_metadata['flac_available'] = True
        
        if track_url is not None:
            track_sources = get_real_tracks(track_url)
            for source in track_sources:
                if '.mp3' in source:
                    track_metadata['source_mp3'] = source
                if '.flac' in source:
                    track_metadata['source_flac'] = source

            track_metadata['track_url'] = track_url
            tracks.append(track_metadata)
    
    return tracks

def get_real_tracks(url):
    print(f"Fetching {url}")
    tr = requests.get(url)
    rsoup = BeautifulSoup(tr.text, 'html.parser')
    rlinks = rsoup.find_all('span', {'class': 'songDownloadLink'})
    return [link.parent['href'] for link in rlinks]

r = requests.get("https://downloads.khinsider.com/game-soundtracks/browse/%23")

soup = BeautifulSoup(r.text, 'html.parser')

albumList = soup.css.select("table.albumList tr")[1:]

for item in albumList:
    albumUrlSuffix = item.css.select('td a')[0]['href']
    slug = albumUrlSuffix.replace("/game-soundtracks/album/", "")
    url = f"https://downloads.khinsider.com{albumUrlSuffix}"
    mr = requests.get(url)
    msoup = BeautifulSoup(mr.text, 'html.parser')
    title = msoup.css.select("#pageContent h2")[0].text

    print(title)
    print(url)

    album = {
        "title": title,
        "slug": slug,
        "url": url,
        "tracks": parse_album_tracks(msoup),
        "platforms": [],
        "images": []
    }

    with open(f"albums/{slug}.json", 'w') as file:
        json.dump(album, file, indent=2)
