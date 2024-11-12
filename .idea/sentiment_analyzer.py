import logging
import openai
import json
from germansentiment import SentimentModel

class SentimentAnalyzer:
    def __init__(self, gui_queue):
        self.gui_queue = gui_queue
        # German Sentiment Model laden
        self.sentiment_model = SentimentModel(model_name="oliverguhr/german-sentiment-bert")
        # OpenAI API-Schlüssel setzen (Bitte hier Ihren API-Schlüssel einfügen)
        openai.api_key = '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'

    def analyze(self, articles):
        self.gui_queue.put({'type': 'status', 'text': 'Sentimentanalyse wird durchgeführt...'})
        sentiment_results = []
        total_scores_bert = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}
        total_scores_gpt = {'positive': 0.0, 'negative': 0.0, 'neutral': 0.0}

        for article in articles:
            body = article['body']

            # BERT Sentimentanalyse
            sentiment_result_bert = self.sentiment_model.predict_sentiment([body], output_probabilities=True)
            sentiment_class_bert = sentiment_result_bert[0][0]  # Da wir nur einen Text analysieren
            sentiment_scores_bert_list = sentiment_result_bert[1][0]  # Liste von Listen

            # Konvertieren der Liste von Listen in ein Dictionary
            sentiment_scores_bert = dict(sentiment_scores_bert_list)
            sentiment_scores_bert = {k: float(v) for k, v in sentiment_scores_bert.items()}

            # Gesamtwertungen aktualisieren
            for k in total_scores_bert.keys():
                total_scores_bert[k] += sentiment_scores_bert.get(k, 0.0)

            # GPT Sentimentanalyse
            sentiment_class_gpt, sentiment_scores_gpt = self.gpt_sentiment_analysis(body)

            # Gesamtwertungen aktualisieren
            for k in total_scores_gpt.keys():
                total_scores_gpt[k] += sentiment_scores_gpt.get(k, 0.0)

            sentiment_results.append({
                "title": article['title'],
                "url": article['url'],
                "sentiment_bert": sentiment_class_bert,
                "sentiment_scores_bert": sentiment_scores_bert,
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
        overall_sentiment_bert = max(total_scores_bert.items(), key=lambda x: x[1])[0]
        overall_sentiment_gpt = max(total_scores_gpt.items(), key=lambda x: x[1])[0]

        overall_output = (
            f"\nGesamt BERT Scores: {total_scores_bert}\n"
            f"Gesamtsentiment BERT: {overall_sentiment_bert}\n"
            f"Gesamt GPT Scores: {total_scores_gpt}\n"
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
                            "{\"positive\": wert, \"negative\": wert, \"neutral\": wert}"
                        )
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                n=1,
                stop=None,
                temperature=1
            )
            sentiment = response.choices[0].message['content'].strip()
            sentiment_scores_gpt = json.loads(sentiment)
            sentiment_scores_gpt = {k: float(v) for k, v in sentiment_scores_gpt.items()}
            sentiment_class = max(sentiment_scores_gpt.items(), key=lambda x: x[1])[0]
            return sentiment_class, sentiment_scores_gpt
        except Exception as e:
            logging.error(f"Fehler bei der GPT-Sentimentanalyse: {e}")
            return "neutral", {"neutral": 1.0, "positive": 0.0, "negative": 0.0}
