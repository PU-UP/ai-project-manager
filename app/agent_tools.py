"""CLI：供外部 Agent 导出项目经理上下文 / 提交结构化操作。"""

import argparse
import json
import sys

from app.services.apply_control import apply_raw_json, build_context


def cmd_export() -> None:
    ctx = build_context()
    print(json.dumps(ctx, ensure_ascii=False, indent=2))


def cmd_apply(file_path: str | None, stdin: bool) -> None:
    if stdin or file_path == "-":
        raw = sys.stdin.read()
    elif file_path:
        with open(file_path, encoding="utf-8") as f:
            raw = f.read()
    else:
        print("请指定 --file 或使用 --stdin", file=sys.stderr)
        sys.exit(1)

    result = apply_raw_json(raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


def main_export() -> None:
    cmd_export()


def main_apply() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", help="JSON 文件路径，- 表示 stdin")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取")
    args = parser.parse_args()
    cmd_apply(args.file, args.stdin)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI项目管家 Agent 工具")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("export", help="导出当前项目态 JSON")

    p_apply = sub.add_parser("apply", help="应用 Agent 产出的 JSON")
    p_apply.add_argument("--file", "-f", help="JSON 文件路径")
    p_apply.add_argument("--stdin", action="store_true", help="从 stdin 读取")

    args = parser.parse_args()
    if args.command == "export":
        cmd_export()
    elif args.command == "apply":
        cmd_apply(getattr(args, "file", None), getattr(args, "stdin", False))


if __name__ == "__main__":
    main()
