import os

import numpy as np
import plotly.express as px
import pandas as pd


from kivy import Logger
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, \
    ListProperty, BooleanProperty
from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib as mpl
import matplotlib.pyplot as plt


from donkeycar import load_config
from donkeycar.management.ui.common import FileChooserBase, \
    PaddedBoxLayout, decompose, get_app_screen, BackgroundBoxLayout, AppScreen, \
    status
from donkeycar.management.ui.rc_file_handler import rc_handler
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord


mpl.rcParams.update({'font.size': 8})
plt.style.use('dark_background')
fig, ax = plt.subplots()
plt.tight_layout(pad=1.5)
plt.subplots_adjust(bottom=0.16)
cmap = mpl.cm.get_cmap("plasma")


class ConfigManager(BackgroundBoxLayout, FileChooserBase):
    """ Class to manage loading of the config file from the car directory"""
    config = ObjectProperty(None, allownone=True)
    file_path = StringProperty(rc_handler.data.get('car_dir', ''))

    def load_action(self):
        """ Load the config from the file path"""
        if not self.file_path:
            return
        try:
            path = os.path.join(self.file_path, 'config.py')
            new_conf = load_config(path)
            self.config = new_conf
            # If load successful, store into app config
            rc_handler.data['car_dir'] = self.file_path
        except FileNotFoundError:
            Logger.error(f'Config: Directory {self.file_path} has no '
                         f'config.py')
            self.config = None
        except Exception as e:
            Logger.error(f'Config: {e}')
            self.config = None

    def on_config(self, obj, cfg):
        tub_screen = get_app_screen('tub')
        if tub_screen:
            tub_screen.ids.tub_loader.ids.tub_button.disabled = False
            tub_screen.ids.tub_loader.root_path = self.file_path
        pilot_screen = get_app_screen('pilot')
        if pilot_screen:
            pilot_screen.config = self.config
        train_screen = get_app_screen('train')
        if train_screen:
            train_screen.config = self.config
        car_screen = get_app_screen('car')
        if car_screen:
            car_screen.config = self.config
        status('Config loaded from' + self.file_path)


class TubLoader(BackgroundBoxLayout, FileChooserBase):
    """ Class to manage loading or reloading of the Tub from the tub directory.
        Loading triggers many actions on other widgets of the app. """
    file_path = StringProperty(rc_handler.data.get('last_tub', ''))
    tub = ObjectProperty(None)
    len = NumericProperty(1)
    records = None

    def load_action(self):
        """ Update tub from the file path"""
        if self.update_tub():
            # If update successful, store into app config
            rc_handler.data['last_tub'] = self.file_path

    def update_tub(self, event=None):
        if not self.file_path:
            return False
        # If config not yet loaded return
        tub_screen = get_app_screen('tub')
        cfg = tub_screen.ids.config_manager.config
        if not cfg:
            return False
        # At least check if there is a manifest file in the tub path
        if not os.path.exists(os.path.join(self.file_path, 'manifest.json')):
            status(f'Path {self.file_path} is not a valid tub.')
            return False
        try:
            if self.tub:
                self.tub.close()
            self.tub = Tub(self.file_path)
        except Exception as e:
            status(f'Failed loading tub: {str(e)}')
            return False
        # Check if filter is set in tub screen
        # expression = tub_screen().ids.tub_filter.filter_expression
        train_filter = getattr(cfg, 'TRAIN_FILTER', None)

        # Use filter, this defines the function
        def select(underlying):
            if not train_filter:
                return True
            else:
                try:
                    record = TubRecord(cfg, self.tub.base_path, underlying)
                    res = train_filter(record)
                    return res
                except KeyError as err:
                    Logger.error(f'Filter: {err}')
                    return True

        self.records = [TubRecord(cfg, self.tub.base_path, record)
                        for record in self.tub if select(record)]
        self.len = len(self.records)
        if self.len > 0:
            tub_screen.index = 0
            tub_screen.ids.data_plot.update_dataframe_from_tub()
            msg = f'Loaded tub {self.file_path} with {self.len} records'
            get_app_screen('pilot').ids.slider.max = self.len - 1
        else:
            msg = f'No records in tub {self.file_path}'
        status(msg)
        return True


class TubEditor(BoxLayout):
    """ Tub editor widget. Contains left/right index interval and the
        manipulator buttons for deleting / restoring and reloading """
    lr = ListProperty([0, 0])

    def set_lr(self, is_l=True):
        """ Sets left or right range to the current tub record index """
        if not get_app_screen('tub').current_record:
            return
        self.lr[0 if is_l else 1] \
            = get_app_screen('tub').current_record.underlying['_index']

    def del_lr(self, is_del):
        """ Deletes or restores records in chosen range """
        tub = get_app_screen('tub').ids.tub_loader.tub
        if self.lr[1] >= self.lr[0]:
            selected = list(range(*self.lr))
        else:
            last_id = tub.manifest.current_index
            selected = list(range(self.lr[0], last_id))
            selected += list(range(self.lr[1]))
        tub.delete_records(selected) if is_del else tub.restore_records(selected)


class TubFilter(BoxLayout):
    """ Tub filter widget. """
    screen = ObjectProperty()
    filter_expression = StringProperty(None)
    record_filter = StringProperty(rc_handler.data.get('record_filter', ''))

    def update_filter(self):
        filter_text = self.ids.record_filter.text
        config = get_app_screen('tub').ids.config_manager.config
        # empty string resets the filter
        if filter_text == '':
            self.record_filter = ''
            self.filter_expression = ''
            rc_handler.data['record_filter'] = self.record_filter
            if hasattr(config, 'TRAIN_FILTER'):
                delattr(config, 'TRAIN_FILTER')
                status(f'Filter cleared')
            return
        filter_expression = self.create_filter_string(filter_text)
        try:
            record = get_app_screen('tub').current_record
            filter_func_text = f"""def filter_func(record): 
                                       return {filter_expression}       
                                """
            # creates the function 'filter_func'
            ldict = {}
            exec(filter_func_text, globals(), ldict)
            filter_func = ldict['filter_func']
            res = filter_func(record)
            msg = f'Filter result on current record: {res}'
            if isinstance(res, bool):
                self.record_filter = filter_text
                self.filter_expression = filter_expression
                rc_handler.data['record_filter'] = self.record_filter
                setattr(config, 'TRAIN_FILTER', filter_func)
            else:
                msg += ' - non bool expression can\'t be applied'
            msg += ' - press <Reload tub> to see effect'
            status(msg)
        except Exception as e:
            status(f'Filter error on current record: {e}')

    def filter_focus(self):
        focus = self.ids.record_filter.focus
        self.screen.keys_enabled = not focus
        if not focus:
            self.screen.bind_keyboard()

    @staticmethod
    def create_filter_string(filter_text, record_name='record'):
        """ Converts text like 'user/angle' into 'record.underlying['user/angle']
        so that it can be used in a filter. Will replace only expressions that
        are found in the tub inputs list.

        :param filter_text: input text like 'user/throttle > 0.1'
        :param record_name: name of the record in the expression
        :return:            updated string that has all input fields wrapped
        """
        for field in get_app_screen('tub').current_record.underlying.keys():
            field_list = filter_text.split(field)
            if len(field_list) > 1:
                filter_text = f'{record_name}.underlying["{field}"]'\
                    .join(field_list)
        return filter_text


class Plot(FigureCanvasKivyAgg):
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(fig, **kwargs)

    def on_df(self, e=None, z=None):
        ax.clear()
        if not self.df.empty:
            n = len(self.df.columns)
            it = np.linspace(0, 1, n)
            self.df.plot(ax=ax, linewidth=0.5, color=cmap(it))
            # Put a legend to the right of the current axis
            ax.legend(loc='center left', bbox_to_anchor=(0.87, 0.5))
        self.draw()


class DataPlot(PaddedBoxLayout):
    """ Data plot panel which embeds matplotlib interactive graph"""
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def plot_from_current_bars(self, in_app=True):
        """ Plotting from current selected bars. The DataFrame for plotting
            should contain all bars except for strings fields and all data is
            selected if bars are empty.  """
        tub = get_app_screen('tub').ids.tub_loader.tub
        field_map = dict(zip(tub.manifest.inputs, tub.manifest.types))
        # Use selected fields or all fields if nothing is slected
        all_cols = (get_app_screen('tub').ids.data_panel.labels.keys()
                    or self.df.columns)
        cols = [c for c in all_cols if decompose(c)[0] in field_map
                and field_map[decompose(c)[0]] not in ('image_array', 'str')]

        df = self.df[cols]
        if df is None:
            return
        # Don't plot the milliseconds time stamp as this is a too big number
        df = df.drop(labels=['_timestamp_ms'], axis=1, errors='ignore')

        if in_app:
            get_app_screen('tub').ids.graph.df = df
        else:
            fig = px.line(df, x=df.index, y=df.columns, title=tub.base_path)
            fig.update_xaxes(rangeslider=dict(visible=True))
            fig.show()

    def unravel_vectors(self):
        """ Unravels vector and list entries in tub which are created
            when the DataFrame is created from a list of records"""
        manifest = get_app_screen('tub').ids.tub_loader.tub.manifest
        for k, v in zip(manifest.inputs, manifest.types):
            if v == 'vector' or v == 'list':
                dim = len(get_app_screen('tub').current_record.underlying[k])
                df_keys = [k + f'_{i}' for i in range(dim)]
                self.df[df_keys] = pd.DataFrame(self.df[k].tolist(),
                                                index=self.df.index)
                self.df.drop(k, axis=1, inplace=True)

    def update_dataframe_from_tub(self):
        """ Called from TubManager when a tub is reloaded/recreated. Fills
            the DataFrame from records, and updates the dropdown menu in the
            data panel."""
        tub_screen = get_app_screen('tub')
        generator = (t.underlying for t in tub_screen.ids.tub_loader.records)
        self.df = pd.DataFrame(generator).dropna()
        to_drop = ['cam/image_array']
        self.df.drop(labels=to_drop, axis=1, errors='ignore', inplace=True)
        self.df.set_index('_index', inplace=True)
        self.unravel_vectors()
        tub_screen.ids.data_panel.ids.data_spinner.values = self.df.columns
        self.plot_from_current_bars()


class TubScreen(AppScreen):
    """ First screen of the app managing the tub data. """
    index = NumericProperty(None, force_dispatch=True)
    current_record = ObjectProperty(None)
    keys_enabled = BooleanProperty(True)

    def initialise(self, e):
        self.ids.config_manager.load_action()
        self.ids.tub_loader.update_tub()

    def on_index(self, obj, index):
        """ Kivy method that is called if self.index changes"""
        if index >= 0:
            self.current_record = self.ids.tub_loader.records[index]
            self.ids.slider.value = index

    def on_current_record(self, obj, record):
        """ Kivy method that is called if self.current_record changes."""
        self.ids.img.update(record)
        i = record.underlying['_index']
        self.ids.control_panel.record_display = f"Record {i:06}"

    def on_keyboard(self, keyboard, scancode, text=None, modifier=None):
        if not self.keys_enabled:
            return
        self.ids.control_panel.on_keyboard(keyboard, scancode, text, modifier)

