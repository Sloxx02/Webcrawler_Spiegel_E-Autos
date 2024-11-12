import os
import sys
import spacy
from tkinter import messagebox

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

def initialize_models():
    # spaCy-Modell laden
    try:
        nlp = spacy.load('de_core_news_sm')
    except OSError:
        # Falls das Modell nicht vorhanden ist, herunterladen und laden
        spacy.cli.download('de_core_news_sm')
        nlp = spacy.load('de_core_news_sm')
    return nlp
