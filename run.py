"""InsightEngine 启动入口与调试脚本."""

import argparse
from loguru import logger

from engine.service import InsightEngineService
from engine.insight_agent import ExtractedInsight


def test_wechat_push(service: InsightEngineService):
    """测试企业微信 1000005 通知通道."""
    logger.info("=== 测试企业微信 1000005 洞察引擎通知通道 ===")
    fake_insight = ExtractedInsight(
        insight_type="提出问题",
        depth_score=95,
        title="在相同计算语义下，能否用 ASIC 预重排置换 DRAM 随机访存带宽？",
        core_insight=(
            "大模型 Decode 阶段的显存墙本质不是缺少浮点算力，而是细粒度 Gather/Scatter 访存打碎了 DRAM 的连续突发（Burst）。"
            "既然地址的生成在数学上具有可预测性，能否通过向内存侧下发声明式‘意图 Token’，利用极轻量的片上专用电路提前完成物理地址聚类与重排，"
            "从而彻底消解 CXL 链路的握手延迟？"
        ),
        philosophical_takeaway="AXI/CHI 只是特定苹果，信息传输的互信息与状态机可预测性才是万有引力；别在带宽死墙上撞死，用仅 2% 面积的 ASIC 片上重构彻底对冲带宽开销。",
        cross_sources=["arXiv: CXL-PIM 近存加速论文", "知乎: 存算一体落地工程瓶颈探讨", "个人笔记: 边缘端推理瓶颈主动转移范式"],
        research_directions=[
            "形式化推导在特定局部性数据流下，控制元数据与有效载荷的互信息下界",
            "在 gem5 模拟器中集成 32KB SRAM 描述符缓冲，量化评估稀疏 GEMV 下的 Row Buffer Hit 率提升"
        ]
    )
    ok = service.notifier.send_insight_notification(fake_insight)
    if ok:
        logger.success("洞察卡片已成功推送到您的个人微信与企微！请查看。")
    else:
        logger.error("推送失败，请检查配置。")


def main():
    parser = argparse.ArgumentParser(description="InsightEngine - 跨信源渐进思考与深度学术洞察提炼引擎")
    parser.add_argument("--test-wechat", action="store_true", help="测试企业微信连通性与发送洞察卡片")
    parser.add_argument("--once", action="store_true", help="单次执行全源聚合与 AI 深度思考后退出")
    parser.add_argument("--interval-hours", type=int, default=None, help="覆盖分析周期 (小时，默认 6)")

    args = parser.parse_args()

    service = InsightEngineService()

    if args.interval_hours:
        service.run_interval_hours = args.interval_hours

    if args.test_wechat:
        test_wechat_push(service)
        return

    if args.once:
        logger.info("执行单次跨信源渐进思考分析...")
        service.run_pipeline()
        logger.info("单次提炼流程完成！")
        return

    # 默认常驻守护思考
    service.run_forever()


if __name__ == "__main__":
    main()
