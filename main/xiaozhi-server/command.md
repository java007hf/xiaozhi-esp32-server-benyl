# xiaozhi-server Docker 常用命令

以下命令都在本目录执行：

```powershell
cd C:\workspace\xiaozhi-esp32-server-benyl\main\xiaozhi-server
```

当前 `docker-compose.yml` 使用的是远程镜像：

```yaml
image: ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest
container_name: xiaozhi-esp32-server
```

所以升级时要 `pull` 新镜像，不是 `--build`。

## 查看状态

```powershell
docker-compose ps
```

查看容器是否存在：

```powershell
docker ps -a --filter "name=xiaozhi-esp32-server"
```

## 启动

```powershell
docker-compose up -d
```

## 停止

```powershell
docker-compose stop
```

## 重启

配置文件改完后，一般用这个：

```powershell
docker-compose restart
```

如果想确保重新创建容器：

```powershell
docker-compose up -d --force-recreate
```

## 停止并删除容器

不会删除 `data`、`models` 目录里的本地文件。

```powershell
docker-compose down
```

然后重新启动：

```powershell
docker-compose up -d
```

## 查看日志

实时日志：

```powershell
docker-compose logs -f
```

只看最近 200 行：

```powershell
docker-compose logs --tail=200
```

只看当前容器：

```powershell
docker logs -f xiaozhi-esp32-server
```

## 升级镜像

拉取最新镜像：

```powershell
docker-compose pull
```

重新创建并启动：

```powershell
docker-compose up -d --force-recreate
```

看启动日志确认是否正常：

```powershell
docker-compose logs -f
```

## 检查接口

OTA 接口：

```powershell
curl.exe http://127.0.0.1:8003/xiaozhi/ota/
```

视觉接口：

```powershell
curl.exe http://127.0.0.1:8003/mcp/vision/explain
```

如果 ESP32 使用局域网 IP，例如 `192.168.3.104`：

```powershell
curl.exe http://192.168.3.104:8003/xiaozhi/ota/
curl.exe http://192.168.3.104:8003/mcp/vision/explain
```

## 常用配置位置

Docker 挂载的是本地 `data` 目录：

```yaml
volumes:
  - ./data:/opt/xiaozhi-esp32-server/data
```

所以常改的是：

```text
data/.config.yaml
data/.mcp_server_settings.json
```

注意：当前 compose 使用远程镜像，本地 `core`、`plugins_func` 等代码目录不会自动进入容器。只改本地代码文件后，容器里的服务不会生效，除非改成源码构建镜像或把代码目录挂载进去。

## ESP32 使用局域网 IP 时的关键配置

如果 ESP32 通过 OTA 地址连接：

```text
http://192.168.3.104:8003/xiaozhi/ota/
```

那么 `data/.config.yaml` 里建议也使用局域网 IP，不能用 `127.0.0.1`：

```yaml
server:
  websocket: ws://192.168.3.104:8000/xiaozhi/v1/
  vision_explain: http://192.168.3.104:8003/mcp/vision/explain
```

改完后重启：

```powershell
docker-compose restart
```

然后看日志确认启动输出的地址是否正确：

```powershell
docker-compose logs --tail=100
```

## 浏览器本机测试时的配置

如果只是在同一台电脑浏览器测试，可以用：

```yaml
server:
  websocket: ws://127.0.0.1:8000/xiaozhi/v1/
  vision_explain: http://127.0.0.1:8003/mcp/vision/explain
```

但这个配置不适合 ESP32，因为 ESP32 访问 `127.0.0.1` 会访问它自己，不会访问电脑。

## 新版 Docker Compose 命令

如果你的环境支持新版命令，也可以把上面的 `docker-compose` 替换成：

```powershell
docker compose
```

例如：

```powershell
docker compose up -d
docker compose restart
docker compose logs -f
docker compose pull
```

## 飞书 MCP

当前使用方案 A：在 `data/.mcp_server_settings.json` 里配置 stdio MCP，由 `xiaozhi-esp32-server` 容器内部直接执行：

```text
lark-mcp mcp ...
```

当前 `docker-compose.yml` 使用本地自定义镜像构建：

```text
xiaozhi-esp32-server-with-node:local
```

`Dockerfile` 会基于官方 xiaozhi server 镜像安装 `node/npm`，并全局安装：

```text
@larksuiteoapi/lark-mcp@0.5.1
```

检查容器内是否支持：

```powershell
docker exec -it xiaozhi-esp32-server sh
node -v
npm -v
lark-mcp --version
exit
```

需要先在 `.env` 里填写飞书应用密钥，`docker-compose.yml` 会把它们注入到 xiaozhi 容器：

```powershell
notepad .env
```

内容格式：

```text
FEISHU_APP_ID=cli_aa8f86fa87ba5cc7
FEISHU_APP_SECRET=你的飞书应用 App Secret
```

首次部署或 Dockerfile 改动后，先构建镜像：

```powershell
docker-compose build xiaozhi-esp32-server
```

改完 `.env` 后重新创建 xiaozhi 容器，让环境变量生效：

```powershell
docker-compose up -d --force-recreate xiaozhi-esp32-server
```

如果只改了 `data/.mcp_server_settings.json`，可以只重启：

```powershell
docker-compose restart xiaozhi-esp32-server
```

查看 xiaozhi 是否加载到飞书 MCP 工具：

```powershell
docker-compose logs --tail=200 xiaozhi-esp32-server
```

正常情况下日志里应该能看到类似：

```text
初始化服务端MCP客户端: feishu
当前支持的函数列表: ...
```

如果要看更完整日志：

```powershell
docker-compose logs -f xiaozhi-esp32-server
```

## 飞书 MCP 最终部署记录

当前采用方案 A：`xiaozhi-esp32-server` 容器内部通过 stdio 启动飞书 MCP，不单独运行 `lark-mcp` 容器。

关键文件：

```text
Dockerfile
docker-compose.yml
data/.mcp_server_settings.json
.env
```

当前本地镜像：

```text
xiaozhi-esp32-server-with-node:local
```

`Dockerfile` 使用多阶段构建：

```text
第一阶段：docker.m.daocloud.io/library/node:22-bookworm-slim
第二阶段：ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest
```

第一阶段安装：

```text
@larksuiteoapi/lark-mcp@0.5.1
```

第二阶段把 `node/npm/npx/lark-mcp` 复制进 xiaozhi 镜像。使用 `docker.m.daocloud.io` 是为了避免 Docker Hub 直连失败。

当前 `data/.mcp_server_settings.json` 配置为：

```json
{
  "mcpServers": {
    "feishu": {
      "command": "sh",
      "args": [
        "-c",
        "lark-mcp mcp --app-id \"$FEISHU_APP_ID\" --app-secret \"$FEISHU_APP_SECRET\" --domain https://open.feishu.cn --tools preset.default --tool-name-case snake --language zh --token-mode auto --mode stdio"
      ]
    }
  }
}
```

`.env` 里保存飞书应用配置：

```text
FEISHU_APP_ID=cli_aa8f86fa87ba5cc7
FEISHU_APP_SECRET=你的飞书应用 App Secret
```

首次部署或修改 `Dockerfile` 后：

```powershell
docker-compose build xiaozhi-esp32-server
docker-compose up -d --force-recreate xiaozhi-esp32-server
```

修改 `.env` 或 `docker-compose.yml` 后，需要重新创建容器：

```powershell
docker-compose up -d --force-recreate xiaozhi-esp32-server
```

只修改 `data/.mcp_server_settings.json` 后，可以只重启：

```powershell
docker-compose restart xiaozhi-esp32-server
```

验证容器内 Node 和飞书 MCP：

```powershell
docker exec xiaozhi-esp32-server sh -c "node -v && npm -v && npx -v && lark-mcp --version"
```

当前已验证结果：

```text
node v22.22.3
npm 10.9.8
npx 10.9.8
lark-mcp 0.5.1
```

不输出密钥内容，只检查飞书环境变量是否注入：

```powershell
docker exec xiaozhi-esp32-server sh -c 'test -n "$FEISHU_APP_ID" && test -n "$FEISHU_APP_SECRET" && echo FEISHU_ENV_OK'
```

确认当前容器使用本地镜像：

```powershell
docker inspect xiaozhi-esp32-server --format "{{.Config.Image}}"
```

应该输出：

```text
xiaozhi-esp32-server-with-node:local
```

查看 MCP 初始化日志：

```powershell
docker-compose logs --tail=200 xiaozhi-esp32-server
```

正常应看到类似：

```text
初始化服务端MCP客户端: feishu
当前支持的函数列表: ...
```

重建后检查 OTA 下发地址：

```powershell
curl.exe -s http://127.0.0.1:8003/xiaozhi/ota/
```

ESP32 场景下应该是局域网 IP，例如：

```text
OTA接口运行正常，向设备发送的websocket地址是：ws://192.168.3.104:8000/xiaozhi/v1/
```

如果变成 `127.0.0.1` 或 `172.x.x.x`，检查 `data/.config.yaml`：

```yaml
server:
  websocket: ws://192.168.3.104:8000/xiaozhi/v1/
  vision_explain: http://192.168.3.104:8003/mcp/vision/explain
```

## 飞书 MCP 本人身份映射

当前 `lark-mcp` 使用 App ID/Secret 以应用身份启动，不会自动继承宿主机 `lark-cli auth status` 里的当前用户。因此用户说“我自己”“发给我”时，模型不一定知道应该发给谁。

已在 `data/.config.yaml` 的默认 `prompt` 中加入本人映射：

```text
当用户说“我”“我自己”“发给我”“给我发消息”时，默认指飞书用户王映理。
王映理的飞书 open_id 是 ou_f570159fe59f7faa0b5722a3b2d748ee。
使用飞书 MCP 发送消息给用户本人时，直接使用这个 open_id，不要再询问手机号或邮箱。
```

修改 `data/.config.yaml` 后重启即可生效：

```powershell
docker-compose restart xiaozhi-esp32-server
```

如果以后换使用者，需要同步修改 `data/.config.yaml` 里的这个 open_id。

宿主机查询当前 lark-cli 授权用户：

```powershell
& 'C:\Users\Administrator\AppData\Local\npm-cache\_npx\cca705bd6109e4e4\node_modules\.bin\lark-cli.cmd' auth status
```

## Skills + shell_command 方案

当前飞书能力已经从 MCP 方案切换为官方 Skills + 通用 shell 工具方案。

核心思路：

```text
官方 lark-* skills 负责告诉模型什么时候用 lark-cli
shell_command 负责在 xiaozhi 容器里执行 CLI 命令
lark-cli 负责真正调用飞书开放平台
```

当前已接入的项目 skills：

```text
skills/lark-shared
skills/lark-im
skills/shell
skills/weather
```

`skills/shell/SKILL.md` 绑定的函数：

```text
shell_command
```

`shell_command` 是通用命令执行工具，不是飞书专用。以后接入其他 CLI 型 skill 时，只要对应 CLI 已安装，skill 可以通过 `shell_command` 执行命令。

飞书 MCP 已删除，当前 `data/.mcp_server_settings.json` 为：

```json
{"mcpServers":{}}
```

容器内验证 skills 加载：

```powershell
docker exec xiaozhi-esp32-server sh -c "cd /opt/xiaozhi-esp32-server && python -c 'from config.config_loader import load_config; from core.providers.skills import SkillLoader; c=load_config(); print(SkillLoader(c).get_enabled_functions()); print([s.name for s in SkillLoader(c).get_enabled_skills()])'"
```

期望看到：

```text
['shell_command', 'get_weather']
['lark-im', 'lark-shared', 'shell', 'weather']
```

飞书 CLI 安装在镜像内：

```powershell
docker exec xiaozhi-esp32-server sh -c "lark-cli --help"
```

容器启动时会自动执行：

```sh
printf "%s" "$FEISHU_APP_SECRET" | lark-cli config init --app-id "$FEISHU_APP_ID" --app-secret-stdin --brand feishu --force-init && python app.py
```

所以每次容器重建后都会重新初始化 lark-cli，避免 keychain 配置丢失。

验证 bot 身份：

```powershell
docker exec xiaozhi-esp32-server sh -c "lark-cli auth status"
```

期望看到：

```text
Bot identity: ready
```

直接测试发送消息：

```powershell
docker exec xiaozhi-esp32-server sh -c "lark-cli im +messages-send --user-id ou_f570159fe59f7faa0b5722a3b2d748ee --text hello --as bot"
```

当前已验证该命令发送成功。

## 当前有效状态补充

当前已经从“飞书 MCP”切换为“官方飞书 Skills + 通用 `shell_command` 工具”方案。

当前 `data/.mcp_server_settings.json` 应保持为空：

```json
{"mcpServers":{}}
```

当前飞书相关能力依赖：

```text
skills/lark-shared
skills/lark-im
skills/shell
plugins_func/functions/shell_command.py
core/providers/skills
core/providers/tools/server_plugins
```

注意：`shell_command` 是否进入“当前支持的函数列表”，取决于容器内是否加载到本地修改后的 `plugin_executor.py`。因此 `docker-compose.yml` 需要挂载：

```yaml
  - ./core/providers/tools/server_plugins:/opt/xiaozhi-esp32-server/core/providers/tools/server_plugins
```

修改 `docker-compose.yml` 或挂载目录后，要重新创建容器：

```powershell
docker-compose up -d --force-recreate xiaozhi-esp32-server
```

然后让 ESP32 或网页端重新连接一次，工具列表会在新会话初始化时刷新。

验证 Skills 是否加载到 `shell_command`：

```powershell
docker exec xiaozhi-esp32-server sh -c "cd /opt/xiaozhi-esp32-server && python -c 'from config.config_loader import load_config; from core.providers.skills import SkillLoader; c=load_config(); print(SkillLoader(c).get_enabled_functions()); print([s.name for s in SkillLoader(c).get_enabled_skills()])'"
```

期望看到：

```text
['shell_command', 'get_weather']
['lark-im', 'lark-shared', 'shell', 'weather']
```

验证飞书 bot 身份：

```powershell
docker exec xiaozhi-esp32-server sh -c "lark-cli auth status"
```

期望看到：

```text
Bot identity: ready
```

直接验证飞书发送链路：

```powershell
docker exec xiaozhi-esp32-server sh -c "lark-cli im +messages-send --user-id ou_f570159fe59f7faa0b5722a3b2d748ee --text hello --as bot"
```

## Skills 命令执行解耦规则

不要修改每个官方 skill 来适配小智。当前采用通用 `skills/shell/SKILL.md` 做运行时适配：

```text
任何已启用 skill 要求执行 CLI / shell / terminal / lark-cli / npm / npx / python / node / git / curl 等命令时，统一调用 shell_command。
```

因此新增其他 CLI 型 skill 时，通常只需要：

```text
1. 把 skill 放到 skills/ 目录
2. 确保对应 CLI 在容器里已安装
3. 确保 shell skill 已启用
4. 重新连接 ESP32/网页端会话，让系统提示重新注入
```

`skills/shell/SKILL.md` 必须是无 BOM UTF-8，否则 SkillLoader 可能无法识别 YAML frontmatter。

验证 shell skill 已加载：

```powershell
docker exec xiaozhi-esp32-server python -c "from config.config_loader import load_config; from core.providers.skills import SkillLoader; c=load_config(); l=SkillLoader(c); print([x.name for x in l.get_enabled_skills()]); p=l.build_prompt_block(); print('shell_command' in p); print(len(p))"
```

## Codex-style Skills Runtime

当前已新增通用 skill 运行时能力，不改官方飞书 skills，也不在 `shell_command` 中写飞书特例。

新增文件：

```text
skills/skill-runtime/SKILL.md
plugins_func/functions/skill_read_reference.py
```

新增工具：

```text
skill_read_reference
```

用途：当任意已启用 skill 引用了 reference、workflow、`references/*.md` 或其他 skill 文件，模型可以主动调用 `skill_read_reference` 读取，不需要等工具失败后才读。

示例：

```json
{
  "skill_name": "lark-im",
  "path": "references/lark-im-messages-send.md"
}
```

也支持读取相邻已启用 skill：

```json
{
  "skill_name": "lark-im",
  "path": "../lark-shared/SKILL.md"
}
```

安全边界：只能读取已启用 skill 目录内的文件，不能借此读取项目任意文件。

工具结果回灌也增加了通用 agent loop 提示：

```text
如果下一步需要某个 skill 的准确命令、参数、workflow 或约束，优先调用 skill_read_reference 主动读取相关 reference。
如果工具失败，并且错误信息或 reference 能明确给出修正方法，可以继续调用工具进行有限重试。
最终回复不要朗读 stdout/stderr/exit_code/JSON。
```

验证：

```powershell
docker exec xiaozhi-esp32-server python -c "from config.config_loader import load_config; from core.providers.skills import SkillLoader; c=load_config(); l=SkillLoader(c); print([s.name for s in l.get_enabled_skills()]); print(l.get_enabled_functions())"
```

期望包含：

```text
skill-runtime
skill_read_reference
```

直接验证读取飞书发送消息 reference：

```powershell
docker exec xiaozhi-esp32-server python -c "from config.config_loader import load_config; from plugins_func.functions.skill_read_reference import skill_read_reference; C=type('C', (), {}); c=C(); c.config=load_config(); r=skill_read_reference(c, 'lark-im', 'references/lark-im-messages-send.md', 1200); print(r.action); print((r.result or '')[:800])"
```
