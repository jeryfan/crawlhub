terraform {
  required_providers {
    coder = {
      source = "coder/coder"
    }
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

locals {
  username = "crawlhub"
  home_dir = "/home/crawlhub"
  workspace_dir = "/home/crawlhub/workspace"
}

variable "docker_socket" {
  default     = ""
  description = "(Optional) Docker socket URI"
  type        = string
}

provider "docker" {
  host = var.docker_socket != "" ? var.docker_socket : null
}

data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

# 项目来源
data "coder_parameter" "source" {
  name         = "source"
  display_name = "项目来源"
  type         = "string"
  default      = "empty"
  mutable      = false
  option {
    name  = "新建空项目"
    value = "empty"
  }
  option {
    name  = "新建 Scrapy 项目"
    value = "scrapy"
  }
  option {
    name  = "克隆 Git 仓库"
    value = "git"
  }
  option {
    name  = "上传文件"
    value = "upload"
  }
}

# 项目名称
data "coder_parameter" "name" {
  name         = "name"
  display_name = "项目名称"
  type         = "string"
  default      = "my_project"
  mutable      = false
  validation {
    regex = "^[a-zA-Z][a-zA-Z0-9_]*$"
    error = "项目名必须以字母开头，只能包含字母、数字、下划线"
  }
}

# Git 仓库地址
data "coder_parameter" "repo" {
  name         = "repo"
  display_name = "Git 仓库地址"
  type         = "string"
  default      = ""
  mutable      = false
}

resource "coder_agent" "main" {
  arch           = data.coder_provisioner.me.arch
  os             = "linux"
  startup_script = <<-EOT
    set -e

    # 创建 crawlhub 用户（如果不存在）
    if ! id -u ${local.username} > /dev/null 2>&1; then
      sudo useradd -m -s /bin/bash ${local.username}
      sudo usermod -aG sudo ${local.username}
      echo "${local.username} ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/${local.username}
    fi

    # 创建 workspace 目录
    sudo mkdir -p ${local.workspace_dir}
    sudo chown -R ${local.username}:${local.username} ${local.home_dir}

    # 初始化用户环境
    if [ ! -f ${local.home_dir}/.init_done ]; then
      sudo -u ${local.username} cp -rT /etc/skel ${local.home_dir} 2>/dev/null || true
      sudo -u ${local.username} touch ${local.home_dir}/.init_done
    fi

    SOURCE="${data.coder_parameter.source.value}"
    NAME="${data.coder_parameter.name.value}"
    REPO="${data.coder_parameter.repo.value}"
    PROJECT_DIR="${local.workspace_dir}/$NAME"

    echo "========================================"
    echo "  爬虫开发环境初始化"
    echo "  用户: ${local.username}"
    echo "  项目来源: $SOURCE"
    echo "  项目名称: $NAME"
    echo "  开始时间: $(date)"
    echo "========================================"

    # 安装系统依赖
    echo "[1/3] 安装系统依赖..."
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y -qq python3-pip python3-venv git vim curl wget unzip 2>/dev/null || true

    # 创建 Python 虚拟环境
    echo "[2/3] 设置 Python 虚拟环境..."
    sudo -u ${local.username} mkdir -p ${local.home_dir}/.venvs
    if [ ! -d ${local.home_dir}/.venvs/spider-env ]; then
        sudo -u ${local.username} python3 -m venv ${local.home_dir}/.venvs/spider-env
    fi
    sudo -u ${local.username} ${local.home_dir}/.venvs/spider-env/bin/pip install -q --upgrade pip
    sudo -u ${local.username} ${local.home_dir}/.venvs/spider-env/bin/pip install -q --no-cache-dir scrapy requests beautifulsoup4 lxml pandas jupyter jupyterlab ipython httpx playwright 2>&1 | tail -3
    echo "  Python 依赖安装完成"

    # 初始化项目
    echo "[3/3] 初始化项目..."
    if [ ! -d "$PROJECT_DIR" ]; then
        case "$SOURCE" in
            empty)
                sudo -u ${local.username} mkdir -p "$PROJECT_DIR"
                ;;
            scrapy)
                cd ${local.workspace_dir}
                sudo -u ${local.username} ${local.home_dir}/.venvs/spider-env/bin/scrapy startproject "$NAME"
                ;;
            git)
                sudo -u ${local.username} git clone "$REPO" "$PROJECT_DIR"
                ;;
            upload)
                sudo -u ${local.username} mkdir -p "$PROJECT_DIR"
                ;;
        esac
    fi

    # 设置权限
    sudo chown -R ${local.username}:${local.username} ${local.workspace_dir} 2>/dev/null || true

    # 配置环境变量
    if ! grep -q "spider-env" ${local.home_dir}/.bashrc 2>/dev/null; then
        echo 'source ${local.home_dir}/.venvs/spider-env/bin/activate' | sudo -u ${local.username} tee -a ${local.home_dir}/.bashrc > /dev/null
        echo 'cd ${local.workspace_dir}' | sudo -u ${local.username} tee -a ${local.home_dir}/.bashrc > /dev/null
    fi

    echo ""
    echo "========================================"
    echo "  开发环境已就绪!"
    echo "  工作目录: ${local.workspace_dir}"
    echo "  项目目录: $PROJECT_DIR"
    echo "  完成时间: $(date)"
    echo "========================================"
  EOT

  env = {
    GIT_AUTHOR_NAME     = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_AUTHOR_EMAIL    = "${data.coder_workspace_owner.me.email}"
    GIT_COMMITTER_NAME  = coalesce(data.coder_workspace_owner.me.full_name, data.coder_workspace_owner.me.name)
    GIT_COMMITTER_EMAIL = "${data.coder_workspace_owner.me.email}"
  }

  metadata {
    display_name = "CPU Usage"
    key          = "0_cpu_usage"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "1_ram_usage"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Workspace Disk"
    key          = "3_workspace_disk"
    script       = "coder stat disk --path ${local.workspace_dir}"
    interval     = 60
    timeout      = 1
  }
}

# VS Code 编辑器 - 打开 workspace 目录
module "code-server" {
  count   = data.coder_workspace.me.start_count
  source  = "registry.coder.com/coder/code-server/coder"
  version = "~> 1.0"

  agent_id = coder_agent.main.id
  folder   = "${local.workspace_dir}"
  order    = 1
}

# JupyterLab
module "jupyterlab" {
  count   = data.coder_workspace.me.start_count
  source  = "registry.coder.com/coder/jupyterlab/coder"
  version = "~> 1.0"

  agent_id  = coder_agent.main.id
  order     = 2
  subdomain = false
}

# 文件管理器 - 管理 workspace 目录
module "filebrowser" {
  count   = data.coder_workspace.me.start_count
  source  = "registry.coder.com/coder/filebrowser/coder"
  version = "~> 1.0"

  agent_id  = coder_agent.main.id
  folder    = "${local.workspace_dir}"
  order     = 3
  subdomain = false
}

resource "docker_volume" "home_volume" {
  name = "coder-${data.coder_workspace.me.id}-home"
  lifecycle {
    ignore_changes = all
  }
  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }
  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  labels {
    label = "coder.workspace_name_at_creation"
    value = data.coder_workspace.me.name
  }
}

resource "docker_container" "workspace" {
  count    = data.coder_workspace.me.start_count
  image    = "codercom/enterprise-base:ubuntu"
  name     = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname = data.coder_workspace.me.name
  entrypoint = ["sh", "-c", replace(coder_agent.main.init_script, "/localhost|127\\.0\\.0\\.1/", "host.docker.internal")]
  env        = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]
  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }
  volumes {
    container_path = "${local.home_dir}"
    volume_name    = docker_volume.home_volume.name
    read_only      = false
  }
  labels {
    label = "coder.owner"
    value = data.coder_workspace_owner.me.name
  }
  labels {
    label = "coder.owner_id"
    value = data.coder_workspace_owner.me.id
  }
  labels {
    label = "coder.workspace_id"
    value = data.coder_workspace.me.id
  }
  labels {
    label = "coder.workspace_name"
    value = data.coder_workspace.me.name
  }
}

output "workspace_directory" {
  value = "${local.workspace_dir}"
}

output "project_directory" {
  value = "${local.workspace_dir}/${data.coder_parameter.name.value}"
}
