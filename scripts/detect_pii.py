#!/usr/bin/env python3
"""
detect_pii.py — PII(个人身份信息)扫描器

扫描 etl_data/ uploads/ logs/ 下的:
  - 中国大陆手机号
  - 18 位身份证号
  - 邮箱
  - 银行卡号(13-19 位 Luhn 校验)
  - IPv4 地址(可能内网泄漏)
  - 内部员工名 / 客户代号

退出码:
  0 — 零命中
  1 — 有命中(阻断 CI)
  2 — 配置错误

设计要点(对应 PLAN.md §6 P0):
  - 不修改文件,只生成报告
  - 命中行只显示脱敏预览(前 3 + 后 2 字符,中间 ****)
  - 输出:文本(默认)/ JSON(--json)
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
except ImportError:
    print("ERROR: PyYAML is required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# 规则定义
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    name: str          # 报告里的类型标签
    pattern: re.Pattern
    mask: bool = True  # 是否对命中字符串脱敏显示


def _luhn_check(num: str) -> bool:
    """Luhn 校验(银行卡号等)。"""
    digits = [int(c) for c in num if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


RULES: tuple[Rule, ...] = (
    Rule(
        "phone_cn",
        re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ),
    Rule(
        "id_card_cn",
        re.compile(r"(?<!\d)[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"),
    ),
    Rule(
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    Rule(
        "credit_card",
        # 13-19 位连续数字,排除 18 位身份证(被 id_card_cn 规则优先匹配)
        # 信用卡常见 13/14/15/16/19 位
        re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
    ),
    Rule(
        "ipv4",
        re.compile(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}(?!\d)"),
    ),
)


# ---------------------------------------------------------------------------
# 内部员工/客户名(从外部配置加载,避免硬编码)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StringRule:
    type_label: str
    word: str


def load_string_rules(cfg: dict) -> list[StringRule]:
    out: list[StringRule] = []
    for word in cfg.get("internal_accounts", []):
        out.append(StringRule("account", str(word)))
    for word in cfg.get("customer_codes", []):
        out.append(StringRule("customer", str(word)))
    return out


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Hit:
    file: Path
    line_no: int
    rule: str
    raw: str
    masked: str
    note: str = ""  # 备注(如 Luhn 校验失败,提示"可能是假号")

    @staticmethod
    def mask_value(raw: str) -> str:
        if len(raw) <= 6:
            return raw[:2] + "****" + raw[-1:] if len(raw) > 3 else "****"
        return raw[:3] + "****" + raw[-2:]


@dataclass
class ScanReport:
    hits: list[Hit] = field(default_factory=list)
    scanned_files: int = 0

    @property
    def is_clean(self) -> bool:
        return not self.hits

    def by_rule(self) -> dict[str, list[Hit]]:
        out: dict[str, list[Hit]] = {}
        for h in self.hits:
            out.setdefault(h.rule, []).append(h)
        return out


# ---------------------------------------------------------------------------
# 文件遍历
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: PII rules config not found: {path}", file=sys.stderr)
        sys.exit(2)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def iter_target_files(
    roots: list[Path],
    ignore_patterns: list[str],
) -> Iterable[Path]:
    """遍历 roots 下所有可能的 PII 文件(扩展名白名单 + 二进制大小过滤)。"""
    candidate_exts = {
        ".csv", ".tsv", ".txt", ".json", ".jsonl", ".ndjson",
        ".xlsx", ".xls",  # Excel(可能含联系方式)
        ".log", ".yaml", ".yml", ".toml", ".ini", ".conf",
        ".sql", ".html", ".xml",
    }
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            # 跳过 5MB 以上的二进制(避免卡死 + 噪音)
            try:
                if p.stat().st_size > 5 * 1024 * 1024:
                    continue
            except OSError:
                continue
            # 没有扩展名的(比如无后缀的日志)按"可能是文本"放行
            if p.suffix and p.suffix.lower() not in candidate_exts:
                continue
            # 路径忽略(支持子目录匹配,如 frontend/node_modules/)
            skip = False
            parts = p.parts
            for pat in ignore_patterns:
                if pat.endswith("/"):
                    dir_name = pat.rstrip("/")
                    if dir_name in parts or pat in p.as_posix():
                        skip = True
                        break
                if fnmatch.fnmatch(p.name, pat):
                    skip = True
                    break
            if skip:
                continue
            yield p


# ---------------------------------------------------------------------------
# 扫描
# ---------------------------------------------------------------------------

def scan_line(
    line: str,
    rules: tuple[Rule, ...],
    string_rules: list[StringRule],
) -> list[Hit]:
    out: list[Hit] = []
    # 正则规则(顺序敏感:长模式优先,避免短模式"吃掉"长模式)
    sorted_rules = sorted(rules, key=lambda r: -len(r.pattern.pattern))
    for rule in sorted_rules:
        for m in rule.pattern.finditer(line):
            raw = m.group(0)
            note = ""
            # 信用卡:过 Luhn;失败时仍报告但加 note(避免假阴性)
            if rule.name == "credit_card":
                cleaned = raw.replace(" ", "").replace("-", "")
                if not _luhn_check(cleaned):
                    note = "luhn_failed_may_be_false_positive"
                # 二次过滤:18 位数字更可能是身份证(被 id_card_cn 优先吃掉后,
                # 但如果 id_card_cn 因校验位未匹配而漏掉,这里要避免重复)
            out.append(Hit(
                file=Path(""),  # 调用方回填
                line_no=0,
                rule=rule.name,
                raw=raw,
                masked=Hit.mask_value(raw),
                note=note,
            ))
    # 字符串规则(子串匹配,忽略大小写)
    line_lower = line.lower()
    for sr in string_rules:
        if sr.word.lower() in line_lower:
            out.append(Hit(
                file=Path(""),
                line_no=0,
                rule=sr.type_label,
                raw=sr.word,
                masked=sr.word[:3] + "***" + sr.word[-2:] if len(sr.word) > 5 else "***",
            ))
    return out


def scan_files(
    files: Iterable[Path],
    rules: tuple[Rule, ...],
    string_rules: list[StringRule],
) -> ScanReport:
    report = ScanReport()
    for f in files:
        report.scanned_files += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"WARN: cannot read {f}: {e}", file=sys.stderr)
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            hits = scan_line(line, rules, string_rules)
            for h in hits:
                h.file = f
                h.line_no = line_no
            report.hits.extend(hits)
    return report


# ---------------------------------------------------------------------------
# 报告输出
# ---------------------------------------------------------------------------

def render_text(report: ScanReport) -> str:
    if report.is_clean:
        return f"[OK] zero PII traces  scanned={report.scanned_files} files\n"

    out: list[str] = []
    out.append(f"[FAIL] {len(report.hits)} PII traces found  scanned={report.scanned_files} files\n")
    for rule_name, hits in report.by_rule().items():
        out.append(f"\n[{rule_name}]  {len(hits)} hits")
        # 同文件命中折叠
        by_file: dict[str, list[Hit]] = {}
        for h in hits:
            key = f"{h.file.name}:{h.line_no}"
            by_file.setdefault(key, []).append(h)
        for key, group in by_file.items():
            masks = ", ".join(
                (h.masked + (f" [{h.note}]" if h.note else "")) for h in group
            )
            out.append(f"  {key}  -> {masks}")
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
                    "rule": h.rule,
                    "masked": h.masked,
                    "note": h.note,
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
    p = argparse.ArgumentParser(description="PII 扫描器(etl_data / uploads / logs)")
    p.add_argument(
        "--root",
        type=Path,
        action="append",
        required=True,
        help="要扫描的根目录,可传多个(至少包含 etl_data/ uploads/ logs/)",
    )
    p.add_argument(
        "--keywords",
        type=Path,
        default=None,
        help="可选:关键词 YAML(从 check_branding.py 的同一份配置加载 internal_accounts / customer_codes)",
    )
    p.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    string_rules: list[StringRule] = []
    if args.keywords:
        cfg = load_config(args.keywords)
        string_rules = load_string_rules(cfg)

    files = iter_target_files(args.root, ignore_patterns=[
        ".git/", "node_modules/", "__pycache__/",
        "reports/",  # W1 净化报告(含原仓脱敏样例,防御性忽略)
        "*.png", "*.jpg", "*.gif", "*.pdf", "*.zip",
    ])
    report = scan_files(files, RULES, string_rules)

    if args.json:
        print(render_json(report))
    else:
        print(render_text(report))
    return 0 if report.is_clean else 1


if __name__ == "__main__":
    sys.exit(main())
