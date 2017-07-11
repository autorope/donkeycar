"""
tags.py

class to manage tags for sessions
"""

import os
import json

class Tags():
    def __init__(self, sessions_path):
        try:
            self.file_path = os.path.join(sessions_path, 'tags')
            with open(self.file_path) as f:
                self.tags = json.load(f)
        except:
            self.tags = {}

    def all_tags(self):
        return self.tags.get('all_tags', [])

    def session_tags(self, session_id):
        return self.tags.get('sessions', {}).get(session_id, [])

    def add_tag_to_session(self, session_id, tag):
        tags = set(self.tags.get('sessions', {}).get(session_id, []))
        tags.add(tag)
        self.tags.get('sessions', {})[session_id] = list(tags)
        with open(self.file_path, 'w') as outfile:
                json.dump(self.tags, outfile, sort_keys=True, indent=4)

    def delete_tag_from_session(self, session_id, tag):
        tags = set(self.tags.get('sessions', {}).get(session_id, []))
        tags.discard(tag)
        self.tags.get('sessions', {})[session_id] = list(tags)
        with open(self.file_path, 'w') as outfile:
                json.dump(self.tags, outfile, sort_keys=True, indent=4)
