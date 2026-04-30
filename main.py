import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

# Parse --model early so sys.path is set before any src.* imports
_preparser = argparse.ArgumentParser(add_help=False)
_preparser.add_argument("--model", choices=["common", "agentic"], default="common")
_pre_args, _ = _preparser.parse_known_args()

sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "common_rag"))

from dotenv import load_dotenv

if _pre_args.model == "agentic":
    from agentic_rag.pipeline import build_index, query
else:
    from common_rag.pipeline import build_index, query
from logger import setup_logger

load_dotenv()
logger = setup_logger("main")


def main():
    parser = argparse.ArgumentParser(description="RAG 问答系统")
    parser.add_argument(
        "--model",
        choices=["common", "agentic"],
        default="common",
        help="RAG 模式：common（普通）或 agentic（智能体，含查询分解）",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"RAG 问答系统启动 [模式: {args.model}]")
    logger.info("=" * 60)

    try:
        build_index()
    except Exception as e:
        logger.error(f"索引构建失败：{e}", exc_info=True)
        return

    logger.info("\n进入交互模式（输入 q 退出）")

    while True:
        try:
            question = input("\n问题：").strip()
        except (KeyboardInterrupt, EOFError):
            logger.info("\n系统关闭")
            break

        if not question:
            continue

        if question.lower() in ("q", "quit", "exit", "退出"):
            logger.info("系统关闭")
            break

        try:
            logger.info("")
            answer = query(question)
            logger.info(f"\n答案：{answer}")
        except Exception as e:
            logger.error(f"查询失败：{e}", exc_info=True)


if __name__ == "__main__":
    main()
