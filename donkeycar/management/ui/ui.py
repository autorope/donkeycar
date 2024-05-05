import os
# need to do this before importing anything else
os.environ['KIVY_LOG_MODE'] = 'MIXED'

from kivy.logger import Logger, LOG_LEVELS
from kivy.clock import Clock
from kivy.app import App
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.lang.builder import Builder
from kivy.core.window import Window

from donkeycar.management.ui.car_screen import CarScreen
from donkeycar.management.ui.pilot_screen import PilotScreen
from donkeycar.management.ui.rc_file_handler import rc_handler
from donkeycar.management.ui.train_screen import TrainScreen
from donkeycar.management.ui.tub_screen import TubScreen
from donkeycar.management.ui.common import AppScreen

Logger.setLevel(LOG_LEVELS["info"])
Window.size = (800, 800)


class Header(BoxLayout):
    title = StringProperty()
    description = StringProperty()


class StartScreen(AppScreen):
    img_path = os.path.realpath(os.path.join(
        os.path.dirname(__file__),
        '../../parts/web_controller/templates/'
        'static/donkeycar-logo-sideways.png'))
    pass


class DonkeyApp(App):
    title = 'Donkey Car'

    def initialise(self, event):
        self.root.ids.tub_screen.ids.config_manager.load_action()
        self.root.ids.train_screen.initialise()
        self.root.ids.pilot_screen.initialise(event)
        self.root.ids.car_screen.initialise()
        self.root.ids.tub_screen.ids.tub_loader.update_tub()
        self.root.ids.status.text = 'Donkey ready'

    def build(self):
        # the builder returns the screen manager in ui.kv file
        for kv in ['common.kv', 'tub_screen.kv', 'train_screen.kv',
                   'pilot_screen.kv', 'car_screen.kv', 'ui.kv']:
            dm = Builder.load_file(os.path.join(os.path.dirname(__file__), kv))
        Clock.schedule_once(self.initialise)
        return dm

    def on_stop(self, *args):
        tub = self.root.ids.tub_screen.ids.tub_loader.tub
        if tub:
            tub.close()
        Logger.info("App: Good bye Donkey")


def main():
    DonkeyApp().run()


if __name__ == '__main__':
    main()
