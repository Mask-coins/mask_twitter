from __future__ import annotations

import datetime
import math
import os

import pandas as pd
import tweepy
from tweepy.models import User as TweepyUser
from tweepy.errors import TweepyException
from collections import OrderedDict

from src.mask_twitter.file import FileWriter


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
                screen_name=screen_name_list,
                since_id=since_id_list,
                score=score_list
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
        return chosen

    @staticmethod
    def read_csv(file_path):
        u = UserScore([],[],[],[])
        u.df = pd.read_csv(file_path, encoding="utf-8", index_col=0)
        return u

    def to_csv(self, file_path):
        self.df.to_csv(file_path, encoding="utf-8")



class TweetGetter(object):
    def __init__(
            self,
            TWITTER_COUSUMER_KEY,
            TWITTER_COUSUMER_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET,
            json_dir_path,
            user_score_path
    ):
        auth = tweepy.OAuthHandler(
            TWITTER_COUSUMER_KEY,
            TWITTER_COUSUMER_SECRET)
        auth.set_access_token(
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET)
        self._api = tweepy.API(auth, wait_on_rate_limit=True)
        self._json_dir_path = json_dir_path
        self.user_score_path = user_score_path

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


class TweetCollectorSystem(object):
    def __init__(self, dir_path, key_word_list):
        self.tg: TweetGetter|None = None
        self.fw: dict[str,FileWriter] = dict()
        self.dir_path = dir_path
        self.key_word_list = key_word_list

    def collect(self, user_score_path):
        if os.path.isfile(user_score_path):
            user_score = UserScore.read_csv(user_score_path)
            ids = user_score.choose(0.2)
            user_id_list = []
            screen_name_list = []
            since_id_list = []
            score_list = []
            for idx in ids:
                if user_score.df["since_id"][idx] < 0:
                    tweets = self.tg.get_tweets(id_num=idx)
                else:
                    tweets = self.tg.get_tweets_since(id_num=idx, since_id=user_score.df["since_id"][idx])
                count = 0
                for tweet in tweets:
                    dtime = tweet["created_at"]
                    dt = datetime.datetime.strptime(dtime,'%a %b %d %H:%M:%S +0000 %Y')
                    day = datetime.datetime.strftime(dt, '%Y-%m-%d')
                    if day not in self.fw:
                        self.fw[day] = FileWriter(self.dir_path+"/tweets/"+day)
                    self.fw[day].add(tweet)
                    for kw in self.key_word_list:
                        if kw in tweet["text"]:
                            count += 1
                    # https://developer.twitter.com/en/docs/twitter-api/v1/data-dictionary/object-model/tweet
                    if "in_reply_to_user_id" in tweet:
                        user_id_list.append(tweet["in_reply_to_user_id"])
                        screen_name_list.append(tweet["in_reply_to_screen_name"])
                        since_id_list.append(-1)
                        score_list.append(-1)
                    if "retweeted_status" in tweet:
                        user_id_list.append(tweet["retweeted_status"]["user"]["id"])
                        screen_name_list.append(tweet["retweeted_status"]["user"]["screen_name"])
                        since_id_list.append(-1)
                        score_list.append(-1)
                score = 1 - 0.5**count
                user_score.df["score"][idx] = score + 0.5 + user_score.df["score"][idx]
                





