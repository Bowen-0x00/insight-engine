"""企业微信应用消息双通道推送模块 (自建应用 1000005 - 洞察引擎专属)."""

import time
import requests
from typing import Optional, Dict, Any
from loguru import logger

from .insight_agent import ExtractedInsight


class WeChatNotifier:
    """企业微信自建应用通知推送器 (时序双通道：企微 Markdown + 个人微信 Textcard 卡片)."""

    def __init__(self, corp_id: str, agent_id: int, corp_secret: str, default_to_user: str = "@all"):
        self.corp_id = corp_id.strip()
        self.agent_id = int(agent_id)
        self.corp_secret = corp_secret.strip()
        self.default_to_user = default_to_user.strip() or "@all"

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取 access_token 带本地过期缓存."""
        now = time.time()
        if not force_refresh and self._access_token and now < self._token_expires_at:
            return self._access_token

        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.corp_secret}

        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("errcode") != 0:
                raise RuntimeError(f"获取 Token 失败: {data.get('errmsg')} (代码: {data.get('errcode')})")

            self._access_token = data["access_token"]
            self._token_expires_at = now + data.get("expires_in", 7200) - 300
            logger.debug("[WeChat] access_token 获取并缓存成功")
            return self._access_token
        except Exception as e:
            logger.error(f"[WeChat] 获取 access_token 异常: {e}")
            raise

    def send_insight_notification(self, insight: ExtractedInsight) -> bool:
        """格式化推送顶级 Insight 洞察卡片 (同时支持企微富文本与个人微信原生卡片)."""
        # 1. 微信原生卡片内容 (HTML)
        title = f"💡 深度洞察【{insight.insight_type}】: {insight.title[:35]}"
        summary = f"深度得分: 🔥 {insight.depth_score}分 | 跨源碰撞: {len(insight.cross_sources)}个信源"

        dirs_str = "、".join(insight.research_directions[:2]) if insight.research_directions else "详见正文分析"
        srcs_str = "、".join([s.strip("《》[] ")[:18] for s in insight.cross_sources[:3]])

        details = f"<b>💡 核心见解</b>:<br/>{insight.core_insight[:300]}...<br/><br/>" \
                  f"<b>🎯 哲学升华</b>: {insight.philosophical_takeaway}<br/>" \
                  f"<b>🔬 实验推演方向</b>: {dirs_str}<br/>" \
                  f"<div class=\"gray\">📚 跨源关联: {srcs_str}</div>"

        # 2. 企微 Markdown 富文本内容
        dirs_md = "\n".join([f"> - {d}" for d in insight.research_directions])
        srcs_md = "\n".join([f"- {s}" for s in insight.cross_sources])

        md_content = f"""### 💡 深度学术洞察【{insight.insight_type}】
**命题**: **{insight.title}**
**深度评分**: 🔥 **{insight.depth_score} 分**
> **💡 核心见解与突破**:
> {insight.core_insight}

> **🎯 哲学与方法论升华**:
> {insight.philosophical_takeaway}

**🔬 建议实验与探索方向**:
{dirs_md}

**📚 触发碰撞的跨源素材**:
{srcs_md}"""

        return self.send_dual_notification(
            title=title,
            summary=summary,
            details=details,
            markdown_content=md_content,
            url="https://work.weixin.qq.com",
            btntxt="查阅洞察"
        )

    def send_dual_notification(
        self,
        title: str,
        summary: str,
        details: str,
        markdown_content: str,
        url: Optional[str] = None,
        btntxt: str = "查看详情"
    ) -> bool:
        """先推送 Markdown 给企微客户端，再推送 Textcard 给个人微信."""
        logger.info("[WeChat] 正在双通道推送 (1. 企微Markdown富文本 -> 2. 个人微信原生卡片)...")
        ok_md = self.send_markdown(markdown_content)
        time.sleep(0.6)
        description = f"<div class=\"gray\">{summary}</div><div class=\"normal\">{details}</div>"
        ok_card = self.send_card(title=title, description=description, url=url or "https://work.weixin.qq.com", btntxt=btntxt)
        return ok_md or ok_card

    def send_card(self, title: str, description: str, url: str, btntxt: str = "查看详情", to_user: Optional[str] = None) -> bool:
        """发送文本卡片消息."""
        payload = {
            "title": title[:120],
            "description": description[:500],
            "url": url,
            "btntxt": btntxt[:8]
        }
        return self._send_message("textcard", payload, to_user)

    def send_markdown(self, content: str, to_user: Optional[str] = None) -> bool:
        return self._send_message("markdown", {"content": content}, to_user)

    def send_text(self, content: str, to_user: Optional[str] = None) -> bool:
        return self._send_message("text", {"content": content}, to_user)

    def _send_message(self, msgtype: str, payload: Dict[str, Any], to_user: Optional[str] = None) -> bool:
        token = self.get_access_token()
        target_user = to_user or self.default_to_user

        send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        body = {
            "touser": target_user,
            "msgtype": msgtype,
            "agentid": self.agent_id,
            msgtype: payload,
            "safe": 0
        }

        try:
            resp = requests.post(send_url, json=body, timeout=10)
            result = resp.json()
            if result.get("errcode") == 0:
                logger.info(f"[WeChat] 微信通知推送成功 ({msgtype}) -> {target_user}")
                return True
            logger.error(f"[WeChat] 发送消息失败 [code {result.get('errcode')}]: {result.get('errmsg')}")
            return False
        except Exception as e:
            logger.error(f"[WeChat] 发送消息异常: {e}")
            return False
