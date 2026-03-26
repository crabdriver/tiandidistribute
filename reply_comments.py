import sys
import os
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent

def main():
    print("=" * 50)
    print("  微信公众号 - AI自动回复评论")
    print("=" * 50)
    
    script_path = BASE_DIR / "scripts" / "comment_reply.py"
    if not script_path.exists():
        print(f"找不到回复脚本: {script_path}")
        sys.exit(1)
        
    cmd = [sys.executable, str(script_path)] + sys.argv[1:]
    try:
        result = subprocess.run(cmd, cwd=str(BASE_DIR))
        raise SystemExit(result.returncode)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断执行")
        raise SystemExit(130)

if __name__ == "__main__":
    main()
