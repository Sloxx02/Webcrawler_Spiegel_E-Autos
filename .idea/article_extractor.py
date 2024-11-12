import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import os
import sys

def load_words_from_file(path):
    words = set()
    try:
        with open(path, 'r', encoding='utf-8') as file:
            for line in file:
                word = line.strip().lower()
                if word:
                    words.add(word)
        return words
    except FileNotFoundError:
        messagebox.showerror("Datei nicht gefunden", f"Die Datei {path} wurde nicht gefunden.")
        sys.exit()

class ArticleExtractorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Artikel Extraktor")
        self.root.geometry("800x600")
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TLabel', font=('Arial', 12))
        style.configure('TEntry', font=('Arial', 12))
        style.configure('TButton', font=('Arial', 12))
        style.configure('Header.TLabel', font=('Arial', 16, 'bold'))

        # Queue für Thread-Kommunikation
        self.gui_queue = queue.Queue()

        # Laden der Kontextwörter und Blacklist
        script_dir = os.path.dirname(os.path.abspath(__file__))
        context_words_path = os.path.join(script_dir, 'Kontextwörter.txt')
        blacklist_path = os.path.join(script_dir, 'Blacklist.txt')

        self.context_words = load_words_from_file(context_words_path)
        self.blacklist = load_words_from_file(blacklist_path)

        self.create_widgets()
        self.root.after(100, self.process_queue)
        self.root.mainloop()

    def create_widgets(self):
        mainframe = ttk.Frame(self.root, padding="10 10 10 10")
        mainframe.pack(fill=tk.BOTH, expand=True)
        header_label = ttk.Label(mainframe, text="Artikel Extraktor", style='Header.TLabel')
        header_label.pack(pady=10)

        input_frame = ttk.Frame(mainframe)
        input_frame.pack(pady=10)
        ttk.Label(input_frame, text="Anzahl der Artikel (max. 1000):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.max_articles_entry = ttk.Entry(input_frame)
        self.max_articles_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Maximale Anzahl der Seiten (max. 500):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.max_pages_entry = ttk.Entry(input_frame)
        self.max_pages_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Startdatum (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        self.start_date_entry = ttk.Entry(input_frame)
        self.start_date_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Enddatum (YYYY-MM-DD):").grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
        self.end_date_entry = ttk.Entry(input_frame)
        self.end_date_entry.grid(row=3, column=1, padx=5, pady=5)

        start_button = ttk.Button(mainframe, text="Artikel extrahieren", command=self.start_extraction)
        start_button.pack(pady=10)

        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(mainframe, variable=self.progress_var, maximum=100)
        progress_bar.pack(pady=10, fill=tk.X)

        self.status_label = ttk.Label(mainframe, text="")
        self.status_label.pack()

        self.results_text = scrolledtext.ScrolledText(mainframe, width=80, height=20, font=('Arial', 10))
        self.results_text.pack(pady=10, fill=tk.BOTH, expand=True)
        # Tags für Textformatierung definieren
        self.results_text.tag_configure('title', font=('Arial', 10, 'bold'))
        self.results_text.tag_configure('separator', foreground='grey')

    def start_extraction(self):
        max_articles = self.max_articles_entry.get()
        max_pages = self.max_pages_entry.get()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        try:
            max_articles_int = int(max_articles)
            max_pages_int = int(max_pages)
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Eingabefehler", "Bitte geben Sie gültige Werte ein. Datum im Format YYYY-MM-DD.")
            return
        self.progress_var.set(0)
        self.status_label.config(text="Extraktion startet...")
        self.results_text.delete(1.0, tk.END)

        def extraction_thread():
            articles = self.extract_articles(
                base_url="https://www.spiegel.de/auto/",
                max_articles=max_articles_int,
                max_pages=max_pages_int,
                start_date=start_date,
                end_date=end_date
            )
            for article in articles:
                output = (
                    f"Titel: {article['title']}\n"
                    f"URL: {article['url']}\n"
                    f"Text:\n{article['body']}\n"
                    f"{'-'*50}\n"
                )
                self.gui_queue.put({'type': 'result', 'text': output})
            self.gui_queue.put({'type': 'status', 'text': 'Extraktion abgeschlossen.'})

        threading.Thread(target=extraction_thread).start()

    def extract_articles(self, base_url, max_articles, max_pages, start_date, end_date):
        article_urls = []
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        page_number = 1
        while len(article_urls) < max_articles and page_number <= max_pages:
            url = f"{base_url}p{page_number}/"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.find_all('article')
                    for article in articles:
                        if len(article_urls) >= max_articles:
                            break
                        link_tag = article.find('a', href=True)
                        if link_tag:
                            full_url = link_tag['href']
                            if not full_url.startswith('http'):
                                full_url = 'https://www.spiegel.de' + full_url
                            # Titel des Artikels extrahieren
                            title_tag = article.find('h2') or article.find('h3') or article.find('h1')
                            if title_tag:
                                title = title_tag.get_text(separator=' ', strip=True).lower()
                            else:
                                title = link_tag.get_text(separator=' ', strip=True).lower()
                            # Überprüfen, ob Kontextwörter im Titel enthalten sind
                            if any(keyword in title for keyword in self.context_words) and not any(black_word in title for black_word in self.blacklist):
                                article_date = self.get_article_date(full_url)
                                if article_date:
                                    if article_date < start_date_dt:
                                        self.gui_queue.put({'type': 'status', 'text': 'Extraktion abgeschlossen.'})
                                        return self.fetch_articles(article_urls)
                                    if start_date_dt <= article_date <= end_date_dt:
                                        if full_url not in article_urls:
                                            article_urls.append(full_url)
                                            progress = len(article_urls) / max_articles * 100
                                            self.gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Artikel suchen... {progress:.2f}% abgeschlossen"})
                else:
                    pass
                page_number += 1
            except requests.exceptions.RequestException as e:
                break
        return self.fetch_articles(article_urls)

    def get_article_date(self, url):
        try:
            article_response = requests.get(url, timeout=5)
            if article_response.status_code == 200:
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                date_element = article_soup.find('meta', {'name': 'date'})
                if date_element:
                    date_string = date_element.get('content', '').split('T')[0]
                else:
                    date_element = article_soup.find('time')
                    date_string = date_element.get('datetime', '').split('T')[0] if date_element else ''
                if date_string:
                    return datetime.strptime(date_string.strip(), "%Y-%m-%d")
            else:
                pass
        except Exception as e:
            pass
        return None

    def fetch_articles(self, article_urls):
        articles = []
        for idx, url in enumerate(article_urls, 1):
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
                        continue

                    articles.append({
                        'title': title,
                        'url': url,
                        'body': body
                    })
                    progress = (idx / len(article_urls)) * 100
                    self.gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Artikel abrufen... {progress:.2f}% abgeschlossen"})
                else:
                    pass
            except requests.exceptions.RequestException as e:
                pass
        return articles

    def extract_article_body(self, soup):
        article_body = soup.find('div', {'class': re.compile(r'Article.*Body')})
        if not article_body:
            article_body = soup.find('section', {'class': re.compile(r'Article.*Content')})
        if article_body:
            paragraphs = article_body.find_all('p')
            body_text = " ".join([p.get_text(separator=' ', strip=True) for p in paragraphs if p.get_text(strip=True)])
            return body_text
        else:
            return soup.get_text(separator=' ', strip=True)

    def process_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg['type'] == 'progress':
                    self.progress_var.set(msg['progress'])
                    self.status_label.config(text=msg['text'])
                elif msg['type'] == 'status':
                    self.status_label.config(text=msg['text'])
                elif msg['type'] == 'result':
                    text = msg['text']
                    lines = text.split('\n')
                    for line in lines:
                        if line.startswith("Titel: "):
                            self.results_text.insert(tk.END, line + '\n', 'title')
                        elif line.startswith('-' * 50):
                            self.results_text.insert(tk.END, line + '\n', 'separator')
                        else:
                            self.results_text.insert(tk.END, line + '\n')
                    self.results_text.insert(tk.END, '\n')
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

if __name__ == "__main__":
    ArticleExtractorApp()
