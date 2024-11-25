# framework/activity_loader.py

import os
import importlib
from framework.activity_decorator import activity_wrapper

def load_activities(directory=None):
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), '..', 'activities')
    activity_functions = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(os.path.relpath(module_path, directory))[0].replace(os.sep, '.')
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                activity_name = os.path.splitext(file)[0]
                # Apply the decorator to the activity function
                activity_func = activity_wrapper(module.run)
                activity_functions[activity_name] = activity_func
    return activity_functions
