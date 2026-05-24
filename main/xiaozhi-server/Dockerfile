FROM docker.m.daocloud.io/library/node:22-bookworm-slim AS node_runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @larksuite/cli@1.0.39

FROM ghcr.nju.edu.cn/xinnan-tech/xiaozhi-esp32-server:server_latest

USER root

COPY --from=node_runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node_runtime /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -sf ../lib/node_modules/@larksuite/cli/scripts/run.js /usr/local/bin/lark-cli
