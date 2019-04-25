# -*- coding: utf-8 -*-
"""
Created: 2019-04-09
Author: Robert Butler
Purpose: This is a script for streaming Twitter API data.

TODO: Consider investigating the following Twitter users:
    'AndrewYNg', 'rdpeng', 'CoreyMSchafer',
    'raymondh', 'gvanrossum', 'dabeaz', 'nedbat', 'rOpenSci',  'rdpeng',
    'xieyihui', 'SciPyTip', 'daattali', 'kdnuggets', 'rbloggers',
    'RLangTip', 'R_Programming'
"""

import tweepy
import pandas as pd
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.orm import sessionmaker

import textwrap
import plotly
import plotly.offline as offl
import plotly.graph_objs as go

TWITTER_API_KEY = '5sOPB7UPox3jexWEYZ53C6kEJ'
TWITTER_API_KEY_SECRET = 'G0CwqysE5nR1lFSNxQPKsb38UMLqh4UVxZWRrkZbxtdokNJxTe'
TWITTER_ACCESS_TOKEN = '1115813594048815104-LklqugH11PQK7nlvkPRXhStbVwAHCt'
TWITTER_ACCESS_TOKEN_SECRET = 'DAIPpCYIR9lPgtAtXw8fq4rSp0DmaAFq2mCcyPQFwFzXL'

# Twitter Classes ------------------------------------------------------------

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
        dataframe = pd.DataFrame()
        dataframe['screen_name'] = pd.Series([t.author.screen_name
                                              for t in tweets])
        dataframe['id'] = pd.Series([t.id for t in tweets])
        dataframe['created_at'] = pd.Series([t.created_at for t in tweets])
        dataframe['source'] = pd.Series([t.source for t in tweets])
        dataframe['text'] = pd.Series([t.text for t in tweets])
        dataframe['favorite_count'] = pd.Series([t.favorite_count
                                                 for t in tweets])
        dataframe['retweet_count'] = pd.Series([t.retweet_count
                                                for t in tweets])
        dataframe = dataframe[
            dataframe['text']
            .apply(lambda t:
                   not t.startswith('RT @') and not t.startswith('@'))
        ]
        return dataframe

    @staticmethod
    def make_trend_dataframe(trends):
        '''Returns a pandas data frame with tweet data.'''
        dataframe = pd.DataFrame()
        dataframe['name'] = pd.Series([t['name'] for t in trends])
        dataframe['url'] = pd.Series([t['url'] for t in trends])
        dataframe['tweet_volume'] = pd.Series([t['tweet_volume']
                                               for t in trends])
        return dataframe

# SQLAlchemy Classes ---------------------------------------------------------

class DatabaseLoader:
    '''This proivdes methods for populating the twitter database.'''
    def __init__(self, db_path='sqlite:///:memory:'):
        self.engine = sqlalchemy.create_engine(db_path)
        self.base = declarative_base()
        self.base.metadata.create_all(self.engine)
        self.bound_session = sessionmaker(bind=self.engine)
        self.session = self.bound_session()

        self.client = TwitterClient()
        self.api = self.client.get_twitter_api()

    def refresh_tweets_table(self, users=('AndrewYNg',
                                          'rdpeng',
                                          'CoreyMSchafer')):
        '''Empties and repopulates the 'tweets' table.'''
        self.session.query(Tweets).delete()
        for user in users:
            tweets = self.client.get_user_timeline_tweets(user=user)
            tweets_df = TwitterAnalyzer.make_tweet_dataframe(tweets=tweets)
            mapped_tweets = [
                Tweets(screen_name=row['screen_name'],
                       tweet_id=row['id'],
                       created_at=row['created_at'],
                       source=row['source'],
                       text=row['text'],
                       favorite_count=row['favorite_count'],
                       retweet_count=row['retweet_count'])
                for index, row in tweets_df.iterrows()
            ]
            self.session.add_all(mapped_tweets)
            self.session.commit()

    def refresh_trends_table(self):
        '''Empties and repopulates the 'trends' table.'''
        self.session.query(Trends).delete()
        trends = self.client.get_location_trends(loc_id=1)
        trends_df = TwitterAnalyzer.make_trend_dataframe(trends=trends)
        trends_df.dropna(inplace=True)
        mapped_trends = [
            Trends(name=row['name'],
                   url=row['url'],
                   tweet_volume=row['tweet_volume'])
            for index, row in trends_df.iterrows()
        ]
        self.session.add_all(mapped_trends)
        self.session.commit()

        def get_remaining_api_calls(self):
            return self.client.get_remaining_api_calls()

DB_LOADER = DatabaseLoader(db_path='sqlite:///twitter_data.db')

class Tweets(DB_LOADER.base):
    '''This proves the model for the 'tweets' table.'''
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True)
    screen_name = Column(String)
    tweet_id = Column(Integer)
    created_at = Column(DATETIME)
    source = Column(String)
    text = Column(String)
    favorite_count = Column(Integer)
    retweet_count = Column(Integer)

    def __repr__(self):
        return (f'<Tweet(screen_name={self.screen_name}, '
                f'created_at={self.created_at}, '
                f'text={self.text})>')

class Trends(DB_LOADER.base):
    '''This proves the model for the 'trends' table.'''
    __tablename__ = 'trends'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    tweet_volume = Column(Integer)

    def __repr__(self):
        return (f'<Trend(name={self.name}, '
                f'url={self.url}, '
                f'tweet_volume={self.tweet_volume})>')

if __name__ == '__main__':
    DB_LOADER.refresh_tweets_table()
    DB_LOADER.refresh_trends_table()








# for row in DB_LOADER.session.query(Tweets).all()[:5]:
#     print(row)

# USER = 'AndrewYNg'

# sql_tweets_df = pd.read_sql(sql=f"SELECT * FROM tweets WHERE screen_name = '{USER}';", con=DB_LOADER.engine)

# trace1 = go.Scatter({'x': sql_tweets_df['created_at'], 'y': sql_tweets_df['favorite_count'], 'mode': 'lines', 'name': 'Favorites', 'text': ['\n'.join(textwrap.wrap(t)) for t in sql_tweets_df['text']]})
# #trace2 = go.Scatter({'x': sql_tweets_df['created_at'], 'y': sql_tweets_df['retweet_count'], 'mode': 'lines', 'name': 'Retweets'})
# data = [trace1]
# layout = go.Layout({'title': f'Posts from {USER}'})
# offl.plot({'data': data, 'layout': layout})

# trace1 = go.Bar({'x': sf_trends_df['tweet_volume'], 'y': sf_trends_df['name'], 'orientation': 'h', 'name': 'San Fransisco Trends', 'marker': {'color': '#ff7800', 'line': {'color': '#a54e00', 'width': 2}}})
# data = [trace1]
# layout = go.Layout({'title': 'Currently Trending on Twitter'})
# offl.plot({'data': data, 'layout': layout})




