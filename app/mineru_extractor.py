import sys

from .services import mineru_extractor as _impl

sys.modules[__name__] = _impl
