import json
import urllib.parse

from bs4 import BeautifulSoup
import requests

BASE_URL = 'https://downloads.khinsider.com/'

r = requests.get("https://downloads.khinsider.com/console-list")

soup = BeautifulSoup(r.text, 'html.parser')

platforms = {}

platformList = soup.find(id='pageContent').find_all('a')

for item in platformList:
    name = item.text
    slug = urllib.parse.urljoin(BASE_URL, item.attrs['href'])
    platforms[name] = slug

with open('../platforms.json', 'w') as file:
    json.dump(platforms, file, indent=2, sort_keys=True)