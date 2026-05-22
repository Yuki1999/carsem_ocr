import sys

from .services import customs_browser as _impl

sys.modules[__name__] = _impl
