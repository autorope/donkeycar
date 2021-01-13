#!/usr/bin/env python3
import math
import os
from collections import namedtuple
import tkinter as tk
from tkinter import ttk, filedialog
import time
from threading import Thread
from PIL import ImageTk, Image
import pandas as pd
import yaml
import datetime
import atexit
from abc import abstractmethod

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, \
    NavigationToolbar2Tk
from matplotlib.backend_bases import key_press_handler

from donkeycar import load_config
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord

# Data struct to show tub field in the progress bar, containing the name,
# the name of the maximum value in the config file and if it is centered.
FieldProperty = namedtuple('FieldProperty',
                           ['field', 'max_value_id', 'centered'])


class RcFileHandler:
    """ This handles the config file which stores the data, like the field
        mapping for displaying of bars and last opened car, tub directory. """

    # These entries are expected in every tub, so they don't need to be in
    # the file
    known_entries = [
        FieldProperty('user/angle', '', centered=True),
        FieldProperty('user/throttle', '', centered=False)]

    def __init__(self, file_path='~/.donkeyrc'):
        self.file_path = os.path.expanduser(file_path)
        self.data = self.read_file()
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

    def read_file(self):
        if os.path.exists(self.file_path):
            with open(self.file_path) as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
                print(f'Donkey file {self.file_path} loaded.')
                return data
        else:
            print(f'Donkey file {self.file_path} does not exist.')
            return {}

    def write_file(self):
        if os.path.exists(self.file_path):
            print(f'Donkey file {self.file_path} updated.')
        with open(self.file_path, mode='w') as f:
            now = datetime.datetime.now()
            self.data['time_stamp'] = now
            data = yaml.dump(self.data, f)
            return data


class CurrentState:
    """ State class that is shared between several gui elements, basically
        like a singleton, but for pythonic reasons we create a global mutable
        object instead. Contains the current active TubRecord and its index in
        the record set."""
    def __init__(self):
        self.i = 0
        self.record = None
        self.dependants = list()

    def step(self, fwd=True):
        self.i += 1 if fwd else -1

    def update_all(self):
        for dependant in self.dependants:
            dependant.update()


class RecordDependent:
    """ Base class for gui objects that share the global state"""

    def __init__(self, state):
        self.state = state
        self.state.dependants.append(self)

    @abstractmethod
    def update(self):
        pass

    def update_others(self):
        for dependant in self.state.dependants:
            if dependant != self:
                dependant.update()


def decompose(field):
    """ Function to decompose a string vector field like 'gyroscope_1' into a
        tuple ('gyroscope', 1) """
    field_split = field.split('_')
    if len(field_split) > 1 and field_split[-1].isdigit():
        return '_'.join(field_split[:-1]), int(field_split[-1])
    return field, None


class ConfigLoader:
    """ Class to mange loading of the config file from the car directory"""
    def __init__(self, app, row):
        self.app = app
        self.config = None
        self.car_dir = self.app.rc_handler.data.get('car_dir')
        self.btn_car_dir = tk.Button(self.app.window, text="Car dir",
                                     command=self.browse_car)
        self.btn_car_dir.grid(row=row, column=0, sticky=tk.W, padx=10)
        self.car_dir_label = ttk.Label(self.app.window)
        self.car_dir_label.grid(row=row, column=1, sticky=tk.W)

    def update_config(self):
        if self.car_dir:
            try:
                self.config = load_config(os.path.join(self.car_dir, 'config.py'))
                self.car_dir_label.configure(text=self.car_dir)
                self.app.tub_manager.btn.configure(state=tk.NORMAL)
                return True
            except FileNotFoundError:
                print(f'Directory {self.car_dir} has no config.py')
            except Exception as e:
                print(e)
            return False

    def browse_car(self):
        self.car_dir = filedialog.askdirectory(
            initialdir=os.path.expanduser('~'),
            title="Select the car dir")
        if self.update_config():
            self.app.rc_handler.data['car_dir'] = self.car_dir


class TubManager(RecordDependent):
    """ Class to manage loading or reloading of the Tub from the tub directory.
        Loading triggers many actions on other widgets of the app. """
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.base_path = self.app.rc_handler.data.get('last_tub')
        self.tub = None
        self.records = None
        self.len = 1
        self.btn = tk.Button(self.app.window, text="Tub dir",
                             command=self.browse_tub,
                             state=tk.DISABLED)
        self.btn.grid(row=row, column=2, sticky=tk.W)
        self.label = ttk.Label(self.app.window)
        self.label.grid(row=row, column=3, columnspan=3, sticky=tk.W)

    def browse_tub(self):
        car_dir = self.app.config_loader.car_dir
        start_dir = car_dir if car_dir else os.path.expanduser('~')
        self.base_path = filedialog.askdirectory(initialdir=start_dir,
                                                 title="Select the tub dir")
        self.update_tub()
        self.state.update_all()
        self.app.rc_handler.data['last_tub'] = self.base_path

    def update_tub(self, reload=False):
        if not self.base_path or not self.app.config_loader.config:
            return
        if not os.path.exists(os.path.join(self.base_path, 'manifest.json')):
            self.app.update_status(f'Path {self.base_path} is not a valid tub.')
            return
        try:
            self.tub = Tub(self.base_path)
        except Exception as e:
            self.app.update_status(f'Failed loading tub: {str(e)}')
            return

        # Use filter, this defines the function
        def select(underlying):
            if self.app.tub_manipulator.filter_expression is None:
                return True
            else:
                record = TubRecord(self.app.config_loader.config,
                                   self.tub.base_path, underlying)
                res = eval(self.app.tub_manipulator.filter_expression)
                return res

        self.records = [TubRecord(self.app.config_loader.config,
                                  self.tub.base_path,
                                  record)
                        for record in self.tub if select(record)]
        self.len = len(self.records)
        self.state.i = 0
        self.label.config(text=self.base_path)
        if self.len > 0:
            self.state.record = self.records[self.state.i]
            # update app components, manipulator, slider and plot
            self.app.tub_manipulator.set_lr(is_l=True)
            self.app.tub_manipulator.set_lr(is_l=False)
            # clear bars for new tub only but not for reloading existing tub
            if not reload:
                self.app.data_panel.clear()
            self.app.slider.slider.configure(to=self.len - 1)
            # update graph
            self.app.data_plot.update_dataframe_from_tub()
            msg = f'Loaded tub {self.base_path} with {self.len} records'
        else:
            msg = f'No records in tub {self.base_path}'
        if self.app.tub_manipulator.record_filter:
            msg += f' using filter {self.app.tub_manipulator.record_filter}'
        self.app.update_status(msg)

    def update(self):
        if self.state.i >= self.len:
            self.state.i = 0
        elif self.state.i < 0:
            self.state.i = self.len - 1
        if not self.records:
            return
        self.state.record = self.records[self.state.i]


class TubManipulator(RecordDependent):
    """ UI element to perform tub manipulation, like delete, restore and
        filtering."""
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.lr = [0, 0]
        self.filter_expression = None
        self.record_filter = self.app.rc_handler.data.get('record_filter', '')
        self.btn_set_l = tk.Button(self.app.window, text="Set left index",
                                   command=lambda: self.set_lr(True))
        self.btn_set_r = tk.Button(self.app.window, text="Set right index",
                                   command=lambda: self.set_lr(False))
        self.btn_set_l.grid(row=row, column=0, sticky=tk.W, padx=10)
        self.btn_set_r.grid(row=row, column=1, sticky=tk.W)
        self.lr_txt = tk.StringVar(self.app.window)
        self.lr_txt.set(f'Index range [{self.lr[0]}, {self.lr[1]})')
        self.lr_label = ttk.Label(self.app.window, textvariable=self.lr_txt)
        self.lr_label.grid(row=row, column=2)
        self.btn_del_lr = tk.Button(self.app.window, text="Delete",
                                    command=lambda: self.del_lr(True))
        self.btn_restore_lr = tk.Button(self.app.window, text="Restore",
                                        command=lambda: self.del_lr(False))
        self.btn_del_lr.grid(row=row, column=3)
        self.btn_restore_lr.grid(row=row, column=4, sticky=tk.E)
        self.btn_refresh_tub = tk.Button(self.app.window, text="Reload tub",
                                         command=lambda:
                                         self.app.tub_manager.update_tub(True))
        self.btn_refresh_tub.grid(row=row, column=5, sticky=tk.E, padx=10)
        self.label_filter = tk.Button(text='Set filter',
                                      command=self.update_filter)
        self.label_filter.grid(row=row + 1, column=0, sticky=tk.W, padx=10)
        self.entry_filter_var = tk.StringVar()
        self.entry_filter_var.set(self.record_filter)
        self.entry_filter_var.trace_add("write", self.filter_on_entry)
        self.entry_filter = tk.Entry(self.app.window,
                                     textvariable=self.entry_filter_var)
        self.entry_filter.grid(row=row + 1, column=1, columnspan=5,
                               sticky=tk.NSEW, padx=10)

    def set_lr(self, is_l=True):
        """ Sets left or right range to the current tubrecord index """
        if not self.state.record:
            return
        self.lr[0 if is_l else 1] = self.state.record.underlying['_index']
        self.lr_txt.set(f'Index range [{self.lr[0]}, {self.lr[1]})')
        msg = f'Setting {"left" if is_l else "right"} range, '
        if self.lr[0] < self.lr[1]:
            msg += (f'affecting records inside [{self.lr[0]}, {self.lr[1]}) ' +
                    '- you can affect records outside by setting left > right')
        else:
            msg += (f'affecting records outside ({self.lr[1]}, {self.lr[0]}] ' +
                    '- you can affect records inside by setting left < right')
        self.app.update_status(msg)

    def del_lr(self, is_del):
        """ Deletes or restores records in chosen range """
        if self.lr[1] >= self.lr[0]:
            selected = list(range(*self.lr))
        else:
            last_id = self.app.tub_manager.tub.manifest.current_index
            selected = list(range(self.lr[0], last_id))
            selected += list(range(self.lr[1]))
        if is_del:
            for d in selected:
                self.app.tub_manager.tub.delete_record(d)
            msg = 'Deleting '
        else:
            for d in selected:
                self.app.tub_manager.tub.restore_record(d)
            msg = 'Restoring '
        msg += f'records {self.lr} - press <Reload tub> to see the ' \
               f'effect, but you can select multiple ranges before doing so.'
        self.app.update_status(msg)

    def update_filter(self):
        filter_text = self.entry_filter_var.get()
        # empty string resets the filter
        if filter_text == '':
            self.record_filter = ''
            self.filter_expression = None
            self.app.enable_keys = True
            self.app.rc_handler.data['record_filter'] = self.record_filter
            self.app.update_status(f'Filter cleared')
            return
        filter_expression = self.create_filter_string(filter_text)
        try:
            record = self.state.record
            res = eval(filter_expression)
            status = f'Filter result on current record: {res}'
            if isinstance(res, bool):
                self.record_filter = filter_text
                self.filter_expression = filter_expression
                self.app.rc_handler.data['record_filter'] = self.record_filter
            else:
                status += ' - non bool expression can\'t be applied'
            status += ' - press <Reload tub> to see effect'
            self.app.update_status(status)
        except Exception as e:
            self.app.update_status(f'Filter error on current record: {e}')
        self.app.enable_keys = True

    def filter_on_entry(self, a, b, c):
        self.app.enable_keys = False
        filter_txt = self.entry_filter_var.get()
        self.app.update_status(f'Received filter: {filter_txt} - press <tab> '
                               f'to exit')

    def create_filter_string(self, filter_text, record_name='record'):
        """ Converts text like 'user/angle' into 'record.underlying['user/angle']
        so that it can be used in a filter. Will replace only expressions that
        are found in the tub inputs list.

        :param filter_text: input text like 'user/throttle > 0.1'
        :param record_name: name of the record in the expression
        :return:            updated string that has all input fields wrapped
        """
        for field in self.state.record.underlying.keys():
            field_list = filter_text.split(field)
            if len(field_list) > 1:
                filter_text = f'{record_name}.underlying["{field}"]'\
                    .join(field_list)
        return filter_text

    def update(self):
        pass


class LabelBar:
    """ This class combines a label with a progress bar. It represents a
        single line item in the app's data panel. """
    row = 0

    def __init__(self, app, field, field_property, colwidth=3):
        self.app = app
        self.field = field
        self.text = tk.StringVar()
        self.label = ttk.Label(self.app.data_panel.data_frame,
                               textvariable=self.text, anchor=tk.E,
                               font='TkFixedFont')
        self.label.grid(row=self.row, column=0, sticky=tk.E)
        # only add bar if we have field property data
        self.field_property = field_property
        text = f'Added field {self.field}'
        if self.field_property:
            self.bar_val = tk.DoubleVar()
            self.bar = ttk.Progressbar(self.app.data_panel.data_frame,
                                       variable=self.bar_val,
                                       orient=tk.HORIZONTAL,
                                       length=100, mode='determinate')
            self.bar.grid(row=self.row, column=1, columnspan=colwidth - 1)
            self.max = getattr(self.app.config_loader.config,
                               self.field_property.max_value_id,
                               1.0)
            self.center = self.field_property.centered
            text += f' with max value={self.max} centered={self.center}'
        else:
            text += "... not showing a bar because it is a string field " \
                    "or there is no field list entry in your .donkeyrc"
        LabelBar.row += 1
        self.app.status.configure(text=text)

    def update(self, record):
        field, index = decompose(self.field)
        if field in record.underlying:
            val = record.underlying[field]
            if index is not None:
                val = val[index]
            # update bar if present
            if self.field_property:
                norm_val = val / self.max
                new_bar_val = (norm_val + 1) * 50 if self.center else norm_val * 100
                self.bar_val.set(new_bar_val)
            if isinstance(val, float):
                text = f' {val:+07.3f}'
            elif isinstance(val, int):
                text = f' {val:10}'
            else:
                text = ' ' + val
            self.text.set(self.field + text)
        else:
            print(f'Bad record {self.app.tub_manager.state.i} - missing field '
                  f'{field}')

    def destroy(self):
        self.label.destroy()
        if self.field_property:
            self.bar.destroy()
        LabelBar.row -= 1
        self.app.update_status(f'Removed field {self.field}')


class DataPanel(RecordDependent):
    """ Data panel which allows do dynamically add and remove LabelBars from
        a drop down menu."""
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.bars = dict()
        self.data_frame = tk.LabelFrame(self.app.window, padx=10, pady=10)
        self.data_frame.grid(row=row, column=0, columnspan=2, rowspan=3,
                             padx=10)
        self.label = ttk.Label(self.data_frame, text='Add or remove')
        self.label.grid(row=row, column=0, sticky=tk.W)
        self.menu = ttk.Combobox(self.data_frame, width=12, state='readonly')
        self.menu.bind('<<ComboboxSelected>>', self.add_remove_bars)
        self.menu.grid(row=row, column=1, columnspan=2)
        LabelBar.row = row + 1

    def add_remove_bars(self, inp):
        """ Adds or removes a LabelBar """
        field = self.menu.get()
        field_property = self.app.rc_handler.field_properties.get(
            decompose(field)[0])
        if field in self.bars:
            self.bars[field].destroy()
            del(self.bars[field])
        else:
            self.bars[field] = LabelBar(self.app, field, field_property)
        self.state.update_all()
        self.app.data_plot.plot_from_current_bars()

    def update(self):
        for field, bar in self.bars.items():
            bar.update(self.state.record)

    def clear(self):
        for bar in self.bars.values():
            bar.destroy()
        self.bars.clear()


class ControlPanel(RecordDependent):
    """ Control panel <, > , <<, >> and speed drop down. """
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.speed_settings = ['0.25', '0.50', '1.00', '1.50', '2.00',
                               '3.00', '4.00']
        self.speed = 1.0
        self.frame = tk.LabelFrame(self.app.window, padx=10, pady=10)
        self.frame.grid(row=row, column=4, columnspan=2, rowspan=4, padx=10)
        self.rec_txt = tk.StringVar(self.frame)
        self.record_label = ttk.Label(self.frame, textvariable=self.rec_txt,
                                      font='TkFixedFont')
        self.record_label.grid(row=row, column=0, sticky=tk.E)
        self.speed_var = tk.StringVar(self.frame)
        self.speed_var.set("1.00")
        self.speed_menu = ttk.OptionMenu(self.frame, self.speed_var, '1.00',
                                         *self.speed_settings,
                                         command=self.set_speed)
        self.speed_menu.grid(row=row, column=1)
        self.btn_bwd = tk.Button(self.frame, text="<",
                                 command=lambda: self.app.step(False))
        self.btn_bwd.grid(row=row + 1, column=0, sticky=tk.NSEW)
        self.btn_fwd = tk.Button(self.frame, text=">",
                                 command=lambda: self.app.step(True))
        self.btn_fwd.grid(row=row + 1, column=1, sticky=tk.NSEW)
        self.btn_rwd = tk.Button(self.frame, text="<<",
                                 command=lambda: self.app.thread_run(False))
        self.btn_rwd.grid(row=row + 2, column=0, sticky=tk.NSEW)
        self.btn_play = tk.Button(self.frame, text=">>",
                                  command=lambda: self.app.thread_run(True))
        self.btn_play.grid(row=row + 2, column=1, sticky=tk.NSEW)
        self.btn_stop = tk.Button(self.frame, text="Stop",
                                  state=tk.DISABLED,
                                  command=self.app.thread_stop)
        self.btn_stop.grid(row=row + 3, column=0, columnspan=2, sticky=tk.NSEW)

    def set_speed(self, inp):
        self.speed = float(inp)
        self.app.update_status(f'Setting speed to {inp} - you can also use the '
                               f'+/- keys.')

    def toggle_button_state(self, run_mode=True):
        self.btn_play.config(state=tk.DISABLED if run_mode else tk.NORMAL)
        self.btn_rwd.config(state=tk.DISABLED if run_mode else tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL if run_mode else tk.DISABLED)

    def increase_speed(self):
        i = self.speed_settings.index(self.speed_var.get())
        if i < len(self.speed_settings) - 1:
            self.speed_var.set(self.speed_settings[i + 1])
            self.set_speed(self.speed_var.get())

    def decrease_speed(self):
        i = self.speed_settings.index(self.speed_var.get())
        if i > 0:
            self.speed_var.set(self.speed_settings[i - 1])
            self.set_speed(self.speed_var.get())

    def update(self):
        if not self.state.record:
            return
        index = self.state.record.underlying['_index']
        self.rec_txt.set(f"Record {index:06}")


class DataPlot:
    """ Data plot panel which embeds matplotlib interactive graph"""
    def __init__(self, app, row):
        self.app = app
        self.df = None
        self.figure = Figure(figsize=(6, 4))
        self.graph = FigureCanvasTkAgg(self.figure, self.app.window)
        self.graph.draw()
        self.graph.get_tk_widget().grid(row=row, column=0, columnspan=6,
                                        sticky=tk.NSEW,
                                        padx=10, pady=10)
        self.toolbar = NavigationToolbar2Tk(self.graph, self.app.window,
                                            pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.grid(row=row + 1, column=0, columnspan=5, sticky=tk.W,
                          padx=10)
        self.graph.mpl_connect("key_press_event", self.on_key_press)

    def on_key_press(self, event):
        key_press_handler(event, self.graph, self.toolbar)

    def plot_from_current_bars(self):
        """ Plotting from current selected bars. The DataFrame for plotting
            should contain all bars except for strings fields and all data is
            selected if bars are empty.  """
        field_map = dict(zip(self.app.tub_manager.tub.manifest.inputs,
                             self.app.tub_manager.tub.manifest.types))
        cols = [c for c in self.app.data_panel.bars.keys() if decompose(c)[0] in
                field_map and field_map[decompose(c)[0]] != 'str']
        df = self.df[cols] if cols else self.df
        # Don't plot the milliseconds time stamp as this is a too big number
        df = df.drop(labels=['_timestamp_ms'], axis=1, errors='ignore')
        ax1 = self.figure.add_subplot(111)
        ax1.clear()
        df.plot(kind='line', legend=True, ax=ax1)
        self.graph.draw()

    def unravel_vectors(self):
        """ Unravels vector and list entries in tub which are created
            when the DataFrame is created from a list of records"""
        for k, v in zip(self.app.tub_manager.tub.manifest.inputs,
                        self.app.tub_manager.tub.manifest.types):
            if v == 'vector' or v == 'list':
                dim = len(self.app.tub_manager.state.record.underlying[k])
                df_keys = [k + f'_{i}' for i in range(dim)]
                self.df[df_keys] = pd.DataFrame(self.df[k].tolist(),
                                                index=self.df.index)
                self.df.drop(k, axis=1, inplace=True)

    def update_dataframe_from_tub(self):
        """ Called from TubManager when a tub is reloaded/recreated. Fills
            the DataFrame from records, and updates the dropdown menu in the
            data panel."""
        underlying_generator = (t.underlying for t in
                                self.app.tub_manager.records)
        self.df = pd.DataFrame(underlying_generator).dropna()
        to_drop = {'cam/image_array'}
        self.df.drop(labels=to_drop, axis=1, errors='ignore', inplace=True)
        self.df.set_index('_index', inplace=True)
        self.unravel_vectors()
        self.app.data_panel.menu.config(value=list(self.df.columns))
        self.plot_from_current_bars()


class ImageFrame(RecordDependent):
    """ UI Image element"""
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.image = None
        self.label = tk.Label(app.window, image=None, bg='black',
                              relief=tk.SUNKEN, borderwidth=3)
        self.label.grid(row=row, column=2, columnspan=2, rowspan=3,
                        padx=15, pady=15)

    def update(self):
        try:
            img_arr = self.state.record.image()
            img = Image.fromarray(img_arr)
            self.image = ImageTk.PhotoImage(img)
        except KeyError as e:
            print('Missing key:', e)
        except Exception as e:
            print('Bad record:', e)
        self.label.configure(image=self.image)


class TubSlider(RecordDependent):
    """ UI slider element"""
    def __init__(self, app, row):
        super().__init__(app.current_state)
        self.app = app
        self.being_updated = False
        self.slider = ttk.Scale(self.app.window, from_=0,
                                to=self.app.tub_manager.len-1,
                                orient=tk.HORIZONTAL, command=self.slide)
        self.slider.grid(column=0, columnspan=6, sticky=tk.NSEW, padx=10)

    def slide(self, val):
        """ Callback function for slider"""
        # if we are being updated externally, no need to update others,
        # just reset the state
        if self.being_updated:
            self.being_updated = False
        # else we are sliding, update state and others:
        else:
            self.state.i = int(math.floor(float(val)))
            self.update_others()

    def update(self):
        # This is a bit tricky, because set() will call slide() as the slider
        # is moved by this command. Here we are only being called by other
        # UI elements, hence we set the flag to not update others in slide().
        self.being_updated = True
        self.slider.set(self.state.i)


class TubUI:
    def __init__(self, window, rc_handler):
        self.window = window
        self.rc_handler = rc_handler
        self.window.title("Donkey Tub Manager")
        self.current_state = CurrentState()
        self.run = False
        self.thread = None
        self.enable_keys = True
        # Build the UI - first row config and tub loaders
        row = 0
        self.config_loader = ConfigLoader(self, row)
        self.tub_manager = TubManager(self, row)
        # Data panel, image and control panel
        row += 1
        self.data_panel = DataPanel(self, row)
        self.image_frame = ImageFrame(self, row)
        self.control_panel = ControlPanel(self, row)
        # Slider
        row += 4
        self.slider = TubSlider(self, row)
        # Tub manipulator for delete, restore and filter
        row += 1
        self.tub_manipulator = TubManipulator(self, row)
        # Data plot
        row += 2
        self.data_plot = DataPlot(self, row)
        row += 1
        # quit button
        self.but_exit = tk.Button(self.window, text="Quit", command=self.quit)
        self.but_exit.grid(row=row, column=5, sticky=tk.E)
        # status bar
        row += 1
        self.status = ttk.Label(self.window, text="Donkey ready...")
        self.status.grid(row=row, column=0, columnspan=6, sticky=tk.W)
        # key bindings
        self.window.bind("<Key>", self.handle_char_key)
        self.window.bind("<Left>", self.handle_left_key)
        self.window.bind("<Right>", self.handle_right_key)
        self.window.bind('<Return>', self.set_enable_keys)
        # refresh
        self.config_loader.update_config()
        self.tub_manager.update_tub()
        self.current_state.update_all()

    def set_enable_keys(self, event):
        self.enable_keys = True

    def step(self, fwd=True):
        self.current_state.step(fwd)
        self.current_state.update_all()
        if not self.run:
            msg = f'Donkey step {"forward" if fwd else "backward"} - you can ' \
                  f'use {"<right>" if fwd else "<left>"} key as well.'
            self.update_status(msg)

    def loop(self, fwd=True):
        self.update_status(f'Donkey running... - toggle stop with <space> key')
        while self.run:
            cycle_time = 1.0 / (self.control_panel.speed *
                                self.config_loader.config.DRIVE_LOOP_HZ)
            tic = time.time()
            self.step(fwd)
            toc = time.time()
            delta_time = toc - tic
            if delta_time < cycle_time:
                time.sleep(cycle_time - delta_time)
        self.update_status('Donkey stopped - toggle run with <space> key')

    def thread_run(self, fwd=True):
        self.run = True
        self.thread = Thread(target=self.loop, args=(fwd,))
        self.thread.start()
        self.control_panel.toggle_button_state(True)

    def thread_stop(self):
        self.run = False
        self.control_panel.toggle_button_state(False)

    def update_status(self, msg):
        self.status.configure(text=msg)

    def quit(self):
        self.run = False
        try:
            self.window.destroy()
        except Exception as e:
            print(e)

    def handle_char_key(self, event=None):
        if event.char == '\t':
            self.set_enable_keys(event)
        if not self.enable_keys:
            return
        if event.char == ' ':
            if self.run:
                self.thread_stop()
            else:
                self.thread_run()
        elif event.char == 'q':
            self.quit()
        elif event.char == '+':
            self.control_panel.increase_speed()
        elif event.char == '-':
            self.control_panel.decrease_speed()

    def handle_left_key(self, event=None):
        if self.enable_keys:
            self.step(fwd=False)

    def handle_right_key(self, event=None):
        if self.enable_keys:
            self.step(fwd=True)


def main():
    rc_handler = RcFileHandler()
    window = tk.Tk()
    ui = TubUI(window, rc_handler)
    window.mainloop()


if __name__ == "__main__":
    main()
