import json
import os
import time
from typing import Dict, List
import pandas as pd

from donkeycar.config import Config


FILE = 'database.json'


class PilotDatabase:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.path = os.path.join(cfg.MODELS_PATH, FILE)
        self.entries = self.read()

    def read(self) -> List[Dict]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as read_file:
                    data = json.load(read_file)
                    return data
            except FileNotFoundError as f:
                print(f)
            except Exception as e:
                print(e)
        else:
            return []

    def generate_model_name(self) -> str:
        df = self.to_df()
        last_num = df.number.max()
        this_num = last_num + 1
        date = time.strftime('%y-%m-%d')
        name = 'pilot_' + date + '_' + str(this_num)
        return name

    def to_df(self) -> pd.DataFrame:
        df = pd.DataFrame.from_records(self.entries)
        df.set_index('number', inplace=True)
        return df

    def write(self):
        try:
            with open(self.path, "w") as data_file:
                json.dump(self.entries, data_file)
        except Exception as e:
            print(e)

    def add_entry(self, entry: Dict):
        self.entries.append(entry)
