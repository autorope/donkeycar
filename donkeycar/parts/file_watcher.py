import os

class FileWatcher(object):
    '''
    Watch a specific file and give a signal when it's modified
    '''

    def __init__(self, filename, verbose=False):
        self.modified_time = os.path.getmtime(filename)
        self.filename = filename
        self.verbose = verbose

    def run(self):
        '''
        return True when file changed. Keep in mind that this does not mean that the 
        file is finished with modification.
        '''
        m_time = os.path.getmtime(self.filename)

        if m_time != self.modified_time:
            self.modified_time = m_time
            if self.verbose:
                print(self.filename, "changed.")
            return True
            
        return False


