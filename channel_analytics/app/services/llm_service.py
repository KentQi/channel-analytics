"""
LLM 服务 - 调用 MiniMax API 生成商品生命周期运营建议
使用 Anthropic 兼容接口，base_url 指向 MiniMax

配置优先级：数据库 sys_config > 环境变量 > 默认值
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# 默认配置（当数据库和环境变量都没有时使用）
_DEFAULT_BASE_URL = "https://api.minimaxi.com/anthropic"
_DEFAULT_MODEL = "MiniMax-M3"

# 缓存的配置（避免每次都查数据库）
_cached_config: Optional[dict] = None
_client = None  # OpenAI client instance (延迟初始化)


def _load_config_from_db() -> Optional[dict]:
    """从数据库 sys_config 表读取 LLM 配置"""
    try:
        from sqlalchemy import text
        from app.database import MainSessionLocal

        db = MainSessionLocal()
        try:
            # 检查表是否存在
            table_exists = db.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = 'sys_config'"
            )).scalar()

            if not table_exists:
                return None

            rows = db.execute(text(
                "SELECT config_key, config_value FROM sys_config "
                "WHERE config_key IN ('minimax_api_key', 'minimax_base_url', 'minimax_model')"
            )).fetchall()

            if not rows:
                return None

            config = {row[0]: row[1] for row in rows}
            return config
        finally:
            db.close()
    except Exception as e:
        logger.debug(f"从数据库读取LLM配置失败: {e}")
        return None


def _get_config() -> dict:
    """
    获取 LLM 配置（带缓存）

    优先级：数据库 > 环境变量 > 默认值
    """
    global _cached_config

    if _cached_config is not None:
        return _cached_config

    # 尝试从数据库读取
    db_config = _load_config_from_db()

    api_key = ""
    base_url = _DEFAULT_BASE_URL
    model = _DEFAULT_MODEL

    if db_config:
        api_key = db_config.get("minimax_api_key", "") or ""
        base_url = db_config.get("minimax_base_url", "") or _DEFAULT_BASE_URL
        model = db_config.get("minimax_model", "") or _DEFAULT_MODEL

    # 环境变量作为补充/覆盖
    if not api_key:
        api_key = os.getenv("MINIMAX_API_KEY", "")
    if base_url == _DEFAULT_BASE_URL:
        env_url = os.getenv("MINIMAX_BASE_URL")
        if env_url:
            base_url = env_url
    if model == _DEFAULT_MODEL:
        env_model = os.getenv("MINIMAX_MODEL")
        if env_model:
            model = env_model

    _cached_config = {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }
    return _cached_config


def invalidate_config_cache():
    """清除配置缓存（配置更新后调用）"""
    global _cached_config, _client
    _cached_config = None
    _client = None


def _get_client():
    global _client
    config = _get_config()

    if not config["api_key"]:
        raise ValueError("未配置 MiniMax API Key，请在【API配置 > 大模型API配置】中设置")

    # 如果配置变了，重新创建客户端
    if _client is not None:
        if getattr(_client, '_api_key', None) != config["api_key"] or \
           getattr(_client, '_base_url', None) != config["base_url"]:
            _client = None

    if _client is None:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("请安装 anthropic 包: pip install anthropic")
        _client = Anthropic(
            api_key=config["api_key"],
            base_url=config["base_url"],
        )
    return _client


SYSTEM_PROMPT = """你是一位资深供应链管理专家和零售数据分析顾问。
你需要根据商品的生命周期阶段和销售数据指标，给出具体、可执行的运营建议。

要求：
1. 建议必须具体、可执行，不要泛泛而谈
2. 必须基于数据指标给出，体现数据驱动
3. 从以下维度给出建议（根据阶段选择最相关的3-5条）：
   - 采购/库存策略（备货量、补货频率、安全库存）
   - 销售/渠道策略（铺货、促销、渠道拓展）
   - 风险提示（滞销、断货、竞品威胁）
   - 关键监控指标（需要重点关注的数据变化）
4. 每条建议简洁有力，一句话概括
5. 使用中文回复"""


def generate_lifecycle_advice(
    material_name: str,
    material_code: str,
    plc_stage: str,
    sub_stage: str,
    cumulative_out_qty: int,
    total_amount: float,
    growth_rate: float,
    sales_acceleration: float,
    customer_penetration: float,
    cv: float,
    days_since_launch: int,
    abc_class: str,
    consecutive_negative_months: int,
    avg_monthly_qty: float,
) -> str:
    """
    调用 MiniMax LLM 生成个性化商品生命周期运营建议

    Args:
        material_name: 商品名称
        material_code: 物料编码
        plc_stage: PLC阶段（导入期/成长期/成熟期/衰退期）
        sub_stage: 子阶段（试销期/爬坡期/稳定期/加速增长/稳定增长/增长放缓等）
        cumulative_out_qty: 累计出库量
        total_amount: 累计销售额
        growth_rate: 环比增长率
        sales_acceleration: 销售加速度
        customer_penetration: 客户渗透率
        cv: 需求稳定性变异系数
        days_since_launch: 上市天数
        abc_class: ABC分类
        consecutive_negative_months: 连续负增长月数
        avg_monthly_qty: 月均销量

    Returns:
        LLM 生成的运营建议文本
    """
    # 格式化指标
    growth_pct = f"{growth_rate * 100:.1f}%" if growth_rate else "N/A"
    accel_str = f"{sales_acceleration:+.2f}" if sales_acceleration else "0"
    pen_pct = f"{customer_penetration * 100:.1f}%" if customer_penetration else "N/A"
    cv_str = f"{cv:.2f}" if cv else "N/A"

    if cv is not None:
        if cv < 0.3:
            cv_desc = "非常稳定"
        elif cv < 0.5:
            cv_desc = "较稳定"
        elif cv < 1.0:
            cv_desc = "波动较大"
        else:
            cv_desc = "波动剧烈"
    else:
        cv_desc = "数据不足"

    user_prompt = f"""请为以下商品生成运营建议：

【基本信息】
- 商品：{material_name}（{material_code}）
- ABC分类：{abc_class or '未分类'}
- 上市天数：{days_since_launch}天

【生命周期阶段】
- 主阶段：{plc_stage}
- 子阶段：{sub_stage}

【核心指标】
- 累计出库量：{cumulative_out_qty:,} 件
- 累计销售额：{total_amount:,.0f} 元
- 月均销量：{avg_monthly_qty:,.0f} 件
- 环比增长率（近3月均值）：{growth_pct}
- 销售加速度：{accel_str}
- 客户渗透率：{pen_pct}
- 需求稳定性（CV）：{cv_str}（{cv_desc}）
- 连续负增长月数：{consecutive_negative_months} 月

请给出3-5条具体可执行的运营建议。"""

    try:
        config = _get_config()
        client = _get_client()
        response = client.messages.create(
            model=config["model"],
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        # 处理不同类型的响应块（TextBlock、ThinkingBlock等）
        content = None
        if response.content:
            for block in response.content:
                if hasattr(block, 'text'):
                    content = block.text
                    break
        tokens_info = ""
        if response.usage:
            tokens_info = f", tokens={response.usage.input_tokens + response.usage.output_tokens}"
        logger.info(f"LLM建议生成成功: {material_code}{tokens_info}")
        return content.strip() if content else "暂无建议"

    except ValueError as e:
        # 未配置 API Key
        logger.warning(str(e))
        return f"（{str(e)}）"

    except Exception as e:
        logger.error(f"LLM建议生成失败: {e}", exc_info=True)
        return f"（建议生成失败: {str(e)[:100]}）"
