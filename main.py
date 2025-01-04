from flask import Flask, render_template, request.render_template, redirect, request 
import numpy as np 
import tweepy 
import pandas as pd 
from textblob import TextBlob 
#from wordcloud import WordCloud
import re 

app = Flask(__name__)

@app.route('/sentiment', methods = ['GET','POST'])
def sentiment():
    userid =  request.form.get('userid')
    hashtag = request.form.get('hashtag')

    if userid == " " and hashtag == " ":
         error = "Please enter valid value"
         return render_template('index.html', error = error)
    
    if not userid == " " and not hashtag == " ":
         error = "Please enter either userid or hashtag"
         return render_template('index.html', error = error)
    


    ###########Insert Twitter API#############
    consumerKey ="I1XCpkNGDeNHJr3JuhKd3zClN"
    consumerSecret ="r7EZXSEuMAYxBAEgK0CPps9RaXftg82Vjh6aZq1PGjuTL0Nr7Y"
    accessToken ="1875259013031718912-tOIl4ihu96jcVsneNaP5NfgJVoCFHx"
    accessTokenSecret ="JfbeH9QSLlivhq7f8jKbAae2zNPZKUxeHMnq2XkaZSneM"

    authenticate = tweepy.OAuthHAndler(consumerKey, consumerSecret)
    authenticate.set_access_token(accessToken, accessTokenSecret)
    api = tweepy.API(authenticate, wait_on_rate_limit=True)#api rate limit(max tweets that can be fetched in a particular time frame )

    def cleanTxt(text):
         text = re.sub(r'@[A-Za-z0-9]+', '', text) #removing @mentions 
         text = re.sub(r'#', '', text) #removing the # symbol
         text = re.sub('RT[\s]+', '', text) # removing the RT 
         text = re.sub(r'https?\/\/\S+', '', text) # removing the link
         return text
    
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
         
# fetching and processing hashtag tweets 
    if userid == "":
         #hashtag coding 
         msgs = []
         msg = []
         for tweet in tweepy.Cursor(api.search, q=hashtag).items(500):
              msg=  [tweet.txt]
              msg=tuple(msg)
              msgs.append(msg)

         df = pd.DataFrame(msgs)
         df['Tweets'] = df[0].apply(cleanTxt)
         df.drop(0, axis=1, inplace=True)
         df['Subjectivity'] = df['Tweets'].apply(getSubjectivity)
         df['Polarity'] = df['Tweets'].apply(getPolarity)
         df['Analysis'] = df['Polarity'].apply(getAnalysis)
    

         positive = df.loc[df['Analysis'].str.contains('Positive')]
         negative = df.loc[df['Analysis'].str.contains('Negative')]
         neutral = df.loc[df['Analysis'].str.contains('Neutral')]

         positive_per = round((positive.shape[0]/df.shape[0])*100, 1)
         negative_per = round((negative.shape[0]/df.shape[0])*100, 1)
         neutral_per = round((neutral.shape[0]/df.shape[0])*100, 1)

         return render_template('sentiment.html', name=hashtag, positive=positive_per, negative=negative_per, neutral=neutral_per)

#Fetches tweets from the specified user's timeline and processes them similarly
    else:
         #user coding 
         username = "@"+userid
         post = api.user_timeline(screen_name=userid, count = 500, lang = "en", tweet_mode="extended")
         twitter = pd.DataFrame([tweet.full_text for tweet in post], columns=['Tweets'])

         twitter['Tweets'] = twitter['Tweets'].apply(cleanTxt)
         twitter['Subjectivity'] = twitter['Tweets'].apply(getSubjectivity)
         twitter['Polarity'] = twitter['Tweets'].apply(getPolarity)
         twitter['Analysis'] = twitter['Polarity'].apply(getAnalysis)

         positive = twitter.loc[twitter['Analysis'].str.contains('Positive')]
         negative = twitter.loc[twitter['Analysis'].str.contains('Negative')]
         neutral = twitter.loc[twitter['Analysis'].str.contains('Neutral')]

         positive_per = round((positive.shape[0]/twitter.shape[0])*100, 1)
         negative_per = round((negative.shape[0]/twitter.shape[0])*100, 1)
         neutral_per = round((neutral.shape[0]/twitter.shape[0])*100, 1)

         return render_template('sentiment.html', name=username,positive=positive_per,negative=negative_per,neutral=neutral_per)
    
@app.route('/')

def home():
     return render_template('index.html')

if __name__=="__main__":
     app.run()