import sys

from .store import template_store as _impl

sys.modules[__name__] = _impl
