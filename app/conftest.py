"""Pytest 配置文件"""

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app_factory import create_app
from models.engine import metadata

# 获取测试数据库配置
TEST_DB_DRIVER = os.getenv("TEST_DB_DRIVER", "postgresql")


def pytest_configure(config):
    """Pytest 配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers",
        "db(postgresql,mysql,sqlite): mark test to run only on specific database",
    )


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_url():
    """根据环境变量构建测试数据库连接字符串"""
    if TEST_DB_DRIVER == "postgresql":
        return "postgresql+asyncpg://postgres:fastapi123456@localhost:5432/fastapi_test"
    elif TEST_DB_DRIVER == "mysql":
        return "mysql+aiomysql://fastapi:fastapi123456@localhost:3306/fastapi_test"
    elif TEST_DB_DRIVER == "sqlite":
        return "sqlite+aiosqlite:///./fastapi_test.db"
    else:
        raise ValueError(f"Unsupported test database driver: {TEST_DB_DRIVER}")


@pytest.fixture(scope="session")
async def test_engine(test_db_url):
    """创建测试数据库引擎"""
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    yield engine

    # 删除所有表
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """创建测试会话"""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
def app():
    """创建应用实例"""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture(scope="function")
async def async_client(app):
    """创建异步测试客户端"""
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
