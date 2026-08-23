# Agent Notes

## Server Deployment

- Use `python .\xiaozhi_deploy.py rebuild` from the repository root for normal server and web rebuilds.
- The deployment script uses `main/xiaozhi-server/docker-compose_all.yml`. Do not use `docker-compose.yml` as the production verification path.
- The server image is `xiaozhi-server:local`, built from `main/xiaozhi-server/Dockerfile`.
- After rebuilding, verify with `python .\xiaozhi_deploy.py status` and inspect logs with `python .\xiaozhi_deploy.py logs xiaozhi-esp32-server`.

## Source Synchronization

- The server Dockerfile must include the current `app.py`, `config`, `core`, and `plugins_func` source. The base image is not guaranteed to contain the same source version as this repository.
- `docker-compose_all.yml` mounts runtime configuration and uploaded skills. Keep the image source and those mounts version-compatible.
- Do not validate a change only against a manually selected Compose file or an old running container.

## Volcengine TTS

- The selected provider is `TTS_HuoshanDoubleStreamTTS`.
- New-console authentication uses the `api_key` field and the `X-Api-Key` WebSocket header.
- Existing `appid` and `access_token` fields remain supported as a fallback for old-console configurations.
- The default WebSocket endpoint is `wss://openspeech.bytedance.com/api/v3/tts/bidirection`.
- The console fields are maintained by the manager-api Liquibase changelog. Apply the changelog before testing a fresh console configuration.

## Required Verification

1. Run `python .\xiaozhi_deploy.py rebuild`.
2. Confirm the server container remains running instead of restarting.
3. Trigger a Digital Human WebSocket connection and check for a successful `hello` response.
4. Confirm server logs contain no `HTTP 401` from `core.providers.tts.huoshan_double_stream`.
5. For a direct auth check, instantiate the configured TTS provider inside the running server container and verify the Volcengine WebSocket handshake.

Do not report completion based only on host-side syntax checks; the running image and the actual WebSocket path must be tested.
