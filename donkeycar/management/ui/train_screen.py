import datetime
import os
from threading import Thread
import json

import pandas as pd
from kivy import Logger
from kivy.clock import Clock
from kivy.properties import ObjectProperty, NumericProperty, ListProperty, \
    StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy_garden.matplotlib import FigureCanvasKivyAgg
import matplotlib as mpl
import matplotlib.pyplot as plt

from donkeycar.config import Config
from donkeycar.management.ui.common import FileChooserBase, get_app_screen, \
    AppScreen, status
from donkeycar.management.ui.rc_file_handler import rc_handler
from donkeycar.pipeline.database import PilotDatabase
from donkeycar.pipeline.training import train


mpl.rcParams.update({'font.size': 8})
plt.style.use('dark_background')
fig1, ax1 = plt.subplots()
plt.tight_layout(pad=1.5)


class ConfigParamSetter(BoxLayout):
    screen = ObjectProperty()
    config = ObjectProperty(force_dispatch=True, allownone=True)

    def get_keys(self):
        if self.config:
            return [str(k) for k in self.config.__dict__.keys()]
        else:
            return []

    def on_config(self, obj=None, config=None):
        if self.ids:
            self.ids.cfg_spinner.values = self.get_keys()

    def set_config_attribute(self, input):
        try:
            val = json.loads(input)
        except ValueError:
            val = input
        att = self.ids.cfg_spinner.text
        setattr(self.config, att, val)
        msg = f'Setting {att} to {val} of type {type(val).__name__}'
        if val in ('True', 'False', 'TRUE', 'FALSE'):
            msg += f' - ATTENTION: {val} is not a Boolean but a String!'
        status(msg)
        if get_app_screen('train').ids.save_cfg.state == 'down':
            car_path = get_app_screen('tub').ids.config_manager.file_path
            my_cfg_path = os.path.join(car_path, 'myconfig.py')
            my_cfg = Config()
            my_cfg.from_pyfile(my_cfg_path)
            my_cfg.from_dict({att: val})
            my_cfg.to_pyfile(my_cfg_path)

    @staticmethod
    def update_rc(att):
        cfg_params = rc_handler.data.get('config_params')
        if cfg_params is None:
            rc_handler.data['config_params'] = [att]
        elif att not in cfg_params:
            cfg_params.append(att)


class ConfigParamPanel(GridLayout):

    def row_count(self):
        rows = int(len(self.children) // self.cols) \
            + 0 if len(self.children) % self.cols == 0 else 1
        return rows

    def add(self):
        train_screen = get_app_screen('train')
        cfg_setter = ConfigParamSetter(screen=train_screen,
                                       config=train_screen.config)
        # We need simulate a config change so the keys get populated
        cfg_setter.on_config()
        self.add_widget(cfg_setter)
        return cfg_setter

    def remove_widget(self, cfg_setter, *args, **kwargs):
        att = cfg_setter.ids.cfg_spinner.text
        cfg_params = rc_handler.data.get('config_params', [])
        if att in cfg_params:
            cfg_params.remove(att)
        super().remove_widget(cfg_setter)


class BackgroundLabel(Label):
    pass


class MenuCheckbox(BoxLayout):
    menu = ObjectProperty()
    text = StringProperty()
    i = NumericProperty()


class CheckBoxRow(BoxLayout):
    selected = ListProperty()
    screen = ObjectProperty()

    def build_widgets(self, labels):
        self.clear_widgets()
        self.selected.clear()
        for i, label in enumerate(labels):
            but = MenuCheckbox(i=i, text=label, menu=self)
            self.add_widget(but)
        self.selected = list(labels)


class TransferSelector(BoxLayout, FileChooserBase):
    """ Class to select transfer model"""
    filters = ['*.h5', '*.savedmodel']


class ConfigViewerPopup(Popup):
    """ Popup to view the config that was saved in the model database as part
        of the training."""

    config = ObjectProperty()

    def _config_to_dict(self):
        # In old-style database format, the config was saved as list of (key,
        # value) pairs. That string could not be de-jsonised and then
        # self.config is a string. In new format is already a dict.
        if isinstance(self.config, dict):
            return self.config
        cfg_list = []
        try:
            s = self.config.replace("'", '"')
            s = s.replace("(", '[').replace(")", "]")
            s = s.replace("False", 'false').replace("True", "true")
            s = s.replace("None", "null")
            cfg_list = json.loads(s)
        except Exception as e:
            Logger.error(f'Failed json read of config: {e}')
        assert isinstance(cfg_list, list), "De-jsonised config should be list"
        return dict(cfg_list)

    def fill_grid(self):
        d = self._config_to_dict()
        for kv in d.items():
            for x in kv:
                label = BackgroundLabel(text=str(x), font_size='13sp')
                self.ids.pilot_cfg_viewer_grid.add_widget(label)


class HistoryViewerPopup(Popup):
    df = ObjectProperty(force_dispatch=True, allownone=True)


class HistoryPlot(FigureCanvasKivyAgg):
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(fig1, **kwargs)

    def on_df(self, e=None, z=None):
        ax1.clear()
        if self.df is None or self.df.empty:
            return
        # only look at loss graphs but not accuracy
        drop = [c for c in self.df.columns if 'loss' not in c]
        loss_df = self.df.drop(columns=drop)
        n = len(loss_df.columns)
        # arrange subplots
        non_val_cols = [c for c in loss_df.columns if c[:4] != 'val_']
        if len(non_val_cols) != n / 2:
            Logger.Error(f"Issue with history data, validation data history "
                         f"is not half of the loss data")
            return
        subplots = [(nv, f'val_{nv}') for nv in non_val_cols]
        loss_df.plot(ax=ax1, linewidth=1.0, subplots=subplots)
        self.draw()


class TrainScreen(AppScreen):
    """ Class showing the training screen. """
    config = ObjectProperty(force_dispatch=True, allownone=True)
    database = ObjectProperty()
    dataframe = ObjectProperty(force_dispatch=True)
    pilot_df = ObjectProperty(force_dispatch=True)
    tub_df = ObjectProperty(force_dispatch=True)
    train_checker = False

    def train_call(self, *args):
        tub_path = get_app_screen('tub').ids.tub_loader.tub.base_path
        transfer = self.ids.transfer_spinner.text
        model_type = self.ids.train_spinner.text
        h5 = os.path.join(self.config.MODELS_PATH, transfer + '.h5')
        sm = os.path.join(self.config.MODELS_PATH, transfer + '.savedmodel')

        if transfer == 'Choose transfer model':
            transfer_model = None
        elif os.path.exists(sm):
            transfer_model = str(sm)
        elif os.path.exists(h5):
            transfer_model = str(h5)
        else:
            transfer_model = None
            status(f'Could find neither {sm} nor {h5} - training without '
                   f'transfer')
        try:
            history = train(self.config, tub_paths=tub_path,
                            model_type=model_type,
                            transfer=transfer_model,
                            comment=self.ids.comment.text)
        except Exception as e:
            Logger.error(e)
            status(f'Training failed see console')

    def train(self):
        self.config.SHOW_PLOT = False
        t = Thread(target=self.train_call)
        status('Training started.')

        def func(dt):
            t.start()

        def check_training_done(dt):
            if t.is_alive():
                return
            self.train_checker.cancel()
            self.ids.comment.text = 'Comment'
            self.ids.transfer_spinner.text = 'Choose transfer model'
            self.ids.train_button.state = 'normal'
            self.ids.train_button.disabled = False
            self.reload_database()
            status('Training completed.')

        # schedules the call after the current frame
        Clock.schedule_once(func, 0)
        # checks if training finished and updates the window if
        self.train_checker = Clock.schedule_interval(check_training_done, 0.5)

    def on_config(self, obj, config):
        if self.config and self.ids:
            self.reload_database()

    def reload_database(self):
        if self.config:
            self.database = PilotDatabase(self.config)

    def on_database(self, obj=None, database=None):
        df = self.database.to_df()
        df.drop(columns=['History', 'Config'], errors='ignore', inplace=True)
        self.dataframe = df

    def on_dataframe(self, obj, dataframe):
        self.plot_dataframe(dataframe)
        if self.dataframe.empty:
            return
        pilot_names = self.dataframe['Name'].values.tolist()
        self.ids.transfer_spinner.values \
            = ['Choose transfer model'] + pilot_names
        self.ids.select_spinner.values = pilot_names
        self.ids.column_chooser.build_widgets(dataframe)

    def plot_dataframe(self, df, selected_cols=None):
        grid = self.ids.scroll_pilots
        grid.clear_widgets()
        # only set column chooser labels on initialisation when selected_cols
        # is not passed in. otherwise project df to selected columns
        df1 = df[selected_cols] if selected_cols is not None else df
        num_cols = len(df1.columns)
        grid.cols = num_cols

        for i, col in enumerate(df1.columns):
            lab = BackgroundLabel(text=f"[b]{col}[/b]", markup=True)
            lab.size = lab.texture_size
            grid.add_widget(lab)
            # if col in ('Pilot', 'Comment'):
            #     grid.cols_minimum |= {i: 100}

        for idx in df1.index:
            for col in df1.columns:
                cell = df1[col][idx]
                if col == 'Time':
                    cell = datetime.datetime.fromtimestamp(cell)
                    cell = cell.strftime("%Y-%m-%d %H:%M:%S")
                cell = str(cell)
                lab = BackgroundLabel(text=cell)
                lab.size = lab.texture_size
                grid.add_widget(lab)

    def show_config(self, obj=None):
        pilot = self.ids.select_spinner.text
        cfg = self.database.get_entry(pilot).get('Config')
        if not cfg:
            Logger.Error(f'Config for pilot {pilot} not found in database')
            return
        popup = ConfigViewerPopup(config=cfg, title=f'Config for {pilot}')
        popup.fill_grid()
        popup.open()

    def show_history(self, obj=None):
        pilot = self.ids.select_spinner.text
        history = self.database.get_entry(pilot).get('History')
        if not history:
            Logger.Error(f'History for pilot {pilot} not found in database')
            return
        df = pd.DataFrame(history)
        popup = HistoryViewerPopup(df=df, title=f'Training history for {pilot}')
        popup.open()

    def initialise(self):
        cfg_params = rc_handler.data.get('config_params', [])
        for param in cfg_params:
            # only restore parameters that are in the config
            if not hasattr(self.config, param):
                continue
            cfg_setter = self.ids.config_panel.add()
            cfg_setter.ids.cfg_spinner.text = param

