import requests
from bs4 import BeautifulSoup
import logging
import re

class ArticleFetcher:
    def __init__(self, article_urls, gui_queue):
        self.article_urls = article_urls
        self.gui_queue = gui_queue

    def fetch_articles(self):
        articles = []
        for idx, url in enumerate(self.article_urls, 1):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title_tag = soup.find('h2')
                    if not title_tag:
                        title_tag = soup.find('h1')
                    title = title_tag.get_text(separator=' ', strip=True) if title_tag else 'Kein Titel'

                    # Artikelinhalt extrahieren
                    body = self.extract_article_body(soup)

                    if not body.strip():
                        logging.warning(f"Leerer Artikeltext bei URL: {url}")
                        continue

                    articles.append({
                        'title': title,
                        'url': url,
                        'body': body
                    })
                    logging.info(f"Artikel {idx}/{len(self.article_urls)} abgerufen: {title}")
                    progress = (idx / len(self.article_urls)) * 100
                    self.gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Artikel abrufen... {progress:.2f}% abgeschlossen"})
                else:
                    logging.error(f"Fehler beim Abrufen des Artikels: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Fehler beim Verbinden mit der URL {url}: {e}")
        return articles

    def extract_article_body(self, soup):
        # Suche nach dem Hauptinhalt des Artikels
        article_body = soup.find('div', {'class': re.compile(r'Article.*Body')})
        if not article_body:
            article_body = soup.find('section', {'class': re.compile(r'Article.*Content')})
        if article_body:
            paragraphs = article_body.find_all('p')
            body_text = " ".join([p.get_text(separator=' ', strip=True) for p in paragraphs if p.get_text(strip=True)])
            return body_text
        else:
            # Fallback: gesamter Text
            return soup.get_text(separator=' ', strip=True)
