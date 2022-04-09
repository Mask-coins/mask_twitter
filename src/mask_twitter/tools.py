from __future__ import annotations

import math

import pandas as pd
import tweepy
from tweepy.models import User as TweepyUser
from tweepy.errors import TweepyException
from collections import OrderedDict


class UserScore(object):
    def __init__(
            self,
            user_id_list,
            screen_name_list,
            since_id_list,
            score_list
    ):
        self.df = pd.DataFrame(
            OrderedDict(
                screen_name_list=screen_name_list,
                since_id_list=since_id_list,
                score_list=score_list
            ),
            index=pd.Index(user_id_list, name="user_id"),
        )

    def concat(self, other:UserScore):
        self.df = pd.concat([self.df,other.df])

    def sort(self):
        self.df.sort_index(ascending=False, inplace=True)

    def choose(self, epsilon:float, n=300):
        rand_num = math.floor(n*epsilon)
        chosen = set()
        df = self.df.sample(n=rand_num)
        for idx in df.idx:
            chosen.add(idx)
        i = 0
        for idx in self.df.index:
            if i > n:
                break
            if idx in chosen:
                continue
            chosen.add(idx)
            i += 1


class TweetGetter(object):
    def __init__(
            self,
            TWITTER_COUSUMER_KEY,
            TWITTER_COUSUMER_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET,
            json_dir_path,
            db_path):
        auth = tweepy.OAuthHandler(
            TWITTER_COUSUMER_KEY,
            TWITTER_COUSUMER_SECRET)
        auth.set_access_token(
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET)
        self._api = tweepy.API(auth, wait_on_rate_limit=True)
        self._json_dir_path = json_dir_path

    def get_profile(self, id_num: int = None, screen_name: str = None) -> None|TweepyUser:
        try:
            if id_num:
                profile_contents: TweepyUser = self._api.get_user(id=id_num)
            elif screen_name:
                profile_contents: TweepyUser = self._api.get_user(screen_name=screen_name)
            else:
                return None
        except TweepyException as e:
            print("ERROR:",e)
            if "User not found." in str(e):
                return None
            elif "User has been suspended." in str(e):
                return None
            else:
                profile_contents = self._api.get_user(id=id_num)
        return profile_contents

    def get_tweets(self, id_num: int):
        tweets = []
        for tweet in tweepy.Cursor(self._api.user_timeline, id=id_num, cursor=-1).items():
            tweets.append(tweet._json)
        return tweets

    def get_tweets_since(self, id_num: int, since_id: int):
        tweets = []
        for tweet in tweepy.Cursor(self._api.user_timeline, id=id_num, cursor=-1, since_id=since_id).items():
            tweets.append(tweet._json)
        return tweets




class Graph(object):
    def __init__(self, id):
        self._id=id
        # self._tweets_score["date"]["user_id"]["tweet_id"]
        self._tweets_score:dict[int,dict[int,dict[int,float]]] = dict()
        # self._edge["date"]["from_id"]["to_id"]["type"]["tweet_id"]
        self._edge:dict[int,dict[int,dict[int,dict[int,dict[int,float]]]]] = dict()


