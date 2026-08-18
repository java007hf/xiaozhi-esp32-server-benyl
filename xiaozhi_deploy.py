#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xiaozhi_deploy.py — 小智服务本地编排管理脚本（离线版）

依赖：Docker + Docker Compose v2（命令为 `docker compose`，非旧版 `docker-compose`）
compose 文件：main/xiaozhi-server/docker-compose_all.yml

用法：
    python xiaozhi_deploy.py up                # 启动全部服务（后台）
    python xiaozhi_deploy.py down              # 停止并移除容器（保留数据卷）
    python xiaozhi_deploy.py restart           # 重启全部容器
    python xiaozhi_deploy.py recreate          # 先加载离线 tar 镜像，再强制重建全部容器
    python xiaozhi_deploy.py load              # 仅把离线 tar 镜像导入 Docker（不启容器）
    python xiaozhi_deploy.py status            # 查看容器状态
    python xiaozhi_deploy.py logs [服务名]      # 跟踪日志，如 logs xiaozhi-esp32-server-web
    python xiaozhi_deploy.py rebuild-web       # 修复 start.sh 换行并重建 web 镜像 + 重建 web 容器
    python xiaozhi_deploy.py rebuild           # 用本地源码重建 server 镜像 + 重建 server 容器
    python xiaozhi_deploy.py save              # 把本地 server/web 镜像导出为 tar 到项目根目录
    python xiaozhi_deploy.py load              # 把项目根目录的离线 tar 镜像导入 Docker（不启容器）

离线镜像 tar 包（默认在项目根目录，可在脚本顶部 IMAGE_TARS 修改路径）：
    xiaozhi-server-local.tar  ->  xiaozhi-server:local
    xiaozhi-web-local.tar     ->  xiaozhi-web:local

注意：脚本所有路径都相对于本文件所在目录（项目根目录），可在任意位置执行。
"""

import os
import subprocess
import sys

# ===== 路径配置 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(
    SCRIPT_DIR, "main", "xiaozhi-server", "docker-compose_all.yml"
)
WEB_DOCKERFILE = os.path.join(SCRIPT_DIR, "Dockerfile-web-offline")
START_SH = os.path.join(SCRIPT_DIR, "docs", "docker", "start.sh")

IMAGE_SERVER = "xiaozhi-server:local"
SERVICE_SERVER = "xiaozhi-esp32-server"

IMAGE_WEB = "xiaozhi-web:local"
SERVICE_WEB = "xiaozhi-esp32-server-web"

# 离线镜像 tar 包（默认放在项目根目录，可改成实际路径）
TAR_SERVER = os.path.join(SCRIPT_DIR, "xiaozhi-server-local.tar")
TAR_WEB = os.path.join(SCRIPT_DIR, "xiaozhi-web-local.tar")
# 加载顺序无所谓，server 先加载
IMAGE_TARS = [TAR_SERVER, TAR_WEB]


def _run(cmd, check=True):
    """执行命令并打印，失败时退出。"""
    print(">>> " + " ".join(cmd))
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[错误] 命令执行失败（退出码 {e.returncode}）", file=sys.stderr)
        sys.exit(e.returncode)


def _compose(args):
    """拼接 docker compose 命令（始终指定 -f 显式文件）。"""
    return ["docker", "compose", "-f", COMPOSE_FILE] + args


def ensure_start_sh_lf():
    """
    把 docs/docker/start.sh 转成 LF 换行，避免镜像内 shebang 变成
    '#!/bin/bash\r' 导致容器启动报 'exec /start.sh: no such file or directory'。
    """
    if not os.path.exists(START_SH):
        print(f"[警告] 未找到 {START_SH}，跳过换行修复")
        return
    with open(START_SH, "rb") as f:
        data = f.read()
    if b"\r\n" in data:
        new_data = data.replace(b"\r\n", b"\n")
        with open(START_SH, "wb") as f:
            f.write(new_data)
        print(f"[修复] 已将 {START_SH} 转换为 LF 换行")
    else:
        print(f"[OK] {START_SH} 已是 LF 换行，无需处理")


def cmd_up():
    _run(_compose(["up", "-d"]))


def cmd_down():
    _run(_compose(["down"]))


def cmd_restart():
    _run(_compose(["restart"]))


def cmd_recreate():
    _load_tars()
    _run(_compose(["up", "-d", "--force-recreate"]))


def _load_tars():
    """离线部署：把本地 tar 镜像导入 Docker（docker load）。"""
    for tar in IMAGE_TARS:
        if not os.path.exists(tar):
            print(f"[警告] 未找到 tar 包，跳过：{tar}")
            continue
        print(f"=== 加载离线镜像：{tar} ===")
        _run(["docker", "load", "-i", tar])


def cmd_load():
    _load_tars()


def cmd_status():
    _run(_compose(["ps"]), check=False)


def cmd_logs(services):
    _run(_compose(["logs", "-f"] + services), check=False)


def cmd_rebuild_web():
    ensure_start_sh_lf()
    if not os.path.exists(WEB_DOCKERFILE):
        print(f"[错误] 未找到离线 Dockerfile：{WEB_DOCKERFILE}", file=sys.stderr)
        sys.exit(1)
    # 1) 重建 web 镜像（构建上下文必须是项目根目录）
    print("=== 开始构建 web 镜像 ===")
    _run([
        "docker", "build",
        "-f", WEB_DOCKERFILE,
        "-t", IMAGE_WEB,
        SCRIPT_DIR,
    ])
    # 2) 仅重建 web 容器使用新镜像
    print("=== 重建 web 容器 ===")
    _run(_compose(["up", "-d", "--force-recreate", SERVICE_WEB]))
    print("=== web 镜像已重建并重建容器，可用 status 查看状态 ===")


def _save_tars():
    """离线部署：把本地镜像导出为 tar 包到项目根目录（docker save）。"""
    save_map = [
        (IMAGE_SERVER, TAR_SERVER),
        (IMAGE_WEB, TAR_WEB),
    ]
    for image, tar in save_map:
        print(f"=== 导出镜像：{image} -> {tar} ===")
        _run(["docker", "save", "-o", tar, image])


def cmd_rebuild():
    """用本地源码重建 server 镜像，并重建 server 容器。

    注意：默认 Dockerfile 仅 COPY 了 core/utils/prompt_manager.py，
    其余 server 代码来自基础镜像 xiaozhi-esp32-server:server_latest。
    如改了其它的 server 文件，请在 Dockerfile 中补充 COPY 或改为 bind mount。
    该命令不会重新加载离线 tar，避免覆盖刚构建好的镜像。
    """
    server_dockerfile = os.path.join(SCRIPT_DIR, "main", "xiaozhi-server", "Dockerfile")
    server_context = os.path.join(SCRIPT_DIR, "main", "xiaozhi-server")
    if not os.path.exists(server_dockerfile):
        print(f"[错误] 未找到 server Dockerfile：{server_dockerfile}", file=sys.stderr)
        sys.exit(1)
    # 1) 构建 server 镜像（构建上下文必须是 main/xiaozhi-server 目录）
    print("=== 开始构建 server 镜像 ===")
    _run([
        "docker", "build",
        "-f", server_dockerfile,
        "-t", IMAGE_SERVER,
        server_context,
    ])
    # 2) 仅重建 server 容器使用新镜像（不重新加载离线 tar）
    print("=== 重建 server 容器 ===")
    _run(_compose(["up", "-d", "--force-recreate", SERVICE_SERVER]))
    print("=== server 镜像已构建并重建容器，可用 status 查看状态 ===")


def cmd_save():
    _save_tars()


def main():
    if not os.path.exists(COMPOSE_FILE):
        print(f"[错误] 未找到 compose 文件：{COMPOSE_FILE}", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    action = args[0]
    rest = args[1:]

    if action in ("--help", "-h", "help"):
        print(__doc__)
        sys.exit(0)

    if action in ("up", "start"):
        cmd_up()
    elif action == "down":
        cmd_down()
    elif action == "restart":
        cmd_restart()
    elif action == "recreate":
        cmd_recreate()
    elif action == "load":
        cmd_load()
    elif action == "status":
        cmd_status()
    elif action == "logs":
        cmd_logs(rest)
    elif action == "rebuild-web":
        cmd_rebuild_web()
    elif action == "rebuild":
        cmd_rebuild()
    elif action == "save":
        cmd_save()
    else:
        print(f"[错误] 未知命令：{action}\n")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
