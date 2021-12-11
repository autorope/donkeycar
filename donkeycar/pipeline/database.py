from datetime import datetime
import json
import os
import time
import shutil
import glob
from typing import Dict, List, Tuple
import pandas as pd
import logging
from donkeycar.config import Config

logger = logging.getLogger(__name__)

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
                    logger.info(f'Found model database {self.path}')
                    return data
            except Exception as e:
                logger.error(f"Could not open database file because: {e}")
                return []
        else:
            logger.warning(f'No model database found at {self.path}')
            return []

    def generate_model_name(self) -> Tuple[str, int]:
        if self.entries:
            df = self.to_df()
            # otherwise this will be a numpy int
            last_num = int(df.index.max())
            this_num = last_num + 1
        else:
            this_num = 0
        date = time.strftime('%y-%m-%d')
        name = f'pilot_{date}_{this_num}.h5'
        return os.path.join(self.cfg.MODELS_PATH, name), this_num

    def to_df(self) -> pd.DataFrame:
        if self.entries:
            df = pd.DataFrame.from_records(self.entries)
            df.set_index('Number', inplace=True)
            return df
        else:
            return pd.DataFrame()

    def write(self):
        try:
            with open(self.path, "w") as data_file:
                json.dump(self.entries, data_file,
                          default=lambda o: '<not serializable>')
                logger.info(f'Writing database file: {self.path}')
        except Exception as e:
            logger.error(f'Failed writing database file: {e}')

    def add_entry(self, entry: Dict):
        self.entries.append(entry)

    def delete_entry(self, pilot_name):
        to_delete_entry = None
        for entry in self.entries:
            if entry['Name'] == pilot_name:
                to_delete_entry = entry
        if to_delete_entry:
            full_path = os.path.join(self.cfg.MODELS_PATH, pilot_name)
            model_versions = glob.glob(f'{full_path}.*')
            logger.info(f'Deleting {",".join(model_versions)}')
            for model_version in model_versions:
                if os.path.isdir(model_version):
                    shutil.rmtree(model_version, ignore_errors=True)
                else:
                    os.remove(model_version)
            self.entries.remove(to_delete_entry)
            self.write()

    def to_df_tubgrouped(self):
        def sorted_string(comma_separated_string):
            """ Return sorted list of comma separated string list"""
            return ','.join(sorted(comma_separated_string.split(',')))

        df_pilots = self.to_df()
        if df_pilots.empty:
            return pd.DataFrame(), pd.DataFrame()
        tubs = df_pilots.Tubs
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

    @staticmethod
    def formatter():
        def time_fmt(t):
            fmt = '%Y-%m-%d %H:%M:%S'
            return datetime.fromtimestamp(t).strftime(fmt)

        def transfer_fmt(model_name):
            return model_name.replace('.h5', '')

        return {'Time': time_fmt, 'Transfer': transfer_fmt}

    def pretty_print(self, group_tubs=False):
        if group_tubs:
            pilot_df, tub_df = self.to_df_tubgrouped()
            tub_text = tub_df.to_string()
        else:
            pilot_df = self.to_df()
            tub_text = ''

        pilot_df.drop(columns=['History', 'Config'], errors='ignore',
                      inplace=True)
        pilot_text = pilot_df.to_string(formatters=self.formatter())
        pilot_names = pilot_df['Name'].tolist() if not pilot_df.empty else []
        return pilot_text, tub_text, pilot_names
