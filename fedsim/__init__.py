"""

FedSim
------

Comprehensive but Flexible Federated Learning Simulator!

"""

__version__ = "0.5.0"

from . import datasets
from . import distributed
from . import local
from . import losses
from . import lr_schedulers
from . import models
from . import scores
from . import utils

__all__ = [
    "datasets",
    "distributed",
    "models",
    "local",
    "lr_schedulers",
    "scores",
    "losses",
    "utils",
]
