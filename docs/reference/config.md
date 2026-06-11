# 配置项

通过 `.env` 文件或环境变量设置。

## 必填

| 变量 | 说明 |
|------|------|
| `SESSION_SECRET` | session 加密密钥(64 字符随机串) |
| `JWT_SECRET` | JWT 签发密钥(64 字符随机串) |
| `DATABASE_URL` | SQLAlchemy 连接串 |

`SESSION_SECRET` / `JWT_SECRET` 必须是真实值,占位符 `GENERATE-ON-FIRST-RUN` 会触发 `RefuseToStart` 异常。

```bash
channel-analytics init-secrets  # 自动生成
```

## 数据库

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./data/dev.db` | sqlite / mysql+pymysql / postgresql+psycopg |

## 应用

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_ENV` | `development` | development / staging / production |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `DEFAULT_TIMEZONE` | `Asia/Shanghai` | APScheduler 时区 |

## RPA

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RPA_ADAPTER` | `channel_analytics.rpa.adapters.example_minimal:ExampleMinimalAdapter` | ErpAdapter 路径 |
| `RPA_TARGET_URL` | 空 | 登录 URL |
| `RPA_USERNAME` | 空 | 登录账号 |
| `RPA_PASSWORD` | 空(可空) | 登录密码(SecretStr) |
| `RPA_DOWNLOAD_DIR` | `./data/rpa_downloads` | 下载目录 |
| `RPA_HEADLESS` | `true` | 是否无头浏览器 |
| `RPA_TIMEOUT_MS` | `30000` | Playwright 默认超时 |
| `RPA_SLOW_MO_MS` | `300` | Playwright slow_mo |

## ETL

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BRAND_PROVIDER` | `channel_analytics.etl.providers.example_minimal:ExampleMinimalProvider` | Brand provider 路径 |
| `BUSINESS_RULES_PATH` | 空 | business_rules.yaml 路径(空 = 用代码内默认) |

## SMTP(可选)

| 变量 | 说明 |
|------|------|
| `SMTP_HOST` | SMTP 服务器 |
| `SMTP_PORT` | 端口(默认 587) |
| `SMTP_USERNAME` | 账号 |
| `SMTP_PASSWORD` | 密码 |
| `SMTP_FROM` | 发件人 |
| `SMTP_TO` | 收件人 |

## 数据库 schema 演进

`BUSINESS_RULES_PATH` / `BRAND_PROVIDER` 改完无需重启服务(Pipeline 每次跑时重读)。