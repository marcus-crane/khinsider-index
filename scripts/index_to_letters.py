import json
from pathlib import Path
import string
import urllib.parse

BASE_URL = 'https://downloads.khinsider.com/'

Path('../letters').mkdir(exist_ok=True)

with open('../index.json') as file:
    data = json.loads(file.read())

title_map = {}

def get_prefix(name):
    char = name[0].lower()
    if char not in string.ascii_lowercase:
        return '_special'
    return char

titles = list(data['entries'].keys())

for title in titles:
    prefix = get_prefix(title)
    if prefix not in title_map.keys():
        title_map[prefix] = {}
    title_map[prefix][title] = urllib.parse.urljoin(BASE_URL, data['entries'][title])

for section in title_map.keys():
    with open(f"../letters/{section}.json", 'w') as file:
        json.dump(title_map[section], file, indent=2)