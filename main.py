import os
from dotenv import load_dotenv

from src.pipeline import build_index, query
from src.logger import setup_logger

load_dotenv()
logger = setup_logger("main")


def main():
    logger.info("=" * 60)
    logger.info("🚀 RAG 问答系统启动")
    logger.info("=" * 60)

    # 离线阶段：构建索引
    try:
        build_index()
    except Exception as e:
        logger.error(f"索引构建失败：{e}", exc_info=True)
        return

    logger.info("\n📝 进入交互模式（输入 q 退出）")

    while True:
        try:
            question = input("\n💬 问题：").strip()
        except (KeyboardInterrupt, EOFError):
            logger.info("\n👋 系统关闭")
            break

        if not question:
            continue

        if question.lower() in ("q", "quit", "exit", "退出"):
            logger.info("👋 系统关闭")
            break

        try:
            logger.info("")
            answer = query(question)
            logger.info(f"\n✅ 答案：{answer}")
        except Exception as e:
            logger.error(f"查询失败：{e}", exc_info=True)


if __name__ == "__main__":
    main()
