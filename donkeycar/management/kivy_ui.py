from random import random
from kivy.core.window import Window
from kivy.app import App
from kivy.uix.scatter import Scatter
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.slider import Slider
from kivy.uix.filechooser import FileChooser
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.popup import Popup
from kivy.lang.builder import Builder

import io
import os
from PIL import Image as PilImage

from donkeycar import load_config
from donkeycar.management.tub_gui import RcFileHandler
from donkeycar.parts.tub_v2 import Tub
from donkeycar.pipeline.types import TubRecord


Builder.load_file('ui.kv')
Window.clearcolor = (0.2, 0.2, 0.2, 1)
HEIGHT = 60
rc_handler = RcFileHandler()


class FileChooserPopup(Popup):
    load = ObjectProperty()
    root_path = StringProperty()


class FileChooserBase:
    file_path = StringProperty("No file chosen")
    popup = ObjectProperty(None)
    root_path = os.path.expanduser('~')
    title = StringProperty(None)

    def open_popup(self):
        self.popup = FileChooserPopup(load=self.load,
                                      root_path=self.root_path,
                                      title=self.title)
        self.popup.open()

    def load(self, selection):
        self.file_path = str(selection[0])
        self.popup.dismiss()
        print(self.file_path)
        self.load_action()

    def load_action(self):
        pass


class ConfigManager(BoxLayout, FileChooserBase):
    """ Class to mange loading of the config file from the car directory"""
    config = ObjectProperty(None)
    file_path = rc_handler.data.get('car_dir', '')

    def load_action(self):
        if self.file_path:
            try:
                self.config = load_config(os.path.join(self.file_path, 'config.py'))
                rc_handler.data['car_dir'] = self.file_path
            except FileNotFoundError:
                print(f'Directory {self.file_path} has no config.py')
            except Exception as e:
                print(e)


class TubLoader(BoxLayout, FileChooserBase):
    """ Class to manage loading or reloading of the Tub from the tub directory.
        Loading triggers many actions on other widgets of the app. """
    file_path = rc_handler.data.get('last_tub')
    tub = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.records = None
        self.len = 1

    def load_action(self):
        if self.update_tub(reload=False):
            rc_handler.data['last_tub'] = self.file_path

    def update_tub(self, reload=False):
        if not self.file_path:
            return False
        if not os.path.exists(os.path.join(self.file_path, 'manifest.json')):
            self.parent.parent.status(f'Path {self.file_path} is not a valid '
                                      f'tub.')
            return False
        try:
            self.tub = Tub(self.file_path)
        except Exception as e:
            self.parent.parent.status(f'Failed loading tub: {str(e)}')
            return False

        cfg = self.parent.parent.ids.config_manager.config
        expression = self.parent.parent.ids.tub_filter.filter_expression

        # Use filter, this defines the function
        def select(underlying):
            if expression is None:
                return True
            else:
                record = TubRecord(cfg, self.tub.base_path, underlying)
                res = eval(expression)
                return res

        self.records = [TubRecord(cfg, self.tub.base_path, record)
                        for record in self.tub if select(record)]
        self.len = len(self.records)
        if self.len > 0:
            # self.state.record = self.records[self.state.i]
            # # update app components, manipulator, slider and plot
            # self.app.tub_manipulator.set_lr(is_l=True)
            # self.app.tub_manipulator.set_lr(is_l=False)
            # # clear bars for new tub only but not for reloading existing tub
            # if not reload:
            #     self.app.data_panel.clear()
            # self.app.slider.slider.configure(to=self.len - 1)
            # # update graph
            # self.app.data_plot.update_dataframe_from_tub()
            msg = f'Loaded tub {self.file_path} with {self.len} records'
        else:
            msg = f'No records in tub {self.file_path}'
        if self.parent.parent.ids.tub_filter.record_filter:
            msg += f' using filter {self.parent.parent.ids.tub_filter.record_filter}'
        self.parent.parent.status(msg)
        return True


class LabelBar(BoxLayout):
    i = NumericProperty(0)

    def __init__(self, i, **kwargs):
        super().__init__(**kwargs)
        self.i = i


class DataPanel(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.labels = []
        self.count = 0

    def add_label(self):
        lb = LabelBar(self.count)
        self.labels.append(lb)
        self.add_widget(lb)
        self.count += 1

    def remove_label(self):
        if self.labels:
            self.remove_widget(self.labels[-1])
            self.labels.pop()
            self.count -= 1


class FullImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self, record):
        try:
            img_arr = record.image()
            pil_image = PilImage.fromarray(img_arr)
            bytes_io = io.BytesIO()
            pil_image.save(bytes_io, format='png')
            bytes_io.seek(0)
            core_img = CoreImage(bytes_io, ext='png')
            self.texture = core_img.texture
        except KeyError as e:
            print('Missing key:', e)
        except Exception as e:
            print('Bad record:', e)


class ControlPanel(GridLayout):
    pass


class TubEditor(BoxLayout):
    pass


class TubFilter(BoxLayout):
    filter_expression = StringProperty(None)
    record_filter = StringProperty(None)
    pass


class UiLayout(BoxLayout):
    index = NumericProperty(None)
    current_record = ObjectProperty(None)

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)

    def initialise(self):
        self.ids.config_manager.load_action()
        self.ids.tub_loader.update_tub()
        self.index = 0

    def on_index(self, obj, index):
        self.current_record = self.ids.tub_loader.records[index]

    def on_current_record(self, obj, record):
        self.ids.img.update(record)

    def status(self, msg):
        self.ids.status.text = msg


class TubApp(App):
    def __init__(self):
        super().__init__(title='Tub Manager')
        self.layout = UiLayout()
        self.layout.initialise()

    def build(self):
        return self.layout


if __name__ == '__main__':
    tub_app = TubApp()
    tub_app.run()
