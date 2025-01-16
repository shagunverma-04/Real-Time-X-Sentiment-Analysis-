from flask import Flask, render_template, request, redirect 
import numpy as np 
import tweepy 
import pandas as pd 
from textblob import TextBlob 
#from wordcloud import WordCloud
import re 
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


#function to clean tweet text
def cleanTxt(text):
         text = re.sub(r'@[A-Za-z0-9]+', '', text) #removing @mentions 
         text = re.sub(r'#', '', text) #removing the # symbol
         text = re.sub('RT[\s]+', '', text) # removing the RT 
         text = re.sub(r'https?\/\/\S+', '', text) # removing the link
         return text
    
#function to calculate sentiment 
def getSubjectivity(text):
         return TextBlob(text).sentiment.subjectivity
    
def getPolarity(text):
         return TextBlob(text).sentiment.polarity 
    
def getAnalysis(score):
         if score > 0:
              return 'Positive'
         elif score < 0:
              return 'Negative'
         else:
              return 'Neutral'

@app.route('/sentiment', methods = ['GET','POST'])
def sentiment():
    userid =  request.form.get('userid')
    hashtag = request.form.get('hashtag')

    if userid == "" and hashtag == "":
         error = "Please enter valid value"
         return render_template('index.html', error = "please enter valid value")
    
    if not userid == "" and not hashtag == "":
         error = "Please enter either userid or hashtag"
         return render_template('index.html', error = "please enter valid value")
    

#twitter api authentication 
    client = tweepy.Client(bearer_token=os.getenv('BEARER_TOKEN'),
                           consumerKey = os.getenv("CONSUMER_KEY"),
                           consumerSecret = os.getenv("CONSUMER_SECRET"),
                           accessToken = os.getenv("ACCESS_TOKEN"),
                           accessTokenSecret = os.getenv("ACCESS_TOKEN_SECRET"))
   
#fetch tweets 
    if hashtag:
       query=f"#{hashtag} -is:retweet lang:en"
       response=client.search_recent_tweets(query=query, max_results=100, tweet_fields=["text"])
       tweets=[cleanTxt(tweet.text)for tweet in response.data]


    elif userid:
       user=client.get_user(username=userid)
       user_id = user.data.id
       response=client.get_users_tweets(id=user_id, max_results=100, tweet_fields=["text"])
       tweets=[cleanTxt(tweet.text)for tweet in response.data]

#analyze sentiment
    df=pd.DataFrame(tweets, columns=['Tweets'])
    df['Subjectivity'] = df['Tweets'].apply(getSubjectivity)
    df['Polarity']=df['Tweets'].apply(getPolarity)
    df['Analysis']=df['Polarity'].apply(getAnalysis)


    positive=df[df['Analysis']== 'Positive']
    negative=df[df['Analysis']== 'Negative']
    neutral=df[df['Analysis']== 'Neutral']

    positive_per= round((positive.shape[0] / df.shape[0])*100, 1)
    negative_per= round((negative.shape[0] / df.shape[0])*100, 1)
    neutral_per= round((neutral.shape[0] / df.shape[0])*100,1)


    return render_template(
     'sentiment.html',
     positive=positive_per,
     negative=negative_per,
     neutral=neutral_per
     )

@app.route('/')

def home():
     return render_template('index.html')

if __name__=="__main__":
     app.run(debug=True)
