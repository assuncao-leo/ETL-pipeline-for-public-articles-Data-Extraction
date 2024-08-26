import requests
from bs4 import BeautifulSoup
import urllib.parse
import csv

def read_urls_and_pmids_from_csv(filename):
    urls_and_pmids = []
    with open(filename, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            urls_and_pmids.append((row['url'], row['pmcid']))
    return urls_and_pmids

def extract_content_and_save(urls_and_pmids):
    for full_url, pmc_id in urls_and_pmids:
        response = requests.get(full_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch the webpage: {full_url}")
            continue

        webpage_content = response.text
        soup = BeautifulSoup(webpage_content, "html.parser")
        parsed_url = urllib.parse.urlparse(full_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        sections_to_process = [
            ("abstract", "abstract"),
            ("introduction", "introduction"),
            ("method", "method"),
            ("experimental", "method"),
            ("results", "result"),
            ("discussion", "discussion"),
            ("conclusion", "conclusion")
        ]

        for header_text, content_type in sections_to_process:
            sections = soup.find_all(lambda tag: tag.name == "h2" and header_text.lower() in tag.text.lower())
            if content_type == "introduction":
                sections += soup.find_all("h2", class_=["headless", "nomenu"])

            for section in sections:
                parent_div = section.find_parent("div")
                if parent_div:
                    paragraphs = parent_div.find_all('p')
                    zone_counter = 1
                    for paragraph in paragraphs:
                        if paragraph.text.strip():
                            text_type = "caption" if "caption" in paragraph.parent.get("class", []) else "text"
                            figure_links = set()
                            if text_type == "caption":
                                figure_links.update(paragraph.parent.find_all('a', href=True, target="figure"))
                                previous_div = paragraph.parent.find_previous_sibling("div")
                                if previous_div:
                                    figure_links.update(previous_div.find_all('a', href=True, target="figure"))
                            else:
                                figure_links.update(paragraph.find_all('a', href=True, target="figure"))

                            figure_urls = '; '.join(set(base_url + urllib.parse.quote(a['href'], safe=":/") for a in figure_links))
                            figure_numbers = '; '.join(set(a.get('rid-figpopup', '') for a in figure_links))
                            references = '; '.join([a['href'] for a in paragraph.find_all('a', href=True, class_="bibr popnode")])

                            with open("extracted_data.csv", "a", newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writerow({
                                    'pmc_id': pmc_id,
                                    'content_type': content_type,
                                    'text_type': text_type,
                                    'content': paragraph.text.strip(),
                                    'zone': zone_counter,
                                    'reference': references,
                                    'figure_url': figure_urls,
                                    'figure_number': figure_numbers
                                })
                            zone_counter += 1

# Headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

fieldnames = ['pmc_id', 'content_type', 'text_type', 'content', 'zone', 'reference', 'figure_url', 'figure_number']

# Reading URLs and PMCIDs from the CSV file
urls_and_pmids = read_urls_and_pmids_from_csv("pubmed_pmcid_data.csv")

# Initialize the CSV file once with headers
with open("extracted_data.csv", "w", newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# Extracting content from each URL and appending data
extract_content_and_save(urls_and_pmids)

print("Extraction complete. Data saved to extracted_data.csv.")
