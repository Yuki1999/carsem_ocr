import sys

from .services import qwen_vision_extractor as _impl

sys.modules[__name__] = _impl
