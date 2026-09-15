"""InsightEngine 业务编排主控制器."""

import os
import time
import yaml
from typing import List, Dict, Any, Optional
from loguru import logger

from .knowledge_hub import KnowledgeHub, SourceKnowledgeItem
from .insight_agent import InsightAgent, ExtractedInsight
from .storage import InsightStorage
from .notifier import WeChatNotifier
from .command_receiver import CommandReceiver


class InsightEngineService:
    """跨信源渐进思考与深度洞察引擎主控制器."""

    def __init__(self, config_path: str = "config/config.yaml"):
        if not os.path.exists(config_path):
            if os.path.exists("config/config.example.yaml"):
                config_path = "config/config.example.yaml"
            else:
                raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)

        # 1. 存储与门槛配置
        ec = self.cfg.get("engine", {})
        self.lookback_hours = int(ec.get("lookback_hours", 72))
        self.min_insight_score = int(ec.get("min_insight_score", 80))
        self.run_interval_hours = int(ec.get("run_interval_hours", 6))

        db_cfg = self.cfg.get("databases", {})
        self.storage = InsightStorage(db_path=db_cfg.get("insight_db", "data/insights.db"))
        self.knowledge_hub = KnowledgeHub(db_cfg)

        # 2. 微信通知 (1000005)
        wc = self.cfg.get("wechat", {})
        self.notifier = WeChatNotifier(
            corp_id=wc.get("corp_id", ""),
            agent_id=int(wc.get("agent_id", 1000005)),
            corp_secret=wc.get("corp_secret", ""),
            default_to_user=wc.get("to_user", "@all")
        )

        # 3. 大模型 Agent (支持主备多通道)
        self.insight_agent = InsightAgent(
            llm_config=self.cfg.get("llm", {}),
            philosophy_path="config/architecture_philosophy.yaml",
            min_score=self.min_insight_score
        )

        # 4. 控制指令接收器
        self.controller = CommandReceiver(self)
        self._start_command_server(port=8086)

    def send_startup_message(self):
        """服务启动通知."""
        title = "💡 InsightEngine 洞察引擎已上线"
        summary = "跨信源渐进思考与深度洞察系统已启动"

        active_p = self.insight_agent.active_provider
        p_name = self.cfg.get("llm", {}).get("providers", {}).get(active_p, {}).get("name", active_p)

        details = f"<b>聚合信源</b>: 邮件论文 + 微信随手记 + 知乎动态<br/>" \
                  f"<b>思考周期</b>: 每 {self.run_interval_hours} 小时全源提炼一次<br/>" \
                  f"<b>推送门槛</b>: ≥ {self.min_insight_score} 分 (顶级 Insight 才会推送，宁缺毋滥)<br/>" \
                  f"<b>大模型通道</b>: {p_name} (主备容灾已就绪)<br/>" \
                  f"<div class=\"highlight\">💡 <b>微信快捷指令</b>:<br/>" \
                  f"• <code>/insight</code> : 立即触发跨源思考与提炼<br/>" \
                  f"• <code>/llm secondary</code> : 快速切换大模型通道<br/>" \
                  f"• <code>/cookie &lt;新Cookie&gt;</code> : 微信热更新知乎凭据<br/>" \
                  f"• <code>/status</code> : 查看全系统健康状态</div>"

        md_content = f"""### 💡 InsightEngine 洞察提炼引擎已就绪！
**状态**: 🟢 正常守护运行中 (宁缺毋滥，直击本质)
**聚合信源**: 📚 邮件学术论文 + 📝 微信长文随手记 + 💬 知乎前沿讨论
**思考周期**: 每 **{self.run_interval_hours}** 小时深度碰撞提炼一次
**推送门槛**: 🔥 评分 ≥ **{self.min_insight_score}** 分 (唯有穿透本质的真见解才推送，绝不打扰)
**大模型通道**: `{active_p}` ({p_name})

> 💡 **微信交互指令支持**：在此对话框发送以下命令可实时控制：
> - `/insight` 或 `提炼`：立即执行全源渐进思考
> - `/status` 或 `状态`：检查三大信源库与大模型状态
> - `/llm secondary`：大模型故障时一键切换备用通道
> - `/cookie <新Cookie>`：知乎失效时免登服务器直接热更新！
> - `/help`：获取完整指令菜单"""

        self.notifier.send_dual_notification(
            title=title,
            summary=summary,
            details=details,
            markdown_content=md_content,
            url="https://work.weixin.qq.com",
            btntxt="进入系统"
        )

    def run_pipeline(self) -> List[ExtractedInsight]:
        """执行一次完整的知识聚合、AI 渐进思考、价值筛选与通知."""
        logger.info("[InsightEngine] 开始执行跨信源渐进思考分析流...")

        # 1. 跨库提取素材
        pkg = self.knowledge_hub.fetch_recent_knowledge(lookback_hours=self.lookback_hours)

        # 2. 大模型提炼洞察
        insights = self.insight_agent.generate_insights(pkg)

        # 3. 过滤、落盘归档与通知推送
        sent_count = 0
        for ins in insights:
            if self.storage.is_title_archived(ins.title):
                logger.debug(f"[InsightEngine] 类似命题已归档推送过，跳过: {ins.title}")
                continue

            # 微信推送 (双通道)
            logger.info(f"[InsightEngine] 发现突破性 Insight [{ins.insight_type}] ({ins.depth_score}分): {ins.title}")
            ok = self.notifier.send_insight_notification(ins)
            if ok:
                sent_count += 1

            # 归档到 SQLite
            self.storage.record_insight(ins)

            # 可选：追加到本地 Obsidian 知识库
            self._append_to_obsidian(ins)

        logger.info(f"[InsightEngine] 本轮分析完成，成功推送并沉淀 {sent_count} 条顶级洞察！")
        return insights

    def _append_to_obsidian(self, ins: ExtractedInsight):
        """将提炼出的 Insight 自动沉淀到 Obsidian 知识库 (若路径可用)."""
        obs_dir = "D:/Obsidian/workspace/00-Inbox"
        if not os.path.exists(obs_dir):
            return

        target_file = os.path.join(obs_dir, "WeChat_Insights.md")
        dirs_md = "\n".join([f"- {d}" for d in ins.research_directions])
        srcs_md = ", ".join(ins.cross_sources)

        snippet = f"""
---
### 💡 深度洞察【{ins.insight_type}】: {ins.title}
- **时间**: {time.strftime("%Y-%m-%d %H:%M:%S")} | **评分**: 🔥 {ins.depth_score}分
- **跨源素材**: {srcs_md}

> [!insight] 核心见解
> {ins.core_insight}

> [!quote] 哲学与方法论升华
> {ins.philosophical_takeaway}

**🔬 建议研究与实验推演方向**:
{dirs_md}
"""
        try:
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(snippet)
            logger.info(f"[InsightEngine] 洞察已自动追加写入 Obsidian: {target_file}")
        except Exception as e:
            logger.warning(f"[InsightEngine] 写入 Obsidian 异常: {e}")

    def _start_command_server(self, port: int = 8086):
        """本地轻量 HTTP 命令接收器 (用于接收来自 OpenResty 或微信的控制请求)."""
        import threading, json
        from urllib.parse import urlparse, parse_qs
        from http.server import HTTPServer, BaseHTTPRequestHandler

        service_ref = self

        class CmdHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                cmd = params.get("cmd", [""])[0]
                if cmd:
                    reply = service_ref.controller.handle_command(cmd)
                    service_ref.notifier.send_dual_notification(
                        title="⚙️ 洞察引擎指令结果",
                        summary="指令交互调参",
                        details=reply.replace("\n", "<br/>"),
                        markdown_content=reply,
                        url="https://work.weixin.qq.com",
                        btntxt="查看状态"
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(reply.encode("utf-8"))
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"InsightEngine Command Server Active")

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8", errors="replace")
                try:
                    data = json.loads(body)
                    cmd = data.get("command", "")
                    from_user = data.get("from_user", "@all")
                    reply = service_ref.controller.handle_command(cmd, from_user)
                    service_ref.notifier.send_dual_notification(
                        title="⚙️ 洞察引擎指令结果",
                        summary="来自微信指令交互",
                        details=reply.replace("\n", "<br/>"),
                        markdown_content=reply,
                        url="https://work.weixin.qq.com",
                        btntxt="查看状态"
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"code": 0, "reply": reply}, ensure_ascii=False).encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))

            def log_message(self, format, *args):
                pass

        def run_srv():
            try:
                httpd = HTTPServer(("127.0.0.1", port), CmdHandler)
                logger.info(f"[InsightEngine] 本地控制交互服务已就绪: http://127.0.0.1:{port}")
                httpd.serve_forever()
            except Exception as e:
                logger.debug(f"[InsightEngine] 命令服务端口异常 (可能已运行): {e}")

        threading.Thread(target=run_srv, daemon=True).start()

    def run_forever(self):
        """长期后台守护循环 (每 N 小时聚合渐进思考一次)."""
        self.send_startup_message()
        logger.info(f"[InsightEngine] 启动后台常驻思考守护 (周期: {self.run_interval_hours} 小时)...")

        while True:
            try:
                self.run_pipeline()
            except Exception as e:
                logger.error(f"[InsightEngine] 分析流水线异常: {e}")

            sleep_sec = self.run_interval_hours * 3600
            logger.info(f"[InsightEngine] 进入思考沉淀期，将在 {self.run_interval_hours} 小时后再次执行全源扫描...")
            time.sleep(sleep_sec)
