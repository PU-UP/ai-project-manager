"""产品边界与记录契约的可执行定义（canonical 实现入口）。"""

from app.contracts.intent import classify_intent, load_intent_matrix
from app.contracts.record_guard import validate_record_payload

__all__ = [
    "classify_intent",
    "load_intent_matrix",
    "validate_record_payload",
]
