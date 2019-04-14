from datetime import datetime
import json
import os
import requests
import time
import urllib3

from bs4 import BeautifulSoup
import regex as re
from unidecode import unidecode

# Collection Settings.
START_URL = 'https://www.loc.gov/collections/general-news-on-the-internet-web-archive/?st=list&c=150'
OUTPUT_PATH = os.path.join(os.getcwd(), 'json')
ORIGINAL_XML_PATH = os.path.join(os.getcwd(), 'xml')
COURTESY_SLEEP = 1.15

# Get rid of SSL warnings.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get all results.
sites = []
print(' ╔' + START_URL.split('?')[0], end='')
with requests.get(START_URL, verify=False) as response:
    list_soup = BeautifulSoup(response.text, 'html5lib')

# Look for archived web sites; avoid other stuff.
results = []
for rc in list_soup.find_all('div', {'class': 'description'}):
    if 'Archived Web Site' in rc.find('span', {'class': 'original-format'}).text:
        results.append(rc)
print(f' ({len(results)} Results)')

index = 0
for rc in results:
    index += 1
    with requests.get(rc.find('a').get('href'), verify=False) as response:
        result_soup = BeautifulSoup(response.text, 'html5lib')
    urls = [a.get('href') for a in result_soup.find_all('a')]
    xml_url = next(a for a in urls if str(a).endswith('.xml'))

    # Use metadata to add a site to our list.
    with requests.get(xml_url) as response:
        metadata_soup = BeautifulSoup(response.text, 'lxml')

    site_name = metadata_soup.find('title').text    
    if index < len(results):
        print(' ╠═╤' + site_name, end='')
    else:
        print(' ╚═╤' + site_name, end='')

    site_slug = unidecode(site_name).strip().lower()
    site_slug = site_slug.replace('.com', '').replace('.net', '').replace('.org', '')
    site_slug = re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', site_slug))

    # NB: First URL is not always the "base" one. Use shortest instead.
    site_urls = [a.text for a in metadata_soup.find_all('text', {'displaylabel': 'domain'})]
    site_url = min([s for s in site_urls if 'pinterest' not in s], key=len)  # Hotfix for one site
    print(' (' + site_url +')')

    sites.append({
        'name': site_name,
        'slug': site_slug,
        'url': site_url,
        'other_urls': site_urls,
        'language': metadata_soup.find('languageterm').text,
        'media-type': metadata_soup.find('genre').text,
        'target-audience': metadata_soup.find('targetaudience').text,
        'location': metadata_soup.find('placeterm').text,
        'date': datetime.utcnow().strftime('%Y-%m-%d')
    })

    # Save JSON metadata.
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)
    filename = os.path.join(OUTPUT_PATH, site_slug + '.json')
    if index < len(results):
        print(' ║ ├─' + filename)
    else:
        print('   ├─' + filename)
    with open(filename, 'w', encoding='utf-8') as outfile:
        json.dump(sites[-1:][0], outfile, ensure_ascii=False, indent=4)

    # Keep a copy of the original XML, too.
    if not os.path.exists(ORIGINAL_XML_PATH):
        os.makedirs(ORIGINAL_XML_PATH)
    filename = os.path.join(ORIGINAL_XML_PATH, site_slug + '.xml')
    if index < len(results):
        print(' ║ └─' + filename)
    else:
        print('   └─' + filename)
    with open(filename, 'w', encoding='utf-8') as outfile:
        outfile.write(metadata_soup.mods.prettify())

    time.sleep(COURTESY_SLEEP)