""".. :noindex cli for a simple Federated Learning simulator!

"""

__version__ = "0.0.2"

import os
import logging

# Set default logging handler to avoid "No handler found" warnings.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# get all classes
__all__ = [
    module[:-3] for module in os.listdir(os.path.dirname(__file__))
    if module != '__init__.py' and module[-3:] == '.py'
]