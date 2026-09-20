"""微信交互调参与容错控制中心 (支持 /llm 切换 Provider, /cookie 热换 Cookie, /insight 即时提炼)."""

import os
import re
import yaml
import requests
from typing import Dict, Any, Optional
from datetime import datetime, time
from loguru import logger


def is_in_quiet_hours(quiet_str: str, now: Optional[datetime] = None) -> bool:
    if not quiet_str or quiet_str.lower() in ("off", "none", "false", "0", "关闭"):
        return False
    try:
        parts = quiet_str.strip().split("-")
        if len(parts) != 2:
            return False
        sh, sm = map(int, parts[0].strip().split(":"))
        eh, em = map(int, parts[1].strip().split(":"))
        start_t = time(sh, sm)
        end_t = time(eh, em)
        cur_t = (now or datetime.now()).time()

        if start_t <= end_t:
            return start_t <= cur_t < end_t
        else:
            return cur_t >= start_t or cur_t < end_t
    except Exception:
        return False


class CommandReceiver:
    """容错控制器与微信交互指令接收器."""

    def __init__(self, engine_service):
        self.service = engine_service

    def handle_command(self, cmd_text: str, from_user: str = "@all") -> str:
        """解析并执行微信交互命令."""
        cmd = cmd_text.strip()
        logger.info(f"[Controller] 收到交互控制指令: {cmd}")

        # 1. 帮助指令
        if cmd.lower() in ("/help", "help", "帮助", "?", "？"):
            return self._cmd_help()

        # 2. 状态查询 (大模型健康度、数据库统计、爬虫状态)
        if cmd.lower() in ("/status", "status", "状态"):
            return self._cmd_status()

        # 3. 即刻触发跨源渐进思考与 Insight 提炼
        if cmd.lower() in ("/insight", "insight", "/run", "run", "提炼", "思考"):
            return self._cmd_trigger_insight()
        # 4. 免打扰休眠设置: /quiet 23:00-09:00 或 /quiet off 或 休眠 23:00-09:00
        m_quiet = re.match(r'^(?:/quiet|quiet|/sleep|sleep|休眠)\s*(.+)$', cmd, re.IGNORECASE)
        if m_quiet:
            return self._cmd_set_quiet_hours(m_quiet.group(1).strip())

        # 5. 回溯天数设置: /days 3 或 范围 3
        m_days = re.match(r'^(?:/days|days|范围)\s*(\d+)$', cmd, re.IGNORECASE)
        if m_days:
            days = int(m_days.group(1))
            return self._cmd_set_days(days)

        # 6. 思考频率设置: /interval 6 或 频率 6 (小时)
        m_interval = re.match(r'^(?:/interval|interval|频率)\s*(\d+)$', cmd, re.IGNORECASE)
        if m_interval:
            hours = int(m_interval.group(1))
            return self._cmd_set_interval(hours)

        # 7. AI深度追问 或 切换通道:
        # 格式A: /llm primary 或 /llm secondary -> 切换模型通道
        # 格式B: /llm <追问问题> 或 /llm last <问题> 或 /llm history -> 对当前洞察进行对话追问
        if cmd.lower().startswith(("/llm", "／llm")):
            llm_text = cmd[4:].strip() if len(cmd) > 4 else ""
            parts = llm_text.split(maxsplit=1)
            first_token = parts[0].strip().lower() if parts else ""
            if first_token in ("primary", "secondary"):
                return self._cmd_switch_llm(first_token)
            else:
                # 走 AI 对话追问流程
                return self._cmd_chat_llm(llm_text)

        # 5. 更新大模型 API Key: /setkey <key>
        m_key = re.match(r'^(?:/setkey|setkey|设置密钥)\s*(.+)$', cmd, re.IGNORECASE)
        if m_key:
            new_key = m_key.group(1).strip()
            return self._cmd_set_llm_key(new_key)

        # 6. 热更新知乎 Cookie (解决爬虫反爬/失效问题): /cookie <new_cookie>
        m_cookie = re.match(r'^(?:/cookie|cookie|更新知乎)\s*(.+)$', cmd, re.IGNORECASE | re.DOTALL)
        if m_cookie:
            new_cookie = m_cookie.group(1).strip()
            return self._cmd_update_zhihu_cookie(new_cookie)

        # 7. 测试大模型连通性: /testllm
        if cmd.lower() in ("/testllm", "testllm", "测试模型"):
            return self._cmd_test_llm()

        # 8. 调整洞察推送阈值: /score <分数>
        m_score = re.match(r'^(?:/score|score|阈值)\s*(\d+)$', cmd, re.IGNORECASE)
        if m_score:
            score = int(m_score.group(1))
            return self._cmd_set_score(score)

        return (
            f"❓ 未识别的指令: `{cmd}`\n\n"
            f"发送 `/help` 查看支持的容错与调参指令，如 `/insight`、`/llm secondary`、`/cookie <新Cookie>`。"
        )

    def _cmd_help(self) -> str:
        return """🧠 **InsightEngine 交互控制手册**
━━━━━━━━━━━━━━━━━━
🔹 **AI 深度追问与多轮推演**:
• `/llm <问题>`: 对最新产出的顶级洞察进行多轮深度追问
• `/llm last <问题>`: 追问最新一条洞察
• `/llm <ID> <问题>`: 追问指定 ID 洞察 (如 `/llm 51 ...`)
• `/llm history`: 查看当前选中洞察的概况与已有追问历史

🔹 **核心触发**:
• `/insight` 或 `提炼`: 立即触发全源深度碰撞与洞察提炼
• `/status` 或 `状态`: 检查三大信源库、免打扰与各参数

🔹 **免打扰休眠设置 (夜间不打扰)**:
• `/quiet 23:00-09:00`: 设置夜间休眠时段 (在此期间静默不推送)
• `/quiet off`: 关闭免打扰，全天候实时推送

🔹 **回溯范围与思考频率调参**:
• `/days <天数>`: 设置跨源回溯范围 (如 `/days 3` 或 `/days 7`)
• `/interval <小时>`: 设置思考聚合频率 (如 `/interval 6` 或 `/interval 12`)
• `/score <分数>`: 调整洞察推送门槛 (默认 80 分，宁缺毋滥)

🔹 **大模型容灾与热切换 (解决 API 失效)**:
• `/llm primary`: 切换为默认主通道 (如 Gemini-3.8-Flash)
• `/llm secondary`: 切换为备用容灾通道 (如 DeepSeek-V3)
• `/setkey <Key>`: 动态热更新当前生效通道的 API Key
• `/testllm`: 实时测试大模型连通性与响应速度

🔹 **知乎爬虫容错与更新 (解决 Cookie 失效)**:
• `/cookie <完整Cookie>`: 免登服务器，直接在微信对话框中热更新知乎 Cookie 并测试生效！"""

    def _cmd_status(self) -> str:
        cfg = self.service.cfg
        llm_cfg = cfg.get("llm", {})
        active_p = self.service.insight_agent.active_provider
        p_info = llm_cfg.get("providers", {}).get(active_p, {})

        quiet_h = getattr(self.service, "quiet_hours", "23:00-09:00")
        quiet_desc = "休眠静默中 🌙" if is_in_quiet_hours(quiet_h) else "活跃思考中 🟢"
        days = self.service.lookback_hours // 24

        # 检查三大数据库
        mail_exist = os.path.exists(self.service.knowledge_hub.mail_db)
        obs_exist = os.path.exists(self.service.knowledge_hub.obsidian_db)
        soc_exist = os.path.exists(self.service.knowledge_hub.social_db)

        return f"""📊 **InsightEngine 系统健康与配置看板**
━━━━━━━━━━━━━━━━━━
🟢 **服务状态**: 守护运行中
🌙 **免打扰时段**: `{quiet_h}` ({quiet_desc})
📅 **跨源回溯范围**: 最近 **{days}** 天 ({self.service.lookback_hours} 小时)
⏰ **思考沉淀周期**: 每 **{self.service.run_interval_hours}** 小时全源提炼一次
🔥 **洞察推送门槛**: ≥ {self.service.min_insight_score} 分 (低于此分绝对静默)
🤖 **当前大模型**: `{active_p}` ({p_info.get('name', '未配置')})

📚 **三大信源数据库联通情况**:
- 邮件学术库: {'✅ 正常连接' if mail_exist else '⚠️ 未找到文件'}
- 微信随手记: {'✅ 正常连接' if obs_exist else '⚠️ 未找到文件'}
- 社交雷达库: {'✅ 正常连接' if soc_exist else '⚠️ 未找到文件'}

💡 若大模型异常可发 `/llm secondary` 切换通道；若知乎失效可发 `/cookie <新Cookie>` 热替换！"""

    def _cmd_set_quiet_hours(self, val: str) -> str:
        clean_val = val.strip()
        if clean_val.lower() in ("off", "none", "false", "0", "关闭"):
            self.service.quiet_hours = "off"
            self.service.cfg.setdefault("engine", {})["quiet_hours"] = "off"
            self._save_yaml("config/config.yaml", self.service.cfg)
            return "✅ **免打扰休眠已关闭**\n\n系统将恢复全天候 24 小时即时推送。"

        if not re.match(r'^\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}$', clean_val):
            return "⚠️ 格式不正确！请使用 `HH:MM-HH:MM` 格式，如 `/quiet 23:00-09:00`，或发送 `/quiet off` 关闭。"

        clean_val = re.sub(r'\s+', '', clean_val)
        self.service.quiet_hours = clean_val
        self.service.cfg.setdefault("engine", {})["quiet_hours"] = clean_val
        self._save_yaml("config/config.yaml", self.service.cfg)
        return f"🌙 **夜间免打扰休眠时段已生效！**\n\n时段: **{clean_val}**\n在该时段内系统静默沉淀，绝不打扰您的休息。"

    def _cmd_set_days(self, days: int) -> str:
        if days <= 0:
            return "⚠️ 回溯天数必须大于 0 天。"
        hours = days * 24
        self.service.lookback_hours = hours
        self.service.cfg.setdefault("engine", {})["lookback_hours"] = hours
        self._save_yaml("config/config.yaml", self.service.cfg)
        return f"✅ **跨源回溯范围已修改**\n\n新范围: 最近 **{days}** 天 ({hours} 小时) 的增量素材 (已持久化保存)。"

    def _cmd_set_interval(self, hours: int) -> str:
        if hours < 1:
            return "⚠️ 思考周期不能小于 1 小时，以留出充分的知识发酵与沉淀时间。"
        self.service.run_interval_hours = hours
        self.service.cfg.setdefault("engine", {})["run_interval_hours"] = hours
        self._save_yaml("config/config.yaml", self.service.cfg)
        return f"✅ **思考聚合周期已修改**\n\n新周期: 每 **{hours}** 小时执行一次全源碰撞提炼 (已持久化保存)。"

    def _cmd_trigger_insight(self) -> str:
        import threading
        threading.Thread(target=self.service.run_pipeline, daemon=True).start()
        return "🧠 **已立即启动全信源跨界渐进思考**\n\n正在聚合邮件学术推送、微信随手记与知乎前沿讨论，由大模型深度研读碰撞，若提炼出 ≥80 分的顶级 Insight 将立即为您呈送！"

    def _cmd_switch_llm(self, provider: str) -> str:
        if provider not in ("primary", "secondary"):
            return "⚠️ 通道名称仅支持 `primary` (主通道) 或 `secondary` (备用通道)。"
        
        self.service.insight_agent.active_provider = provider
        self.service.cfg["llm"]["active_provider"] = provider
    def _cmd_chat_llm(self, llm_text: str) -> str:
        """处理针对洞察材料的 /llm 追问命令."""
        parts = llm_text.split(maxsplit=1)
        if not parts:
            return (
                "💡 **InsightEngine AI 深度追问指南**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "• `/llm <问题>`: 对最新产出的顶级洞察进行深度追问\n"
                "• `/llm last <问题>`: 追问最新一条洞察\n"
                "• `/llm <ID> <问题>`: 追问指定 ID 洞察 (如 `/llm 5 ...`)\n"
                "• `/llm history`: 查看最新洞察的概况与追问历史\n\n"
                "💡 切换思考模型请使用: `/llm primary` 或 `/llm secondary`"
            )

        first_token = parts[0].strip().lower()
        if first_token in ("last", "latest") or first_token.isdigit() or (len(first_token) >= 8 and first_token.isalnum() and not any('\u4e00' <= char <= '\u9fff' for char in first_token)):
            target = first_token
            question = parts[1].strip() if len(parts) > 1 else ""
        else:
            target = "last"
            question = llm_text
        with self.service.storage._get_connection() as conn:
            row = None
            if target in ("last", "latest"):
                cur = conn.execute("SELECT * FROM archived_insights ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
            elif target.isdigit():
                cur = conn.execute("SELECT * FROM archived_insights WHERE id = ?", (int(target),))
                row = cur.fetchone()
            else:
                cur = conn.execute("SELECT * FROM archived_insights WHERE title LIKE ? OR core_insight LIKE ? ORDER BY id DESC LIMIT 1", (f"%{target}%", f"%{target}%"))
                row = cur.fetchone()

        if not row:
            return f"❌ 未在洞察库中找到相关记录 (查询目标: `{target}`)。\n系统当前可能尚未沉淀出 ≥80 分的顶级洞察，或请发送 `/insight` 立即触发一次提炼！"

        item = dict(row)
        item_id = item["id"]
        title = item.get("title", "未命名洞察")
        score = item.get("depth_score", 0)
        category = item.get("insight_type", "综合")
        # 如果只是查看概况或 /llm history
        if not question or question.lower() == "history":
            hist = self.service.storage.get_chat_history(item_id) if hasattr(self.service.storage, "get_chat_history") else []
            return (
                f"🧠 **当前选中洞察** [ID: {item_id}]\n"
                f"📌 《{title}》\n"
                f"🏷️ 领域: {category} | 🔥 深度评分: {score}分\n"
                f"💡 核心结论: {item.get('core_insight', '')}\n\n"
                f"💬 已有追问历史: {len(hist)} 条消息。\n"
                f"您可以发送：`/llm {item_id} 您的具体问题` 进行深度追问。"
            )

        # 调用大模型执行上下文追问
        hist = self.service.storage.get_chat_history(item_id) if hasattr(self.service.storage, "get_chat_history") else []
        
        context_parts = [
            f"【洞察标题】: {title}",
            f"【所属领域】: {category}",
            f"【深度洞察评分】: {score}分",
            f"【核心结论】: {item.get('core_insight', '')}",
            f"【哲学/架构启示】: {item.get('philosophical_takeaway', '')}",
            f"【跨界创新/思考推演】:\n{item.get('progressive_synthesis', '')}",
        ]
        doc_context = "\n".join(context_parts)

        system_prompt = f"""你是一位深度的商业与前沿技术洞察研究助手。
请基于以下由【InsightEngine】提炼的顶级跨界洞察与推演内容，回答用户的追问。

--- 洞察推演上下文 ---
{doc_context}
--- 结束 ---

回答要求：
1. 严格依据上述推演和结论作答，突出商业壁垒、技术演进或未来范式。
2. 语言简练，逻辑严密，适合手机微信阅读，控制在 500 字以内。"""

        messages = [{"role": "system", "content": system_prompt}]
        for h in hist[-6:]:
            r = h.get("role", "user")
            c = h.get("content", "")
            if r in ("user", "assistant") and c:
                messages.append({"role": r, "content": c})
        messages.append({"role": "user", "content": question})

        active_p = self.service.insight_agent.active_provider
        client_tuple = self.service.insight_agent._get_client_for_provider(active_p)
        if not client_tuple:
            return f"❌ 通道 `{active_p}` 未配置有效凭据。"
        client, model, temp, display_name = client_tuple

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=800
            )
            ans = resp.choices[0].message.content.strip()
            if hasattr(self.service.storage, "add_chat_message"):
                self.service.storage.add_chat_message(item_id, "user", "user", question)
                self.service.storage.add_chat_message(item_id, "user", "assistant", ans)
            return (
                f"🤖 **【InsightEngine·深度追问】** [ID: {item_id}]\n"
                f"📄 《{title}》\n"
                f"❓ 问: {question}\n\n"
                f"💡 答:\n{ans}"
            )
        except Exception as e:
            return f"⚠️ 追问回答生成失败: {e}"
        self._save_yaml("config/config.yaml", self.service.cfg)
        
        p_name = self.service.cfg["llm"]["providers"].get(provider, {}).get("name", provider)
        logger.info(f"[Controller] 大模型通道已热切换为: {provider} ({p_name})")
        return f"✅ **大模型通道已成功热切换**\n\n当前活动通道: `{provider}` ({p_name})，后续分析将走该通道。"

    def _cmd_set_llm_key(self, new_key: str) -> str:
        if len(new_key) < 10:
            return "⚠️ API Key 格式不正确，过短。"

        active_p = self.service.insight_agent.active_provider
        p_cfg = self.service.cfg["llm"]["providers"].get(active_p, {})
        p_cfg["api_key"] = new_key
        self._save_yaml("config/config.yaml", self.service.cfg)

        logger.info(f"[Controller] 已为通道 [{active_p}] 更新 API Key")
        return f"✅ **API Key 已成功更新并持久化保存**\n\n目标通道: `{active_p}`，可发送 `/testllm` 测试连通性！"

    def _cmd_test_llm(self) -> str:
        active_p = self.service.insight_agent.active_provider
        client_tuple = self.service.insight_agent._get_client_for_provider(active_p)
        if not client_tuple:
            return f"❌ 通道 `{active_p}` 未配置有效凭据。"

        client, model, temp, display_name = client_tuple
        import time
        start = time.time()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "请回复四个字：体系结构"}],
                max_tokens=20
            )
            cost = time.time() - start
            reply = resp.choices[0].message.content.strip()
            return f"🟢 **大模型通道测试成功！**\n\n- 通道: `{active_p}` ({display_name})\n- 模型: `{model}`\n- 耗时: {cost:.2f} 秒\n- 响应: {reply}"
        except Exception as e:
            cost = time.time() - start
            return f"🔴 **大模型通道异常！**\n\n- 通道: `{active_p}` ({display_name})\n- 耗时: {cost:.2f} 秒\n- 错误: {e}\n\n💡 建议发送 `/llm secondary` 切换到备用通道。"

    def _cmd_update_zhihu_cookie(self, new_cookie: str) -> str:
        """跨项目热更新知乎 Cookie (同时更新 social_radar 配置)."""
        if len(new_cookie) < 30 or "z_c0" not in new_cookie:
            return "⚠️ Cookie 格式似乎不完整（未包含 z_c0 等关键凭据），请完整复制后重试。"

        # 1. 更新本地 social_radar/config/config.yaml
        radar_cfg_path = "D:/Project/social_radar/config/config.yaml"
        updated_ok = False
        if os.path.exists(radar_cfg_path):
            try:
                with open(radar_cfg_path, "r", encoding="utf-8") as f:
                    r_cfg = yaml.safe_load(f) or {}
                r_cfg.setdefault("zhihu", {})["cookie"] = new_cookie
                with open(radar_cfg_path, "w", encoding="utf-8") as f:
                    yaml.dump(r_cfg, f, allow_unicode=True, sort_keys=False)
                updated_ok = True
            except Exception as e:
                logger.error(f"[Controller] 更新本地知乎配置异常: {e}")

        # 2. 验证新 Cookie 连通性
        test_url = "https://www.zhihu.com/api/v4/me?include=is_realname"
        headers = {
            "accept": "*/*",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            "cookie": new_cookie
        }
        try:
            r = requests.get(test_url, headers=headers, timeout=10)
            if r.status_code == 200:
                name = r.json().get("name", "用户")
                return f"🎉 **知乎 Cookie 热更新成功！**\n\n- 验证账号: `{name}` (HTTP 200 OK)\n- 爬虫凭据已自动注入并持久化保存！\n- 雷达监控已恢复正常采集。"
            else:
                return f"⚠️ Cookie 已写入，但知乎服务端验证返回 HTTP {r.status_code}，可能触发了滑块验证码或已过期。"
        except Exception as e:
            return f"⚠️ Cookie 已保存，但网络探测异常: {e}"

    def _cmd_set_score(self, score: int) -> str:
        if not (50 <= score <= 100):
            return "⚠️ 门槛分数建议在 50 到 100 之间。"
        self.service.min_insight_score = score
        self.service.insight_agent.min_score = score
        self.service.cfg["engine"]["min_insight_score"] = score
        self._save_yaml("config/config.yaml", self.service.cfg)
        return f"✅ **Insight 推送门槛已修改为**: **{score}** 分 (低于此分绝对静默不打扰)。"

    def _save_yaml(self, path: str, data: dict):
        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"[Controller] 保存配置异常: {e}")
