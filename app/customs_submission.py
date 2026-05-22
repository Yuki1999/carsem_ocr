import sys

from .services import customs_submission as _impl

sys.modules[__name__] = _impl
