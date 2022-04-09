from __future__ import annotations

import json
from tweepy.models import Status as TweepyStatus


class FileWriter(object):
    def __init__(self, file_path):
        self._file_path = file_path

    def add(self, obj: dict | list):
        with open(self._file_path, encoding="utf-8", mode='a') as fp:
            fp.write(json.dumps(obj=obj, ensure_ascii=False))
            fp.write("\n")

    def load_tweets_json(self) -> list[dict]:
        with open(self._file_path, encoding="utf-8", mode='r') as fp:
            tweets = []
            text = fp.readline()
            while text:
                tweets.append(json.loads(text))
                text = fp.readline()
            return tweets

    def load_tweepy_status(self, api) -> list[TweepyStatus]:
        with open(self._file_path, encoding="utf-8", mode='r') as fp:
            tweets = []
            text = fp.readline()
            while text:
                tweets.append(TweepyStatus.parse(api, text))
                text = fp.readline()
            return tweets
