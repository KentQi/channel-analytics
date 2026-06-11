#!/usr/bin/env python3
"""
One-click demo: setup -> seed -> run

Usage:
    python demo.py              # One-click start (open http://127.0.0.1:8602)
    python demo.py --seed-only  # Seed only, don't start server
    python demo.py --run-only   # Run server only (seed assumed done)
    python demo.py --reset      # Clear tables + reseed
"""
from __future__ import annotations
import sys
import os
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

DEMO_PORT = 8602
DEMO_HOST = "127.0.0.1"

WELCOME = """
========================================
  Channel Analytics -- Demo Mode
  Mock data + SQLite, no MySQL needed

  API docs:  http://{host}:{port}/api/docs
  Login:     admin / admin123
========================================
"""


def check_deps():
    missing = []
    for pkg in [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("sqlalchemy", "sqlalchemy"),
        ("pydantic", "pydantic"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("passlib", "passlib"),
        ("jwt", "pyjwt"),
        ("openpyxl", "openpyxl"),
    ]:
        try:
            __import__(pkg[0])
        except ImportError:
            missing.append(pkg[1])
    return missing


def install_deps(missing):
    print(f"  Installing: {', '.join(missing)} ...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q"] + missing,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )


def seed(reset: bool = False):
    print("\n[2/3] Seeding mock data...")
    args = ["-m", "channel_analytics.data.seed"]
    if reset:
        args.append("--reset")
    result = subprocess.run(
        [sys.executable] + args,
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"  Seed failed:\n{result.stderr[-500:]}")
        sys.exit(1)
    for line in result.stdout.splitlines():
        if "[INFO]" in line or "done" in line.lower():
            print(f"  {line}")


def run_server():
    print(f"\n[3/3] Starting API server...")
    print(WELCOME.format(host=DEMO_HOST, port=DEMO_PORT))
    print("  [SECURITY NOTICE] 默认密码 'admin123' 仅供演示。")
    print("                  生产部署请立即修改并设置 SESSION_SECRET/JWT_SECRET。")
    print("")
    os.chdir(str(PROJECT_ROOT))
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", DEMO_HOST,
        "--port", str(DEMO_PORT),
    ])


def main():
    parser = argparse.ArgumentParser(description="Channel Analytics - One-click Demo")
    parser.add_argument("--seed-only", action="store_true", help="Seed only, don't start server")
    parser.add_argument("--run-only", action="store_true", help="Run server only")
    parser.add_argument("--reset", action="store_true", help="Clear tables before seed")
    args = parser.parse_args()

    print("\n[1/3] Checking dependencies...")
    missing = check_deps()
    if missing:
        install_deps(missing)
        print(f"  OK Installed: {', '.join(missing)}")
    else:
        print("  OK All dependencies present")

    if not args.run_only:
        seed(reset=args.reset)

    if not args.seed_only:
        run_server()


if __name__ == "__main__":
    main()
