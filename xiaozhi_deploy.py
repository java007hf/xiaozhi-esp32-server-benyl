#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xiaozhi_deploy.py — 小智服务本地编排管理脚本（离线版）

依赖：Docker + Docker Compose v2（命令为 `docker compose`，非旧版 `docker-compose`）
compose 文件：main/xiaozhi-server/docker-compose_all.yml

默认启用 BuildKit（Docker 23+ 默认开启；旧版需 DOCKER_BUILDKIT=1），
让 Dockerfile 里的 --mount=type=cache 跨 build 复用依赖缓存（.m2 / node_modules）。

用法：
    python xiaozhi_deploy.py up                        # 启动全部服务（后台）
    python xiaozhi_deploy.py down                      # 停止并移除容器（保留数据卷）
    python xiaozhi_deploy.py restart                   # 重启全部容器
    python xiaozhi_deploy.py recreate                  # 先加载离线 tar 镜像，再强制重建全部容器
    python xiaozhi_deploy.py load                      # 仅把离线 tar 镜像导入 Docker（不启容器）
    python xiaozhi_deploy.py status                    # 查看容器状态
    python xiaozhi_deploy.py logs [服务名]              # 跟踪日志，如 logs xiaozhi-esp32-server-web
    python xiaozhi_deploy.py rebuild                   # 全量重建 server + web 镜像（仅在镜像 hash 变化时重建容器）
    python xiaozhi_deploy.py rebuild-server            # 仅重建 server 镜像 + server 容器
    python xiaozhi_deploy.py rebuild-web               # 仅重建 web 镜像 + web 容器
    python xiaozhi_deploy.py rebuild --force           # 强制重建容器（镜像 hash 未变也重建；改 compose 配置后用）
    python xiaozhi_deploy.py rebuild --no-cache        # 重建镜像且不使用 Docker 构建缓存（依赖也重下）
    python xiaozhi_deploy.py rebuild-web --force       # 仅重建 web，加 --force
    python xiaozhi_deploy.py save                      # 把本地 server/web 镜像导出为 tar 到项目根目录

离线镜像 tar 包（默认在项目根目录，可在脚本顶部 IMAGE_TARS 修改路径）：
    xiaozhi-server-local.tar  ->  xiaozhi-server:local
    xiaozhi-web-local.tar     ->  xiaozhi-web:local

注意：
    - 脚本所有路径都相对于本文件所在目录（项目根目录），可在任意位置执行。
    - rebuild 默认仅在镜像 hash 实际变化时重建容器（由 compose 自动判断）。
      反复 rebuild 不会重复支付 Spring Boot 启动时间。改完代码 → 自动重启；
      没改代码 → 容器保持运行，秒级返回。
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
SERVER_DOCKERFILE = os.path.join(SCRIPT_DIR, "main", "xiaozhi-server", "Dockerfile")
SERVER_CONTEXT = os.path.join(SCRIPT_DIR, "main", "xiaozhi-server")

IMAGE_SERVER = "xiaozhi-server:local"
SERVICE_SERVER = "xiaozhi-esp32-server"

IMAGE_WEB = "xiaozhi-web:local"
SERVICE_WEB = "xiaozhi-esp32-server-web"

# 离线镜像 tar 包（默认放在项目根目录，可改成实际路径）
TAR_SERVER = os.path.join(SCRIPT_DIR, "xiaozhi-server-local.tar")
TAR_WEB = os.path.join(SCRIPT_DIR, "xiaozhi-web-local.tar")
# 加载顺序无所谓，server 先加载
IMAGE_TARS = [TAR_SERVER, TAR_WEB]

# 强制开启 BuildKit，让 Dockerfile 里的 --mount=type=cache 跨 build 复用依赖
os.environ["DOCKER_BUILDKIT"] = "1"


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


def _docker_build(dockerfile, context, image, no_cache=False):
    """统一封装 docker build，支持 --no-cache。"""
    cmd = ["docker", "build", "-f", dockerfile, "-t", image]
    if no_cache:
        cmd.append("--no-cache")
    cmd.append(context)
    _run(cmd)


def _up(service, force_recreate=False):
    """按需重建单个容器。镜像 hash 未变时 compose 默认不重启，省 Spring Boot 启动时间。"""
    up_args = ["up", "-d"]
    if force_recreate:
        up_args.append("--force-recreate")
    up_args.append(service)
    _run(_compose(up_args))


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


def _build_web_image(no_cache=False):
    """构建 web 镜像（修复 start.sh 换行 + docker build）。"""
    ensure_start_sh_lf()
    if not os.path.exists(WEB_DOCKERFILE):
        print(f"[错误] 未找到离线 Dockerfile：{WEB_DOCKERFILE}", file=sys.stderr)
        sys.exit(1)
    print("=== 开始构建 web 镜像 ===")
    _docker_build(WEB_DOCKERFILE, SCRIPT_DIR, IMAGE_WEB, no_cache=no_cache)


def cmd_rebuild_web(force_recreate=False, no_cache=False):
    print("=== 构建 web 镜像 ===")
    _build_web_image(no_cache=no_cache)
    print("=== 重建 web 容器（仅在镜像变化时）===")
    _up(SERVICE_WEB, force_recreate=force_recreate)
    print("=== web 镜像已构建并按需重建容器，可用 status 查看状态 ===")


def _save_tars():
    """离线部署：把本地镜像导出为 tar 包到项目根目录（docker save）。"""
    save_map = [
        (IMAGE_SERVER, TAR_SERVER),
        (IMAGE_WEB, TAR_WEB),
    ]
    for image, tar in save_map:
        print(f"=== 导出镜像：{image} -> {tar} ===")
        _run(["docker", "save", "-o", tar, image])


def cmd_save():
    _save_tars()


def cmd_rebuild_server(force_recreate=False, no_cache=False):
    if not os.path.exists(SERVER_DOCKERFILE):
        print(f"[错误] 未找到 server Dockerfile：{SERVER_DOCKERFILE}", file=sys.stderr)
        sys.exit(1)
    print("=== 开始构建 server 镜像 ===")
    _docker_build(SERVER_DOCKERFILE, SERVER_CONTEXT, IMAGE_SERVER, no_cache=no_cache)
    print("=== 重建 server 容器（仅在镜像变化时）===")
    _up(SERVICE_SERVER, force_recreate=force_recreate)
    print("=== server 镜像已构建并按需重建容器，可用 status 查看状态 ===")


def cmd_rebuild(force_recreate=False, no_cache=False):
    """用本地源码重建 server + web 镜像，并按需重建容器。

    默认仅在镜像 hash 实际变化时重建容器（由 compose 自动判断），
    这样反复 rebuild 不会重复支付 Spring Boot 启动时间。
    改完代码 → 自动重启；没改代码 → 容器保持运行，秒级返回。

    注意：默认 server Dockerfile 仅 COPY 了 core/utils/prompt_manager.py，
    其余 server 代码来自基础镜像 xiaozhi-esp32-server:server_latest。
    如改了其它的 server 文件，请在 Dockerfile 中补充 COPY 或改为 bind mount。
    该命令不会重新加载离线 tar，避免覆盖刚构建好的镜像。
    """
    cmd_rebuild_server(force_recreate=force_recreate, no_cache=no_cache)
    cmd_rebuild_web(force_recreate=force_recreate, no_cache=no_cache)
    print("=== server + web 镜像已构建并按需重建容器，可用 status 查看状态 ===")


def _parse_flags(args):
    """解析 --force / --no-cache，返回 (force, no_cache, remaining_args)。"""
    force = False
    no_cache = False
    remaining = []
    for a in args:
        if a == "--force":
            force = True
        elif a == "--no-cache":
            no_cache = True
        else:
            remaining.append(a)
    return force, no_cache, remaining


def main():
    if not os.path.exists(COMPOSE_FILE):
        print(f"[错误] 未找到 compose 文件：{COMPOSE_FILE}", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    # 任意位置出现 --help / -h 都直接展示帮助，避免误触发真实 build
    if any(a in ("--help", "-h") for a in args):
        print(__doc__)
        sys.exit(0)

    action = args[0]
    rest = args[1:]

    if action == "help":
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
        force, no_cache, _ = _parse_flags(rest)
        cmd_rebuild_web(force_recreate=force, no_cache=no_cache)
    elif action == "rebuild-server":
        force, no_cache, _ = _parse_flags(rest)
        cmd_rebuild_server(force_recreate=force, no_cache=no_cache)
    elif action == "rebuild":
        force, no_cache, _ = _parse_flags(rest)
        cmd_rebuild(force_recreate=force, no_cache=no_cache)
    elif action == "save":
        cmd_save()
    else:
        print(f"[错误] 未知命令：{action}\n")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
