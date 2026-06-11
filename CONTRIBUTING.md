# 贡献指南

欢迎贡献 `channel-analytics`!🎉

## 行为准则

请阅读我们的 [行为准则](CODE_OF_CONDUCT.md)。

## 如何贡献

### 报告 Bug

用 [GitHub Issues](https://github.com/your-org/channel-analytics/issues) 报告 bug,使用 **Bug Report** 模板。

### 提出新功能

用 [GitHub Discussions](https://github.com/your-org/channel-analytics/discussions) 提出新功能想法,等待维护者反馈后再开始编码。

### 提交代码

#### 1. Fork & Clone

```bash
git clone https://github.com/your-org/channel-analytics.git
cd channel-analytics
git remote add upstream https://github.com/your-org/channel-analytics.git
```

#### 2. 创建 Feature 分支

```bash
git checkout -b feat/your-feature-name
# 或
git checkout -b fix/issue-number
```

分支命名规范:
- `feat/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 仅文档
- `refactor/xxx` - 重构
- `test/xxx` - 仅测试

#### 3. 开发

```bash
# 启动 demo
python demo.py

# 跑测试
pytest tests/unit -v
```

#### 4. 提交

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: 添加新功能描述
fix: 修复某问题
docs: 更新文档
style: 格式化代码(无功能变更)
refactor: 重构代码(无功能变更)
test: 添加/修改测试
chore: 杂项(依赖、CI 等)
```

示例:
```bash
git commit -m "feat: 添加新的销售报表权限检查"
git commit -m "fix: 修复 ETL pipeline 在 SQLite 下的类型错误"
```

#### 5. 推送 & 创建 PR

```bash
git push origin feat/your-feature-name
```

然后到 GitHub 创建 Pull Request,使用 **PR 模板** 填写。

### 代码规范

- **Python**: 遵循 PEP 8,使用 `black` / `ruff` 格式化
- **Vue**: 遵循 Vue 3 官方风格指南
- **TypeScript**: `strict: true` 已启用
- **测试**: 新功能必须包含单元测试,覆盖率 ≥ 80%
- **文档**: 新增 API 需更新 `docs/`

### Commit 前自检

- [ ] `pytest tests/unit` 全部通过
- [ ] 新增/修改的功能有对应测试
- [ ] 没有新增 `print()` / `console.log()` 调试代码
- [ ] 没有真实凭据/品牌名/IP
- [ ] Commit 信息遵循 Conventional Commits
- [ ] 如果是 UI 变更,附上截图

## 开发流程

```
Fork → Clone → Branch → Code → Test → Commit → Push → PR → Review → Merge
```

所有 PR 必须经过:

1. ✅ CI 全部通过(`pytest`, `gitleaks`, `check_branding`, `detect_pii`)
2. ✅ 1 个以上维护者 Review
3. ✅ 无冲突(自动 rebase)
4. ✅ 覆盖率不下降

## 提交 PR 后

- 我们会在 5 个工作日内 Review
- 可能会要求修改
- 合并后你的贡献会出现在 [CHANGELOG.md](CHANGELOG.md)

## 联系方式

有问题? 提 [Issue](https://github.com/your-org/channel-analytics/issues) 或加入 [Discussions](https://github.com/your-org/channel-analytics/discussions)。

---

感谢你的贡献!❤️
