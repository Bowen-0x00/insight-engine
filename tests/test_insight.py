"""InsightEngine 单元与功能测试套件."""

import pytest
import os
from engine.insight_agent import ExtractedInsight, InsightAgent
from engine.storage import InsightStorage
from engine.command_receiver import CommandReceiver


@pytest.fixture
def temp_storage(tmp_path):
    db_file = str(tmp_path / "test_insights.db")
    return InsightStorage(db_file)


def test_insight_storage_deduplication(temp_storage):
    fake_insight = ExtractedInsight(
        insight_type="提出问题",
        depth_score=90,
        title="测试洞察：CXL近存语义重排可行性",
        core_insight="分析核心突破",
        philosophical_takeaway="本体vs载体",
        cross_sources=["素材1", "素材2"],
        research_directions=["方向1"]
    )

    assert not temp_storage.is_title_archived(fake_insight.title)
    temp_storage.record_insight(fake_insight)
    assert temp_storage.is_title_archived(fake_insight.title)


def test_command_receiver_parsing():
    class DummyService:
        def __init__(self):
            self.min_insight_score = 80
            self.cfg = {
                "engine": {"min_insight_score": 80, "run_interval_hours": 6},
                "llm": {
                    "active_provider": "primary",
                    "providers": {"primary": {"name": "TestLLM"}, "secondary": {"name": "BackupLLM"}}
                },
                "databases": {}
            }
            self.insight_agent = type("DummyAgent", (), {
                "active_provider": "primary",
                "min_score": 80,
                "_get_client_for_provider": lambda s, p: None
            })()

        def run_pipeline(self):
            pass

    service = DummyService()
    receiver = CommandReceiver(service)
    receiver._save_yaml = lambda *args: None
    # Test /help
    help_res = receiver.handle_command("/help")
    assert "InsightEngine" in help_res

    # Test /status
    status_res = receiver.handle_command("/status")
    assert "系统健康" in status_res

    # Test /score 85
    score_res = receiver.handle_command("/score 85")
    assert "85" in score_res
    assert service.min_insight_score == 85

    # Test /llm secondary
    llm_res = receiver.handle_command("/llm secondary")
    assert "secondary" in llm_res
    assert service.insight_agent.active_provider == "secondary"
