# base image
FROM node:22-alpine3.21 AS base

# if you located in China, you can use aliyun mirror to speed up
# RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# if you located in China, you can use taobao registry to speed up
# RUN npm config set registry https://registry.npmmirror.com

RUN apk add --no-cache tzdata
RUN corepack enable
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV NEXT_PUBLIC_BASE_PATH="/platform"


# install packages
FROM base AS packages

WORKDIR /app/web

COPY package.json pnpm-lock.yaml /app/web/

# Use packageManager from package.json
RUN corepack install

RUN pnpm install --frozen-lockfile

# build resources
FROM base AS builder
WORKDIR /app/web
COPY --from=packages /app/web/ .
COPY . .

ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN pnpm build:docker


# production stage
FROM base AS production

ENV NODE_ENV=production
ENV EDITION=SELF_HOSTED
ENV DEPLOY_ENV=PRODUCTION
ENV CONSOLE_API_URL=http://127.0.0.1:8000
ENV APP_API_URL=http://127.0.0.1:8001
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1
ENV PM2_INSTANCES=2

# set timezone
ENV TZ=UTC
RUN ln -s /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone

# global runtime packages
RUN pnpm add -g pm2


# Create non-root user
ARG fastapi_uid=1001
RUN addgroup -S -g ${fastapi_uid} fastapi && \
    adduser -S -u ${fastapi_uid} -G fastapi -s /bin/ash -h /home/fastapi fastapi && \
    mkdir /app && \
    mkdir /.pm2 && \
    chown -R fastapi:fastapi /app /.pm2


WORKDIR /app/web

COPY --from=builder --chown=fastapi:fastapi /app/web/public ./public
COPY --from=builder --chown=fastapi:fastapi /app/web/.next/standalone ./
COPY --from=builder --chown=fastapi:fastapi /app/web/.next/static ./.next/static

COPY --chown=fastapi:fastapi --chmod=755 docker/entrypoint.sh ./entrypoint.sh

ARG COMMIT_SHA
ENV COMMIT_SHA=${COMMIT_SHA}

USER fastapi
EXPOSE 3000
ENTRYPOINT ["/bin/sh", "./entrypoint.sh"]
