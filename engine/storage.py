"""SQLite 洞察归档与历史去重存储模块."""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .insight_agent import ExtractedInsight


class InsightStorage:
    """本地 SQLite 数据库管理，用于历史 Insight 归档与防重复提炼."""

    def __init__(self, db_path: str = "data/insights.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据表."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS archived_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                insight_type TEXT NOT NULL,
                depth_score INTEGER,
                core_insight TEXT,
                philosophical_takeaway TEXT,
                cross_sources TEXT,          -- JSON 字符串
                research_directions TEXT,    -- JSON 字符串
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_insight_type ON archived_insights(insight_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_insight_score ON archived_insights(depth_score)")
            conn.commit()
            logger.debug(f"[Storage] 洞察归档数据库就绪: {self.db_path}")

    def is_title_archived(self, title: str) -> bool:
        """检查类似命题是否已归档推送过."""
        if not title:
            return False
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM archived_insights WHERE title = ?", (title.strip(),))
            return cur.fetchone() is not None

    def record_insight(self, insight: ExtractedInsight) -> int:
        """归档一条高价值 Insight."""
        sources_json = json.dumps(insight.cross_sources, ensure_ascii=False)
        dirs_json = json.dumps(insight.research_directions, ensure_ascii=False)

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR IGNORE INTO archived_insights
            (title, insight_type, depth_score, core_insight, philosophical_takeaway, cross_sources, research_directions, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.title.strip(),
                insight.insight_type,
                insight.depth_score,
                insight.core_insight,
                insight.philosophical_takeaway,
                sources_json,
                dirs_json,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            last_id = cur.lastrowid
            logger.info(f"[Storage] 成功归档顶级洞察 [ID {last_id}]: {insight.title}")
            return last_id
