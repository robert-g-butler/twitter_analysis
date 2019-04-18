
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 17:44:29 2019

@author: robbi
"""

import twitter


API_KEY = 'NxYCf93MQhS5vkTjiqp9jREH0'
API_SECRET_KEY = 'iVPBnWUG3PQ2Oq0vwtVZ4ztzDEH2N3axmWElttSEvjSYAXSh7b'
ACCESS_TOKEN = '1115813594048815104-CXOxyK0M08ZwFGWDALtHwlp9m0ngzv'
ACCESS_TOKEN_SECRET = 'PH7Fr3nfy2adDstKZDtlFZJESpxAM66coOiUKmFRpF1tX'


api = twitter.Api(consumer_key=API_KEY,
                  consumer_secret=API_SECRET_KEY,
                  access_token_key=ACCESS_TOKEN,
                  access_token_secret=ACCESS_TOKEN_SECRET)


api.VerifyCredentials()

statuses = api.GetUserTimeline(screen_name='CoreyMSchafer')
len(statuses)
statuses[0]
for s in statuses:
    print(s.text)

type(statuses[0].text)

api.GetSearch(term='trump')[0]

api.GetUserTimeline(screen_name='CoreyMSchafer', count=1)

users = api.GetFriends(screen_name='CoreyMSchafer')
len(users)
print([u for u in users])





