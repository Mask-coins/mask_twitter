from __future__ import annotations

import tweepy
from tweepy.models import User as TweepyUser
from tweepy.errors import TweepyException


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
        self._db_path = db_path

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





