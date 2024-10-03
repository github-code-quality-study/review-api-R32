import nltk
import csv
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores
        

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """
        with open('data/reviews.csv', 'r') as file:
            reader = csv.DictReader(file)
            reviews

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            
            # Write your code here
            if environ["REQUEST_METHOD"] == "GET":
                # Parse the query string
                query_string = environ.get("QUERY_STRING", "")
                params = parse_qs(query_string)
                location = params.get("location", [None])[0]
                start_date = params.get("start_date", [None])[0]
                end_date = params.get("end_date", [None])[0]

                filtered_reviews = reviews
                if location:
                    allowed_locations = ["Albuquerque, New Mexico","Carlsbad, California"
                                         ,"Chula Vista, California","Colorado Springs, Colorado","Denver, Colorado","El Cajon, California","El Paso, Texas","Escondido, California","Fresno, California","La Mesa, California","Las Vegas, Nevada","Los Angeles, California","Oceanside, California","Phoenix, Arizona","Sacramento, California","Salt Lake City, Utah","Salt Lake City, Utah","San Diego, California","Tucson, Arizona"]
                    if location in allowed_locations:
                        filtered_reviews = [r for r in filtered_reviews if r["Location"] == location]
                    else:
                        filtered_reviews = []
                if start_date:
                    filtered_reviews = [r for r in filtered_reviews if r["Timestamp"] and datetime.strptime(r["Timestamp"], "%Y-%m-%d %H:%M:%S") >= datetime.strptime(start_date, "%Y-%m-%d")]

                if end_date:
                    filtered_reviews = [r for r in filtered_reviews if r["Timestamp"] and datetime.strptime(r["Timestamp"], "%Y-%m-%d %H:%M:%S") <= datetime.strptime(end_date, "%Y-%m-%d")]

                for review in filtered_reviews:
                    if review.get('ReviewBody'):
                        review["sentiment"] = self.analyze_sentiment(review["ReviewBody"])
                    else:
                        review["sentiment"] = {"neg": 0.0, "neu": 0.0, "pos": 0.0, "compound": 0.0}

                filtered_reviews.sort(key=lambda x: x["sentiment"]["compound"], reverse=True)      
                response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8") 

            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]
            
            


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            try:
                content_length = int(environ.get("CONTENT_LENGTH", 0))
                post_data = environ["wsgi.input"].read(content_length).decode('utf-8')
                data = parse_qs(post_data)
                location = data.get("Location", [None])[0]
                review_body = data.get("ReviewBody", [None])[0]

                if not location or not review_body:
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [json.dumps({"error":"Location and ReviewBody are required"}).encode("utf-8")]
                
                allowed_locations = ["Albuquerque, New Mexico","Carlsbad, California"
                                         ,"Chula Vista, California","Colorado Springs, Colorado","Denver, Colorado","El Cajon, California","El Paso, Texas","Escondido, California","Fresno, California","La Mesa, California","Las Vegas, Nevada","Los Angeles, California","Oceanside, California","Phoenix, Arizona","Sacramento, California","Salt Lake City, Utah","Salt Lake City, Utah","San Diego, California","Tucson, Arizona"]
                if location not in allowed_locations:
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [json.dumps({"error":"Invalid location"}).encode("utf-8")]
                
                review_id = str(uuid.uuid4())
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                review ={
                    "ReviewId": review_id,
                    "Location": location,
                    "ReviewBody": review_body,
                    "Timestamp": timestamp,
                    # "sentiment": self.analyze_sentiment(review_body)
                }
                reviews.append(review)

                response_body = json.dumps(review, indent=2).encode("utf-8")
                start_response("201 Created", [("Content-Type", "application/json"), ("Content-Length", str(len(response_body)))])
                return [ response_body ]
            
            except Exception as e:
                start_response("500 Internal Server Error", [("Content-Type", "application/json")])
                return [json.dumps({"error": str(e)}).encode("utf-8")]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()