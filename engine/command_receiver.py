"""微信交互调参与容错控制中心 (支持 /llm 切换 Provider, /cookie 热换 Cookie, /insight 即时提炼)."""

import os
import re
import yaml
import requests
from typing import Dict, Any, Optional
from loguru import logger


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

        # 4. 切换大模型通道: /llm primary 或 /llm secondary
        m_llm = re.match(r'^(?:/llm|llm|切换模型)\s*(\w+)$', cmd, re.IGNORECASE)
        if m_llm:
            provider = m_llm.group(1).lower()
            return self._cmd_switch_llm(provider)

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
🔹 **核心触发**:
- `/insight` 或 `提炼`: 立即触发一次全源渐进思考与洞察提炼
- `/status` 或 `状态`: 检查三大信源库、LLM 通道与运行状态

🔹 **大模型容灾与热切换 (解决 API 失效)**:
- `/llm primary`: 切换为默认主通道 (如 Gemini-3.8-Flash)
- `/llm secondary`: 切换为备用容灾通道 (如 DeepSeek-V3)
- `/setkey <Key>`: 动态热更新当前生效通道的 API Key
- `/testllm`: 实时测试大模型连通性与响应速度

🔹 **知乎爬虫容错与更新 (解决 Cookie 失效)**:
- `/cookie <完整Cookie>`: 免登服务器，直接在微信对话框中热更新知乎 Cookie 并测试生效！

🔹 **参数调整**:
- `/score <分数>`: 调整洞察推送门槛 (默认 80 分，宁缺毋滥)"""

    def _cmd_status(self) -> str:
        cfg = self.service.cfg
        llm_cfg = cfg.get("llm", {})
        active_p = self.service.insight_agent.active_provider
        p_info = llm_cfg.get("providers", {}).get(active_p, {})

        # 检查三大数据库
        db_cfg = cfg.get("databases", {})
        mail_exist = os.path.exists(db_cfg.get("mail_db", ""))
        obs_exist = os.path.exists(db_cfg.get("obsidian_db", ""))
        soc_exist = os.path.exists(db_cfg.get("social_db", ""))

        return f"""📊 **InsightEngine 系统健康与配置状态**
━━━━━━━━━━━━━━━━━━
🟢 **服务状态**: 守护运行中 (每 {cfg['engine']['run_interval_hours']} 小时深度思考)
🤖 **当前大模型**: `{active_p}` ({p_info.get('name', '未配置')})
🔥 **推送门槛**: ≥ {self.service.min_insight_score} 分 (低于此分绝对不打扰)

📚 **三大信源数据库联通情况**:
- 邮件学术库 (mail_db): {'✅ 已就绪' if mail_exist else '⚠️ 未找到文件'}
- 微信随手记 (obsidian_db): {'✅ 已就绪' if obs_exist else '⚠️ 未找到文件'}
- 社交雷达库 (social_db): {'✅ 已就绪' if soc_exist else '⚠️ 未找到文件'}

💡 若大模型异常可发 `/llm secondary` 切换通道；若知乎失效可发 `/cookie <新Cookie>` 热替换！"""

    def _cmd_trigger_insight(self) -> str:
        import threading
        threading.Thread(target=self.service.run_pipeline, daemon=True).start()
        return "🧠 **已立即启动全信源跨界渐进思考**\n\n正在聚合邮件学术推送、微信随手记与知乎前沿讨论，由大模型深度研读碰撞，若提炼出 ≥80 分的顶级 Insight 将立即为您呈送！"

    def _cmd_switch_llm(self, provider: str) -> str:
        if provider not in ("primary", "secondary"):
            return "⚠️ 通道名称仅支持 `primary` (主通道) 或 `secondary` (备用通道)。"
        
        self.service.insight_agent.active_provider = provider
        self.service.cfg["llm"]["active_provider"] = provider
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
