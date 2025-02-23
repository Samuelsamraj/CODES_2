
import os import time import requests from bs4 import BeautifulSoup import re

CHAPTER_TEXT = """<?xml version="1.0"?>

<body>  
<div class="WordSection1">"""Base URLs

main_url = "https://gc.nh.gov/rsa/html/nhtoc.htm" base_url = "https://gc.nh.gov/rsa/html/"

Create master directory

master_directory = "New_Hampshire_RSA_Titles" os.makedirs(master_directory, exist_ok=True)

Fetch main page

headers = {'User-Agent': 'Mozilla/5.0'} try: response = requests.get(main_url, headers=headers, timeout=10) response.raise_for_status() except requests.exceptions.RequestException as e: print(f"❌ Failed to fetch main page: {e}") exit()

soup = BeautifulSoup(response.text, 'html.parser')

Find all titles

title_links = soup.find_all('a', href=True) title_urls = [(a.text.strip(), base_url + a['href'].replace("../", "NHTOC/")) for a in title_links if 'NHTOC/' in a['href']]

print(f"Found {len(title_urls)} titles. Processing...")

Loop through each title

for title_name, title_url in title_urls: print(f"\n📖 Fetching {title_name} from {title_url}...") safe_title_name = title_name.replace(':', ' -').replace('/', '-').strip() title_directory = os.path.join(master_directory, safe_title_name) os.makedirs(title_directory, exist_ok=True)

# Fetch title page
try:
    title_response = requests.get(title_url, headers=headers, timeout=10)
    title_response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(f"⚠️ Skipping {title_name} - Failed to fetch title page: {e}")
    continue

title_soup = BeautifulSoup(title_response.text, 'html.parser')

# Find all chapter links
chapter_links = title_soup.find_all('a', href=True)
chapter_urls = [(a.text.strip(), base_url + "NHTOC/" + a['href']) for a in chapter_links if 'NHTOC-' in a['href']]

print(f"📂 Found {len(chapter_urls)} chapters in {title_name}. Processing...")

for chapter_name, chapter_url in chapter_urls:
    print(f"\n📄 Fetching {chapter_name} from {chapter_url}...")
    time.sleep(1)

    try:
        chapter_response = requests.get(chapter_url, headers=headers, timeout=10)
        chapter_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Skipping {chapter_name} - Failed to fetch chapter page: {e}")
        continue

    chapter_soup = BeautifulSoup(chapter_response.text, 'html.parser')
    body_tag = chapter_soup.find('body')
    if not body_tag:
        print(f"⚠️ Skipping {chapter_name} - No <body> tag found.")
        continue

    section_url = None
    for h2_tag in body_tag.find_all('h2'):
        a_tag = h2_tag.find('a', href=True)
        if a_tag and "../" in a_tag["href"]:
            section_url = base_url + a_tag["href"].replace('../', '')
            break

    print(f"🔗 Extracted section link: {section_url}")

    if not section_url:
        print(f"⚠️ No valid section link found. Checking for direct content...")
        direct_content = chapter_soup.find_all('p')
        chapter_content = CHAPTER_TEXT + f'\n<p class="c1">{title_name}</p>'
        chapter_content += f'\n<p class="c1">{chapter_name}</p>'
        for para in direct_content:
            chapter_content += f'\n<p>{para.get_text(strip=True)}</p>'
        chapter_content += "\n</div>\n</body>"
        xml_filename = os.path.join(title_directory, f'{chapter_name}.xml')
        with open(xml_filename, 'w', encoding='utf-8') as f:
            f.write(chapter_content)
        print(f"✅ Saved direct content for {chapter_name} in {xml_filename}")
        continue

    try:
        section_response = requests.get(section_url, headers=headers, timeout=10)
        section_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Skipping {chapter_name} - Failed to fetch section page: {e}")
        continue

    section_soup = BeautifulSoup(section_response.text, 'html.parser')
    chapter_content = CHAPTER_TEXT + f'\n<p class="c1">{title_name}</p>'
    chapter_content += f'\n<p class="c1">{chapter_name}</p>'

    sections = section_soup.find_all('center')
    section_count = 0
    for section in sections:
        bold_tag = section.find_next('b')
        if bold_tag:
            section_title = bold_tag.get_text(strip=True)
            chapter_content += f'\n<h1 class="c2">{section_title}</h1>'
            
            section_content = section.find_next('codesect')
            section_content_text = section_content.get_text("\n", strip=True) if section_content else ""
            
            # Include repealed content
            repealed_tag = section.find_next('sourcenote')
            repealed_text = repealed_tag.get_text("\n", strip=True) if repealed_tag else ""
            
            if not section_content_text.strip() and not repealed_text.strip():
                chapter_content += f'\n<h2>No additional content available.</h2>'
            else:
                if section_content_text.strip():
                    chapter_content += f'\n<h2>{section_content_text}</h2>'
                if repealed_text.strip():
                    chapter_content += f'\n<p class="gc.nh.gov">{repealed_text}</p>'
            
            section_count += 1

    chapter_content += "\n</div>\n</body>"

    xml_filename = os.path.join(title_directory, f'{chapter_name}.xml')
    with open(xml_filename, 'w', encoding='utf-8') as f:
        f.write(chapter_content)

    print(f"✅ Saved {section_count} sections in {xml_filename}")

print("\n✅ All titles and chapters processed successfully!")

