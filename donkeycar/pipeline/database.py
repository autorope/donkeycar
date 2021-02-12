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
        df.set_index('Number', inplace=True)
        return df

    def write(self):
        try:
            with open(self.path, "w") as data_file:
                json.dump(self.entries, data_file)
        except Exception as e:
            print(e)

    def add_entry(self, entry: Dict):
        self.entries.append(entry)

    def to_df_tubgrouped(self):
        df = self.to_df()
        tubs = df.Tubs
        multi_tubs = [tub for tub in tubs if ',' in tub]
        # We might still have 'duplicates in here as 'tub_1,tub2' and 'tub_2,
        # tub_1' would be two different entries. Hence we need to compress these
        multi_tub_set = set([sorted_string(tub) for tub in multi_tubs])
        # Because set is only using unique entries we can now map each list to a
        # group and give it a name
        d = dict(zip(multi_tub_set,
                     ['tub_group_' + str(i) for i in range(len(multi_tubs))]))
        new_tubs = [d[sorted_string(tub)] if tub in multi_tubs
                    else tub for tub in df_pilots['Tubs']]
        df_pilots['Tubs'] = new_tubs
        df_pilots.sort_index(inplace=True)
        # pandas explode normalises multiplicity of arrays as entries in data
        # frame
        df_tubs = pd.DataFrame(
            zip(d.values(), [k.split(',') for k in d.keys()]),
            columns=['TubGroup', 'Tubs']).explode('Tubs')
        return df_pilots, df_tubs