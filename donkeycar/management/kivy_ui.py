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


Builder.load_file('ui.kv')
Window.clearcolor = (0.2, 0.2, 0.2, 1)
HEIGHT = 60
rc_handler = RcFileHandler()


class FileChooserPopup(Popup):
    load = ObjectProperty()
    root_path = os.path.expanduser('~')


class FileChooserBase:
    file_path = StringProperty("No file chosen")
    the_popup = ObjectProperty(None)

    def open_popup(self):
        self.the_popup = FileChooserPopup(load=self.load)
        self.the_popup.open()

    def load(self, selection):
        self.file_path = str(selection[0])
        self.the_popup.dismiss()
        print(self.file_path)
        self.load_action()

    def load_action(self):
        pass


class ConfigManager(BoxLayout, FileChooserBase):
    """ Class to mange loading of the config file from the car directory"""
    config = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.car_dir = rc_handler.data.get('car_dir')

    def update_config(self):
        if self.car_dir:
            try:
                self.config = load_config(os.path.join(self.car_dir, 'config.py'))
                # self.parent.parent.ids.tub_manager.ids.tub_button.disabled =
                # False
                return True
            except FileNotFoundError:
                print(f'Directory {self.car_dir} has no config.py')
            except Exception as e:
                print(e)
            return False

    def load_action(self):
        self.car_dir = self.file_path
        if self.update_config():
            # self.ids.car_dir.text = self.car_dir
            rc_handler.data['car_dir'] = self.car_dir


class TubManager(BoxLayout):
    pass


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

    def set_texture(self, i=0):
        source = f'/Users/dirk/mycar/data2/tub_53/images/' \
                 f'{i}_cam_image_array_.jpg'
        image = PilImage.open(source)
        bytes_io = io.BytesIO()
        image.save(bytes_io, format='png')
        bytes_io.seek(0)
        core_img = CoreImage(bytes_io, ext='png')
        self.texture = core_img.texture

    def update(self, index):
        self.set_texture(index)


class ControlPanel(GridLayout):
    pass


class TubEditor(BoxLayout):
    pass


class TubFilter(BoxLayout):
    pass


class UiLayout(BoxLayout):
    index = NumericProperty(0)

    def on_index(self, obj, val):
        self.ids.img.update(val)


class TubApp(App):
    def __init__(self):
        super().__init__(title='Tub Manager')
        self.layout = UiLayout()

    def build(self):
        return self.layout


if __name__ == '__main__':
    tub_app = TubApp()
    tub_app.run()
