"""Intent matrix 契约测试。

契约来源：docs/product-boundary.md
失败时：修改 app/contracts/intent.py 或 docs/product-boundary.md
"""

import pytest

from app.contracts.intent import CONTRACT_REF, classify_intent, load_intent_matrix


@pytest.fixture(scope="module")
def intent_matrix():
    matrix = load_intent_matrix()
    assert matrix["contract"] == CONTRACT_REF
    return matrix


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(c, id=c["id"])
        for c in load_intent_matrix()["cases"]
    ],
)
def test_intent_matrix_case(case):
    mode = classify_intent(case["user_input"])
    assert mode == case["expected_mode"], (
        f"意图判定错误：输入={case['user_input']!r} "
        f"期望={case['expected_mode']} 实际={mode}；"
        f"修改 app/contracts/intent.py 或 {case['contract_ref']}"
    )


def test_record_user_decision_does_not_require_system_judgement(intent_matrix):
    case = next(c for c in intent_matrix["cases"] if c["id"] == "record-user-decision")
    expectations = case.get("record_expectations", {})
    assert expectations.get("requires_system_judgement") is False
    assert classify_intent(case["user_input"]) == "record"
