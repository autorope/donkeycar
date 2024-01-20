import os
import re
from functools import partial
from subprocess import Popen, PIPE, STDOUT

from kivy import Logger
from kivy.clock import Clock
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, \
    ListProperty, BooleanProperty

from donkeycar.management.ui.common import get_app_screen, AppScreen, status
from donkeycar.management.ui.rc_file_handler import rc_handler


class CarScreen(AppScreen):
    """ Screen for interacting with the car. """
    config = ObjectProperty(force_dispatch=True, allownone=True)
    files = ListProperty()
    car_dir = StringProperty(rc_handler.data.get('robot_car_dir', '~/mycar'))
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
        # non-empty, if directory found
        if self.files:
            rc_handler.data['robot_car_dir'] = dir
            status(f'Successfully loaded directory: {dir}')

    def update_pilots(self):
        model_dir = os.path.join(self.car_dir, 'models')
        self.pilots = self.list_remote_dir(model_dir)

    def pull(self, tub_dir):
        target = f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}' + \
               f':{os.path.join(self.car_dir, tub_dir)}'
        dest = self.config.DATA_PATH
        if not self.ids.create_dir.active:
            target += '/'
        cmd = ['rsync', '-rv', '--progress', '--partial', target, dest]
        Logger.info('car pull: ' + str(cmd))
        proc = Popen(cmd, shell=False, stdout=PIPE, text=True,
                     encoding='utf-8', universal_newlines=True)
        repeats = 100
        call = partial(self.show_progress, proc, repeats, True)
        event = Clock.schedule_interval(call, 0.0001)

    def send_pilot(self):
        # add trailing '/'
        src = os.path.join(self.config.MODELS_PATH, '')
        # check if any sync buttons are pressed and update path accordingly
        buttons = ['h5', 'savedmodel', 'tflite', 'trt']
        select = [btn for btn in buttons if self.ids[f'btn_{btn}'].state
                  == 'down']
        # build filter: for example this rsyncs all .tfilte and .trt models
        # --include=*.trt/*** --include=*.tflite --exclude=*
        filter = ['--include=database.json']
        for ext in select:
            if ext in ['savedmodel', 'trt']:
                ext += '/***'
            filter.append(f'--include=*.{ext}')
        # if nothing selected, sync all
        if not select:
            filter.append('--include=*')
        else:
            filter.append('--exclude=*')
        dest = f'{self.config.PI_USERNAME}@{self.config.PI_HOSTNAME}:' + \
               f'{os.path.join(self.car_dir, "models")}'
        cmd = ['rsync', '-rv', '--progress', '--partial', *filter, src, dest]
        Logger.info('car push: ' + ' '.join(cmd))
        proc = Popen(cmd, shell=False, stdout=PIPE,
                     encoding='utf-8', universal_newlines=True)
        repeats = 0
        call = partial(self.show_progress, proc, repeats, False)
        event = Clock.schedule_interval(call, 0.0001)

    def show_progress(self, proc, repeats, is_pull, e):
        # find 'to-check=33/4551)' in OSX or 'to-chk=33/4551)' in
        # Linux which is end of line
        pattern = 'to-(check|chk)=(.*)\)'

        def end():
            # call ended this stops the schedule
            if is_pull:
                button = self.ids.pull_tub
                self.ids.pull_bar.value = 0
                # merge in previous deleted indexes which now might have been
                # overwritten
                old_tub = get_app_screen('tub').ids.tub_loader.tub
                if old_tub:
                    deleted_indexes = old_tub.manifest.deleted_indexes
                    get_app_screen('tub').ids.tub_loader.update_tub()
                    if deleted_indexes:
                        new_tub = get_app_screen('tub').ids.tub_loader.tub
                        new_tub.manifest.add_deleted_indexes(deleted_indexes)
            else:
                button = self.ids.send_pilots
                self.ids.push_bar.value = 0
                self.update_pilots()
            button.disabled = False

        if proc.poll() is not None:
            end()
            return False
        # find the next repeats lines with update info
        count = 0
        while True:
            stdout_data = proc.stdout.readline()
            if stdout_data:
                res = re.search(pattern, stdout_data)
                if res:
                    if count < repeats:
                        count += 1
                    else:
                        remain, total = tuple(res.group(2).split('/'))
                        bar = 100 * (1. - float(remain) / float(total))
                        if is_pull:
                            self.ids.pull_bar.value = bar
                        else:
                            self.ids.push_bar.value = bar
                        return True
            else:
                # end of stream command completed
                end()
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
            self.connection = Popen(cmd, shell=False, stdout=PIPE,
                                    stderr=STDOUT, text=True,
                                    encoding='utf-8', universal_newlines=True)
        else:
            # ssh is already running, check where we are
            return_val = self.connection.poll()
            self.is_connected = False
            if return_val is None:
                # command still running, do nothing and check next time again
                msg = 'Awaiting connection to...'
                self.ids.connected.color = 0.8, 0.8, 0.0, 1
            else:
                # command finished, check if successful and reset connection
                if return_val == 0:
                    msg = 'Connected to'
                    self.ids.connected.color = 0, 0.9, 0, 1
                    self.is_connected = True
                else:
                    msg = 'Disconnected from'
                    self.ids.connected.color = 0.9, 0, 0, 1
                self.connection = None
            self.ids.connected.text \
                = f'{msg} {getattr(self.config, "PI_HOSTNAME")}'

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
                  + f'kill -SIGINT {self.pid}'
            out = os.popen(cmd).read()
            Logger.info(f"car connect: Kill PID {self.pid} + {out}")
            self.pid = None
