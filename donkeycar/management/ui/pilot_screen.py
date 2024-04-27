from copy import copy #, deepcopy
import os

from kivy import Logger
from kivy.properties import StringProperty, ObjectProperty, ListProperty, \
    NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup

from donkeycar.management.base import ShowPredictionPlots
from donkeycar.management.ui.common import FileChooserBase, \
    FullImage, get_app_screen, get_norm_value, LABEL_SPINNER_TEXT, AppScreen, \
    status, BackgroundBoxLayout, RoundedButton, MyLabel
from donkeycar.management.ui.rc_file_handler import rc_handler
from donkeycar.parts.image_transformations import ImageTransformations
from donkeycar.pipeline.augmentations import ImageAugmentation
from donkeycar.utils import get_model_by_type


ALL_FILTERS = ['*.h5', '*.tflite', '*.savedmodel', '*.trt']


class PilotLoader(BoxLayout, FileChooserBase):
    """ Class to manage loading of the config file from the car directory"""
    model_type = StringProperty()
    pilot = ObjectProperty(None)
    is_loaded = BooleanProperty(False)
    filters = copy(ALL_FILTERS)

    def load_action(self):
        def remove_pilot_from_db(entry):
            if entry in rc_handler.data['pilots']:
                rc_handler.data['pilots'].remove(entry)

        if self.file_path and self.pilot:
            entry = [self.file_path, self.model_type]
            try:
                self.pilot.load(os.path.join(self.file_path))
                self.is_loaded = True
                self.ids.pilot_spinner.text = self.model_type
                # if successfully loaded, add to rc file
                if entry not in rc_handler.data['pilots']:
                    rc_handler.data['pilots'].append(entry)
                Logger.info(f'Pilot: Successfully loaded {self.file_path}')
            except FileNotFoundError:
                Logger.error(f'Pilot: Model {self.file_path} not found')
                remove_pilot_from_db(entry)
            except Exception as e:
                Logger.error(f'Failed loading {self.file_path}: {e}')
                remove_pilot_from_db(entry)

    def on_model_type(self, obj, model_type):
        """ Kivy method that is called if self.model_type changes. """
        if self.model_type and self.model_type != 'Model type':
            # we cannot use get_app_screen() here as the app is not
            # completely build when we are entering this the first time
            tub_screen = get_app_screen('tub')
            cfg = tub_screen.ids.config_manager.config if tub_screen else None
            if not cfg:
                return
            try:
                self.root_path = cfg.MODELS_PATH
                self.pilot = get_model_by_type(self.model_type, cfg)
                self.ids.pilot_button.disabled = False
                if 'tflite' in self.model_type:
                    self.filters = ['*.tflite']
                elif 'tensorrt' in self.model_type:
                    self.filters = ['*.trt', '*.savedmodel']
                else:
                    self.filters = ['*.h5', '*.savedmodel']
            except Exception as e:
                status(f'Error: {e}')

    def remove_from_rcfile(self):
        if not self.is_loaded:
            return
        entry = [self.file_path, self.model_type]
        if entry in rc_handler.data['pilots']:
            rc_handler.data['pilots'].remove(entry)


class OverlayImage(FullImage):
    """ Widget to display the image and the user/pilot data for the tub. """
    pilot_loader = ObjectProperty()
    pilot_record = ObjectProperty()
    throttle_field = StringProperty('user/throttle')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_left = True

    def augment(self, img_arr):
        pilot_screen = get_app_screen('pilot')
        if pilot_screen.trans_list:
            img_arr = pilot_screen.transformation.run(img_arr)
        if pilot_screen.aug_list:
            img_arr = pilot_screen.augmentation.run(img_arr)
        if pilot_screen.post_trans_list:
            img_arr = pilot_screen.post_transformation.run(img_arr)
        return img_arr

    def get_image(self, record):
        from donkeycar.management.makemovie import MakeMovie
        config = get_app_screen('tub').ids.config_manager.config
        orig_img_arr = super().get_image(record)
        aug_img_arr = self.augment(orig_img_arr)
        img_arr = copy(aug_img_arr)
        angle = record.underlying['user/angle']
        throttle = get_norm_value(
            record.underlying[self.throttle_field], config,
            rc_handler.field_properties[self.throttle_field])
        rgb = (0, 255, 0)
        MakeMovie.draw_line_into_image(angle, throttle, False, img_arr, rgb)
        if not self.pilot_loader.is_loaded:
            return img_arr
        output = (0, 0)
        try:
            # Not each model is supported in each interpreter
            output = self.pilot_loader.pilot.run(aug_img_arr)
        except Exception as e:
            Logger.error(e)

        rgb = (0, 0, 255)
        MakeMovie.draw_line_into_image(output[0], output[1], True, img_arr, rgb)
        out_record = copy(record)
        out_record.underlying['pilot/angle'] = output[0]
        # rename and denormalise the throttle output
        pilot_throttle_field \
            = rc_handler.data['user_pilot_map'][self.throttle_field]
        out_record.underlying[pilot_throttle_field] \
            = get_norm_value(output[1],
                             config,
                             rc_handler.field_properties[self.throttle_field],
                             normalised=False)
        self.pilot_record = out_record
        return img_arr


class TransformationPopup(Popup):
    """ Transformation popup window"""
    title = StringProperty()
    transformations = \
        ["TRAPEZE", "CROP", "RGB2BGR", "BGR2RGB", "RGB2HSV", "HSV2RGB",
         "BGR2HSV", "HSV2BGR", "RGB2GRAY", "RBGR2GRAY", "HSV2GRAY", "GRAY2RGB",
         "GRAY2BGR", "CANNY", "BLUR", "RESIZE", "SCALE", "GAMMANORM"]
    transformations_obj = ObjectProperty()
    selected = ListProperty()
    right = BooleanProperty()

    def __init__(self, selected, **kwargs):
        super().__init__(**kwargs)
        for t in self.transformations:
            btn = RoundedButton(text=t)
            btn.bind(on_release=self.toggle_transformation)
            self.ids.trafo_list.add_widget(btn)
        self.selected = selected

    def toggle_transformation(self, btn):
        trafo = btn.text
        if trafo in self.selected:
            self.selected.remove(trafo)
        else:
            self.selected.append(trafo)

    def on_selected(self, obj, select):
        self.ids.selected_list.clear_widgets()
        for l in self.selected:
            lab = MyLabel(text=l)
            self.ids.selected_list.add_widget(lab)
        self.transformations_obj.selected = self.selected


class Transformations(RoundedButton):
    """ Base class for transformation widgets"""
    title = StringProperty(None)
    pilot_screen = ObjectProperty()
    is_post = False
    selected = ListProperty()

    def open_popup(self):
        popup = TransformationPopup(title=self.title, transformations_obj=self,
                                    selected=self.selected, right=self.is_post)
        popup.open()

    def on_selected(self, obj, select):
        Logger.info(f"Selected {select}")
        if self.is_post:
            self.pilot_screen.post_trans_list = self.selected
        else:
            self.pilot_screen.trans_list = self.selected


class PilotViewer(BackgroundBoxLayout):
    screen = ObjectProperty()
    current_user_field = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ids.data_panel.ids.data_spinner.disabled = True
        # for any new create viewer, copy the user fields over
        for field in self.screen.ids.data_in.labels.keys():
            self.current_user_field = field

    def update(self, record):
        self.ids.img.update(record)

    def map_pilot_field(self, text):
        """ Method to return user -> pilot mapped fields except for the
            initial value called Add/remove. """
        if text == LABEL_SPINNER_TEXT:
            return text
        return rc_handler.data['user_pilot_map'][text]

    def remove_from_rcfile(self):
        self.ids.pilot_loader.remove_from_rcfile()


class PilotBoard(GridLayout):
    screen = ObjectProperty()

    def add_viewer(self):
        viewer = PilotViewer(screen=self.screen)
        self.add_widget(viewer)
        return viewer

    def remove_viewer(self, viewer):
        viewer.remove_from_rcfile()
        self.remove_widget(viewer)

    def get_pilot_names(self):
        return [c.ids.pilot_loader.file_path for c in self.children]


class TubplotPopup(Popup):
    screen = ObjectProperty()


class Tubplot(RoundedButton):

    def open_popup(self, screen):
        popup = TubplotPopup(title='Tub Plot', screen=screen)
        popup.open()


class PilotScreen(AppScreen):
    """ Screen to do the pilot vs pilot comparison ."""
    index = NumericProperty(None, force_dispatch=True)
    current_record = ObjectProperty(None)
    aug_list = ListProperty(force_dispatch=True)
    augmentation = ObjectProperty()
    trans_list = ListProperty(force_dispatch=True)
    transformation = ObjectProperty()
    post_trans_list = ListProperty(force_dispatch=True)
    post_transformation = ObjectProperty()
    config = ObjectProperty(allownone=True)

    def on_index(self, obj, index):
        """ Kivy method that is called if self.index changes. Here we update
            self.current_record and the slider value. """
        if get_app_screen('tub').ids.tub_loader.records:
            self.current_record \
                = get_app_screen('tub').ids.tub_loader.records[index]
            self.ids.slider.value = index

    def on_current_record(self, obj, record):
        """ Kivy method that is called when self.current_index changes. Here
            we update the images and the control panel entry."""
        if not record:
            return
        i = record.underlying['_index']
        self.ids.pilot_control.record_display = f"Record {i:06}"
        for c in self.ids.pilot_board.children:
            c.update(record)

    def on_config(self, obj, cfg):
        if not self.config:
            return
        try:
            for c in self.ids.pilot_board.children:
                c.ids.pilot_loader.root_path = self.config.MODELS_PATH
        except Exception as e:
            Logger.error(f'Error at config update in train screen: {e}')

    def initialise(self, e):
        # self.ids.pilot_board.add_viewer()
        for entry in rc_handler.data.get('pilots', []):
            model_path = entry[0]
            model_type = entry[1]
            viewer = self.ids.pilot_board.add_viewer()
            viewer.ids.pilot_loader.model_type = model_type
            viewer.ids.pilot_loader.file_path = model_path
            viewer.ids.pilot_loader.load_action()

        mapping = rc_handler.data['user_pilot_map']
        self.ids.data_in.ids.data_spinner.values = mapping.keys()

    def set_brightness(self, val=None):
        if not self.config:
            return
        if self.ids.button_bright.state == 'down':
            self.config.AUG_BRIGHTNESS_RANGE = (val, val)
            if 'BRIGHTNESS' not in self.aug_list:
                self.aug_list.append('BRIGHTNESS')
            else:
                # Since we only changed the content of the config here,
                # self.on_aug_list() would not be called, but we want to update
                # the augmentation. Hence, update the dependency manually here.
                self.on_aug_list(None, None)
        elif 'BRIGHTNESS' in self.aug_list:
            self.aug_list.remove('BRIGHTNESS')

    def set_blur(self, val=None):
        if not self.config:
            return
        if self.ids.button_blur.state == 'down':
            self.config.AUG_BLUR_RANGE = (val, val)
            if 'BLUR' not in self.aug_list:
                self.aug_list.append('BLUR')
        elif 'BLUR' in self.aug_list:
            self.aug_list.remove('BLUR')
        # update dependency
        self.on_aug_list(None, None)

    def on_aug_list(self, obj, aug_list):
        if not self.config:
            return
        # cast to python list, otherwise we have an ObservableList in the config
        self.config.AUGMENTATIONS = list(self.aug_list)
        self.augmentation = ImageAugmentation(
            self.config, 'AUGMENTATIONS', always_apply=True)
        self.on_current_record(None, self.current_record)

    def on_trans_list(self, obj, trans_list):
        if not self.config:
            return
        # cast to python list, otherwise we have an ObservableList in the config
        self.config.TRANSFORMATIONS = list(self.trans_list)
        self.transformation = ImageTransformations(
            self.config, 'TRANSFORMATIONS')
        self.on_current_record(None, self.current_record)

    def on_post_trans_list(self, obj, trans_list):
        if not self.config:
            return
        # cast to python list, otherwise we have an ObservableList in the config
        self.config.POST_TRANSFORMATIONS = list(self.post_trans_list)
        self.post_transformation = ImageTransformations(
            self.config, 'POST_TRANSFORMATIONS')
        self.on_current_record(None, self.current_record)

    def set_mask(self, state):
        if state == 'down':
            status('Trapezoidal mask on')
            self.trans_list.append('TRAPEZE')
        else:
            status('Trapezoidal mask off')
            if 'TRAPEZE' in self.trans_list:
                self.trans_list.remove('TRAPEZE')

    def set_crop(self, state):
        if state == 'down':
            status('Crop on')
            self.trans_list.append('CROP')
        else:
            status('Crop off')
            if 'CROP' in self.trans_list:
                self.trans_list.remove('CROP')

    def tub_plot(self, model_path, limit):
        model_type = None
        for c in self.ids.pilot_board.children:
            if c.ids.pilot_loader.file_path == model_path:
                model_type = c.ids.pilot_loader.model_type
        assert model_type, f"Could not find{model_path} in pilot display"
        ShowPredictionPlots().plot_predictions(
            cfg=self.config,
            tub_paths=get_app_screen('tub').ids.tub_loader.file_path,
            model_path=model_path,
            limit=limit,
            model_type=model_type,
            noshow=False,
            dark=True)

    def on_keyboard(self, keyboard, scancode, text=None, modifier=None):
        self.ids.pilot_control.on_keyboard(keyboard, scancode, text, modifier)
