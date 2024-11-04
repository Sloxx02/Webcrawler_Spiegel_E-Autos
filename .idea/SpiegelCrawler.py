import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import sys
from datetime import datetime
from collections import Counter
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import os

# Konfiguriere Logging mit Datum und Uhrzeit im Dateinamen
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_erstellt.log")
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')

# Schlüsselwörter für die Artikelsuche - einfach erweiterbar
keywords = [
    "elektromobilität",
    "e-auto",
    "e-autos",
    "tesla",
    "ladesäulen",
    "ladeinfrastruktur",
    "bmw i",
    "audi e",
    "mercedes eq",
    "vw id",
    "renault zoe",
    "nissan leaf"
]

# Listen mit positiven und negativen Ausdrücken - einfach erweiterbar
positive_words = [
    "fortschrittlich",
    "umweltfreundlich",
    "innovativ",
    "positiv",
    "effizient",
    "zukunftsweisend",
    "nachhaltig"
]

negative_words = [
    "teuer",
    "problematisch",
    "unzuverlässig",
    "kritisch",
    "negativ",
    "ineffizient",
    "mangelhaft"
]

# 1. Webcrawler zum Abrufen von Artikeln zu E-Autos
class SpiegelCrawler:
    def __init__(self, base_url, max_articles, max_pages, start_date, end_date):
        self.base_url = base_url
        self.max_articles = max_articles
        self.max_pages = max_pages
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.article_urls = []

    def find_e_auto_articles(self):
        page_number = 1
        start_time = time.time()
        while len(self.article_urls) < self.max_articles and page_number <= self.max_pages:
            url = f"{self.base_url}p{page_number}/"
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a', href=re.compile(r'/auto/.*'))
                    for link in links:
                        if len(self.article_urls) >= self.max_articles:
                            break
                        full_url = f"{link['href']}"
                        # Überprüfen, ob einer der Schlüsselwörter im Linktext vorhanden ist
                        if any(keyword in link.text.lower() for keyword in keywords):
                            # Rufe die Artikelseite auf, um das Datum zu überprüfen
                            article_response = requests.get(full_url, timeout=2)
                            if article_response.status_code == 200:
                                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                                # Suche nach dem Datum im Artikel
                                date_strings = article_soup.find_all(string=re.compile(r'\d{2}\.\d{2}\.\d{4}'))
                                if date_strings:
                                    date_string = date_strings[0]
                                    try:
                                        article_date = datetime.strptime(date_string.strip().split(',')[0], "%d.%m.%Y")
                                        if self.start_date <= article_date <= self.end_date:
                                            self.article_urls.append(full_url)
                                            logging.info(f"Gefundener Artikel: {full_url.split('/auto/')[-1]}")
                                    except ValueError:
                                        continue
                    elapsed_time = time.time() - start_time
                    progress = len(self.article_urls) / self.max_articles * 100
                    sys.stdout.write(f"\rCrawler arbeitet... {progress:.2f}% abgeschlossen, Laufzeit: {elapsed_time:.2f} Sekunden")
                    sys.stdout.flush()
                    if not links:
                        break
                else:
                    print(f"\nFehler beim Abrufen der Seite: {response.status_code}")
                page_number += 1
            except requests.exceptions.RequestException as e:
                print(f"\nFehler beim Verbinden mit der URL {url}: {e}")
                break

        if len(self.article_urls) >= self.max_articles or page_number > self.max_pages:
            print("\nVorgang erfolgreich abgeschlossen.")
            logging.info("Vorgang erfolgreich abgeschlossen.")

    def open_articles(self):
        sentiment_results = []
        total_positive_count = 0
        total_negative_count = 0
        for url in self.article_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title = soup.find('h2').text.strip() if soup.find('h2') else 'Kein Titel'
                    body = " ".join([p.text for p in soup.find_all('p')])
                    positive_count = sum(body.lower().count(word) for word in positive_words)
                    negative_count = sum(body.lower().count(word) for word in negative_words)
                    total_positive_count += positive_count
                    total_negative_count += negative_count
                    sentiment = "positiv" if positive_count > negative_count else ("negativ" if negative_count > positive_count else "neutral")
                    sentiment_results.append({
                        "title": title,
                        "url": url,
                        "positive_count": positive_count,
                        "negative_count": negative_count,
                        "sentiment": sentiment
                    })
                else:
                    print(f"\nFehler beim Abrufen des Artikels: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"\nFehler beim Verbinden mit der URL {url}: {e}")

        # Ergebnisse der Sentimentanalyse ausgeben und ins Log schreiben
        for result in sentiment_results:
            output = f"Titel: {result['title']}\nURL: {result['url']}\nPositiv: {result['positive_count']}, Negativ: {result['negative_count']}, Sentiment: {result['sentiment']}\n"
            print(output)
            logging.info(output)
            results_text.insert(tk.END, output + "\n")

        # Gesamtergebnisse der Sentimentanalyse
        overall_sentiment = "positiv" if total_positive_count > total_negative_count else ("negativ" if total_negative_count > total_positive_count else "neutral")
        overall_output = f"\nGesamtanzahl positive Wörter: {total_positive_count}\nGesamtanzahl negative Wörter: {total_negative_count}\nGesamtsentiment: {overall_sentiment}\n"
        print(overall_output)
        logging.info(overall_output)
        results_text.insert(tk.END, overall_output + "\n")

# Hauptprogramm mit GUI-Frontend
def start_crawler():
    max_articles = max_articles_entry.get()
    max_pages = max_pages_entry.get()
    start_date = start_date_entry.get()
    end_date = end_date_entry.get()

    try:
        max_articles = int(max_articles)
        max_pages = int(max_pages)
        # Prüfen, ob die Eingaben gültig sind
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Eingabefehler", "Bitte geben Sie gültige Werte ein. Datum im Format YYYY-MM-DD.")
        return

    # Initialisiere Webcrawler
    crawler = SpiegelCrawler(base_url="https://www.spiegel.de/auto/", max_articles=max_articles, max_pages=max_pages, start_date=start_date, end_date=end_date)
    crawler.find_e_auto_articles()  # Finde Artikel zu E-Autos auf den angegebenen Seiten
    crawler.open_articles()  # Öffne die gefundenen Artikel

def load_log():
    log_file = filedialog.askopenfilename(filetypes=[("Log-Dateien", "*.log")])
    if log_file:
        with open(log_file, "r") as file:
            results_text.delete(1.0, tk.END)
            results_text.insert(tk.END, file.read())

# GUI erstellen
root = tk.Tk()
root.title("Spiegel E-Auto Sentimentanalyse")

# Labels und Eingabefelder
tk.Label(root, text="Anzahl der Artikel (max. 1000):").grid(row=0, column=0, padx=10, pady=5)
max_articles_entry = tk.Entry(root)
max_articles_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(root, text="Maximale Anzahl der Seiten (max. 500):").grid(row=1, column=0, padx=10, pady=5)
max_pages_entry = tk.Entry(root)
max_pages_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(root, text="Startdatum (YYYY-MM-DD):").grid(row=2, column=0, padx=10, pady=5)
start_date_entry = tk.Entry(root)
start_date_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(root, text="Enddatum (YYYY-MM-DD):").grid(row=3, column=0, padx=10, pady=5)
end_date_entry = tk.Entry(root)
end_date_entry.grid(row=3, column=1, padx=10, pady=5)

# Start-Button
start_button = tk.Button(root, text="Crawler starten", command=start_crawler)
start_button.grid(row=4, column=0, columnspan=2, pady=10)

# Log laden Button
load_log_button = tk.Button(root, text="Log-Datei laden", command=load_log)
load_log_button.grid(row=5, column=0, columnspan=2, pady=5)

# Ergebnisanzeige
results_text = scrolledtext.ScrolledText(root, width=100, height=20)
results_text.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

# GUI starten
root.mainloop()
