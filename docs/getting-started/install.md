# 安装

## 前置

- Python 3.11 或更高
- pip / uv
- (可选) Docker + docker-compose

## pip 安装

```bash
pip install channel-analytics
```

带 MySQL / Postgres 驱动:

```bash
pip install "channel-analytics[mysql]"
# 或
pip install "channel-analytics[postgres]"
```

带开发依赖(测试 + lint):

```bash
pip install "channel-analytics[dev]"
```

## 从源码安装

```bash
git clone https://github.com/your-org/channel-analytics
cd channel-analytics
pip install -e ".[dev]"
```

## 验证

```bash
python -c "from channel_analytics.api.app import create_app; print(create_app())"
```

输出类似 `<fastapi.applications.FastAPI object>` 即成功。