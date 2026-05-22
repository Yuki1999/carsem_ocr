import sys

from .services import llm_extract as _impl

sys.modules[__name__] = _impl
