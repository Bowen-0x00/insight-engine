# InsightEngine - 跨信源渐进思考与深度洞察提炼引擎

[中文文档](README.md) | [English Documentation](README_EN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![LLM: Multi_Provider](https://img.shields.io/badge/LLM-Multi--Provider--Failover-green.svg)](https://platform.openai.com/)

**InsightEngine** 是一个顶层的个人科研与技术洞察智能引擎。
它将分散在三个不同管道的被动信息源进行跨域聚合：
1. **邮件学术推送与顶会论文**（arXiv / Google Scholar Alerts / 工作沟通）
2. **个人微信随手记与长文收藏**（Obsidian 知识收集箱、个人碎片灵感）
3. **社交雷达前沿动态**（知乎技术大牛动态、高价值专业问答讨论）

通过大语言模型（LLM）注入**系统架构底层研究哲学**进行**多源渐进思考（Progressive Thinking & Cross-Pollination）**。秉持**“宁缺毋滥、绝不打扰”**的严苛原则，唯有跨源碰撞出触及本质、真正具备学术突破性的顶级 Insight 时（深度评分 $\ge 80$ 分），才会通过企业微信（应用 1000005）推送到用户手机，并自动追加沉淀到 Obsidian 知识库中。

---

## ✨ 核心特性

- 🧠 **跨信源渐进思考与灵感碰撞 (Cross-Pollination)**：
  - 打破单一渠道的信息孤岛，将顶会论文、同行一线讨论与个人沉淀笔记进行多维交叉比对。
  - 例如：将一篇关于 *CXL 内存池化* 的 arXiv 论文，与知乎上关于 *存算一体落地瓶颈* 的讨论，结合用户个人关于 *PagedAttention 硬件 MMU* 的随手记碰撞，产生全新的技术架构假设。
- 🎯 **四大经典 Insight 输出形态**：
  - **模式 A【提出问题 / Sharp Question】**：提出直击痛点的技术设问（如：*在相同语义下，能否用比通用核心更低的硬件成本提前形成并保留更多可合法重排的访存地址？*）。
  - **模式 B【底层感悟 / First-Principle Insight】**：第一性原理思考、算力对冲带宽范式（用仅 2% 面积的片上专用 ASIC 解码对冲物理互连死墙）、白盒与黑盒边界。
  - **模式 C【趋势与方向 / Paradigm Shift】**：寻找经典假设（规则实心网格、双层SRAM-DRAM、2D硅片）崩溃后的全新战役。
  - **模式 D【本质追问 / Root-Cause “Why”】**：穿透表象解释根本原因（如：*AXI/CHI 只是苹果，通信元数据与有效载荷互信息规律才是万有引力*）。
- 🛡️ **双大模型主备容灾与微信热切换 (High Availability)**：
  - 内置 Primary 与 Secondary 双通道自动故障转移。主通道超时或失效时自动平滑切换到备用通道。
  - 微信对话框直接支持发送 `/llm secondary` 一键切换，发送 `/setkey <Key>` 动态更新密钥！
- 🍪 **知乎爬虫失效感知与微信免登热换 Cookie**：
  - 当社交雷达爬虫遭遇凭据过期或风控时，系统主动向微信推送告警。
  - 用户无需远程 SSH 登录服务器，直接在微信回复 `/cookie <新Cookie>` 即可热更新并自动生效！
- 📝 **Obsidian 自动化知识沉淀**：
  - 提炼出的高分洞察自动生成标准 Markdown Callout 卡片，追加写入 Obsidian Vault。

---

## 🏗️ 系统架构图

```
[ 信源 1: 邮件与学术推送 ]       [ 信源 2: 微信长文与随手记 ]       [ 信源 3: 知乎大牛动态与问答 ]
  (mail_assist.db)               (inbox.db)                      (social_radar.db)
          │                               │                               │
          └───────────────────────────────┼───────────────────────────────┘
                                          ▼
                     ┌────────────────────────────────────────┐
                     │ 1. 统一跨源知识中枢 (Knowledge Hub)    │
                     │    - 提取最近 48~72 小时跨源增量数据   │
                     │    - 标准化为 SourceKnowledgeItem      │
                     └────────────────────┬───────────────────┘
                                          ▼
                     ┌────────────────────────────────────────┐
                     │ 2. 渐进思考与哲学碰撞 (Insight Agent)  │
                     │    - 注入体系结构心法与自检清单三大战役│
                     │    - 多 Provider 主备容灾 (Gemini/DS)  │
                     │    - 提炼 4 种经典 Insight 模式        │
                     └────────────────────┬───────────────────┘
                                          ▼
                     ┌────────────────────────────────────────┐
                     │ 3. 极高门槛过滤 (Zero Noise Filter)    │
                     │    - 深度评分 ≥ 80 分才放行            │
                     │    - 否则完全静默 (宁缺毋滥，绝不打扰) │
                     └────────────────────┬───────────────────┘
                                          ▼
                     ┌────────────────────────────────────────┐
                     │ 4. 微信推送与本地沉淀                  │
                     │    - 企微 Markdown + 个人微信 Textcard │
                     │    - 自动追加写入 Obsidian 灵感库      │
                     └────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 克隆与安装依赖
```bash
git clone https://github.com/Bowen-0x00/insight-engine.git
cd insight-engine

pip install -r requirements.txt
```

### 2. 准备配置
```bash
cp config/config.example.yaml config/config.yaml
```

编辑 `config/config.yaml` 填入您的企业微信应用（1000005）凭据、主备大模型 API Key 以及三个上游数据库路径。

### 3. 运行与验证
```bash
# 1. 测试企业微信 1000005 洞察通知通道
python run.py --test-wechat

# 2. 单次执行全信源跨界渐进思考并输出洞察
python run.py --once

# 3. 启动后台常驻守护思考 (默认每 6 小时提炼一次)
python run.py
```

---

## 💬 微信对话框快捷指令指南

直接在微信的“洞察引擎”应用对话框中发送以下命令，系统秒级响应：

| 指令 | 别名 | 功能说明 | 示例 |
| :--- | :--- | :--- | :--- |
| **`/insight`** | `提炼` / `思考` | **立即触发全源深度碰撞与洞察提炼** | 发送 `/insight` |
| **`/status`** | `状态` | 检查大模型主备健康度、三大数据库联通状态 | 发送 `/status` |
| **`/llm <通道>`** | `切换模型` | **一键热切换大模型通道**（`primary` 或 `secondary`） | 发送 `/llm secondary` |
| **`/setkey <Key>`**| `设置密钥` | 动态热更新当前大模型通道的 API Key | 发送 `/setkey sk-xxx` |
| **`/testllm`** | `测试模型` | 实时测试大模型连通性与耗时 | 发送 `/testllm` |
| **`/cookie <Cookie>`**| `更新知乎` | **免登录服务器，直接在微信热更新知乎 Cookie** | 发送 `/cookie _xsrf=...` |
| **`/score <分数>`** | `阈值` | 调整洞察推送门槛（默认 80 分，宁缺毋滥） | 发送 `/score 85` |
| **`/help`** | `帮助` | 获取完整指令手册 | 发送 `/help` |

---

## 📂 项目结构

```
insight_extractor/
├── config/
│   ├── config.example.yaml          # 配置模板 (微信凭据、主备LLM、三库路径)
│   └── architecture_philosophy.yaml # 核心体系结构研究心法与自检清单知识库
├── engine/
│   ├── knowledge_hub.py             # 跨源知识聚合中枢 (连接三大数据库)
│   ├── insight_agent.py             # 渐进思考与深度洞察提炼核心 Agent
│   ├── notifier.py                  # 微信时序双通道推送分发器
│   ├── command_receiver.py          # 微信交互调参、模型切换与Cookie热更控制中心
│   ├── storage.py                   # SQLite 洞察归档与去重
│   └── service.py                   # 业务编排主控制器与命令监听服务
├── deploy/
│   └── insight_extractor.service    # Linux Systemd 守护服务单元
├── tests/
│   └── test_insight.py              # 单元与功能自动化测试
├── run.py                           # CLI 启动与调试入口
├── sync_to_aliyun.py                # 一键代码同步云端工具
├── sync_to_aliyun.bat               # Windows 双击一键同步批处理
├── requirements.txt                 # 依赖清单
├── LICENSE                          # MIT 开源许可证
└── README.md
```

---

## 📄 开源许可证

本项目采用 [MIT License](LICENSE) 许可证。
