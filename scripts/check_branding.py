#!/usr/bin/env python3
"""
check_branding.py — 品牌痕迹扫描器

扫描代码库中的:
  1. 已知自营品牌(12 个,硬编码在原仓 etl_service.py:27-31)
  2. 内部员工/客户账号
  3. 严格模式下常见 ERP 厂商字符串

退出码:
  0 — 零命中
  1 — 有命中(阻断 CI)
  2 — 配置错误

设计要点(对应 PLAN.md §6 P0):
  - 关键词列表从外部 YAML 加载,文件不进开源仓(参见 README 与 §304/§442)
  - 支持子串匹配 + 忽略大小写
  - 支持忽略路径(Git LFS / 截图 / 调试快照)
  - 输出:文本报告(默认)/ JSON 报告(--json)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeywordGroup:
    """一组同类型的关键词(品牌/账号/客户/厂商)。"""
    type_label: str
    words: tuple[str, ...]


@dataclass
class Hit:
    file: Path
    line_no: int
    line_text: str
    matched_word: str
    type_label: str

    def excerpt(self, width: int = 60) -> str:
        """截取命中点左右 width 字符作为预览(中文按 1 字计)。"""
        text = self.line_text.strip()
        if len(text) <= width * 2 + 6:
            return text
        idx = text.lower().find(self.matched_word.lower())
        if idx < 0:
            return text[: width * 2 + 3] + "..."
        start = max(0, idx - width)
        end = min(len(text), idx + len(self.matched_word) + width)
        return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")


@dataclass
class ScanReport:
    hits: list[Hit] = field(default_factory=list)
    scanned_files: int = 0
    skipped_files: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.hits

    def by_type(self) -> dict[str, list[Hit]]:
        out: dict[str, list[Hit]] = {}
        for h in self.hits:
            out.setdefault(h.type_label, []).append(h)
        return out


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """加载关键词配置。

    优先级:
      1. --keywords 显式指定
      2. scripts/branding_keywords.local.yaml  (本地真实词条, .gitignore)
      3. scripts/branding_keywords.example.yaml  (占位模板, 无词条)
    """
    if not path.exists():
        # 回退到 local / example
        script_dir = Path(__file__).parent
        for fallback in (script_dir / "branding_keywords.local.yaml",
                         script_dir / "branding_keywords.example.yaml"):
            if fallback.exists():
                print(f"WARN: --keywords not given, falling back to {fallback}", file=sys.stderr)
                path = fallback
                break
        else:
            print(f"ERROR: keyword config not found: {path}", file=sys.stderr)
            sys.exit(2)
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        print(f"ERROR: invalid YAML in {path}", file=sys.stderr)
        sys.exit(2)
    return cfg


def build_keyword_groups(cfg: dict) -> list[KeywordGroup]:
    """把 YAML 配置摊平成 KeywordGroup 列表。"""
    groups: list[KeywordGroup] = []

    for word in cfg.get("known_brands", []):
        groups.append(KeywordGroup("brand", (str(word),)))

    for word in cfg.get("internal_accounts", []):
        groups.append(KeywordGroup("account", (str(word),)))

    for word in cfg.get("customer_codes", []):
        groups.append(KeywordGroup("customer", (str(word),)))

    if cfg.get("strict_mode", False):
        for word in cfg.get("erp_vendors_strict", []):
            groups.append(KeywordGroup("vendor", (str(word),)))

    return groups


# ---------------------------------------------------------------------------
# 路径过滤
# ---------------------------------------------------------------------------

def should_skip(path: Path, ignore_patterns: list[str], root: Path) -> bool:
    """判断 path 是否在忽略列表中(支持 glob 与子目录匹配)。"""
    try:
        rel = path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
    except ValueError:
        rel = path.as_posix()
    parts = rel.split("/")
    for pat in ignore_patterns:
        # 目录前缀匹配:pat 以 / 结尾时,匹配 "pat" 自身或以 "/pat" 开头的路径
        # 同时匹配路径中任意位置(支持 frontend/node_modules/...)
        if pat.endswith("/"):
            dir_name = pat.rstrip("/")
            if dir_name in parts or rel.startswith(pat) or (rel + "/") == pat:
                return True
        # glob 匹配文件名(比如 *.png)
        if fnmatch.fnmatch(path.name, pat):
            return True
        # glob 匹配整个相对路径
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


def iter_target_files(root: Path, ignore_patterns: list[str]) -> Iterable[Path]:
    """遍历 root 下所有文本文件(白名单扩展名),应用忽略规则。"""
    text_exts = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".md", ".txt",
        ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
        ".html", ".css", ".scss", ".sh", ".bat", ".sql", ".env",
        ".gitignore", ".dockerignore", ".editorconfig",
    }
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in text_exts and p.name not in {
            "Dockerfile", "Makefile", "LICENSE", "NOTICE",
        }:
            continue
        if should_skip(p, ignore_patterns, root):
            continue
        yield p


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------

def scan_file(path: Path, groups: list[KeywordGroup]) -> list[Hit]:
    """扫描单个文件,返回所有命中。

    匹配规则:
      - 大小写不敏感子串匹配
      - 英文关键词长度 >= 3 时,要求单词边界(\b),避免 'roze' 命中 'frozen'  # example:brand
      - 中文关键词(任何 Unicode > U+4E00)不做边界处理
    """
    hits: list[Hit] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"WARN: cannot read {path}: {e}", file=sys.stderr)
        return hits

    def _is_chinese(s: str) -> bool:
        return any("一" <= ch <= "鿿" for ch in s)

    # 注释行中的反例文档(避免 false positive)
    # 用法: 在行尾加 "  # example:brand" 或行首以该标记开头
    example_brand_re = re.compile(r"#\s*example\s*:\s*brand", re.IGNORECASE)

    word_boundary_re_cache: dict[str, re.Pattern[str]] = {}

    for line_no, line in enumerate(text.splitlines(), start=1):
        line_lower = line.lower()
        # 含 "# example:brand" 标记的注释行(反例文档)跳过
        if example_brand_re.search(line):
            continue
        for grp in groups:
            for word in grp.words:
                wlow = word.lower()
                if not _is_chinese(word) and len(wlow) >= 3:
                    # 英文关键词,要求 \b...\b
                    if wlow not in word_boundary_re_cache:
                        word_boundary_re_cache[wlow] = re.compile(rf"\b{re.escape(wlow)}\b", re.IGNORECASE)
                    if not word_boundary_re_cache[wlow].search(line):
                        continue
                else:
                    # 中文或短词,保留子串匹配
                    if wlow not in line_lower:
                        continue

                hits.append(Hit(
                    file=path,
                    line_no=line_no,
                    line_text=line,
                    matched_word=word,
                    type_label=grp.type_label,
                ))
                # 一行只记一次(避免重复)
                break
    return hits


def scan(root: Path, groups: list[KeywordGroup], ignore_patterns: list[str]) -> ScanReport:
    report = ScanReport()
    for f in iter_target_files(root, ignore_patterns):
        report.scanned_files += 1
        file_hits = scan_file(f, groups)
        report.hits.extend(file_hits)
    return report


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------

def render_text(report: ScanReport, *, group_by: str, show_excerpt: bool) -> str:
    if report.is_clean:
        return f"[OK] zero branding traces  scanned={report.scanned_files} files\n"

    out: list[str] = []
    out.append(f"[FAIL] {len(report.hits)} branding traces found  scanned={report.scanned_files} files\n")

    if group_by == "type":
        for type_label, hits in report.by_type().items():
            out.append(f"\n[{type_label}]  {len(hits)} hits")
            for h in hits:
                rel = h.file.name
                out.append(f"  {rel}:{h.line_no}  matched='{h.matched_word}'")
                if show_excerpt:
                    out.append(f"    {h.excerpt()}")
    else:  # group_by == "file"
        by_file: dict[Path, list[Hit]] = {}
        for h in report.hits:
            by_file.setdefault(h.file, []).append(h)
        for f, hits in by_file.items():
            out.append(f"\n{f}")
            for h in hits:
                out.append(f"  L{h.line_no}  [{h.type_label}] matched='{h.matched_word}'")
                if show_excerpt:
                    out.append(f"    {h.excerpt()}")
    return "\n".join(out) + "\n"


def render_json(report: ScanReport) -> str:
    return json.dumps(
        {
            "clean": report.is_clean,
            "scanned_files": report.scanned_files,
            "hit_count": len(report.hits),
            "hits": [
                {
                    "file": str(h.file),
                    "line": h.line_no,
                    "type": h.type_label,
                    "matched": h.matched_word,
                    "excerpt": h.excerpt(),
                }
                for h in report.hits
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="品牌痕迹扫描器(原仓 → 开源仓净化前必跑)",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="要扫描的根目录(默认: 当前目录)",
    )
    p.add_argument(
        "--keywords",
        type=Path,
        required=True,
        help="关键词 YAML 配置文件(本文件不进开源仓)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出报告",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="启用严格模式,扫描常见 ERP 厂商字符串(覆盖 YAML strict_mode)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = load_config(args.keywords)
    if args.strict:
        cfg["strict_mode"] = True
    groups = build_keyword_groups(cfg)
    ignore = cfg.get("ignore_paths", [])

    if not groups:
        # 空词条(开源仓 example.yaml)应被视为 0 命中,而不是配置错误
        # 配合 CI 让"未配置真实词条"也能 green(本任务上游)
        print(
            "INFO: no keyword groups loaded; "
            "passing a real keywords file via --keywords will activate scanning.",
            file=sys.stderr,
        )
        report = ScanReport()
        if args.json:
            print(render_json(report))
        else:
            print("[OK] no keyword groups loaded (template mode)\n")
        return 0

    report = scan(args.root.resolve(), groups, ignore)

    if args.json:
        print(render_json(report))
    else:
        report_cfg = cfg.get("report", {})
        print(render_text(
            report,
            group_by=report_cfg.get("group_by", "type"),
            show_excerpt=report_cfg.get("show_excerpt", True),
        ))

    return 0 if report.is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
