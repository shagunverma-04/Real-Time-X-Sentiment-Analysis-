from flask import Flask, render_template, request, redirect 
import numpy as np 
import tweepy 
import pandas as pd 
from textblob import TextBlob 
#from wordcloud import WordCloud
import re 

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
         return render_template('index.html', error = error)
    
    if not userid == "" and not hashtag == "":
         error = "Please enter either userid or hashtag"
         return render_template('index.html', error = error)
    


    ###########Insert Twitter API#############
    consumerKey ="Swr7ruFRv5HrrBws0XSNu6PnI"
    consumerSecret ="xz2vHh7B5bQQDWTMLtFWuAWfE4BfbuG4I8ECkGH68zOeIZvXqQ"
    accessToken ="1875259013031718912-3y3cx7N2MBmlg2VFzBGLlp7YrVGgaT"
    accessTokenSecret ="Qb7VBe0kPXr9l7fgkrKb9KDOl8bsrvHWA0M2LxHFjtKi2"
    bearer_token = "AAAAAAAAAAAAAAAAAAAAALKexwEAAAAASWdZPgBPZVnPNY0copI%2FzqVdr1g%3DCo0FBOxCyaYle5YSy0804wwDtOdssGclA7O1trTYR3hZfq8QSu"

    authenticate = tweepy.OAuthHandler(consumerKey, consumerSecret)
    authenticate.set_access_token(accessToken, accessTokenSecret)
    api = tweepy.API(authenticate, wait_on_rate_limit=True)#api rate limit(max tweets that can be fetched in a particular time frame )

    client = tweepy.Client(bearer_token="")
    user = client.get_user(username="USERNAME")
    user_id = user.data.id
    # Fetch user tweets
    response = client.get_users_tweets(
    id="USER_ID",
    max_results=100
    )
    
    for tweet in response.data:
         print(tweet.text)

         
# fetching and processing hashtag tweets 
    if hashtag:
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
     app.run(debug=True)
