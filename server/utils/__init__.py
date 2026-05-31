# utils/__init__.py
# This file is the initializer for the utils package in the Synora Studio. It imports utility functions and constants that are used throughout the application.  

from server.utils.constants import APP_NAME, APP_VERSION, APP_AUTHOR
from server.utils.helpers import format_timestamp, truncate_text
from server.utils.path_utils import get_resource_path 
