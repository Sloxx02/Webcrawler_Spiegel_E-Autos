import logging
import openai
import json
from germansentiment import SentimentModel
import spacy
import numpy as np

class SentimentAnalyzer:
    def __init__(self, gui_queue):
        self.gui_queue = gui_queue
        # German Sentiment Model laden
        self.sentiment_model = SentimentModel(model_name="oliverguhr/german-sentiment-bert")
        # OpenAI API-Schlüssel setzen (Bitte hier Ihren API-Schlüssel einfügen)
        openai.api_key = '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'
        # Laden des spaCy-Modells für die Satzaufteilung
        self.nlp = spacy.load('de_core_news_sm')

    def analyze(self, articles):
        self.gui_queue.put({'type': 'status', 'text': 'Sentimentanalyse wird durchgeführt...'})
        sentiment_results = []
        total_scores_bert = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
        total_scores_gpt = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}

        for article in articles:
            body = article['body']

            # Überprüfen, ob der Artikeltext nicht leer ist
            if not body.strip():
                logging.warning(f"Leerer Artikeltext für Artikel: {article['url']}")
                continue

            # Text in Sätze aufteilen
            doc = self.nlp(body)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

            # Sentimentanalyse für jeden Satz mit BERT und Sammeln der Wahrscheinlichkeiten
            sentiments_probs_bert = []
            for sentence in sentences:
                sentiment_result = self.sentiment_model.predict_sentiment([sentence], output_probabilities=True)
                # sentiment_result[1][0] enthält die Liste von (Label, Wahrscheinlichkeit)-Paaren für den Satz
                probs_dict = dict(sentiment_result[1][0])
                # Konvertiere Wahrscheinlichkeiten zu float
                probs_dict = {k: float(v) for k, v in probs_dict.items()}
                sentiments_probs_bert.append(probs_dict)

            # Aggregation der Wahrscheinlichkeiten über die Sätze
            if sentiments_probs_bert:
                # Summiere die Wahrscheinlichkeiten für jedes Sentiment
                summed_probs = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
                for probs in sentiments_probs_bert:
                    for sentiment in summed_probs.keys():
                        summed_probs[sentiment] += probs.get(sentiment, 0.0)
                # Normiere die Summen, sodass die Wahrscheinlichkeiten zwischen 0 und 1 liegen
                total = sum(summed_probs.values())
                if total > 0:
                    normalized_probs = {k: v / total for k, v in summed_probs.items()}
                else:
                    normalized_probs = {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
            else:
                normalized_probs = {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}

            # Bestimme das Sentiment mit der höchsten Wahrscheinlichkeit
            sentiment_class_bert = max(normalized_probs, key=normalized_probs.get)

            # Gesamtwertungen aktualisieren für BERT
            for k in total_scores_bert.keys():
                total_scores_bert[k] += normalized_probs[k]

            # GPT Sentimentanalyse auf den gesamten Artikeltext
            sentiment_class_gpt, sentiment_scores_gpt = self.gpt_sentiment_analysis(body)

            # Gesamtwertungen aktualisieren für GPT
            for k in total_scores_gpt.keys():
                total_scores_gpt[k] += sentiment_scores_gpt.get(k, 0.0)

            sentiment_results.append({
                "title": article['title'],
                "url": article['url'],
                "sentiment_bert": sentiment_class_bert,
                "sentiment_scores_bert": normalized_probs,
                "sentiment_gpt": sentiment_class_gpt,
                "sentiment_scores_gpt": sentiment_scores_gpt
            })

        # Ergebnisse anzeigen
        for result in sentiment_results:
            output = (
                f"Titel: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"BERT Sentiment: {result['sentiment_bert']}\n"
                f"BERT Scores: {result['sentiment_scores_bert']}\n"
                f"GPT Sentiment: {result['sentiment_gpt']}\n"
                f"GPT Scores: {result['sentiment_scores_gpt']}\n"
                f"{'-'*50}\n"
            )
            logging.info(output)
            self.gui_queue.put({'type': 'sentiment', 'text': output})

        # Gesamtsentiment bestimmen
        overall_total_bert = sum(total_scores_bert.values())
        if overall_total_bert > 0:
            overall_probs_bert = {k: v / overall_total_bert for k, v in total_scores_bert.items()}
        else:
            overall_probs_bert = {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        overall_sentiment_bert = max(overall_probs_bert, key=overall_probs_bert.get)

        overall_total_gpt = sum(total_scores_gpt.values())
        if overall_total_gpt > 0:
            overall_probs_gpt = {k: v / overall_total_gpt for k, v in total_scores_gpt.items()}
        else:
            overall_probs_gpt = {'positive': 0.0, 'negative': 0.0, 'neutral': 1.0}
        overall_sentiment_gpt = max(overall_probs_gpt, key=overall_probs_gpt.get)

        overall_output = (
            f"\nGesamt BERT Scores: {overall_probs_bert}\n"
            f"Gesamtsentiment BERT: {overall_sentiment_bert}\n"
            f"Gesamt GPT Scores: {overall_probs_gpt}\n"
            f"Gesamtsentiment GPT: {overall_sentiment_gpt}\n"
        )
        logging.info(overall_output)
        self.gui_queue.put({'type': 'sentiment', 'text': overall_output})
        self.gui_queue.put({'type': 'status', 'text': 'Vorgang abgeschlossen.'})

    def gpt_sentiment_analysis(self, text):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Du bist ein Sentiment-Analyse-Modell. "
                            "Analysiere den folgenden deutschen Text und gib die Wahrscheinlichkeit für 'positive', "
                            "'negative' und 'neutral' im folgenden JSON-Format aus: "
                            "{\"positive\": Wert zwischen 0 und 1, \"negative\": Wert zwischen 0 und 1, \"neutral\": Wert zwischen 0 und 1}"
                        )
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                n=1,
                stop=None,
                temperature=0
            )
            sentiment = response.choices[0].message['content'].strip()
            sentiment_scores_gpt = json.loads(sentiment)
            sentiment_scores_gpt = {k: float(v) for k, v in sentiment_scores_gpt.items()}
            # Bestimme das Sentiment mit der höchsten Wahrscheinlichkeit
            sentiment_class = max(sentiment_scores_gpt, key=sentiment_scores_gpt.get)
            return sentiment_class, sentiment_scores_gpt
        except Exception as e:
            logging.error(f"Fehler bei der GPT-Sentimentanalyse: {e}")
            return "neutral", {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
