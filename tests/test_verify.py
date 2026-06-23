"""verify 命令与 feedback-report 行为测试。"""

from app.agent_tools import cmd_feedback_report, cmd_verify


def test_verify_passes_in_repo():
    report = cmd_verify(quiet=True, quick=True)
    assert report["ok"] is True
    assert all(c["ok"] for c in report["checks"])


def test_feedback_report_has_no_recommendations(capsys):
    cmd_feedback_report()
    out = capsys.readouterr().out
    data = __import__("json").loads(out)
    assert "recommendations" not in data
    assert "total_usage_records" in data
