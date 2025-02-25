





if title:
    title_url = re.sub(r'nhtoc\.htm', r'NHTOC/nhtoc_ch', url)
    title_url = title_url + title + ".htm"

    ack = await fetch_title(title_url, title, toc_list, collection_path)

    if not ack:
        logger.warning(f"No titles found for {title}")
        return None  # Handle this gracefully

    with connect_to_mongodb() as client:
        logger.info(f"Connected to {config['docdb']} database")
        db = client[config['docdb']]
        collection = db[config['collection_name']]

        if (book := collection.find_one({"jx": 'NH', "titleNo": title, "isDeleted": {"$exists": False}})) is not None:
            task_id = book["taskId"]
            query = {"taskId": task_id}
            file_details = []

            for file in ack.keys():
                details = {
                    "Name": f"{title}_{file}.xml",
                    "collection": "true",
                    "common_conversion": "",
                    "mncr_conversion": "",
                    "meta": "",
                    "toc": "",
                    "type": config['NH_seclevel'],
                    "titleName": ack[file],
                    "normCite": ""
                }
                file_details.append(details)

            con_values = {"$set": {"fileDetail": file_details}}
            collection.update_one(query, con_values)

            total_file = len(ack)
            total = {"$set": {"totalFiles": total_file, "finalStage": "Conversion"}}
            collection.update_one(query, total)

            logger.info(f"Title {title} inserted into {config['collection_name']} collection")

        client.close()
        logger.info(f"Title {title} Conversion in progress")

        conv_url = config_yml['convert_request']
        payload = json.dumps({
            "data": {
                "createdBy": "",
                "createdDate": datetime.now().strftime("%Y-%m-%d"),
                "firstleveno": f"{title}",
                "jx": "NH",
                "firstLeveltitle": ""
            },
            "additionalParam": {
                "convRawXm1": "yes",
                "convMncrXm1": "string"
            }
        }, indent=4)

        headers = {'Content-Type': 'application/json'}
        logger.info(f"Payload {payload}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(conv_url, headers=headers, data=payload) as response:
                    request_resp = await response.text()
                    logger.info(f"Conversion request sent for {title}")
        except Exception as e:
            logger.error(f"Conversion request failed for {title} {e}")

    return ack
else:
    for title_num, div_value in toc_list.items():
        title_url = re.sub(r'nhtoc\.htm', r'NHTOC/nhtoc_ch', url)
        title_url = title_url + title_num + ".htm"
        message = await fetch_title(title_url, title_num, toc_list, collection_path)

    return message



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

    # Find first section link in <h2>
    section_link_tag = None
    for h2_tag in body_tag.find_all('h2'):
        a_tag = h2_tag.find('a', href=True)
        if a_tag and "../" in a_tag["href"]:
            section_link_tag = a_tag
            break

    section_url = base_url + section_link_tag['href'].replace('../', '') if section_link_tag else None
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
    meta_tag = section_soup.find('meta', {'name': 'chapter'})
    if meta_tag:
        chapter_name = meta_tag['content'].strip()
    safe_chapter_name = chapter_name.replace(':', ' -').replace('/', '-').strip()

    chapter_content = CHAPTER_TEXT + f'\n<p class="c1">{title_name}</p>'
    chapter_content += f'\n<p class="c1">{chapter_name}</p>'

    sections = section_soup.find_all('center')






    async def fetch_section(section_url, chapter_name, title_name):
    """Fetch section data and return formatted content for MongoDB storage"""
    section_soup = await get_content(section_url)
    if not section_soup:
        return None

    meta_tag = section_soup.find('meta', {'name': 'chapter'})
    if meta_tag:
        chapter_name = meta_tag['content'].strip()

    chapter_content = {
        "title_name": title_name,
        "chapter_name": chapter_name,
        "sections": []
    }

    sections = section_soup.find_all('center')
    seen_sections = set()
    section_count = 0

    for section in sections:
        section_title_tag = section.find_next('b')
        if section_title_tag:
            section_text = section_title_tag.get_text(strip=True)
            
            if section_text in seen_sections:
                continue
            seen_sections.add(section_text)

            section_content = section.find_next('codesect')
            section_content_text = section_content.get_text("\n").strip() if section_content else "No content available"

            formatted_content = [
                {"type": "h3", "text": line.strip()} if re.match(r"^?[a-z0-9]+?\.", line.strip()) else {"type": "p", "text": line.strip()}
                for line in section_content_text.split("\n") if line.strip()
            ]

            chapter_content["sections"].append({
                "section_title": section_text,
                "content": formatted_content
            })

            source_note = section.find_next('sourcenote')
            if source_note:
                history_text = source_note.get_text(" ", strip=True)
                chapter_content["sections"][-1]["history"] = history_text

            section_count += 1

    if section_count > 0:
        return chapter_content
    else:
        logger.warning(f"No sections found for {chapter_name}. Skipping.")
        return None


        
    section_count = 0
    for section in sections:
        section_title = section.find('h3')
        if section_title:
            section_text = section_title.get_text(strip=True)
            chapter_content += f'\n<h1 class="c2">{section_text}</h1>'

            section_content = section.find_next('codesect')
            section_content_text = section_content.get_text(strip=True) if section_content else ""

            if not section_content_text.strip():
                chapter_content += f'\n<h2>No additional content available.</h2>'
            else:
                formatted_content = ""
                for line in re.split(r'([a-z0-9]+)', section_content_text):
                    if re.match(r'^[a-z0-9]+$', line.strip()):
                        formatted_content += f'\n<h2>{line.strip()}</h2>'
                    else:
                        formatted_content += f'\n<h3>{line.strip()}</h3>'
                chapter_content += formatted_content

            source_note = section.find_next('sourcenote')
            if source_note:
                history_text = source_note.get_text(strip=True)
                chapter_content += f'\n<p class="gc.nh.gov"><span class="history"> History: </span> {history_text}</p>'

            section_count += 1

    chapter_content += "\n</div>\n</body>"

    xml_filename = os.path.join(title_directory, f'{safe_chapter_name}.xml')
    with open(xml_filename, 'w', encoding='utf-8') as f:
        f.write(chapter_content)

    print(f"✅ Saved {section_count} sections in {xml_filename}")

print("\n✅ All titles and chapters processed successfully!")






async def fetch_section(section_url, chapter_name, title_name):
    """Fetch section data and return formatted content for MongoDB storage"""
    section_soup = await get_content(section_url)
    if not section_soup:
        return None

    meta_tag = section_soup.find('meta', {'name': 'chapter'})
    if meta_tag:
        chapter_name = meta_tag['content'].strip()

    chapter_content = {
        "title_name": title_name,
        "chapter_name": chapter_name,
        "sections": []
    }

    sections = section_soup.find_all('center')
    seen_sections = set()
    section_count = 0

    for section in sections:
        section_title_tag = section.find_next('b')
        if section_title_tag:
            section_text = section_title_tag.get_text(strip=True)
            
            if section_text in seen_sections:
                continue
            seen_sections.add(section_text)

            section_content = section.find_next('codesect')
            section_content_text = section_content.get_text("\n").strip() if section_content else "No content available"

            formatted_content = [
                {"type": "h3", "text": line.strip()} if re.match(r"^?[a-z0-9]+?\.", line.strip()) else {"type": "p", "text": line.strip()}
                for line in section_content_text.split("\n") if line.strip()
            ]

            chapter_content["sections"].append({
                "section_title": section_text,
                "content": formatted_content
            })

            source_note = section.find_next('sourcenote')
            if source_note:
                history_text = source_note.get_text(" ", strip=True)
                chapter_content["sections"][-1]["history"] = history_text

            section_count += 1

    if section_count > 0:
        return chapter_content
    else:
        logger.warning(f"No sections found for {chapter_name}. Skipping.")
        return None






async def download_NH_input(url, base_url, title, download):
    """Download and process NH legal statutes and store in MongoDB"""
    
    toc_list = await get_title_dict(url)

    if title:
        title_url = re.sub(r'nhtoc\.htm', r'NHTOC/nhtoc_ch', url) + title + ".htm"
        ack = await fetch_title(title, title_url)

        with connect_to_mongodb() as client:
            logger.info(f"Connected to {config['docdb']} database")
            db = client[config['docdb']]
            collection = db[config['collection_name']]

            if (book := collection.find_one({"jx": 'NH', "titleNo": title, "isDeleted": {"$exists": False}})) is not None:
                task_id = book["taskId"]
                query = {"taskId": task_id}
                file_details = []

                for chapter_name, chapter_url in ack["chapters"].items():
                    chapter_data = await fetch_chapter(chapter_name, chapter_url, ack["title_name"])
                    
                    if chapter_data:
                        details = {
                            "Name": f"{title}_{chapter_name}",
                            "content": chapter_data,
                            "type": config['NH_seclevel'],
                            "titleName": chapter_name
                        }
                        file_details.append(details)
                        collection.insert_one(details)

                con_values = {"$set": {"fileDetail": file_details}}
                collection.update_one(query, con_values)

                total_files = len(file_details)
                collection.update_one(query, {"$set": {"totalFiles": total_files, "finalStage": "Conversion"}})

                logger.info(f"Title {title} inserted into {config['collection_name']} collection")

            client.close()
            logger.info(f"Title {title} Conversion in progress")

        return ack
    else:
        for title_num in toc_list.keys():
            title_url = re.sub(r'nhtoc\.htm', r'NHTOC/nhtoc_ch', url) + title_num + ".htm"
            await fetch_title(title_num, title_url)

