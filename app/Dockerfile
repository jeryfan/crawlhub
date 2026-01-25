FROM ubuntu:22.04

# 配置 Ubuntu 镜像源（使用阿里云镜像，支持 arm64 和 amd64）
# 对于 x86_64，源通常是 archive.ubuntu.com
# 对于 arm64 (Mac M1/M2)，源通常是 ports.ubuntu.com
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    sed -i 's@//.*ports.ubuntu.com@//mirrors.aliyun.com@g' /etc/apt/sources.list && \
    cat /etc/apt/sources.list

# 设置时区环境变量以避免 tzdata 交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gcc \
    libpq-dev \
    build-essential \
    ca-certificates \
    pipx \
    tzdata \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-eng \
    && pipx ensurepath && \
    rm -rf /var/lib/apt/lists/*

RUN pipx install uv
ENV PATH="/root/.local/bin:$PATH"

# 配置 PyPI 镜像源（使用阿里云镜像）
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY ./ ./

RUN uv sync
ENV PYTHON=/workspace/.venv/bin/python3

COPY docker/entrypoint.sh /
RUN chmod +x /entrypoint*.sh
ENTRYPOINT ["/entrypoint.sh"]


