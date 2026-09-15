"""渐进思考与跨信源深度洞察提炼 Agent (多 LLM 主备容灾 + 体系结构哲学碰撞)."""

import re
import json
import yaml
import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from openai import OpenAI
from loguru import logger

from .knowledge_hub import SourceKnowledgeItem


@dataclass
class ExtractedInsight:
    """提炼出的高价值 Insight 结构体."""
    insight_type: str              # '提出问题', '底层感悟', '趋势与方向', '本质追问'
    depth_score: int               # 0-100 深度分 (需 >= min_score 才会推送)
    title: str                     # Insight 核心标题
    core_insight: str              # 核心论断与深层见解
    philosophical_takeaway: str    # 哲学或方法论升华 (如本体vs载体, 算力置换带宽)
    cross_sources: List[str]       # 产生碰撞的跨源素材标题
    research_directions: List[str] # 启发可做的推演或实验方向
    timestamp: str = ""


class InsightAgent:
    """深度洞察提炼引擎."""

    def __init__(self, llm_config: Dict[str, Any], philosophy_path: str = "config/architecture_philosophy.yaml", min_score: int = 80):
        self.llm_cfg = llm_config
        self.min_score = min_score
        self.philosophy_text = self._load_philosophy(philosophy_path)
        
        # 支持主备多 Provider
        self.providers = self.llm_cfg.get("providers", {})
        self.active_provider = self.llm_cfg.get("active_provider", "primary")

    def _load_philosophy(self, path: str) -> str:
        if not path or not __import__("os").path.exists(path):
            return "体系结构研究核心：区分课题本体与载体，用第一性原理框住物理底线，以算力对冲带宽。"
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
                return yaml.dump(raw, allow_unicode=True)
        except Exception:
            return ""

    def _get_client_for_provider(self, provider_key: str) -> Optional[tuple]:
        """获取指定 Provider 的 OpenAI Client 与模型名称."""
        p_cfg = self.providers.get(provider_key)
        if not p_cfg or not p_cfg.get("api_key") or p_cfg.get("api_key") == "YOUR_LLM_API_KEY":
            return None

        proxy = p_cfg.get("proxy")
        http_client = httpx.Client(timeout=60.0, proxy=proxy) if proxy else httpx.Client(timeout=60.0)
        client = OpenAI(
            base_url=p_cfg.get("base_url"),
            api_key=p_cfg.get("api_key"),
            http_client=http_client
        )
        return client, p_cfg.get("model", "deepseek-chat"), p_cfg.get("temperature", 0.2), p_cfg.get("name", provider_key)

    def generate_insights(self, knowledge_package: Dict[str, List[SourceKnowledgeItem]]) -> List[ExtractedInsight]:
        """跨源深度碰撞与渐进思考，提炼极高门槛洞察."""
        papers = knowledge_package.get("papers", [])
        notes = knowledge_package.get("notes", [])
        discussions = knowledge_package.get("discussions", [])

        total_items = len(papers) + len(notes) + len(discussions)
        if total_items == 0:
            logger.info("[InsightAgent] 当前无新增跨源素材，跳过提炼")
            return []

        logger.info(f"[InsightAgent] 开始跨源渐进思考 (素材源: {len(papers)}篇论文, {len(notes)}条笔记, {len(discussions)}条讨论)...")

        # 组装素材文本供大模型碰撞
        materials_text = self._format_materials(papers, notes, discussions)
        
        # 依次尝试当前 Provider 与备用 Provider (自动故障转移容灾)
        provider_order = [self.active_provider]
        for k in self.providers.keys():
            if k not in provider_order:
                provider_order.append(k)

        for p_key in provider_order:
            client_tuple = self._get_client_for_provider(p_key)
            if not client_tuple:
                continue

            client, model_name, temp, p_display = client_tuple
            try:
                logger.info(f"[InsightAgent] 正在调用大模型通道: {p_display} ({model_name})...")
                res = self._call_llm_insight(client, model_name, temp, materials_text)
                if res:
                    return res
            except Exception as e:
                logger.warning(f"[InsightAgent] 通道 [{p_display}] 调用失败: {e}，尝试切换备用通道...")

        logger.error("[InsightAgent] 所有大模型通道均不可用或未生成洞察")
        return []

    def _format_materials(self, papers: List[SourceKnowledgeItem], notes: List[SourceKnowledgeItem], discussions: List[SourceKnowledgeItem]) -> str:
        lines = []
        if papers:
            lines.append("### 📚 1. 邮件与顶会学术论文 (Academic Alerts & Papers):")
            for p in papers[:6]:
                lines.append(f"- 《{p.title}》 (作者: {p.author})\n  {p.content}")
        if notes:
            lines.append("\n### 📝 2. 用户个人随手记与长文收藏 (Personal Notes & Thoughts):")
            for n in notes[:8]:
                lines.append(f"- 《{n.title}》:\n  {n.content}")
        if discussions:
            lines.append("\n### 💬 3. 知乎等前沿同行深度讨论 (Industry Discussions):")
            for d in discussions[:6]:
                lines.append(f"- [{d.title}] (答主: {d.author}):\n  {d.content}")

        return "\n".join(lines)

    def _call_llm_insight(self, client: OpenAI, model: str, temperature: float, materials_text: str) -> List[ExtractedInsight]:
        system_prompt = f"""你是一位享誉体系结构领域的资深学术导师与首席架构师。
你的唯一任务是：阅读用户近期聚合的【论文】、【个人随想】和【行业讨论】素材，结合用户的【核心研究心法与自检清单】，进行**跨信源的渐进思考（Progressive Reflection）与灵感碰撞**。

【用户的核心研究哲学与自检清单 (Architecture Philosophy)】
{self.philosophy_text}

【你的提炼原则（宁缺毋滥，直击灵魂）】:
1. 严禁假大空的套话与浅层复述。必须穿透表象，抓住本质（比如 AXI/CHI 只是苹果，通信元数据与有效载荷互信息规律才是万有引力；软件不会动态检查误差，全是离线 Minimax 多项式展开）。
2. 洞察必须归属于以下【四种经典模式】之一：
   - 模式 A【提出问题】：在相同语义下，寻找资源置换、提前形成地址或打破现有假设的犀利设问。
   - 模式 B【底层感悟】：第一性原理算力对冲带宽、白盒与黑盒边界、本质 vs 载体。
   - 模式 C【趋势与方向】：从论文、讨论与自己笔记的缝隙中，发现经典假设正在崩溃的新战役。
   - 模式 D【本质追问】：深究为什么只能这么做，揭示底层不可打破的物理规律。
3. 极高门槛筛选：
   - 只有深度得分 depth_score >= {self.min_score} 且真正有学术价值时，才设置 has_valuable_insight: true。
   - 如果只是普通信息汇总，没有真正有价值的化学反应，务必坦诚返回 has_valuable_insight: false（宁缺毋滥，绝不打扰用户！）。

请输出标准 JSON 格式：
{{
  "has_valuable_insight": true 或 false,
  "insights": [
    {{
      "insight_type": "提出问题" 或 "底层感悟" 或 "趋势与方向" 或 "本质追问",
      "depth_score": 80到100的整数,
      "title": "一句话抓人眼球且深刻的洞察命题",
      "core_insight": "200~400字的精辟剖析，说明发现了什么矛盾、打破了什么旧规则、或提出了什么新规律",
      "philosophical_takeaway": "1~2句话的方法论升华 (如本体与载体、算力对冲带宽、时空置换)",
      "cross_sources": ["产生碰撞的论文/笔记/讨论标题1", "素材2"],
      "research_directions": ["具体可推导的形式化模型或可跑模拟器的实验方向"]
    }}
  ]
}}"""

        user_prompt = f"""以下是近期跨信源的知识素材（包含前沿论文、我自己的思考记录与知乎同行讨论）：

{materials_text[:6000]}"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content or "{}"
        data = self._parse_json(raw)

        if not data.get("has_valuable_insight"):
            logger.info("[InsightAgent] 大模型判断当前素材尚未形成具有突破性的深度洞察 (宁缺毋滥，不打扰)")
            return []

        results = []
        for item in data.get("insights", []):
            score = int(item.get("depth_score", 70))
            if score >= self.min_score:
                results.append(ExtractedInsight(
                    insight_type=item.get("insight_type", "底层感悟"),
                    depth_score=score,
                    title=item.get("title", "前沿体系结构洞察"),
                    core_insight=item.get("core_insight", ""),
                    philosophical_takeaway=item.get("philosophical_takeaway", ""),
                    cross_sources=list(item.get("cross_sources", [])),
                    research_directions=list(item.get("research_directions", []))
                ))

        logger.info(f"[InsightAgent] 成功提炼出 {len(results)} 条顶级高价值 Insight (评分均 ≥ {self.min_score})！")
        return results

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except Exception:
            m2 = re.search(r'\{[\s\S]*\}', text)
            if m2:
                try:
                    return json.loads(m2.group(0))
                except Exception:
                    pass
            return {}
