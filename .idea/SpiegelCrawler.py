import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from textblob_de import TextBlobDE as TextBlob
import time

# 1. Webcrawler zum Sammeln von Artikeln
class SpiegelCrawler:
    def __init__(self, base_url):
        self.base_url = base_url
        self.article_urls = []

    def get_article_links(self):
        url = f"{self.base_url}"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=re.compile(r'/auto/.*'))
            for link in links:
                full_url = f"https://www.spiegel.de{link['href']}"
                if full_url not in self.article_urls:
                    if any(keyword in full_url.lower() for keyword in ["elektromobilität", "e-auto", "e-autos"]):
                        self.article_urls.append(full_url)
        else:
            print(f"Fehler beim Abrufen der Seite: {response.status_code}")
        time.sleep(1)  # Warten, um die Serverlast zu reduzieren

    def get_articles(self):
        articles = []
        for url in self.article_urls:
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('h2').text.strip() if soup.find('h2') else 'Kein Titel'
                body = " ".join([p.text for p in soup.find_all('p')])
                articles.append({"title": title, "body": body, "url": url})
            else:
                print(f"Fehler beim Abrufen des Artikels: {url}")
            time.sleep(1)  # Warten, um die Serverlast zu reduzieren
        return articles

# 2. Sentimentanalyse der Artikel
class SentimentAnalyzer:
    def __init__(self, articles):
        self.articles = articles

    def analyze_sentiments(self):
        results = []
        for article in self.articles:
            blob = TextBlob(article['body'])
            sentiment_polarity = blob.sentiment.polarity
            sentiment = "positiv" if sentiment_polarity > 0 else ("negativ" if sentiment_polarity < 0 else "neutral")
            results.append({"title": article['title'], "url": article['url'], "sentiment": sentiment, "polarity": sentiment_polarity})
        return results

# 3. Kontextuelle Analyse: Häufigkeit von Schlüsselwörtern und deren Kontext
class ContextAnalyzer:
    def __init__(self, articles, keywords):
        self.articles = articles
        self.keywords = keywords

    def keyword_context(self):
        context_results = []
        for article in self.articles:
            for keyword in self.keywords:
                if keyword in article['body']:
                    sentences = re.split(r'[.!?]', article['body'])
                    keyword_sentences = [sentence for sentence in sentences if keyword in sentence]
                    context_results.append({"title": article['title'], "url": article['url'], "keyword": keyword, "context": keyword_sentences})
        return context_results

# Hauptprogramm
if __name__ == "__main__":
    # Initialisiere Webcrawler
    crawler = SpiegelCrawler(base_url="https://www.spiegel.de/auto/")
    crawler.get_article_links()  # Links von der Mobilitätsseite sammeln
    articles = crawler.get_articles()

    # Sentimentanalyse durchführen
    sentiment_analyzer = SentimentAnalyzer(articles)
    sentiment_results = sentiment_analyzer.analyze_sentiments()
    sentiment_df = pd.DataFrame(sentiment_results)
    print("Sentimentanalyse:")
    print(sentiment_df)

    # Kontextuelle Analyse der Schlüsselwörter
    keywords = ["Umwelt", "Technologie", "Kosten", "Reichweite"]
    context_analyzer = ContextAnalyzer(articles, keywords)
    context_results = context_analyzer.keyword_context()
    context_df = pd.DataFrame(context_results)
    print("\nKontextuelle Analyse der Schlüsselwörter:")
    print(context_df)