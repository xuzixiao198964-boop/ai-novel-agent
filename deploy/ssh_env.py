# -*- coding: utf-8 -*-
"""部署脚本共用：SSH 与密钥仅从环境变量读取，禁止在仓库中硬编码口令。"""
from __future__ import annotations

import os


def require_ssh_password() -> str:
    p = os.environ.get("DEPLOY_SSH_PASSWORD", "").strip()
    if not p:
        raise SystemExit(
            "未设置 DEPLOY_SSH_PASSWORD。请在 shell 中导出后再运行部署脚本，"
            "例如：set DEPLOY_SSH_PASSWORD=你的密码（Windows）或 export DEPLOY_SSH_PASSWORD=...（Linux）"
        )
    return p


def ssh_host() -> str:
    return os.environ.get("DEPLOY_SSH_HOST", "104.244.90.202").strip()


def ssh_port() -> int:
    return int(os.environ.get("DEPLOY_SSH_PORT", "22"))


def ssh_user() -> str:
    return os.environ.get("DEPLOY_SSH_USER", "root").strip()


def require_llm_api_key() -> str:
    k = os.environ.get("LLM_API_KEY", "").strip()
    if not k:
        raise SystemExit("未设置 LLM_API_KEY（写入服务器 .env 需要）")
    return k
