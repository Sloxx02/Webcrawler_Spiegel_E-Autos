import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import sys
from datetime import datetime
from collections import Counter
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
from tkinter import ttk
import os
import queue

# Konfiguriere Logging mit Datum und Uhrzeit im Dateinamen
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_erstellt.log")
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')

# Schlüsselwörter für die Artikelsuche - einfach erweiterbar
keywords = [
    "elektroauto",
    "elektroautos",
    "e-auto",
    "e-autos",
    "elektromobilität",
    "e-mobilität",
    "elektrofahrzeug",
    "elektrofahrzeuge",
    "elektroantrieb",
    "e-motor",
    "batterieauto",
    "batterieautos",
    "Autos emissionsfrei",
    "E-Autos emissionsfrei",
    "Autos null-emissionen",
    "elektrisches fahrzeug",
    "e-fahrzeug",
    "e-fahrzeuge",
    "elektromobil",
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
    "komfortable"
    "postive entwicklung"
    "steigende Zahlen"
    "Elektroautos günstiger"
    "E-Autos günstiger"
    "Recyclinganlage eröffnet"
    "Nachfrage wächst"
    "kaum Gefahr"
    "weiter"
]

negative_words = [
    "teuer",
    "problematisch",
    "unzuverlässig",
    "kritisch",
    "negativ",
    "ineffizient",
    "mangelhaft"
    "gefährlich"
    "unmenschlich"
    "Brand"
    "E-Debakel"
    "E-Auto brennt"
    "Totalschäden"

]

# Queue für Thread-Kommunikation
gui_queue = queue.Queue()

# 1. Webcrawler zum Abrufen von Artikeln zu E-Autos
class SpiegelCrawler:
    def __init__(self, base_url, max_articles, max_pages, start_date, end_date):
        self.base_url = base_url
        self.max_articles = max_articles
        self.max_pages = max_pages
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.article_urls = []
        # Logge die Konfiguration
        logging.info(f"Konfiguration: max_articles={max_articles}, max_pages={max_pages}, start_date={start_date}, end_date={end_date}")

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
                                        # Abbruch, wenn das Datum unter dem Startdatum liegt
                                        if article_date < self.start_date:
                                            logging.info("Artikel liegt vor dem Startdatum. Prozess wird abgebrochen.")
                                            gui_queue.put({'type': 'status', 'text': 'Crawler abgeschlossen.'})
                                            return
                                        if self.start_date <= article_date <= self.end_date:
                                            self.article_urls.append(full_url)
                                            logging.info(f"Gefundener Artikel: {full_url.split('/auto/')[-1]}")
                                    except ValueError:
                                        continue
                    elapsed_time = time.time() - start_time
                    progress = len(self.article_urls) / self.max_articles * 100
                    # Aktualisiere Fortschrittsanzeige im GUI
                    gui_queue.put({'type': 'progress', 'progress': progress, 'text': f"Crawler arbeitet... {progress:.2f}% abgeschlossen"})
                    if not links:
                        break
                else:
                    logging.error(f"Fehler beim Abrufen der Seite: {response.status_code}")
                page_number += 1
            except requests.exceptions.RequestException as e:
                logging.error(f"Fehler beim Verbinden mit der URL {url}: {e}")
                break

        if len(self.article_urls) >= self.max_articles or page_number > self.max_pages:
            logging.info("Vorgang erfolgreich abgeschlossen.")
            gui_queue.put({'type': 'progress', 'progress': 100, 'text': 'Crawler abgeschlossen.'})

    def open_articles(self):
        gui_queue.put({'type': 'status', 'text': 'Sentimentanalyse wird durchgeführt...'})
        sentiment_results = []
        total_positive_count = 0
        total_negative_count = 0
        for url in self.article_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    title_tag = soup.find('h2')
                    if title_tag:
                        title = title_tag.get_text(separator=' ', strip=True)
                        title = ' '.join(title.split())
                    else:
                        title = 'Kein Titel'
                    body = " ".join([p.get_text(separator=' ', strip=True) for p in soup.find_all('p')])
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
                    logging.error(f"Fehler beim Abrufen des Artikels: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Fehler beim Verbinden mit der URL {url}: {e}")

        # Ergebnisse der Sentimentanalyse ausgeben und ins Log schreiben
        for result in sentiment_results:
            output = f"Titel: {result['title']}\nURL: {result['url']}\nPositiv: {result['positive_count']}, Negativ: {result['negative_count']}, Sentiment: {result['sentiment']}\n"
            logging.info(output)
            gui_queue.put({'type': 'sentiment', 'text': output})

        # Gesamtergebnisse der Sentimentanalyse
        overall_sentiment = "positiv" if total_positive_count > total_negative_count else ("negativ" if total_negative_count > total_positive_count else "neutral")
        overall_output = f"\nGesamtanzahl positive Wörter: {total_positive_count}\nGesamtanzahl negative Wörter: {total_negative_count}\nGesamtsentiment: {overall_sentiment}\n"
        logging.info(overall_output)
        gui_queue.put({'type': 'sentiment', 'text': overall_output})
        gui_queue.put({'type': 'status', 'text': 'Vorgang abgeschlossen.'})

# Hauptprogramm mit modernisiertem GUI-Frontend
def start_crawler():
    max_articles = max_articles_entry.get()
    max_pages = max_pages_entry.get()
    start_date = start_date_entry.get()
    end_date = end_date_entry.get()

    try:
        max_articles_int = int(max_articles)
        max_pages_int = int(max_pages)
        # Prüfen, ob die Eingaben gültig sind
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Eingabefehler", "Bitte geben Sie gültige Werte ein. Datum im Format YYYY-MM-DD.")
        return

    # Fortschrittsleiste zurücksetzen
    progress_var.set(0)
    status_label.config(text="Crawler startet...")
    results_text.delete(1.0, tk.END)

    # Crawler in separatem Thread starten
    def crawler_thread():
        # Initialisiere Webcrawler
        crawler = SpiegelCrawler(
            base_url="https://www.spiegel.de/auto/",
            max_articles=max_articles_int,
            max_pages=max_pages_int,
            start_date=start_date,
            end_date=end_date
        )
        crawler.find_e_auto_articles()  # Finde Artikel zu E-Autos auf den angegebenen Seiten
        crawler.open_articles()  # Öffne die gefundenen Artikel

    threading.Thread(target=crawler_thread).start()

def process_queue():
    try:
        while True:
            msg = gui_queue.get_nowait()
            if msg['type'] == 'progress':
                progress_var.set(msg['progress'])
                status_label.config(text=msg['text'])
            elif msg['type'] == 'status':
                status_label.config(text=msg['text'])
            elif msg['type'] == 'sentiment':
                results_text.insert(tk.END, msg['text'] + "\n")
    except queue.Empty:
        pass
    root.after(100, process_queue)

def load_log():
    log_file = filedialog.askopenfilename(filetypes=[("Log-Dateien", "*.log")])
    if log_file:
        with open(log_file, "r") as file:
            results_text.delete(1.0, tk.END)
            results_text.insert(tk.END, file.read())

# Modernisiertes GUI erstellen
root = tk.Tk()
root.title("Spiegel E-Auto Sentimentanalyse")
root.geometry("800x600")

# Stil definieren
style = ttk.Style()
style.theme_use('default')
style.configure('TLabel', font=('Arial', 12))
style.configure('TEntry', font=('Arial', 12))
style.configure('TButton', font=('Arial', 12))
style.configure('Header.TLabel', font=('Arial', 16, 'bold'))

# Hauptframe
mainframe = ttk.Frame(root, padding="10 10 10 10")
mainframe.pack(fill=tk.BOTH, expand=True)

# Überschrift
header_label = ttk.Label(mainframe, text="Spiegel E-Auto Sentimentanalyse", style='Header.TLabel')
header_label.pack(pady=10)

# Eingabefelder Frame
input_frame = ttk.Frame(mainframe)
input_frame.pack(pady=10)

# Labels und Eingabefelder
ttk.Label(input_frame, text="Anzahl der Artikel (max. 1000):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
max_articles_entry = ttk.Entry(input_frame)
max_articles_entry.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="Maximale Anzahl der Seiten (max. 500):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
max_pages_entry = ttk.Entry(input_frame)
max_pages_entry.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="Startdatum (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
start_date_entry = ttk.Entry(input_frame)
start_date_entry.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(input_frame, text="Enddatum (YYYY-MM-DD):").grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
end_date_entry = ttk.Entry(input_frame)
end_date_entry.grid(row=3, column=1, padx=5, pady=5)

# Buttons Frame
buttons_frame = ttk.Frame(mainframe)
buttons_frame.pack(pady=10)

# Start-Button
start_button = ttk.Button(buttons_frame, text="Crawler starten", command=start_crawler)
start_button.grid(row=0, column=0, padx=5)

# Log laden Button
load_log_button = ttk.Button(buttons_frame, text="Log-Datei laden", command=load_log)
load_log_button.grid(row=0, column=1, padx=5)

# Fortschrittsanzeige
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(mainframe, variable=progress_var, maximum=100)
progress_bar.pack(pady=10, fill=tk.X)

# Statuslabel
status_label = ttk.Label(mainframe, text="")
status_label.pack()

# Ergebnisanzeige
results_text = scrolledtext.ScrolledText(mainframe, width=80, height=20, font=('Arial', 10))
results_text.pack(pady=10, fill=tk.BOTH, expand=True)

# Starten der Queue-Verarbeitung
root.after(100, process_queue)

# GUI starten
root.mainloop()
