# 安全扫描工具(W1)

本目录是 **W1 净化 & 安全** 阶段产出的扫描工具集,用于开源化前对原仓库做脱敏体检。

## 工具清单

| 脚本 | 用途 | 退出码 |
|------|------|--------|
| `check_branding.py` | 扫描品牌痕迹(自营品牌名 / 员工账号 / 客户代号 / 严格模式扫 ERP 厂商) | 0=clean, 1=hit, 2=config err |
| `detect_pii.py` | 扫描 PII(手机/身份证/邮箱/银行卡/IPv4/内部账号) | 同上 |
| `../.gitleaks.toml` | gitleaks 加严规则(本项目特定 JWT/DB/RPA + 通用云凭据) | gitleaks 自己定 |

## 安装

```bash
pip install pyyaml  # check_branding + detect_pii 共用依赖
# gitleaks 单独装
# Windows: winget install gitleaks
# macOS:   brew install gitleaks
# Linux:   https://github.com/gitleaks/gitleaks/releases
```

## 关键词配置(本仓不进)

`check_branding.py` 和 `detect_pii.py` 共享**同一份关键词 YAML**,该文件 **绝对不进入开源仓**,
**也不要放在仓内任何位置**(哪怕在 .gitignore 里)—— 误操作 / 云盘同步 / 编辑器索引都可能带出。

按 PLAN.md §6 P0 要求:"关键词列表本身不进入开源仓,放在构建脚本的私有配置里"。

| 位置 | 说明 |
|------|------|
| `scripts/branding_keywords.example.yaml` | 模板,只有占位(进开源仓) |
| `~/.config/channel-analytics/branding_keywords.yaml` | 跨项目共享的真实词条(**仓外**) |
| `<your-任意位置>/brand_words.yaml` | 你自己的私有路径,通过 `--keywords` 传入 |

**绝不要**把真实词条写到 `C:\opensource\channel-analytics\`(本仓根)或任何子目录。

## 快速使用

### 1. 准备仓外词条

```bash
# ⚠️ 真实词条必须在仓外(避开 OneDrive / 任何云盘)
mkdir -p ~/.config/channel-analytics
cp /c/opensource/channel-analytics/scripts/branding_keywords.example.yaml \
   ~/.config/channel-analytics/branding_keywords.yaml
# 编辑 ~/.config/.../branding_keywords.yaml 填入真实词条
```

### 2. 跑品牌扫描

```bash
# 在私有仓库上跑品牌扫描(路径替换为你的私有仓库路径)
python scripts/check_branding.py \
  --root <your-private-repo-path> \
  --keywords ~/.config/channel-analytics/branding_keywords.yaml \
  --json > /tmp/branding.json
```

可选 `--strict` 启用 ERP 厂商字符串扫描。

### 3. 跑 PII 扫描

```bash
python scripts/detect_pii.py \
  --root <your-private-repo-path>/etl_data \
  --root <your-private-repo-path>/uploads \
  --root <your-private-repo-path>/logs \
  --keywords ~/.config/channel-analytics/branding_keywords.yaml \
  --json > /tmp/pii.json
```

### 4. 跑 gitleaks

```bash
# 历史扫描(扫整个 working tree)
gitleaks detect --config .gitleaks.toml --no-git --source <your-private-repo-path> -v

# 增量扫描(PR 阶段)
gitleaks protect --config .gitleaks.toml --staged
```

## CI 接入(W7)

`.github/workflows/ci.yml` 计划包含两个 step:

```yaml
- name: Brand scan (fail-closed)
  run: |
    python scripts/check_branding.py \
      --root . \
      --keywords ${{ secrets.BRANDING_KEYWORDS_PATH }}

- name: Gitleaks
  uses: gitleaks/gitleaks-action@v2
  env:
    GITLEAKS_CONFIG: .gitleaks.toml
```

## W1 末验证

按 PLAN.md §10 末节:

```bash
python scripts/check_branding.py --root . && \
  gitleaks detect --config .gitleaks.toml --no-git && \
  python scripts/detect_pii.py --root ./etl_data --root ./uploads --root ./logs
```

三项全 0 命中 → W1 完成。
