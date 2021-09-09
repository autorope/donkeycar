# -*- coding: utf-8 -*-
"""
Created on Wed Sep 13 21:27:44 2017

@author: wroscoe
"""
import os
import types
import ast
from logging import getLogger

class Config:
    
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

def load_config(config_path=None, myconfig="myconfig.py"):
    """
    There's an ability to read config variables from env

    Usage example:

    `DONKEYCAR_CFG_MAX_LOOPS=2000 python manage.py drive`

    this command will override config variable MAX_LOOPS and set it to 2000
    this is the equivalent of having MAX_LOOPS=2000 in the myconfig.py
    """

    if config_path is None:
        import __main__ as main
        main_path = os.path.dirname(os.path.realpath(main.__file__))
        config_path = os.path.join(main_path, 'config.py')
        if not os.path.exists(config_path):
            local_config = os.path.join(os.path.curdir, 'config.py')
            if os.path.exists(local_config):
                config_path = local_config
    
    logger = getLogger()
    logger.info('loading config file: {}'.format(config_path))
    cfg = Config()
    cfg.from_pyfile(config_path)

    # look for the optional myconfig.py in the same path.
    personal_cfg_path = config_path.replace("config.py", myconfig)
    if os.path.exists(personal_cfg_path):
        logger.info("loading personal config over-rides from", myconfig)
        personal_cfg = Config()
        personal_cfg.from_pyfile(personal_cfg_path)
        cfg.from_object(personal_cfg)
    else:
        logger.info("personal config: file not found ", personal_cfg_path)

    # derived settings
    if hasattr(cfg, 'IMAGE_H') and hasattr(cfg, 'IMAGE_W'): 
        cfg.TARGET_H = cfg.IMAGE_H
        cfg.TARGET_W = cfg.IMAGE_W
        if hasattr(cfg, 'IMAGE_DEPTH'):
            cfg.TARGET_D = cfg.IMAGE_DEPTH

    # from env
    for attr in dir(cfg):
        if attr.isupper():
            cfg_name = f'DONKEYCAR_CFG_{attr}'
            new_value = os.getenv(cfg_name)
            if new_value is not None:
                old_val = getattr(cfg, attr)
                new_value_casted = ast.literal_eval(new_value)
                attr_type = type(new_value_casted)
                setattr(cfg, attr, new_value_casted)
                logger.info(f'Set cfg var from env: {attr}={new_value} (type={attr_type} old_val={old_val})')

    return cfg
