import os
from loguru import logger
from config.config import LOG_LEVEL, LOG_FILE

# Fjern default handler
logger.remove()

# Console output
logger.add(
    lambda msg: print(msg, end=''),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL
)

# File output
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logger.add(
    LOG_FILE,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=LOG_LEVEL,
    rotation="500 MB"
)

__all__ = ['logger']
