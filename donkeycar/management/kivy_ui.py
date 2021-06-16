import json
import re
import time
from copy import copy
from datetime import datetime
from functools import partial
import subprocess
from subprocess import Popen, PIPE
from threading import Thread
from collections import namedtuple
from kivy.logger import Logger
import io
import os
import atexit
import yaml
from PIL import Image as PilImage
import pandas as pd
import numpy as np
import plotly.express as px

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, \
    ListProperty, BooleanProperty
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.lang.builder import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import SpinnerOption, Spinner

from donkeycar import load_config
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.augmentations import ImageAugmentation
from donkeycar.pipeline.database import PilotDatabase
from donkeycar.pipeline.types import TubRecord
from donkeycar.utils import get_model_by_type
from donkeycar.pipeline.training import train


Builder.load_file(os.path.join(os.path.dirname(__file__), 'ui.kv'))
Window.clearcolor = (0.2, 0.2, 0.2, 1)
LABEL_SPINNER_TEXT = 'Add/remove'

# Data struct to show tub field in the progress bar, containing the name,
# the name of the maximum value in the config file and if it is centered.
FieldProperty = namedtuple('FieldProperty',
                           ['field', 'max_value_id', 'centered'])


def get_norm_value(value, cfg, field_property, normalised=True):
    max_val_key = field_property.max_value_id
    max_value = getattr(cfg, max_val_key, 1.0)
    out_val = value / max_value if normalised else value * max_value
    return out_val


def tub_screen():
    return App.get_running_app().tub_screen if App.get_running_app() else None


def pilot_screen():
    return App.get_running_app().pilot_screen if App.get_running_app() else None


def train_screen():
    return App.get_running_app().train_screen if App.get_running_app() else None


def car_screen():
    return App.get_running_app().car_screen if App.get_running_app() else None


def recursive_update(target, source):
    """ Recursively update dictionary """
    if isinstance(target, dict) and isinstance(source, dict):
        for k, v in source.items():
            v_t = target.get(k)
            if not recursive_update(v_t, v):
                target[k] = v
        return True
    else:
        return False


def decompose(field):
    """ Function to decompose a string vector field like 'gyroscope_1' into a
        tuple ('gyroscope', 1) """
    field_split = field.split('_')
    if len(field_split) > 1 and field_split[-1].isdigit():
        return '_'.join(field_split[:-1]), int(field_split[-1])
    return field, None


class RcFileHandler:
    """ This handles the config file which stores the data, like the field
        mapping for displaying of bars and last opened car, tub directory. """

    # These entries are expected in every tub, so they don't need to be in
    # the file
    known_entries = [
        FieldProperty('user/angle', '', centered=True),
        FieldProperty('user/throttle', '', centered=False),
        FieldProperty('pilot/angle', '', centered=True),
        FieldProperty('pilot/throttle', '', centered=False),
    ]

    def __init__(self, file_path='~/.donkeyrc'):
        self.file_path = os.path.expanduser(file_path)
        self.data = self.create_data()
        recursive_update(self.data, self.read_file())
        self.field_properties = self.create_field_properties()

        def exit_hook():
            self.write_file()
        # Automatically save config when program ends
        atexit.register(exit_hook)

    def create_field_properties(self):
        """ Merges known field properties with the ones from the file """
        field_properties = {entry.field: entry for entry in self.known_entries}
        field_list = self.data.get('field_mapping')
        if field_list is None:
            field_list = {}
        for entry in field_list:
            assert isinstance(entry, dict), \
                'Dictionary required in each entry in the field_mapping list'
            field_property = FieldProperty(**entry)
            field_properties[field_property.field] = field_property
        return field_properties

    def create_data(self):
        data = dict()
        data['user_pilot_map'] = {'user/throttle': 'pilot/throttle',
                                  'user/angle': 'pilot/angle'}
        return data

    def read_file(self):
        if os.path.exists(self.file_path):
            with open(self.file_path) as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                Logger.info(f'Donkeyrc: Donkey file {self.file_path} loaded.')
                return data
        else:
            Logger.warn(f'Donkeyrc: Donkey file {self.file_path} does not '
                        f'exist.')
            return {}

    def write_file(self):
        if os.path.exists(self.file_path):
            Logger.info(f'Donkeyrc: Donkey file {self.file_path} updated.')
        with open(self.file_path, mode='w') as f:
            self.data['time_stamp'] = datetime.now()
            data = yaml.dump(self.data, f)
            return data


rc_handler = RcFileHandler()


class MySpinnerOption(SpinnerOption):
    """ Customization for Spinner """
    pass


class MySpinner(Spinner):
    """ Customization of Spinner drop down menu """
    def __init__(self, **kwargs):
        super().__init__(option_cls=MySpinnerOption, **kwargs)


class FileChooserPopup(Popup):
    """ File Chooser popup window"""
    load = ObjectProperty()
    root_path = StringProperty()
    filters = ListProperty()


class FileChooserBase:
    """ Base class for file chooser widgets"""
    file_path = StringProperty("No file chosen")
    popup = ObjectProperty(None)
    root_path = os.path.expanduser('~')
    title = StringProperty(None)
    filters = ListProperty()

    def open_popup(self):
        self.popup = FileChooserPopup(load=self.load, root_path=self.root_path,
                                      title=self.title, filters=self.filters)
        self.popup.open()

    def load(self, selection):
        """ Method to load the chosen file into the path and call an action"""
        self.file_path = str(selection[0])
        self.popup.dismiss()
        self.load_action()

    def load_action(self):
        """ Virtual method to run when file_path has been updated """
        pass


class ConfigManager(BoxLayout, FileChooserBase):
    """ Class to mange loading of the config file from the car directory"""
    config = ObjectProperty(None)
    file_path = StringProperty(rc_handler.data.get('car_dir', ''))

    def load_action(self):
        """ Load the config from the file path"""
        if self.file_path:
            try:
                path = os.path.join(self.file_path, 'config.py')
                self.config = load_config(path)
                # If load successful, store into app config
                rc_handler.data['car_dir'] = self.file_path
            except FileNotFoundError:
                Logger.error(f'Config: Directory {self.file_path} has no '
                             f'config.py')
            except Exception as e:
                Logger.error(f'Config: {e}')


class TubLoader(BoxLayout, FileChooserBase):
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
        cfg = tub_screen().ids.config_manager.config
        if not cfg:
            return False
        # At least check if there is a manifest file in the tub path
        if not os.path.exists(os.path.join(self.file_path, 'manifest.json')):
            tub_screen().status(f'Path {self.file_path} is not a valid tub.')
            return False
        try:
            self.tub = Tub(self.file_path)
        except Exception as e:
            tub_screen().status(f'Failed loading tub: {str(e)}')
            return False
        # Check if filter is set in tub screen
        expression = tub_screen().ids.tub_filter.filter_expression

        # Use filter, this defines the function
        def select(underlying):
            if not expression:
                return True
            else:
                try:
                    record = TubRecord(cfg, self.tub.base_path, underlying)
                    res = eval(expression)
                    return res
                except KeyError as err:
                    Logger.error(f'Filter: {err}')
                    return True

        self.records = [TubRecord(cfg, self.tub.base_path, record)
                        for record in self.tub if select(record)]
        self.len = len(self.records)
        if self.len > 0:
            tub_screen().index = 0
            tub_screen().ids.data_plot.update_dataframe_from_tub()
            msg = f'Loaded tub {self.file_path} with {self.len} records'
        else:
            msg = f'No records in tub {self.file_path}'
        if expression:
            msg += f' using filter {tub_screen().ids.tub_filter.record_filter}'
        tub_screen().status(msg)
        return True


class LabelBar(BoxLayout):
    """ Widget that combines a label with a progress bar. This is used to
        display the record fields in the data panel."""
    field = StringProperty()
    field_property = ObjectProperty()
    config = ObjectProperty()
    msg = ''

    def update(self, record):
        """ This function is called everytime the current record is updated"""
        if not record:
            return
        field, index = decompose(self.field)
        if field in record.underlying:
            val = record.underlying[field]
            if index is not None:
                val = val[index]
            # Update bar if a field property for this field is known
            if self.field_property:
                norm_value = get_norm_value(val, self.config,
                                            self.field_property)
                new_bar_val = (norm_value + 1) * 50 if \
                    self.field_property.centered else norm_value * 100
                self.ids.bar.value = new_bar_val
            self.ids.field_label.text = self.field
            if isinstance(val, float) or isinstance(val, np.float32):
                text = f'{val:+07.3f}'
            elif isinstance(val, int):
                text = f'{val:10}'
            else:
                text = str(val)
            self.ids.value_label.text = text
        else:
            Logger.error(f'Record: Bad record {record.underlying["_index"]} - '
                         f'missing field {self.field}')


class DataPanel(BoxLayout):
    """ Data panel widget that contains the label/bar widgets and the drop
        down menu to select/deselect fields."""
    record = ObjectProperty()
    # dual mode is used in the pilot arena where we only show angle and
    # throttle or speed
    dual_mode = BooleanProperty(False)
    auto_text = StringProperty(LABEL_SPINNER_TEXT)
    throttle_field = StringProperty('user/throttle')
    link = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = {}
        self.screen = ObjectProperty()

    def add_remove(self):
        """ Method to add or remove a LabelBar. Depending on the value of the
            drop down menu the LabelBar is added if it is not present otherwise
            removed."""
        field = self.ids.data_spinner.text
        if field is LABEL_SPINNER_TEXT:
            return
        if field in self.labels and not self.dual_mode:
            self.remove_widget(self.labels[field])
            del(self.labels[field])
            self.screen.status(f'Removing {field}')
        else:
            # in dual mode replace the second entry with the new one
            if self.dual_mode and len(self.labels) == 2:
                k, v = list(self.labels.items())[-1]
                self.remove_widget(v)
                del(self.labels[k])
            field_property = rc_handler.field_properties.get(decompose(field)[0])
            cfg = tub_screen().ids.config_manager.config
            lb = LabelBar(field=field, field_property=field_property, config=cfg)
            self.labels[field] = lb
            self.add_widget(lb)
            lb.update(self.record)
            if len(self.labels) == 2:
                self.throttle_field = field
            self.screen.status(f'Adding {field}')
        if self.screen.name == 'tub':
            self.screen.ids.data_plot.plot_from_current_bars()
        self.ids.data_spinner.text = LABEL_SPINNER_TEXT
        self.auto_text = field

    def on_record(self, obj, record):
        """ Kivy function that is called every time self.record changes"""
        for v in self.labels.values():
            v.update(record)

    def clear(self):
        for v in self.labels.values():
            self.remove_widget(v)
        self.labels.clear()


class FullImage(Image):
    """ Widget to display an image that fills the space. """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.core_image = None

    def update(self, record):
        """ This method is called ever time a record gets updated. """
        try:
            img_arr = self.get_image(record)
            pil_image = PilImage.fromarray(img_arr)
            bytes_io = io.BytesIO()
            pil_image.save(bytes_io, format='png')
            bytes_io.seek(0)
            self.core_image = CoreImage(bytes_io, ext='png')
            self.texture = self.core_image.texture
        except KeyError as e:
            Logger.error('Record: Missing key:', e)
        except Exception as e:
            Logger.error('Record: Bad record:', e)

    def get_image(self, record):
        return record.image(cached=False)


class ControlPanel(BoxLayout):
    """ Class for control panel navigation. """
    screen = ObjectProperty()
    speed = NumericProperty(1.0)
    record_display = StringProperty()
    clock = None
    fwd = None

    def start(self, fwd=True, continuous=False):
        """
        Method to cycle through records if either single <,> or continuous
        <<, >> buttons are pressed
        :param fwd:         If we go forward or backward
        :param continuous:  If we do <<, >> or <, >
        :return:            None
        """
        time.sleep(0.1)
        call = partial(self.step, fwd, continuous)
        if continuous:
            self.fwd = fwd
            s = float(self.speed) * tub_screen().ids.config_manager.config.DRIVE_LOOP_HZ
            cycle_time = 1.0 / s
        else:
            cycle_time = 0.08
        self.clock = Clock.schedule_interval(call, cycle_time)

    def step(self, fwd=True, continuous=False, *largs):
        """
        Updating a single step and cap/floor the index so we stay w/in the tub.
        :param fwd:         If we go forward or backward
        :param continuous:  If we are in continuous mode <<, >>
        :param largs:       dummy
        :return:            None
        """
        new_index = self.screen.index + (1 if fwd else -1)
        if new_index >= tub_screen().ids.tub_loader.len:
            new_index = 0
        elif new_index < 0:
            new_index = tub_screen().ids.tub_loader.len - 1
        self.screen.index = new_index
        msg = f'Donkey {"run" if continuous else "step"} ' \
              f'{"forward" if fwd else "backward"}'
        if not continuous:
            msg += f' - you can also use {"<right>" if fwd else "<left>"} key'
        else:
            msg += ' - you can toggle run/stop with <space>'
        self.screen.status(msg)

    def stop(self):
        if self.clock:
            self.clock.cancel()
            self.clock = None

    def restart(self):
        if self.clock:
            self.stop()
            self.start(self.fwd, True)

    def update_speed(self, up=True):
        """ Method to update the speed on the controller"""
        values = self.ids.control_spinner.values
        idx = values.index(self.ids.control_spinner.text)
        if up and idx < len(values) - 1:
            self.ids.control_spinner.text = values[idx + 1]
        elif not up and idx > 0:
            self.ids.control_spinner.text = values[idx - 1]

    def set_button_status(self, disabled=True):
        """ Method to disable(enable) all buttons. """
        self.ids.run_bwd.disabled = self.ids.run_fwd.disabled = \
            self.ids.step_fwd.disabled = self.ids.step_bwd.disabled = disabled

    def on_keyboard(self, key, scancode):
        """ Method to chack with keystroke has ben sent. """
        if key == ' ':
            if self.clock and self.clock.is_triggered:
                self.stop()
                self.set_button_status(disabled=False)
                self.screen.status('Donkey stopped')
            else:
                self.start(continuous=True)
                self.set_button_status(disabled=True)
        elif scancode == 79:
            self.step(fwd=True)
        elif scancode == 80:
            self.step(fwd=False)
        elif scancode == 45:
            self.update_speed(up=False)
        elif scancode == 46:
            self.update_speed(up=True)


class PaddedBoxLayout(BoxLayout):
    pass


class TubEditor(PaddedBoxLayout):
    """ Tub editor widget. Contains left/right index interval and the
        manipulator buttons for deleting / restoring and reloading """
    lr = ListProperty([0, 0])

    def set_lr(self, is_l=True):
        """ Sets left or right range to the current tub record index """
        if not tub_screen().current_record:
            return
        self.lr[0 if is_l else 1] = tub_screen().current_record.underlying['_index']

    def del_lr(self, is_del):
        """ Deletes or restores records in chosen range """
        tub = tub_screen().ids.tub_loader.tub
        if self.lr[1] >= self.lr[0]:
            selected = list(range(*self.lr))
        else:
            last_id = tub.manifest.current_index
            selected = list(range(self.lr[0], last_id))
            selected += list(range(self.lr[1]))
        tub.delete_records(selected) if is_del else tub.restore_records(selected)


class TubFilter(PaddedBoxLayout):
    """ Tub filter widget. """
    filter_expression = StringProperty(None)
    record_filter = StringProperty(rc_handler.data.get('record_filter', ''))

    def update_filter(self):
        filter_text = self.ids.record_filter.text
        # empty string resets the filter
        if filter_text == '':
            self.record_filter = ''
            self.filter_expression = ''
            rc_handler.data['record_filter'] = self.record_filter
            tub_screen().status(f'Filter cleared')
            return
        filter_expression = self.create_filter_string(filter_text)
        try:
            record = tub_screen().current_record
            res = eval(filter_expression)
            status = f'Filter result on current record: {res}'
            if isinstance(res, bool):
                self.record_filter = filter_text
                self.filter_expression = filter_expression
                rc_handler.data['record_filter'] = self.record_filter
            else:
                status += ' - non bool expression can\'t be applied'
            status += ' - press <Reload tub> to see effect'
            tub_screen().status(status)
        except Exception as e:
            tub_screen().status(f'Filter error on current record: {e}')

    @staticmethod
    def create_filter_string(filter_text, record_name='record'):
        """ Converts text like 'user/angle' into 'record.underlying['user/angle']
        so that it can be used in a filter. Will replace only expressions that
        are found in the tub inputs list.

        :param filter_text: input text like 'user/throttle > 0.1'
        :param record_name: name of the record in the expression
        :return:            updated string that has all input fields wrapped
        """
        for field in tub_screen().current_record.underlying.keys():
            field_list = filter_text.split(field)
            if len(field_list) > 1:
                filter_text = f'{record_name}.underlying["{field}"]'\
                    .join(field_list)
        return filter_text


class DataPlot(PaddedBoxLayout):
    """ Data plot panel which embeds matplotlib interactive graph"""
    df = ObjectProperty(force_dispatch=True, allownone=True)

    def plot_from_current_bars(self, in_app=True):
        """ Plotting from current selected bars. The DataFrame for plotting
            should contain all bars except for strings fields and all data is
            selected if bars are empty.  """
        tub = tub_screen().ids.tub_loader.tub
        field_map = dict(zip(tub.manifest.inputs, tub.manifest.types))
        # Use selected fields or all fields if nothing is slected
        all_cols = tub_screen().ids.data_panel.labels.keys() or self.df.columns
        cols = [c for c in all_cols if decompose(c)[0] in field_map
                and field_map[decompose(c)[0]] not in ('image_array', 'str')]

        df = self.df[cols]
        if df is None:
            return
        # Don't plot the milliseconds time stamp as this is a too big number
        df = df.drop(labels=['_timestamp_ms'], axis=1, errors='ignore')

        if in_app:
            tub_screen().ids.graph.df = df
        else:
            fig = px.line(df, x=df.index, y=df.columns, title=tub.base_path)
            fig.update_xaxes(rangeslider=dict(visible=True))
            fig.show()

    def unravel_vectors(self):
        """ Unravels vector and list entries in tub which are created
            when the DataFrame is created from a list of records"""
        manifest = tub_screen().ids.tub_loader.tub.manifest
        for k, v in zip(manifest.inputs, manifest.types):
            if v == 'vector' or v == 'list':
                dim = len(tub_screen().current_record.underlying[k])
                df_keys = [k + f'_{i}' for i in range(dim)]
                self.df[df_keys] = pd.DataFrame(self.df[k].tolist(),
                                                index=self.df.index)
                self.df.drop(k, axis=1, inplace=True)

    def update_dataframe_from_tub(self):
        """ Called from TubManager when a tub is reloaded/recreated. Fills
            the DataFrame from records, and updates the dropdown menu in the
            data panel."""
        generator = (t.underlying for t in tub_screen().ids.tub_loader.records)
        self.df = pd.DataFrame(generator).dropna()
        to_drop = {'cam/image_array'}
        self.df.drop(labels=to_drop, axis=1, errors='ignore', inplace=True)
        self.df.set_index('_index', inplace=True)
        self.unravel_vectors()
        tub_screen().ids.data_panel.ids.data_spinner.values = self.df.columns
        self.plot_from_current_bars()


class TabBar(BoxLayout):
    manager = ObjectProperty(None)

    def disable_only(self, bar_name):
        this_button_name = bar_name + '_btn'
        for button_name, button in self.ids.items():
            button.disabled = button_name == this_button_name


class TubScreen(Screen):
    """ First screen of the app managing the tub data. """
    index = NumericProperty(None, force_dispatch=True)
    current_record = ObjectProperty(None)
    keys_enabled = BooleanProperty(True)

    def initialise(self, e):
        self.ids.config_manager.load_action()
        self.ids.tub_loader.update_tub()

    def on_index(self, obj, index):
        """ Kivy method that is called if self.index changes"""
        self.current_record = self.ids.tub_loader.records[index]
        self.ids.slider.value = index

    def on_current_record(self, obj, record):
        """ Kivy method that is called if self.current_record changes."""
        self.ids.img.update(record)
        i = record.underlying['_index']
        self.ids.control_panel.record_display = f"Record {i:06}"

    def status(self, msg):
        self.ids.status.text = msg

    def on_keyboard(self, instance, keycode, scancode, key, modifiers):
        if self.keys_enabled:
            self.ids.control_panel.on_keyboard(key, scancode)


class PilotLoader(BoxLayout, FileChooserBase):
    """ Class to mange loading of the config file from the car directory"""
    num = StringProperty()
    model_type = StringProperty()
    pilot = ObjectProperty(None)
    filters = ['*.h5', '*.tflite']

    def load_action(self):
        if self.file_path and self.pilot:
            try:
                self.pilot.load(os.path.join(self.file_path))
                rc_handler.data['pilot_' + self.num] = self.file_path
                rc_handler.data['model_type_' + self.num] = self.model_type
            except FileNotFoundError:
                Logger.error(f'Pilot: Model {self.file_path} not found')
            except Exception as e:
                Logger.error(f'Pilot: {e}')

    def on_model_type(self, obj, model_type):
        """ Kivy method that is called if self.model_type changes. """
        if self.model_type and self.model_type != 'Model type':
            cfg = tub_screen().ids.config_manager.config
            if cfg:
                self.pilot = get_model_by_type(self.model_type, cfg)
                self.ids.pilot_button.disabled = False

    def on_num(self, e, num):
        """ Kivy method that is called if self.num changes. """
        self.file_path = rc_handler.data.get('pilot_' + self.num, '')
        self.model_type = rc_handler.data.get('model_type_' + self.num, '')


class OverlayImage(FullImage):
    """ Widget to display the image and the user/pilot data for the tub. """
    keras_part = ObjectProperty()
    pilot_record = ObjectProperty()
    throttle_field = StringProperty('user/throttle')

    def get_image(self, record):
        from donkeycar.management.makemovie import MakeMovie
        img_arr = copy(super().get_image(record))
        augmentation = pilot_screen().augmentation if pilot_screen().auglist \
            else None
        if augmentation:
            img_arr = pilot_screen().augmentation.augment(img_arr)
        angle = record.underlying['user/angle']
        throttle = get_norm_value(record.underlying[self.throttle_field],
                                  tub_screen().ids.config_manager.config,
                                  rc_handler.field_properties[
                                      self.throttle_field])
        rgb = (0, 255, 0)
        MakeMovie.draw_line_into_image(angle, throttle, False, img_arr, rgb)
        if not self.keras_part:
            return img_arr

        output = self.keras_part.evaluate(record, augmentation)
        rgb = (0, 0, 255)
        MakeMovie.draw_line_into_image(output[0], output[1], True, img_arr, rgb)
        out_record = copy(record)
        out_record.underlying['pilot/angle'] = output[0]
        # rename and denormalise the throttle output
        pilot_throttle_field \
            = rc_handler.data['user_pilot_map'][self.throttle_field]
        out_record.underlying[pilot_throttle_field] \
            = get_norm_value(output[1], tub_screen().ids.config_manager.config,
                             rc_handler.field_properties[self.throttle_field],
                             normalised=False)
        self.pilot_record = out_record
        return img_arr


class PilotScreen(Screen):
    """ Screen to do the pilot vs pilot comparison ."""
    index = NumericProperty(None, force_dispatch=True)
    current_record = ObjectProperty(None)
    keys_enabled = BooleanProperty(False)
    auglist = ListProperty(force_dispatch=True)
    augmentation = ObjectProperty()
    config = ObjectProperty()

    def on_index(self, obj, index):
        """ Kivy method that is called if self.index changes. Here we update
            self.current_record and the slider value. """
        if tub_screen().ids.tub_loader.records:
            self.current_record = tub_screen().ids.tub_loader.records[index]
            self.ids.slider.value = index

    def on_current_record(self, obj, record):
        """ Kivy method that is called when self.current_index changes. Here
            we update the images and the control panel entry."""
        i = record.underlying['_index']
        self.ids.pilot_control.record_display = f"Record {i:06}"
        self.ids.img_1.update(record)
        self.ids.img_2.update(record)

    def initialise(self, e):
        self.ids.pilot_loader_1.on_model_type(None, None)
        self.ids.pilot_loader_1.load_action()
        self.ids.pilot_loader_2.on_model_type(None, None)
        self.ids.pilot_loader_2.load_action()
        mapping = copy(rc_handler.data['user_pilot_map'])
        del(mapping['user/angle'])
        self.ids.data_in.ids.data_spinner.values = mapping.keys()
        self.ids.data_in.ids.data_spinner.text = 'user/angle'
        self.ids.data_panel_1.ids.data_spinner.disabled = True
        self.ids.data_panel_2.ids.data_spinner.disabled = True

    def map_pilot_field(self, text):
        """ Method to return user -> pilot mapped fields except for the
            intial vale called Add/remove. """
        if text == LABEL_SPINNER_TEXT:
            return text
        return rc_handler.data['user_pilot_map'][text]

    def set_brightness(self, val=None):
        if self.ids.button_bright.state == 'down':
            self.config.AUG_MULTIPLY_RANGE = (val, val)
            if self.ids.button_blur.state == 'down':
                self.auglist = ['MULTIPLY', 'BLUR']
            else:
                self.auglist = ['MULTIPLY']

    def remove_brightness(self):
        self.auglist = ['BLUR'] if self.ids.button_blur.state == 'down' else[]

    def set_blur(self, val=None):
        if self.ids.button_blur.state == 'down':
            self.config.AUG_BLUR_RANGE = (val, val)
            if self.ids.button_bright.state == 'down':
                self.auglist = ['MULTIPLY', 'BLUR']
            else:
                self.auglist = ['BLUR']

    def remove_blur(self):
        self.auglist = ['MULTIPLY'] if self.ids.button_bright.state == 'down' \
            else []

    def on_auglist(self, obj, auglist):
        self.config.AUGMENTATIONS = self.auglist
        self.augmentation = ImageAugmentation(self.config)
        self.on_current_record(None, self.current_record)

    def status(self, msg):
        self.ids.status.text = msg

    def on_keyboard(self, instance, keycode, scancode, key, modifiers):
        if self.keys_enabled:
            self.ids.pilot_control.on_keyboard(key, scancode)


class ScrollableLabel(ScrollView):
    pass


class DataFrameLabel(Label):
    pass


class TransferSelector(BoxLayout, FileChooserBase):
    """ Class to select transfer model"""
    filters = ['*.h5']


class TrainScreen(Screen):
    """ Class showing the training screen. """
    config = ObjectProperty(force_dispatch=True, allownone=True)
    database = ObjectProperty()
    pilot_df = ObjectProperty(force_dispatch=True)
    tub_df = ObjectProperty(force_dispatch=True)

    def train_call(self, model_type, *args):
        # remove car directory from path
        tub_path = tub_screen().ids.tub_loader.tub.base_path
        transfer = self.ids.transfer_spinner.text
        if transfer != 'Choose transfer model':
            transfer = os.path.join(self.config.MODELS_PATH, transfer + '.h5')
        else:
            transfer = None
        try:
            history = train(self.config, tub_paths=tub_path,
                            model_type=model_type,
                            transfer=transfer,
                            comment=self.ids.comment.text)
            self.ids.status.text = f'Training completed.'
            self.ids.train_button.state = 'normal'
            self.ids.transfer_spinner.text = 'Choose transfer model'
            self.reload_database()
        except Exception as e:
            self.ids.status.text = f'Train error {e}'

    def train(self, model_type):
        self.config.SHOW_PLOT = False
        Thread(target=self.train_call, args=(model_type,)).start()
        self.ids.status.text = f'Training started.'
        self.ids.comment.text = 'Comment'

    def set_config_attribute(self, input):
        try:
            val = json.loads(input)
        except ValueError:
            val = input

        att = self.ids.cfg_spinner.text.split(':')[0]
        setattr(self.config, att, val)
        self.ids.cfg_spinner.values = self.value_list()
        self.ids.status.text = f'Setting {att} to {val} of type ' \
                               f'{type(val).__name__}'

    def value_list(self):
        if self.config:
            return [f'{k}: {v}' for k, v in self.config.__dict__.items()]
        else:
            return ['select']

    def on_config(self, obj, config):
        if self.config and self.ids:
            self.ids.cfg_spinner.values = self.value_list()
            self.reload_database()

    def reload_database(self):
        if self.config:
            self.database = PilotDatabase(self.config)

    def on_database(self, obj, database):
        if self.ids.check.state == 'down':
            self.pilot_df, self.tub_df = self.database.to_df_tubgrouped()
            self.ids.scroll_tubs.text = self.tub_df.to_string()
        else:
            self.pilot_df = self.database.to_df()
            self.tub_df = pd.DataFrame()
            self.ids.scroll_tubs.text = ''

        self.pilot_df.drop(columns=['History', 'Config'], errors='ignore',
                           inplace=True)
        text = self.pilot_df.to_string(formatters=self.formatter())
        self.ids.scroll_pilots.text = text
        values = ['Choose transfer model']
        if not self.pilot_df.empty:
            values += self.pilot_df['Name'].tolist()
        self.ids.transfer_spinner.values = values

    @staticmethod
    def formatter():
        def time_fmt(t):
            fmt = '%Y-%m-%d %H:%M:%S'
            return datetime.fromtimestamp(t).strftime(format=fmt)

        def transfer_fmt(model_name):
            return model_name.replace('.h5', '')

        return {'Time': time_fmt, 'Transfer': transfer_fmt}


class CarScreen(Screen):
    """ Screen for interacting with the car. """
    config = ObjectProperty(force_dispatch=True, allownone=True)
    files = ListProperty()
    car_dir = StringProperty(rc_handler.data.get('robot_car_dir', '~/mycar'))
    pull_bar = NumericProperty(0)
    push_bar = NumericProperty(0)
    event = ObjectProperty(None, allownone=True)
    connection = ObjectProperty(None, allownone=True)
    pid = NumericProperty(None, allownone=True)
    pilots = ListProperty()
    is_connected = BooleanProperty(False)

    def initialise(self):
        self.event = Clock.schedule_interval(self.connected, 3)

    def list_remote_dir(self, dir):
        if self.is_connected:
            cmd = f'ssh {self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}' + \
                  f' "ls {dir}"'
            listing = os.popen(cmd).read()
            adjusted_listing = listing.split('\n')[1:-1]
            return adjusted_listing
        else:
            return []

    def list_car_dir(self, dir):
        self.car_dir = dir
        self.files = self.list_remote_dir(dir)
        # non-empty director found
        if self.files:
            rc_handler.data['robot_car_dir'] = dir

    def update_pilots(self):
        model_dir = os.path.join(self.car_dir, 'models')
        self.pilots = self.list_remote_dir(model_dir)

    def pull(self, tub_dir):
        target = f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}' + \
               f':{os.path.join(self.car_dir, tub_dir)}'
        if self.ids.create_dir.state == 'normal':
            target += '/'
        dest = self.config.DATA_PATH
        cmd = ['rsync', '-rv', '--progress', '--partial', target, dest]
        Logger.info('car pull: ' + str(cmd))
        proc = Popen(cmd, shell=False, stdout=PIPE, text=True,
                     encoding='utf-8', universal_newlines=True)
        repeats = 100
        call = partial(self.show_progress, proc, repeats, True)
        event = Clock.schedule_interval(call, 0.0001)

    def send_pilot(self):
        src = self.config.MODELS_PATH
        cmd = ['rsync', '-rv', '--progress', '--partial', src,
               f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}:' +
               f'{self.car_dir}']
        Logger.info('car push: ' + ' '.join(cmd))
        proc = Popen(cmd, shell=False, stdout=PIPE,
                     encoding='utf-8', universal_newlines=True)
        repeats = 1
        call = partial(self.show_progress, proc, repeats, False)
        event = Clock.schedule_interval(call, 0.0001)

    def show_progress(self, proc, repeats, is_pull, e):
        if proc.poll() is not None:
            # call ended this stops the schedule
            return False
        # find the next repeats lines with update info
        count = 0
        while True:
            stdout_data = proc.stdout.readline()
            if stdout_data:
                # find 'to-check=33/4551)' which is end of line
                pattern = 'to-check=(.*)\)'
                res = re.search(pattern, stdout_data)
                if res:
                    if count < repeats:
                        count += 1
                    else:
                        remain, total = tuple(res.group(1).split('/'))
                        bar = 100 * (1. - float(remain) / float(total))
                        if is_pull:
                            self.pull_bar = bar
                        else:
                            self.push_bar = bar
                        return True
            else:
                # end of stream command completed
                if is_pull:
                    button = self.ids['pull_tub']
                    self.pull_bar = 0
                else:
                    button = self.ids['send_pilots']
                    self.push_bar = 0
                    self.update_pilots()
                button.disabled = False
                return False

    def connected(self, event):
        if not self.config:
            return
        if self.connection is None:
            if not hasattr(self.config, 'PI_USERNAME') or \
                    not hasattr(self.config, 'PI_HOSTNAME'):
                self.ids.connected.text = 'Requires PI_USERNAME, PI_HOSTNAME'
                return
            # run new command to check connection status
            cmd = ['ssh',
                   '-o ConnectTimeout=3',
                   f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}',
                   'date']
            Logger.info('car check: ' + ' '.join(cmd))
            self.connection = Popen(cmd, shell=False, stdout=PIPE, text=True,
                                    encoding='utf-8', universal_newlines=True)
        else:
            # ssh is already running, check where we are
            return_val = self.connection.poll()
            self.is_connected = False
            if return_val is None:
                # command still running, do nothing and check next time again
                status = 'Awaiting connection...'
                self.ids.connected.color = 0.8, 0.8, 0.0, 1
            else:
                # command finished, check if successful and reset connection
                if return_val == 0:
                    status = 'Connected'
                    self.ids.connected.color = 0, 0.9, 0, 1
                    self.is_connected = True
                else:
                    status = 'Disconnected'
                    self.ids.connected.color = 0.9, 0, 0, 1
                self.connection = None
            self.ids.connected.text = status

    def drive(self):
        model_args = ''
        if self.ids.pilot_spinner.text != 'No pilot':
            model_path = os.path.join(self.car_dir, "models",
                                      self.ids.pilot_spinner.text)
            model_args = f'--type {self.ids.type_spinner.text} ' + \
                         f'--model {model_path}'
        cmd = ['ssh',
               f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}',
               f'source env/bin/activate; cd {self.car_dir}; ./manage.py '
               f'drive {model_args} 2>&1']
        Logger.info(f'car connect: {cmd}')
        proc = Popen(cmd, shell=False, stdout=PIPE, text=True,
                     encoding='utf-8', universal_newlines=True)
        while True:
            stdout_data = proc.stdout.readline()
            if stdout_data:
                # find 'PID: 12345'
                pattern = 'PID: .*'
                res = re.search(pattern, stdout_data)
                if res:
                    try:
                        self.pid = int(res.group(0).split('PID: ')[1])
                        Logger.info(f'car connect: manage.py drive PID: '
                                    f'{self.pid}')
                    except Exception as e:
                        Logger.error(f'car connect: {e}')
                    return
                Logger.info(f'car connect: {stdout_data}')
            else:
                return

    def stop(self):
        if self.pid:
            cmd = f'ssh {self.config.PI_USERNAME}@{self.config.PI_HOSTNAME} '\
                  + f'kill {self.pid}'
            out = os.popen(cmd).read()
            Logger.info(f"car connect: Kill PID {self.pid} + {out}")
            self.pid = None


class StartScreen(Screen):
    img_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__),
        '../parts/web_controller/templates/static/donkeycar-logo-sideways.png'))
    pass


class DonkeyApp(App):
    start_screen = None
    tub_screen = None
    train_screen = None
    pilot_screen = None
    car_screen = None
    title = 'Donkey Manager'

    def initialise(self, event):
        self.tub_screen.ids.config_manager.load_action()
        self.pilot_screen.initialise(event)
        self.car_screen.initialise()
        # This builds the graph which can only happen after everything else
        # has run, therefore delay until the next round.
        Clock.schedule_once(self.tub_screen.ids.tub_loader.update_tub)

    def build(self):
        self.start_screen = StartScreen(name='donkey')
        self.tub_screen = TubScreen(name='tub')
        self.train_screen = TrainScreen(name='train')
        self.pilot_screen = PilotScreen(name='pilot')
        self.car_screen = CarScreen(name='car')
        Window.bind(on_keyboard=self.tub_screen.on_keyboard)
        Window.bind(on_keyboard=self.pilot_screen.on_keyboard)
        Clock.schedule_once(self.initialise)
        sm = ScreenManager()
        sm.add_widget(self.start_screen)
        sm.add_widget(self.tub_screen)
        sm.add_widget(self.train_screen)
        sm.add_widget(self.pilot_screen)
        sm.add_widget(self.car_screen)
        return sm


def main():
    tub_app = DonkeyApp()
    tub_app.run()


if __name__ == '__main__':
    main()
