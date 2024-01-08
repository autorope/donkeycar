# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 21:27:44 2017

@author: wroscoe
"""
import os
import types
from logging import getLogger

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

logger = getLogger(__name__)


class Config():
        
    def from_pyfile(self, filename):
        d = types.ModuleType('config')
        d.__file__ = filename
        try:
            with open(filename, mode='rb') as config_file:
                exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
        except IOError as e:
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)
        return True
    
    def from_object(self, obj):
        for key in dir(obj):
            if key.isupper():
                setattr(self, key, getattr(obj, key))
                
    def update_from_object(self, obj):
        for key in dir(obj):
            if key.isupper():
                current = getattr(self, key,None)
                new = getattr(obj, key)
                if current and current != new:
                    print(f"Config : attribute {key} changed from {current} to {new}")
                    setattr(self, key, getattr(obj, key))

    def __str__(self):
        result = []
        for key in dir(self):
            if key.isupper():
                result.append((key, getattr(self, key)))
        return str(result)

    def show(self):
        for attr in dir(self):
            if attr.isupper():
                print(attr, ":", getattr(self, attr))


class PersonnalCfgMonitor(PatternMatchingEventHandler):

    def __init__(self, patterns=None, cfg:Config=None, personal_cfg_path=None):
        super().__init__(patterns) 
        self.cfg=cfg;
        self.personal_cfg_path = personal_cfg_path

    def  on_modified(self,  event):
        personal_cfg = Config()
        personal_cfg.from_pyfile(self.personal_cfg_path)
        self.cfg.update_from_object(personal_cfg)


    
def load_config(config_path=None, myconfig="myconfig.py"):
    

    if config_path is None:
        import __main__ as main
        main_path = os.path.dirname(os.path.realpath(main.__file__))
        config_path = os.path.join(main_path, 'config.py')
        if not os.path.exists(config_path):
            local_config = os.path.join(os.path.curdir, 'config.py')
            if os.path.exists(local_config):
                config_path = local_config
    
    logger.info(f'loading config file: {config_path}')
    
    cfg = Config()    
    cfg.from_pyfile(config_path)

    # look for the optional myconfig.py in the same path.
    personal_cfg_path = config_path.replace("config.py", myconfig)
    if os.path.exists(personal_cfg_path):
        logger.info(f"loading personal config over-rides from {myconfig}")
        personal_cfg = Config()
        personal_cfg.from_pyfile(personal_cfg_path)
        cfg.from_object(personal_cfg)

        personal_cfg_monitor = PersonnalCfgMonitor(patterns=[myconfig], cfg=cfg, personal_cfg_path=personal_cfg_path)
        observer = Observer()
        observer.schedule(personal_cfg_monitor,  personal_cfg_path,  recursive=False)
        observer.start()
    else:
        logger.warning(f"personal config: file not found {personal_cfg_path}")

    return cfg
