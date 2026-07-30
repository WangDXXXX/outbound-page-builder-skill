"""六层断言 CLI。WARN 开头的消息不计入失败。"""
import sys
from opb.config import load_config
from opb.checks import build_ctx, layers

def run(config_path: str):
    cfg = load_config(config_path)
    ctx = build_ctx(cfg)
    results, hard = {}, 0
    for name, fn in layers():
        msgs = fn(ctx)
        results[name] = msgs
        hard += sum(1 for m in msgs if not m.startswith("WARN"))
    return (1 if hard else 0), results

def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify.py <assert.yaml>"); return 2
    code, res = run(sys.argv[1])
    for name, msgs in res.items():
        if not msgs:
            print(f"✅ {name}")
            continue
        print(f"{'⚠️' if all(m.startswith('WARN') for m in msgs) else '❌'} {name}")
        for m in msgs:
            print("   -", m)
    print("\n" + ("❌ 未通过，禁止交付" if code else "✅ 六层全过"))
    return code

if __name__ == "__main__":
    sys.exit(main())
