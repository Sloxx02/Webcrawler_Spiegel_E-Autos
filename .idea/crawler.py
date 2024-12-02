import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime

class Crawler:
    def __init__(self, base_url, max_articles, max_pages, start_date, end_date, context_words, blacklist, nlp, gui_queue):
        self.base_url = base_url
        self.max_articles = max_articles
        self.max_pages = max_pages
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.context_words = context_words
        self.blacklist = blacklist
        self.nlp = nlp
        self.gui_queue = gui_queue
        self.article_urls = []
        logging.info(f"Konfiguration: max_articles={max_articles}, max_pages={max_pages}, start_date={start_date}, end_date={end_date}")

    def find_articles(self):
        page_number = 1
        while len(self.article_urls) < self.max_articles and page_number <= self.max_pages:
            url = f"{self.base_url}p{page_number}/"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.find_all('article')
                    for article in articles:
                        if len(self.article_urls) >= self.max_articles:
                            break
                        link_tag = article.find('a', href=True)
                        if link_tag:
                            full_url = link_tag['href']
                            if not full_url.startswith('http'):
                                full_url = 'https://www.spiegel.de' + full_url
                            # Entferne die Zeile, die Paywall-Artikel überspringt
                            # Titel des Artikels extrahieren
                            title_tag = article.find('h2') or article.find('h3') or article.find('h1')
                            if title_tag:
                                title = title_tag.get_text(separator=' ', strip=True).lower()
                            else:
                                title = link_tag.get_text(separator=' ', strip=True).lower()
                            # Überprüfen, ob Kontextwörter im Titel enthalten sind
                            if any(keyword in title for keyword in self.context_words) and not any(black_word in title for black_word in self.blacklist):
                                article_date = self.get_article_date(full_url)
                                if article_date is None:
                                    logging.warning(f"Konnte Datum für Artikel {full_url} nicht extrahieren. Artikel wird trotzdem hinzugefügt.")
                                    article_date = self.end_date  # Setze Datum auf Enddatum, um Artikel einzuschließen
                                if article_date < self.start_date:
                                    logging.info("Artikel liegt vor dem Startdatum. Prozess wird abgebrochen.")
                                    self.gui_queue.put({'type': 'status', 'text': 'Crawler abgeschlossen.'})
                                    return
                                if self.start_date <= article_date <= self.end_date:
                                    if full_url not in self.article_urls:
                                        self.article_urls.append(full_url)
                                        logging.info(f"Gefundener Artikel: {full_url}")
                        progress = len(self.article_urls) / self.max_articles * 100
                        self.gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Crawler arbeitet... {progress:.2f}% abgeschlossen"})
                else:
                    logging.error(f"Fehler beim Abrufen der Seite: {response.status_code}")
                page_number += 1
            except requests.exceptions.RequestException as e:
                logging.error(f"Fehler beim Verbinden mit der URL {url}: {e}")
                break
        logging.info("Crawler abgeschlossen.")
        self.gui_queue.put({'type': 'status', 'text': 'Crawler abgeschlossen.'})

    def get_article_date(self, url):
        try:
            article_response = requests.get(url, timeout=10)
            if article_response.status_code == 200:
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                # Suche nach dem <time> Tag mit class='timeformat'
                time_tag = article_soup.find('time', {'class': 'timeformat'})
                if time_tag and time_tag.get('datetime'):
                    date_str = time_tag['datetime'].split(' ')[0]
                    try:
                        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    except ValueError:
                        pass
                # Falls nicht gefunden, andere Methoden versuchen
                # Meta-Tags
                meta_date = article_soup.find('meta', {'name': 'date'})
                if meta_date and meta_date.get('content'):
                    date_str = meta_date['content'].split('T')[0]
                    try:
                        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    except ValueError:
                        pass
                meta_pub_date = article_soup.find('meta', {'property': 'article:published_time'})
                if meta_pub_date and meta_pub_date.get('content'):
                    date_str = meta_pub_date['content'].split('T')[0]
                    try:
                        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    except ValueError:
                        pass
                # Zeit-Tag
                time_tag = article_soup.find('time')
                if time_tag and time_tag.get('datetime'):
                    date_str = time_tag['datetime'].split(' ')[0]
                    try:
                        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    except ValueError:
                        pass
            else:
                logging.error(f"Fehler beim Abrufen des Artikels: {article_response.status_code}")
        except Exception as e:
            logging.error(f"Fehler beim Abrufen des Artikeldatums von {url}: {e}")
        return None  # Datum konnte nicht extrahiert werden
