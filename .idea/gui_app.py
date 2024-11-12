import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import queue
from datetime import datetime
import logging
import os

from crawler import Crawler
from article_fetcher import ArticleFetcher
from sentiment_analyzer import SentimentAnalyzer
from utils import load_words_from_file, initialize_models

class GUIApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Spiegel E-Auto Sentimentanalyse")
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

        # Initialisiere Modelle
        self.nlp = initialize_models()

        self.create_widgets()
        self.root.after(100, self.process_queue)
        self.root.mainloop()

    def create_widgets(self):
        mainframe = ttk.Frame(self.root, padding="10 10 10 10")
        mainframe.pack(fill=tk.BOTH, expand=True)
        header_label = ttk.Label(mainframe, text="Spiegel E-Auto Sentimentanalyse", style='Header.TLabel')
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

        buttons_frame = ttk.Frame(mainframe)
        buttons_frame.pack(pady=10)
        start_button = ttk.Button(buttons_frame, text="Crawler starten", command=self.start_crawler)
        start_button.grid(row=0, column=0, padx=5)

        load_log_button = ttk.Button(buttons_frame, text="Log-Datei laden", command=self.load_log)
        load_log_button.grid(row=0, column=1, padx=5)

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

    def start_crawler(self):
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
        self.status_label.config(text="Crawler startet...")
        self.results_text.delete(1.0, tk.END)

        def crawler_thread():
            crawler = Crawler(
                base_url="https://www.spiegel.de/auto/",
                max_articles=max_articles_int,
                max_pages=max_pages_int,
                start_date=start_date,
                end_date=end_date,
                context_words=self.context_words,
                blacklist=self.blacklist,
                nlp=self.nlp,
                gui_queue=self.gui_queue
            )
            crawler.find_articles()
            fetcher = ArticleFetcher(crawler.article_urls, self.gui_queue)
            articles = fetcher.fetch_articles()
            analyzer = SentimentAnalyzer(self.gui_queue)
            analyzer.analyze(articles)
        threading.Thread(target=crawler_thread).start()

    def process_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg['type'] == 'progress':
                    self.progress_var.set(msg['progress'])
                    self.status_label.config(text=msg['text'])
                elif msg['type'] == 'status':
                    self.status_label.config(text=msg['text'])
                elif msg['type'] == 'sentiment':
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

    def load_log(self):
        log_file = filedialog.askopenfilename(filetypes=[("Log-Dateien", "*.log")])
        if log_file:
            with open(log_file, "r", encoding='utf-8') as file:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, file.read())
