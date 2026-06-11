# 架构决策记录(ADR)

每个重要决策写一份 ADR。

## 模板

```
# ADR-NNN: 标题

## 状态
提议 / 已采纳 / 已废弃 / 替代

## 背景
什么问题

## 决策
选了什么方案

## 后果
正面 / 负面 / 中性
```

## 现有 ADR

(暂无,W7 末补充第一份)

## 候选主题

- ADR-001: 选 Apache-2.0 而非 MIT
- ADR-002: 业务硬编码抽成 YAML 而非 DB
- ADR-003: RPA adapter 用 entry_points 而非手写注册表
- ADR-004: ETL Pipeline 12 步骤而非 SQLAlchemy ORM 反射
- ADR-005: 默认 brand provider 返回空集而非 hardcode 白名单