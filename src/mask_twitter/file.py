from __future__ import annotations

import json


class FileWriter(object):
    def __init__(self, file_path):
        self._file_path = file_path

    def add(self, obj:dict|list):
        with open(self._file_path, encoding="utf-8", mode='a') as fp:
            fp.write(json.dumps(obj=obj, ensure_ascii=False))


