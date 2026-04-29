import logging
import sys

# 全局日志配置
def setup_logger(name: str) -> logging.Logger:
    """创建并配置日志记录器"""
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger  # 避免重复添加处理器

    logger.setLevel(logging.INFO)

    # 控制台处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    # 日志格式：时间 | 日志级别 | 模块名 | 消息
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
