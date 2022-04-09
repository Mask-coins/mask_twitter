from __future__ import annotations

import datetime
import math
import os

import pandas as pd
import tweepy
from tweepy.models import User as TweepyUser
from tweepy.errors import TweepyException

from .file import FileWriter


class UserScore(object):
    def __init__(
            self,
            user_id_list,
            screen_name_list,
            since_id_list,
            update_list,
            score_list):
        user_id = pd.Index(user_id_list, dtype="u8", name="user_id")
        screen_name = pd.Series(screen_name_list, dtype=str, index=user_id, name="screen_name")
        since_id = pd.Series(since_id_list, dtype=str, index=user_id, name="since_id")
        update = pd.Series(update_list, dtype=str, index=user_id, name="update")
        score = pd.Series(score_list, dtype=str, index=user_id, name="score")

        self.df = pd.DataFrame([], index=user_id)
        self.df["screen_name"] = screen_name
        self.df["since_id"] = since_id
        self.df["update"] = update
        self.df["score"] = score

    def concat(self, other:UserScore):
        self.df = pd.concat([self.df,other.df])

    def sort(self):
        self.df.sort_values("score",ascending=False, inplace=True)

    def choose(self, epsilon:float, n=300):
        rand_num = math.floor(n*epsilon)
        chosen = set()
        df = self.df.sample(n=min(rand_num,n))
        for idx in df.index:
            chosen.add(idx)
        random_len = len(chosen)
        print("Random", len(chosen))
        i = 0
        for idx in self.df.index:
            if i > n:
                break
            if idx in chosen:
                continue
            chosen.add(idx)
            i += 1
        print("Greedy", len(chosen) - random_len)
        return chosen

    @staticmethod
    def read_csv(file_path):
        u = UserScore([],[],[],[],[])
        u.df = pd.read_csv(
            file_path,
            encoding="utf-8",
            index_col=0,
            dtype={
                "user_id":"u8",
                "screen_name":str,
                "since_id":"u8",
                "update":str,
                "score":float,
            },
            parse_dates=[3]
        )
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
    ):
        auth = tweepy.OAuthHandler(
            TWITTER_COUSUMER_KEY,
            TWITTER_COUSUMER_SECRET)
        auth.set_access_token(
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_TOKEN_SECRET)
        self._api = tweepy.API(auth, wait_on_rate_limit=True)

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
        try:
            for tweet in tweepy.Cursor(self._api.user_timeline, user_id=id_num).items():
                tweets.append(tweet._json)
            return tweets
        except tweepy.errors.Unauthorized as e:
            print(e)
            return tweets

    def get_tweets_since(self, id_num: int, since_id: int):
        tweets = []
        try:
            for tweet in tweepy.Cursor(self._api.user_timeline, user_id=id_num, cursor=-1, since_id=since_id).items():
                tweets.append(tweet._json)
            return tweets
        except tweepy.errors.Unauthorized as e:
            print(e)
            return tweets



class TweetCollectorSystem(object):
    def __init__(self, dir_path, key_word_list):
        self.tg: TweetGetter|None = None
        self.fw: dict[str,FileWriter] = dict()
        self.dir_path = dir_path
        self.key_word_list = key_word_list

    def collect(self, n=300, epsilon=0.1):
        if os.path.isfile(self.dir_path+"/user_score/user_score.csv"):
            user_score = UserScore.read_csv(self.dir_path+"/user_score/user_score.csv")
            user_score.sort()
            print(user_score.df)
            print(user_score.df.iloc[0,:].T)
            print(user_score.df.dtypes)
            ids = user_score.choose(n=n, epsilon=epsilon)
            print("ids",len(ids))
            user_id_list = []
            screen_name_list = []
            since_id_list = []
            update_list = []
            score_list = []
            for idx in ids:
                print("user")
                print(user_score.df.loc[idx,:])
                if user_score.df.loc[idx,"update"] > datetime.datetime.now() - datetime.timedelta(days=1.0):
                    print("SKIP (update)")
                    continue
                if user_score.df["since_id"][idx] == 0:
                    tweets = self.tg.get_tweets(id_num=idx)
                else:
                    tweets = self.tg.get_tweets_since(id_num=idx, since_id=user_score.df["since_id"][idx])
                count = 0
                max_dt = datetime.datetime(2000, 1, 1, 0, 0, 0, 0)
                for tweet in tweets:
                    # pprint.pprint(tweet)
                    dtime = tweet["created_at"]
                    user_score.df.loc[idx,"since_id"] = max(tweet["id"],user_score.df.loc[idx,"since_id"])
                    dt = datetime.datetime.strptime(dtime,'%a %b %d %H:%M:%S +0000 %Y')
                    max_dt = max(max_dt, dt)
                    day = datetime.datetime.strftime(dt, '%Y-%m-%d')
                    if day not in self.fw:
                        self.fw[day] = FileWriter(self.dir_path+"/tweets/"+day+".jsonl")
                    self.fw[day].add(tweet)
                    for kw in self.key_word_list:
                        if kw in tweet["text"]:
                            count += 1
                    # https://developer.twitter.com/en/docs/twitter-api/v1/data-dictionary/object-model/tweet
                    if "in_reply_to_user_id" in tweet and tweet["in_reply_to_user_id"]:
                        if tweet["in_reply_to_user_id"] not in user_score.df.index:
                            if tweet["in_reply_to_user_id"] not in user_id_list:
                                #print(type(tweet["in_reply_to_user_id"] ),tweet["in_reply_to_user_id"])
                                user_id_list.append(tweet["in_reply_to_user_id"])
                                screen_name_list.append(tweet["in_reply_to_screen_name"])
                                since_id_list.append(0)
                                update_list.append(datetime.datetime(2000, 1, 1, 0, 0, 0, 0))
                                score_list.append(-1)
                    if "retweeted_status" in tweet and tweet["retweeted_status"]:
                        if tweet["retweeted_status"]["user"]["id"] not in user_score.df.index:
                            if tweet["retweeted_status"]["user"]["id"] not in user_id_list:
                                #print(type(tweet["retweeted_status"]["user"]["id"]),tweet["retweeted_status"]["user"]["id"])
                                user_id_list.append(tweet["retweeted_status"]["user"]["id"])
                                screen_name_list.append(tweet["retweeted_status"]["user"]["screen_name"])
                                since_id_list.append(0)
                                update_list.append(datetime.datetime(2000, 1, 1, 0, 0, 0, 0))
                                score_list.append(-1)
                score = 1 - 0.9**count
                user_score.df.loc[idx, "score"] = score + 0.5 * user_score.df.loc[idx, "score"]
                print("id",idx,"count",count,"score",score,"new_score",user_score.df["score"][idx])
                if len(tweets)==0:
                    user_score.df.loc[idx, "update"] = datetime.datetime.now()
                else:
                    user_score.df.loc[idx, "update"] = max_dt

            new_user_score = UserScore(
                user_id_list=user_id_list,
                screen_name_list=screen_name_list,
                since_id_list=since_id_list,
                update_list=update_list,
                score_list=score_list
            )
            user_score.concat(new_user_score)
            user_score.to_csv(self.dir_path+"/user_score/user_score.csv")
            dt = datetime.datetime.now()
            dtstr = datetime.datetime.strftime(dt, '%Y-%m-%d=%H-%M-%S')
            user_score.to_csv(self.dir_path+"/user_score/user_score_"+dtstr+".csv")





