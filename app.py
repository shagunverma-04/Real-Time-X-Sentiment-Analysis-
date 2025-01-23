from flask import Flask, render_template, request, redirect, flash
import numpy as np 
import tweepy 
import pandas as pd 
from textblob import TextBlob 
import re 
import os
from dotenv import load_dotenv
import time
from datetime import datetime
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')  # Add a secret key for flash messages

# Configuration
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
CACHE_DURATION = 900  # 15 minutes cache
MAX_TWEETS_PER_REQUEST = 5  # Reduced to 5 tweets
CACHE_FILE = 'tweet_cache.json'

class TweetCache:
    def __init__(self):
        self.cache_file = Path(CACHE_FILE)
        self.last_write_time = 0
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        current_time = time.time()
        # Only write to file if at least 5 seconds have passed since last write
        if current_time - self.last_write_time >= 5:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
            self.last_write_time = current_time

    def get(self, key):
        if key in self.cache:
            data = self.cache[key]
            if time.time() - data['timestamp'] < CACHE_DURATION:
                print(f"Cache hit for {key}")
                return data['tweets'], data['timestamp']
        return None, None

    def set(self, key, tweets):
        current_time = time.time()
        self.cache[key] = {
            'tweets': tweets,
            'timestamp': current_time
        }
        self._save_cache()

def cleanTxt(text):
    if not text:
        return ""
    text = re.sub(r'@[A-Za-z0-9]+', '', text)
    text = re.sub(r'#', '', text)
    text = re.sub('RT[\s]+', '', text)
    text = re.sub(r'https?\/\/\S+', '', text)
    return text.strip()

def analyze_sentiment(text):
    blob = TextBlob(str(text))
    return {
        'subjectivity': blob.sentiment.subjectivity,
        'polarity': blob.sentiment.polarity,
        'analysis': 'Positive' if blob.sentiment.polarity > 0 
                   else 'Negative' if blob.sentiment.polarity < 0 
                   else 'Neutral'
    }

class TwitterAPI:
    def __init__(self):
        self.client = tweepy.Client(bearer_token=BEARER_TOKEN)
        self.cache = TweetCache()
        self.last_request_time = 0
        self.request_count = 0

    def _wait_between_requests(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 5:  # Minimum 5 seconds between requests
            time.sleep(5 - time_since_last)
        self.last_request_time = time.time()

    def get_tweets(self, query_type, value):
        cache_key = f"{query_type}_{value}"
        tweets, timestamp = self.cache.get(cache_key)
        
        if tweets is not None:
            time_since_cache = time.time() - timestamp
            remaining_cache_time = CACHE_DURATION - time_since_cache
            if remaining_cache_time > 0:
                return tweets, f"Using cached data (refreshes in {int(remaining_cache_time)} seconds)"

        self._wait_between_requests()

        try:
            if query_type == 'hashtag':
                response = self.client.search_recent_tweets(
                    query=f"#{value} -is:retweet lang:en",
                    max_results=MAX_TWEETS_PER_REQUEST,
                    tweet_fields=["text"]
                )
            else:  # userid
                user = self.client.get_user(username=value)
                if not user.data:
                    raise Exception("User not found")
                response = self.client.get_users_tweets(
                    id=user.data.id,
                    max_results=MAX_TWEETS_PER_REQUEST,
                    tweet_fields=["text"]
                )

            if response.data:
                tweets = [tweet.text for tweet in response.data]
                self.cache.set(cache_key, tweets)
                return tweets, "Fresh data fetched"
            return [], "No tweets found"

        except tweepy.TooManyRequests as e:
            reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
            wait_time = max(reset_time - int(time.time()), 60)
            raise Exception(f"Rate limit reached. Please try again in {wait_time} seconds")
        except Exception as e:
            raise Exception(f"Error fetching tweets: {str(e)}")

@app.route('/sentiment', methods=['GET', 'POST'])
def sentiment():
    # For GET requests, just show the form
    if request.method == 'GET':
        return render_template('index.html')

    try:
        # Get form data
        userid = request.form.get('userid', '').strip()
        hashtag = request.form.get('hashtag', '').strip()

        # Validate input
        if not userid and not hashtag:
            flash("Please enter either a user ID or hashtag")
            return render_template('index.html')
        
        if userid and hashtag:
            flash("Please enter only one: user ID or hashtag")
            return render_template('index.html')

        # Initialize API and fetch tweets
        api = TwitterAPI()
        tweets, status = api.get_tweets(
            'hashtag' if hashtag else 'userid',
            hashtag if hashtag else userid
        )

        # Check if we got any tweets
        if not tweets:
            flash(f"No tweets found. {status}")
            return render_template('index.html')

        # Process tweets
        processed_tweets = []
        for tweet in tweets:
            clean_text = cleanTxt(tweet)
            if clean_text:
                sentiment = analyze_sentiment(clean_text)
                processed_tweets.append({
                    'text': clean_text,
                    **sentiment
                })

        # Check if we have any processed tweets
        if not processed_tweets:
            flash("No valid tweets found after cleaning")
            return render_template('index.html')

        # Calculate statistics
        sentiments = [t['analysis'] for t in processed_tweets]
        total = len(sentiments)
        stats = {
            'positive': round(sentiments.count('Positive') / total * 100, 1),
            'negative': round(sentiments.count('Negative') / total * 100, 1),
            'neutral': round(sentiments.count('Neutral') / total * 100, 1)
        }

        # Return results
        flash(f"Analysis complete. {status}")
        return render_template(
            'sentiment.html',
            positive=stats['positive'],
            negative=stats['negative'],
            neutral=stats['neutral'],
            analyzed_tweets=processed_tweets
        )

    except Exception as e:
        # Log the error (you should set up proper logging)
        print(f"Error in sentiment analysis: {str(e)}")
        flash(f"An error occurred: {str(e)}")
        return render_template('index.html')
    

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)