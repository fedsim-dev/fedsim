"""

FedSim
------

Comprehensive and flexible Federated Learning Simulator!

"""

__version__ = "0.6.1"

from . import datasets
from . import distributed
from . import local
from . import losses
from . import models
from . import scores
from . import utils

__all__ = [
    "datasets",
    "distributed",
    "models",
    "local",
    "scores",
    "losses",
    "utils",
]
