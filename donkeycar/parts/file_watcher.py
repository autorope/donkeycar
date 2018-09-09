import os

class FileWatcher(object):
    '''
    Watch a specific file, like the model file, and give a callback
    when it changes. Will also return a flag to notify that file changed.
    This flag will persist for a time so it can be used as a signal
    '''

    def __init__(self, filename, callback_fn, wait_for_write_stop=10.0):
        self.m_time = os.path.getmtime(filename)
        self.callback_fn = callback_fn
        self.filename = filename
        self.delay = 0.0
        self.wait_for_write_stop = wait_for_write_stop
        self.file_changed = 0

    def run(self):
        '''
        return True when file changed
        '''

        m_time = os.path.getmtime(self.filename)

        if self.delay > 0.0:
            self.delay -= 0.05

            if self.delay <= 0.0:
                self.callback_fn(self.filename)

        if m_time != self.m_time:
            self.m_time = m_time
            
            if self.delay <= 0.0:
                self.delay = self.wait_for_write_stop
                self.file_changed = 100
        
        if self.file_changed > 0:
            self.file_changed -= 1

        return self.file_changed != 0

    def shutdown(self):
        pass


