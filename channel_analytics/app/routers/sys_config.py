"""
系统配置API路由
提供大模型API配置等系统级配置的读取和更新
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sys-config", tags=["系统配置"])


class LlmConfigRequest(BaseModel):
    """大模型API配置请求"""
    minimax_api_key: Optional[str] = None
    minimax_base_url: Optional[str] = None
    minimax_model: Optional[str] = None


def _ensure_table(db: Session):
    """确保 sys_config 表存在"""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS sys_config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT,
            description VARCHAR(255),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_config_key (config_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='系统配置表'
    """))
    db.commit()


def _get_config_value(db: Session, key: str) -> Optional[str]:
    """获取单个配置值"""
    result = db.execute(
        text("SELECT config_value FROM sys_config WHERE config_key = :key"),
        {"key": key}
    ).fetchone()
    return result[0] if result else None


def _set_config_value(db: Session, key: str, value: str, description: str = ""):
    """设置单个配置值（upsert）"""
    db.execute(text("""
        INSERT INTO sys_config (config_key, config_value, description, updated_at)
        VALUES (:key, :value, :desc, NOW())
        ON DUPLICATE KEY UPDATE config_value = :value, updated_at = NOW()
    """), {"key": key, "value": value, "desc": description})


@router.get("/llm")
async def get_llm_config(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    获取大模型API配置

    需要admin或创建人权限
    """
    if user.role not in ("admin", "创建人"):
        raise HTTPException(status_code=403, detail="仅管理员可查看API配置")

    _ensure_table(db)

    api_key = _get_config_value(db, "minimax_api_key") or ""
    base_url = _get_config_value(db, "minimax_base_url") or "https://api.minimaxi.com/anthropic"
    model = _get_config_value(db, "minimax_model") or "MiniMax-M3"

    # 脱敏：只显示前8位和后4位
    masked_key = ""
    if api_key:
        if len(api_key) > 12:
            masked_key = api_key[:8] + "****" + api_key[-4:]
        else:
            masked_key = "****"

    return {
        "data": {
            "minimax_api_key": masked_key,
            "minimax_api_key_set": bool(api_key),
            "minimax_base_url": base_url,
            "minimax_model": model,
        }
    }


@router.put("/llm")
async def update_llm_config(
    request: LlmConfigRequest,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    更新大模型API配置

    需要admin或创建人权限
    """
    if user.role not in ("admin", "创建人"):
        raise HTTPException(status_code=403, detail="仅管理员可修改API配置")

    _ensure_table(db)

    updated_fields = []

    if request.minimax_api_key is not None:
        # 如果传入的是脱敏值（包含****），则不更新
        if "****" not in request.minimax_api_key:
            _set_config_value(db, "minimax_api_key", request.minimax_api_key, "MiniMax API密钥")
            updated_fields.append("api_key")

    if request.minimax_base_url is not None:
        _set_config_value(db, "minimax_base_url", request.minimax_base_url, "MiniMax API地址")
        updated_fields.append("base_url")

    if request.minimax_model is not None:
        _set_config_value(db, "minimax_model", request.minimax_model, "MiniMax模型名称")
        updated_fields.append("model")

    db.commit()

    # 清除LLM服务的配置缓存，使其下次使用新配置
    from app.services.llm_service import invalidate_config_cache
    invalidate_config_cache()

    logger.info(f"用户 {user.username} 更新了LLM配置: {updated_fields}")
    return {"message": "配置已保存", "updated": updated_fields}


@router.post("/llm/test")
async def test_llm_connection(
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """
    测试大模型API连接

    需要admin或创建人权限
    """
    if user.role not in ("admin", "创建人"):
        raise HTTPException(status_code=403, detail="仅管理员可测试API连接")

    _ensure_table(db)

    api_key = _get_config_value(db, "minimax_api_key")
    base_url = _get_config_value(db, "minimax_base_url") or "https://api.minimaxi.com/anthropic"
    model = _get_config_value(db, "minimax_model") or "MiniMax-M3"

    if not api_key:
        raise HTTPException(status_code=400, detail="未配置API Key")

    try:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise HTTPException(status_code=500, detail="请安装 anthropic 包: pip install anthropic")
        client = Anthropic(api_key=api_key, base_url=base_url)
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[
                {"role": "user", "content": "回复OK即可"},
            ],
        )
        # 处理不同类型的响应块（TextBlock、ThinkingBlock等）
        content = ""
        if response.content:
            for block in response.content:
                if hasattr(block, 'text'):
                    content = block.text
                    break
                elif hasattr(block, 'thinking'):
                    # ThinkingBlock，跳过继续找TextBlock
                    continue
        tokens_used = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
        return {
            "data": {
                "success": True,
                "message": f"连接成功！模型回复: {content.strip()[:50]}",
                "model": model,
                "tokens_used": tokens_used,
            }
        }
    except Exception as e:
        logger.error(f"LLM连接测试失败: {e}")
        return {
            "data": {
                "success": False,
                "message": f"连接失败: {str(e)[:200]}",
            }
        }
