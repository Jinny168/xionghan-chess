"""
统一日志配置模块
提供标准化的日志记录功能，替代print语句
"""
import logging
import sys
from pathlib import Path
from desktop.config.constants import GameConstants


def setup_logger(
    name: str = "xionghan_chess",
    level: str = None,
    log_to_file: bool = False,
    log_file_path: str = None
) -> logging.Logger:
    """
    设置并返回配置好的logger实例
    
    Args:
        name: logger名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: 是否输出到文件
        log_file_path: 日志文件路径
        
    Returns:
        logging.Logger: 配置好的logger实例
    """
    if level is None:
        level = GameConstants.LOG_LEVEL
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件Handler（可选）
    if log_to_file:
        if log_file_path is None:
            log_file_path = Path(__file__).parent.parent / "logs" / "game.log"
        
        # 确保日志目录存在
        log_file_path = Path(log_file_path)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认logger实例
logger = setup_logger()


def get_module_logger(module_name: str) -> logging.Logger:
    """
    为指定模块获取logger
    
    Args:
        module_name: 模块名称
        
    Returns:
        logging.Logger: 模块专属logger
    """
    return setup_logger(name=f"xionghan_chess.{module_name}")


# 便捷函数
def debug(message: str, *args, **kwargs):
    """记录DEBUG级别日志"""
    logger.debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """记录INFO级别日志"""
    logger.info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """记录WARNING级别日志"""
    logger.warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """记录ERROR级别日志"""
    logger.error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """记录CRITICAL级别日志"""
    logger.critical(message, *args, **kwargs)

