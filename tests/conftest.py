import pytest
import asyncio
from typing import Generator
import os
import sys
import logging

# 将项目根目录添加到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 配置 pytest-asyncio
pytestmark = pytest.mark.asyncio(loop_scope="session")

# 配置日志
@pytest.fixture(autouse=True)
def setup_logging():
    """配置日志"""
    # 创建日志处理器
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 获取根日志记录器并添加处理器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    yield
    
    # 清理
    root_logger.removeHandler(handler) 