"""
邮件发送工具模块
使用标准库 smtplib，无需安装第三方依赖
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from sqlalchemy import text

logger = logging.getLogger(__name__)


def _get_smtp_config(db) -> dict:
    """从 sys_config 读取 SMTP 配置"""
    config = {}
    for key in ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_default_to"]:
        row = db.execute(text("SELECT config_value FROM sys_config WHERE config_key=:k"), {"k": key}).fetchone()
        config[key] = row[0] if row and row[0] else ""
    config["smtp_port"] = int(config["smtp_port"]) if config["smtp_port"] else 465
    return config


def send_email(
    db,
    subject: str,
    body: str,
    to: Optional[List[str]] = None,
    html: bool = False,
) -> bool:
    """
    发送邮件

    Args:
        db: SQLAlchemy Session
        subject: 邮件主题
        body: 邮件正文
        to: 收件人列表，为空时使用 smtp_default_to
        html: 是否为 HTML 格式

    Returns:
        是否发送成功
    """
    cfg = _get_smtp_config(db)

    if not cfg["smtp_host"] or not cfg["smtp_user"]:
        logger.warning("SMTP 未配置，跳过邮件发送")
        return False

    # 收件人
    recipients = to or [addr.strip() for addr in cfg["smtp_default_to"].split(",") if addr.strip()]
    if not recipients:
        logger.warning("无收件人，跳过邮件发送")
        return False

    # 构建邮件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_user"]
    msg["To"] = ", ".join(recipients)

    subtype = "html" if html else "plain"
    msg.attach(MIMEText(body, subtype, "utf-8"))

    # 发送
    try:
        port = cfg["smtp_port"]
        if port == 465:
            # SSL
            with smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=15) as server:
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(cfg["smtp_user"], recipients, msg.as_string())
        else:
            # TLS (587 等)
            with smtplib.SMTP(cfg["smtp_host"], port, timeout=15) as server:
                server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_password"])
                server.sendmail(cfg["smtp_user"], recipients, msg.as_string())

        logger.info(f"邮件发送成功: {subject} -> {recipients}")
        return True

    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def notify_rpa_result(db, task_name: str, module_name: str, status: str,
                      duration_sec: int = 0, error_msg: str = "",
                      file_path: str = "", task_recipients: Optional[List[str]] = None):
    """
    RPA 任务结果通知

    Args:
        db: SQLAlchemy Session
        task_name: 任务名称
        module_name: 模块名称
        status: success / failed
        duration_sec: 耗时秒数
        error_msg: 错误信息
        file_path: 文件路径
        task_recipients: 任务级收件人（逗号分隔字符串），为空时用全局默认
    """
    # 收件人：任务级 > 全局默认
    to = None
    if task_recipients:
        to = [addr.strip() for addr in task_recipients.split(",") if addr.strip()]

    # 只有失败时发通知（成功不发，避免骚扰）
    if status == "success":
        return

    status_text = "✅ 成功" if status == "success" else "❌ 失败"
    duration_text = f"{duration_sec}秒" if duration_sec else "-"

    subject = f"[RPA采集] {module_name} {status_text}"

    body = f"""RPA 采集任务执行结果

任务名称: {task_name}
采集模块: {module_name}
执行结果: {status_text}
执行耗时: {duration_text}
"""
    if file_path:
        body += f"文件路径: {file_path}\n"
    if error_msg:
        # 截断过长的错误信息
        short_err = error_msg[:500] + "..." if len(error_msg) > 500 else error_msg
        body += f"\n错误详情:\n{short_err}\n"

    body += "\n-- 数据分析平台 RPA 自动通知"

    send_email(db, subject, body, to=to)
