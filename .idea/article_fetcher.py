import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

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
                    body = self.extract_article_body(soup, url)

                    # Artikel-Datum extrahieren
                    article_date = self.get_article_date(soup)
                    if not article_date:
                        logging.warning(f"Konnte Datum für Artikel {url} nicht extrahieren. Setze aktuelles Datum.")
                        article_date = datetime.now()

                    articles.append({
                        'title': title,
                        'url': url,
                        'body': body,
                        'date': article_date
                    })
                    progress = (idx / len(self.article_urls)) * 100
                    self.gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Artikel abrufen... {progress:.2f}% abgeschlossen"})
                else:
                    logging.error(f"Fehler beim Abrufen des Artikels: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Fehler beim Abrufen des Artikels von {url}: {e}")
        return articles

    def extract_article_body(self, soup, url):
        # Versuche zuerst, den normalen Artikeltext zu extrahieren
        body_elements = soup.find_all('div', {'data-area': 'text'})
        if body_elements:
            body_text = " ".join([element.get_text(separator=' ', strip=True) for element in body_elements])
            return body_text

        # Falls kein Text gefunden wurde, könnte es sich um einen Spiegel+ Artikel handeln
        # Versuche, den Vorspann aus dem RichText Div zu extrahieren
        richtext_div = soup.find('div', class_=lambda x: x and x.startswith('RichText RichText--sans'))
        if richtext_div:
            body_text = richtext_div.get_text(separator=' ', strip=True)
            logging.info(f"Vorspann für Spiegel+ Artikel {url} extrahiert.")
            return body_text

        # Wenn immer noch kein Text gefunden wurde, verwende den Titel als Fallback
        logging.warning(f"Artikelinhalt nicht verfügbar für {url}. Verwende Titel als Text.")
        return ""  # Leerer Text, Sentimentanalyse wird später entsprechend angepasst

    def get_article_date(self, soup):
        # Suche nach dem <time> Tag mit class='timeformat'
        time_tag = soup.find('time', {'class': 'timeformat'})
        if time_tag and time_tag.get('datetime'):
            date_str = time_tag['datetime'].split(' ')[0]
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                pass
        # Falls nicht gefunden, andere Methoden versuchen
        # Meta-Tags
        meta_date = soup.find('meta', {'name': 'date'})
        if meta_date and meta_date.get('content'):
            date_str = meta_date['content'].split('T')[0]
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                pass
        meta_pub_date = soup.find('meta', {'property': 'article:published_time'})
        if meta_pub_date and meta_pub_date.get('content'):
            date_str = meta_pub_date['content'].split('T')[0]
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                pass
        # Zeit-Tag
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            date_str = time_tag['datetime'].split(' ')[0]
            try:
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                pass
        return None
