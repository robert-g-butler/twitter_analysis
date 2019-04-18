# -*- coding: utf-8 -*-
"""
Created: 2019-04-09
Author: Robert Butler
Purpose: This is a script for streaming Twitter API data.
"""

import textwrap
import tweepy
import pandas as pd
import plotly
import plotly.offline as offl
import plotly.graph_objs as go


TWITTER_API_KEY = '5sOPB7UPox3jexWEYZ53C6kEJ'
TWITTER_API_KEY_SECRET = 'G0CwqysE5nR1lFSNxQPKsb38UMLqh4UVxZWRrkZbxtdokNJxTe'
TWITTER_ACCESS_TOKEN = '1115813594048815104-LklqugH11PQK7nlvkPRXhStbVwAHCt'
TWITTER_ACCESS_TOKEN_SECRET = 'DAIPpCYIR9lPgtAtXw8fq4rSp0DmaAFq2mCcyPQFwFzXL'

class TwitterAuthenticator:
    '''
    This handles authentication when connecting to the Twitter API through
    Tweepy.
    '''
    def authenticate_twitter_conn(self):
        '''Authenticates the Twitter connection.'''
        auth = tweepy.OAuthHandler(consumer_key=TWITTER_API_KEY,
                                   consumer_secret=TWITTER_API_KEY_SECRET)
        auth.set_access_token(key=TWITTER_ACCESS_TOKEN,
                              secret=TWITTER_ACCESS_TOKEN_SECRET)
        return auth

class TwitterListener(tweepy.StreamListener):
    '''
    This is a standard listener class that inherits from Tweepy's
    StreamListener class.
    '''
    def __init__(self, output_filename):
        self.output_filename = output_filename
    def on_data(self, data):
        '''Handles data storage for Twitter Streamer.'''
        try:
            print(data)
            with open(self.output_filename, 'a') as out_file:
                out_file.write(data)
        except Exception as exc:
            print(f'Error on data: {exc}')
        return True

    def on_error(self, status):
        '''Halts connection if Twitter rate limits it.'''
        if status == 420:
            return False
        print(status)

class TwitterClient:
    '''This provides methods for accessing tweets and user data.'''
    def __init__(self):
        self.twitter_authenticator = TwitterAuthenticator()
        self.auth = self.twitter_authenticator.authenticate_twitter_conn()
        self.api = tweepy.API(auth_handler=self.auth)
    def get_twitter_api(self):
        '''Returns the connected Twitter API.'''
        return self.api
    def get_remaining_api_calls(self):
        '''Returns the number of API calls left available for the hour.'''
        limit_status = self.api.rate_limit_status()
        rec = limit_status['resources']
        app = rec['application']
        app_rls = app['/application/rate_limit_status']
        remaining = app_rls['remaining']
        return remaining
    def get_location_trends(self, loc_id=2487956):
        '''Returns the top 10 trends in an area.'''
        loc_trend_data = self.api.trends_place(id=loc_id)
        loc_trends = loc_trend_data[0]['trends']
        return loc_trends
    def get_user_timeline_tweets(self, user=None, limit=0):
        '''Returns a list of the user's most recently posted tweets.'''
        cursor = tweepy.Cursor(method=self.api.user_timeline,
                               id=user)
        tweets = cursor.items(limit=limit)
        return [t for t in tweets]
    def get_user_friends(self, user=None, limit=0):
        '''Returns a list of the user's friends.'''
        cursor = tweepy.Cursor(method=self.api.friends,
                               id=user)
        friends = cursor.items(limit=limit)
        return [f for f in friends]
    def get_home_timeline_tweets(self, limit=0):
        '''Returns a list of tweets on my home timeline.'''
        cursor = tweepy.Cursor(method=self.api.home_timeline)
        tweets = cursor.items(limit=limit)
        return [t for t in tweets]

class TwitterStreamer:
    '''This provides methods for streaming and processing live Tweets.'''
    def __init__(self):
        self.twitter_authenticator = TwitterAuthenticator()
        self.auth = self.twitter_authenticator.authenticate_twitter_conn()
    def stream_tweets(self, output_filename, filter_keywords):
        '''This handles connection to the Twitter API.'''
        listener = TwitterListener(output_filename)
        stream = tweepy.Stream(auth=self.auth, listener=listener)
        stream.filter(track=filter_keywords)

class TwitterAnalyzer:
    '''This provides methods for analyzing Twitter data.'''
    @staticmethod
    def make_tweet_dataframe(tweets):
        '''Returns a pandas data frame with tweet data.'''
        df = pd.DataFrame()
        df['screen_name'] = pd.Series([t.author.screen_name for t in tweets])
        df['id'] = pd.Series([t.id for t in tweets])
        df['created_at'] = pd.Series([t.created_at for t in tweets])
        df['source'] = pd.Series([t.source for t in tweets])
        df['text'] = pd.Series([t.text for t in tweets])
        df['favorite_count'] = pd.Series([t.favorite_count for t in tweets])
        df['retweet_count'] = pd.Series([t.retweet_count for t in tweets])
        return df
    @staticmethod
    def make_trend_dataframe(trends):
        '''Returns a pandas data frame with tweet data.'''
        df = pd.DataFrame()
        df['name'] = pd.Series([t['name'] for t in trends])
        df['url'] = pd.Series([t['url'] for t in trends])
        df['tweet_volume'] = pd.Series([t['tweet_volume'] for t in trends])
        return df


# if __name__ == '__main__':
#     client = TwitterClient()
#     api = client.get_twitter_api()
#     print(api.user_timeline(screen_name='CoreyMSchafer', count=5))

USER = 'CoreyMSchafer'

client = TwitterClient()
api = client.get_twitter_api()
client.get_remaining_api_calls()
tweets = client.get_user_timeline_tweets(user=USER)
tweets_df = TwitterAnalyzer.make_tweet_dataframe(tweets=tweets)
tweets_df = tweets_df[tweets_df['text']
                      .apply(lambda t: not t.startswith('RT @'))]
tweets_df.head()

trace1 = go.Scatter({'x': tweets_df['created_at'], 'y': tweets_df['favorite_count'], 'mode': 'lines', 'name': 'Favorites', 'text': ['\n'.join(textwrap.wrap(t)) for t in tweets_df['text']]})
trace2 = go.Scatter({'x': tweets_df['created_at'], 'y': tweets_df['retweet_count'], 'mode': 'lines', 'name': 'Retweets'})
data = [trace1, trace2]
layout = go.Layout({'title': f'Posts from {USER}'})
offl.plot({'data': data, 'layout': layout})

sf_trends = client.get_location_trends()
sf_trends_df = TwitterAnalyzer.make_trend_dataframe(trends=sf_trends)
sf_trends_df.dropna(inplace=True)
sf_trends_df.head()

trace1 = go.Bar({'x': sf_trends_df['tweet_volume'], 'y': sf_trends_df['name'], 'orientation': 'h', 'name': 'San Fransisco Trends', 'marker': {'color': '#ff7800', 'line': {'color': '#a54e00', 'width': 2}}})
data = [trace1]
layout = go.Layout({'title': 'Currently Trending on Twitter'})
offl.plot({'data': data, 'layout': layout})




