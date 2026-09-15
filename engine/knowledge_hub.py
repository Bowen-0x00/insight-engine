"""跨源知识库聚合提取器 (连接 mail_assist.db, inbox.db, social_radar.db)."""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class SourceKnowledgeItem:
    """标准化的跨源知识条目."""
    source_channel: str      # 'mail_paper', 'wechat_note', 'zhihu_discussion'
    item_id: str
    title: str
    content: str             # 摘要、速读或闪念正文
    url: str
    author: str = ""
    score: int = 0
    tags: List[str] = field(default_factory=list)
    created_at: str = ""


class KnowledgeHub:
    """三大数据源联合检索中枢."""

    def __init__(self, db_paths: Dict[str, str]):
        self.mail_db = self._resolve_db_path(db_paths.get("mail_db", ""), "/root/mail_assist/data/mail_assist.db")
        self.obsidian_db = self._resolve_db_path(db_paths.get("obsidian_db", ""), "/root/wechat_obsidian/data/inbox.db")
        self.social_db = self._resolve_db_path(db_paths.get("social_db", ""), "/root/social_radar/data/social_radar.db")

    def _resolve_db_path(self, configured: str, linux_default: str) -> str:
        if configured and os.path.exists(configured):
            return configured
        if os.path.exists(linux_default):
            return linux_default
        return configured
    def _get_connection(self, db_path: str) -> Optional[sqlite3.Connection]:
        if not db_path or not os.path.exists(db_path):
            logger.debug(f"[KnowledgeHub] 数据库文件不存在，跳过: {db_path}")
            return None
        try:
            conn = sqlite3.connect(db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.warning(f"[KnowledgeHub] 连接数据库失败 ({db_path}): {e}")
            return None

    def fetch_recent_knowledge(self, lookback_hours: int = 72) -> Dict[str, List[SourceKnowledgeItem]]:
        """从三大数据库提取最近 N 小时内的增量学术、笔记与讨论数据."""
        cutoff_dt = datetime.now() - timedelta(hours=lookback_hours)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")

        package = {
            "papers": self._fetch_mail_papers(cutoff_str),
            "notes": self._fetch_obsidian_notes(cutoff_str),
            "discussions": self._fetch_social_discussions(cutoff_str)
        }

        total = sum(len(v) for v in package.values())
        logger.info(
            f"[KnowledgeHub] 知识聚合完成 (最近 {lookback_hours} 小时): "
            f"论文 {len(package['papers'])} 篇, 笔记 {len(package['notes'])} 条, 讨论 {len(package['discussions'])} 条 (共 {total} 条素材)"
        )
        return package

    def _fetch_mail_papers(self, cutoff_str: str) -> List[SourceKnowledgeItem]:
        """提取学术论文 (mail_assist.db)."""
        conn = self._get_connection(self.mail_db)
        if not conn:
            return []

        items = []
        try:
            with conn:
                cur = conn.cursor()
                # 提取评分 >= 60 分的论文
                cur.execute("""
                SELECT paper_id, title, authors, source, abstract, url, relevance_score, analysis, created_at
                FROM processed_papers
                WHERE created_at >= ? AND relevance_score >= 60
                ORDER BY relevance_score DESC, created_at DESC
                LIMIT 15
                """, (cutoff_str,))
                for r in cur.fetchall():
                    items.append(SourceKnowledgeItem(
                        source_channel="mail_paper",
                        item_id=str(r["paper_id"]),
                        title=r["title"] or "",
                        content=f"【摘要导读】: {r['abstract'][:600]}\n【AI分析】: {r['analysis']}",
                        url=r["url"] or "",
                        author=r["authors"] or "",
                        score=r["relevance_score"] or 0,
                        created_at=str(r["created_at"])
                    ))
        except Exception as e:
            logger.warning(f"[KnowledgeHub] 查询学术论文库异常: {e}")
        return items

    def _fetch_obsidian_notes(self, cutoff_str: str) -> List[SourceKnowledgeItem]:
        """提取个人随手记与长文收藏 (inbox.db)."""
        conn = self._get_connection(self.obsidian_db)
        if not conn:
            return []

        items = []
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                SELECT id, msg_id, msg_type, raw_content, title, author, url, tldr, tags, created_at
                FROM inbox_notes
                WHERE created_at >= ?
                ORDER BY id DESC
                LIMIT 20
                """, (cutoff_str,))
                for r in cur.fetchall():
                    tags_list = json.loads(r["tags"] or "[]")
                    content = r["tldr"] or r["raw_content"] or ""
                    items.append(SourceKnowledgeItem(
                        source_channel="wechat_note",
                        item_id=f"note_{r['id']}",
                        title=r["title"] or "个人随想",
                        content=content[:800],
                        url=r["url"] or "",
                        author=r["author"] or "本人",
                        tags=tags_list,
                        created_at=str(r["created_at"])
                    ))
        except Exception as e:
            logger.warning(f"[KnowledgeHub] 查询个人笔记库异常: {e}")
        return items

    def _fetch_social_discussions(self, cutoff_str: str) -> List[SourceKnowledgeItem]:
        """提取知乎等高价值前沿动态与问答 (social_radar.db)."""
        conn = self._get_connection(self.social_db)
        if not conn:
            return []

        items = []
        try:
            with conn:
                cur = conn.cursor()
                # 提取评分 >= 65 分的高价值动态
                cur.execute("""
                SELECT item_id, platform, item_type, title, author, url, value_score, core_insight, created_at
                FROM processed_items
                WHERE created_at >= ? AND value_score >= 65
                ORDER BY value_score DESC, created_at DESC
                LIMIT 15
                """, (cutoff_str,))
                for r in cur.fetchall():
                    items.append(SourceKnowledgeItem(
                        source_channel="zhihu_discussion",
                        item_id=str(r["item_id"]),
                        title=r["title"] or "",
                        content=r["core_insight"] or "",
                        url=r["url"] or "",
                        author=r["author"] or "",
                        score=r["value_score"] or 0,
                        created_at=str(r["created_at"])
                    ))
        except Exception as e:
            logger.warning(f"[KnowledgeHub] 查询社交动态库异常: {e}")
        return items
