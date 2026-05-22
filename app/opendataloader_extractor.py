import sys

from .services import opendataloader_extractor as _impl

sys.modules[__name__] = _impl
