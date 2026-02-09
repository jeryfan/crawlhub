from datetime import datetime

from pydantic import BaseModel, Field

from models.crawlhub.datasource import DataSourceMode, DataSourceStatus, DataSourceType


# ============ DataSource Schemas ============

class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="数据源名称")
    description: str | None = Field(None, description="描述")
    type: DataSourceType = Field(..., description="数据库类型")
    mode: DataSourceMode = Field(default=DataSourceMode.EXTERNAL, description="连接模式")
    # 连接信息 (external 模式需要)
    host: str | None = Field(None, description="主机地址")
    port: int | None = Field(None, description="端口")
    username: str | None = Field(None, description="用户名")
    password: str | None = Field(None, description="密码")
    database: str | None = Field(None, description="数据库名")
    connection_options: dict | None = Field(None, description="连接选项")
    create_db_if_not_exists: bool = Field(default=False, description="数据库不存在时自动创建")
    # managed 模式
    docker_image: str | None = Field(None, description="Docker镜像")


class DataSourceTestRequest(BaseModel):
    type: DataSourceType = Field(..., description="数据库类型")
    host: str = Field(..., description="主机地址")
    port: int | None = Field(None, description="端口")
    username: str | None = Field(None, description="用户名")
    password: str | None = Field(None, description="密码")
    database: str | None = Field(None, description="数据库名")
    connection_options: dict | None = Field(None, description="连接选项")


class DataSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    database: str | None = None
    connection_options: dict | None = None


class DataSourceResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    type: DataSourceType
    mode: DataSourceMode
    status: DataSourceStatus
    host: str | None = None
    port: int | None = None
    username: str | None = None
    database: str | None = None
    connection_options: dict | None = None
    container_id: str | None = None
    container_name: str | None = None
    docker_image: str | None = None
    mapped_port: int | None = None
    volume_path: str | None = None
    last_check_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataSourceListResponse(BaseModel):
    items: list[DataSourceResponse]
    total: int


# ============ SpiderDataSource Schemas ============

class SpiderDataSourceCreate(BaseModel):
    datasource_id: str = Field(..., description="数据源ID")
    target_table: str = Field(..., min_length=1, max_length=255, description="目标表名/集合名")
    is_enabled: bool = Field(default=True, description="是否启用")


class SpiderDataSourceUpdate(BaseModel):
    target_table: str | None = Field(None, min_length=1, max_length=255)
    is_enabled: bool | None = None


class SpiderDataSourceResponse(BaseModel):
    id: str
    spider_id: str
    datasource_id: str
    target_table: str
    is_enabled: bool
    datasource_name: str | None = None
    datasource_type: DataSourceType | None = None
    datasource_status: DataSourceStatus | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
