import sys

from .services import spatial_extract as _impl

sys.modules[__name__] = _impl
