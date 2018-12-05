#!/usr/bin/python3
# -*- coding: utf-8 -*-

EXIT_CODE_REBOOT = -123456

"""
A collection of miscellaneous utility functions.
"""
import os, shutil
import logging
import inspect
import re

logger = logging.getLogger()
handler = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(levelname)s: (%(module)s, %(lineno)d) -> %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

num_pattern = re.compile(r"[^\s\(\)]+")

def checkdir(dirname):
    """
Сheck the existence of the directory, if there is no then it is created
    """
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def get_class_from_frame(frame):
  args, _, _, value_dict = inspect.getargvalues(frame)

  if len(args) and args[0] == 'self':

    instance = value_dict.get('self', None)
    if instance:
      return getattr(instance, '__class__', None).__name__

  return None

def getCallingClassName(curframe):
    callframe = inspect.getouterframes(curframe, 2)[1][0]
    return get_class_from_frame(callframe)

def move_dirs(src, dst):
    """
Go through the source directory, create any directories that do not already exist in destination directory,
and move files from source to the destination directory.

Any pre-existing files will be removed first.
    """
    for src_dir, dirs, files in os.walk(src):
        dst_dir = src_dir.replace(src, dst, 1)

        checkdir(dst_dir)

        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.move(src_file, dst_dir)

# necessary for path in PyInstaller
def resource_path(relative_path, folder = ""):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(folder)

    return os.path.join(base_path, relative_path)

def sort_dict(diction):
    sort_list = sorted(list(diction.items()), key = lambda x: float(x[0]))

    sort_diction = {}
    for itm in sort_list:
            sort_diction[itm[0]]=itm[1]

    return sort_diction
