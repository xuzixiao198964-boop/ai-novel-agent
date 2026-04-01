# AI Novel Media Agent 架构设计文档

## 设计信息
- **设计阶段**: 架构设计（资源约束适配版）
- **设计日期**: 2026-04-01
- **设计模型**: Claude (via Cursor)
- **工程方法**: OpenClaw软件工程化全流程
- **设计状态**: ✅ 完成
- **目标服务器**: 104.244.90.202（2核/1GB RAM/20GB磁盘）

## ⚠️ 服务器资源约束说明

本架构设计基于以下**真实硬件约束**，所有技术决策均围绕此约束展开：

```
┌────────────────────────────────────────────────────────┐
│  服务器: 104.244.90.202 (裸金属 Ubuntu 24.04 LTS)      │
├────────────────────────────────────────────────────────┤
│  CPU:   2 核                                           │
│  RAM:   1GB 总量 (可用 ~476MB)                          │
│  Swap:  4.5GB (重度使用中)                              │
│  Disk:  20GB 总量 (可用 ~1GB, 使用率 95%!)              │
│  OS:    Ubuntu 24.04 LTS                               │
├────────────────────────────────────────────────────────┤
│  已运行服务:                                            │
│  - PostgreSQL 16           (端口 5432)                  │
│  - ai-novel-agent (FastAPI) (端口 9000)                 │
│  - media-agent (uvicorn+celery) (端口 9090)             │
├────────────────────────────────────────────────────────┤
│  ❌ 不可用: Docker, Redis, RabbitMQ, Pinecone,          │
│            MinIO/S3, Prometheus, Grafana, Loki, Kong    │
└────────────────────────────────────────────────────────┘
```

---

## 1. 架构设计原则

### 1.1 设计目标
```
1. 资源极致利用：在 2核/1GB RAM/20GB 磁盘约束下稳定运行
2. 可维护性：模块化设计，清晰边界，单进程内模块解耦
3. 安全性：JWT认证 + HTTPS + 审计日志
4. 性能：API响应时间 < 500ms（简单查询），合理容忍长任务
5. 成本效益：零额外基础设施成本，所有组件共享同一 PostgreSQL
6. 渐进扩展：架构支持未来升级到更强硬件后逐步拆分
```

### 1.2 架构风格选择
```
选择：模块化单体 (Modular Monolith)

理由：
1. 1GB 内存无法同时运行多个独立服务进程
2. 单进程模块间调用零网络开销，性能最优
3. 共享数据库连接池，避免连接数爆炸
4. 部署维护简单：一个 systemd service 管理一切
5. 模块边界清晰，未来可按需拆分为独立服务

❌ 明确拒绝：
- 微服务：内存不够运行多个独立进程
- Docker：额外内存/磁盘开销不可承受
- 独立BFF服务：每个BFF占用独立端口和内存，不现实
```

### 1.3 关键技术约束与替代方案
```
┌──────────────────┬────────────────────────────────────────┐
│  原方案(不可用)    │  替代方案                               │
├──────────────────┼────────────────────────────────────────┤
│  Redis 缓存       │  Python lru_cache / cachetools.TTLCache │
│  RabbitMQ 消息队列 │  PostgreSQL task_queue 表 + 轮询        │
│  Pinecone 向量库  │  PostgreSQL pg_trgm + GIN 索引          │
│  MinIO/S3 存储    │  本地文件系统 + 自动清理策略              │
│  Prometheus       │  /health + /metrics 端点 + 日志          │
│  Grafana          │  systemd journal + logrotate            │
│  Loki             │  Python logging → 轮转文件               │
│  Kong 网关        │  Nginx 反向代理                          │
│  Docker           │  systemd 服务 + venv 虚拟环境            │
│  多个 BFF 进程     │  单进程内路径路由 (/api/web/*, /api/wx/*) │
│  Celery + Redis   │  PostgreSQL 任务表 或 asyncio 内部队列   │
└──────────────────┴────────────────────────────────────────┘
```

---

## 2. 系统架构概览

### 2.1 整体架构图
```
┌─────────────────────────────────────────────────────────────────────────┐
│                              客户端层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Web前端   │  │ 微信小程序 │  │ 抖音小程序 │  │ Native   │  │ OpenClaw │ │
│  │ (React)  │  │          │  │          │  │  App     │  │  CLI     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       └──────────────┴──────────────┴──────┬──────┴──────────────┘      │
└────────────────────────────────────────────┼────────────────────────────┘
                                             │ HTTPS
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Nginx 反向代理 (:80/443)                           │
│                                                                         │
│  路由规则:                                                               │
│  /api/*       → FastAPI (:9000)                                         │
│  /static/*    → 本地静态文件                                              │
│  /ws/*        → WebSocket 代理 → FastAPI                                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               单一 FastAPI 进程 (:9000) — 模块化单体                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     核心中间件层                                  │    │
│  │  JWT认证 │ 限流 │ 日志 │ 异常处理 │ CORS │ 请求追踪              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Auth      │  │ Payment   │  │ Novel     │  │ Video     │           │
│  │ Module    │  │ Module    │  │ Module    │  │ Module    │           │
│  │           │  │           │  │           │  │           │           │
│  │ 用户认证   │  │ 支付/退款  │  │ 7-Agent   │  │ TTS+FFmpeg│           │
│  │ SSO/多端  │  │ 对账/发票  │  │ 流水线     │  │ 视频生成   │           │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘           │
│                                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │ Publish   │  │ Subscribe │  │ Quality   │  │ Review    │           │
│  │ Module    │  │ Module    │  │ Module    │  │ Module    │           │
│  │           │  │           │  │           │  │           │           │
│  │ 多平台发布 │  │ 套餐/计费  │  │ 专家建议   │  │ 视频评审   │           │
│  │ 适配器模式 │  │ 权益引擎   │  │ 冲突检测   │  │ 记忆点     │           │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     渠道适配层 (路径路由)                         │    │
│  │  /api/web/*  │ /api/wx/*  │ /api/dy/*  │ /api/app/* │ /api/oc/* │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                     共享基础设施层                                │    │
│  │  SQLAlchemy连接池 │ 进程内缓存 │ 后台任务调度 │ 文件管理           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
          ┌────────────┐ ┌──────────┐ ┌──────────────┐
          │ PostgreSQL │ │ 本地文件  │ │ 后台Worker   │
          │   (:5432)  │ │ 系统     │ │ (可选Celery)  │
          │            │ │          │ │ concurrency=1│
          │ 业务数据    │ │ /opt/    │ │ PG作为Broker │
          │ 任务队列    │ │ ai-novel │ │              │
          │ 会话缓存    │ │ -agent/  │ └──────────────┘
          │ 审计日志    │ │ data/    │
          └────────────┘ └──────────┘
```

### 2.2 模块划分设计

所有模块在同一 FastAPI 进程内以 **APIRouter** 方式注册，通过 Python 包边界实现解耦：

```
ai-novel-agent/
├── app/
│   ├── main.py                 # FastAPI 入口，注册所有 Router
│   ├── core/                   # 核心层：配置、安全、DB、缓存
│   │   ├── config.py           # 全局配置 (Pydantic Settings)
│   │   ├── security.py         # JWT、密码哈希、限流
│   │   ├── database.py         # SQLAlchemy async engine + session
│   │   ├── cache.py            # 进程内缓存 (TTLCache)
│   │   ├── task_queue.py       # PostgreSQL 任务队列
│   │   └── file_manager.py     # 本地文件管理 + 清理策略
│   │
│   ├── modules/
│   │   ├── auth/               # 认证模块 (JWT, SSO, 多渠道登录)
│   │   │   ├── router.py
│   │   │   ├── service.py
│   │   │   ├── models.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── payment/            # 支付模块 (Webhook, 退款, 对账)
│   │   ├── novel/              # 小说模块 (7-Agent 流水线)
│   │   ├── video/              # 视频模块 (TTS + FFmpeg)
│   │   ├── publish/            # 发布模块 (多平台适配器)
│   │   ├── subscription/       # 订阅模块 (套餐, 计费, 权益)
│   │   ├── quality/            # 质量模块 (专家建议, 冲突检测)
│   │   └── review/             # 评审模块 (视频评审, 记忆点)
│   │
│   ├── channels/               # 渠道适配层 (替代独立BFF)
│   │   ├── web.py              # Web端适配 (/api/web/*)
│   │   ├── wechat.py           # 微信小程序适配 (/api/wx/*)
│   │   ├── douyin.py           # 抖音小程序适配 (/api/dy/*)
│   │   ├── app_native.py       # App端适配 (/api/app/*)
│   │   └── openclaw.py         # OpenClaw适配 (/api/oc/*)
│   │
│   └── background/             # 后台任务
│       ├── task_worker.py      # 任务消费者 (轮询 task_queue 表)
│       ├── cleanup.py          # 磁盘清理任务
│       └── scheduler.py        # 定时任务 (APScheduler)
│
├── alembic/                    # 数据库迁移
├── scripts/                    # 运维脚本
│   ├── disk_cleanup.sh         # 磁盘清理 cron 脚本
│   └── health_check.py         # 健康检查脚本
└── requirements.txt
```

### 2.3 模块间通信

```
模块间通信方式（单进程内）：

1. 同步调用：直接 import 调用 service 层函数
   示例：payment.service 调用 subscription.service.check_entitlement()
   优势：零序列化开销，零网络延迟

2. 异步任务：写入 PostgreSQL task_queue 表
   示例：novel.service 提交生成任务 → task_worker 轮询执行
   优势：解耦长任务，防止阻塞 API 响应

3. 进程内事件：Python 信号机制 (blinker 库)
   示例：支付完成 → 发送 payment_completed 信号 → 订阅模块监听激活
   优势：模块解耦，无外部依赖

通信规则：
- 模块间仅通过 service 层公开接口通信
- 禁止跨模块直接访问 models/ORM 对象
- 共享的数据通过 schemas (Pydantic) 传递
```

---

## 3. 数据架构设计

### 3.1 数据存储策略
```
数据分层（全部基于 PostgreSQL + 本地文件系统）：

1. 业务数据 → PostgreSQL (唯一数据库)
   - 所有业务表、会话数据、任务队列、审计日志

2. 缓存数据 → Python 进程内缓存 (零额外内存服务)
   - cachetools.TTLCache：带 TTL 的 LRU 缓存
   - functools.lru_cache：纯函数结果缓存

3. 文件数据 → 本地文件系统
   - /opt/ai-novel-agent/data/novels/    小说文件
   - /opt/ai-novel-agent/data/videos/    视频文件
   - /opt/ai-novel-agent/data/audio/     音频文件
   - /opt/ai-novel-agent/data/temp/      临时文件
   - /opt/ai-novel-agent/data/invoices/  发票PDF
   - /opt/ai-novel-agent/logs/           应用日志

4. 文本搜索 → PostgreSQL pg_trgm + GIN 索引
   - 替代向量数据库，用于专家建议语义匹配
   - 关键词搜索 + 三元组相似度匹配

❌ 不使用：
- Redis：内存不足
- Pinecone：外部服务成本 + 复杂度
- MinIO/S3：磁盘空间不足以运行对象存储服务
- 读写分离/从库：单机部署无需
```

### 3.2 核心数据表设计

#### 用户相关表
```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 用户认证绑定表 (多端SSO)
CREATE TABLE user_auth_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,       -- wechat/douyin/phone/email/apple
    open_id VARCHAR(255) NOT NULL,       -- 各平台的openid
    union_id VARCHAR(255),               -- 微信unionid等
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, open_id)
);

-- API密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '[]',
    ip_restrictions CIDR[],
    usage_limits JSONB,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_auth_bindings_user ON user_auth_bindings(user_id);
CREATE INDEX idx_auth_bindings_provider ON user_auth_bindings(provider, open_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key ON api_keys(key);
```

#### 支付相关表
```sql
-- 订单表
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'CNY',
    status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(20),
    transaction_id VARCHAR(100),
    channel VARCHAR(20),                 -- web/wechat/douyin/app
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 支付记录表
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook幂等记录表 (替代 Redis SETNX)
CREATE TABLE webhook_idempotency (
    transaction_id VARCHAR(100) PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result JSONB
);

-- 退款记录表
CREATE TABLE refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refund_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by UUID,
    reviewed_at TIMESTAMP,
    review_note TEXT,
    gateway_refund_id VARCHAR(100),
    completed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对账记录表
CREATE TABLE reconciliation_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_date DATE NOT NULL,
    payment_provider VARCHAR(20) NOT NULL,
    total_orders INT DEFAULT 0,
    total_amount DECIMAL(12, 2) DEFAULT 0.00,
    matched_count INT DEFAULT 0,
    mismatched_count INT DEFAULT 0,
    missing_in_system INT DEFAULT 0,
    missing_in_gateway INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reconciliation_date, payment_provider)
);

-- 发票表
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID,
    order_id UUID REFERENCES orders(id),
    invoice_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    invoice_type VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    tax_number VARCHAR(30),
    status VARCHAR(20) DEFAULT 'pending',
    issued_at TIMESTAMP,
    pdf_path VARCHAR(500),              -- 本地文件路径 (非S3)
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_transaction_id ON payments(transaction_id);
CREATE INDEX idx_webhook_idempotency_time ON webhook_idempotency(processed_at);
CREATE INDEX idx_refunds_order_id ON refunds(order_id);
CREATE INDEX idx_refunds_user_id ON refunds(user_id);
CREATE INDEX idx_refunds_status ON refunds(status);
CREATE INDEX idx_reconciliation_date ON reconciliation_records(reconciliation_date);
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_invoice_no ON invoices(invoice_no);
```

#### 内容相关表
```sql
-- 小说表
CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    genre VARCHAR(50) NOT NULL,
    chapters INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INT DEFAULT 0,
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 章节表
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(255),
    content TEXT,
    word_count INT,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(novel_id, chapter_number)
);

-- 视频表
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL,
    source_id UUID,
    title VARCHAR(255) NOT NULL,
    generation_mode VARCHAR(20) NOT NULL,
    duration INT,
    file_path VARCHAR(500),             -- 本地文件路径
    file_size_bytes BIGINT,             -- 文件大小 (用于磁盘管理)
    status VARCHAR(20) DEFAULT 'pending',
    progress INT DEFAULT 0,
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_novels_user_id ON novels(user_id);
CREATE INDEX idx_novels_status ON novels(status);
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_source ON videos(source_type, source_id);
CREATE INDEX idx_videos_created ON videos(created_at);  -- 用于清理策略
```

#### 发布相关表
```sql
-- 发布记录表
CREATE TABLE publish_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL,
    content_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_account_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    publish_time TIMESTAMP,
    platform_content_id VARCHAR(100),
    analytics JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 平台账号表
CREATE TABLE platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    permissions JSONB,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, platform, account_id)
);

CREATE INDEX idx_publish_records_user_id ON publish_records(user_id);
CREATE INDEX idx_publish_records_content ON publish_records(content_type, content_id);
CREATE INDEX idx_publish_records_platform ON publish_records(platform);
CREATE INDEX idx_platform_accounts_user_id ON platform_accounts(user_id);
```

#### 订阅与权益相关表
```sql
-- 套餐定义表
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    tier INT NOT NULL,
    max_word_count INT,
    monthly_quota INT,
    monthly_price DECIMAL(10, 2),
    yearly_price DECIMAL(10, 2),
    markup_ratio DECIMAL(4, 2) DEFAULT 1.15,
    features JSONB NOT NULL DEFAULT '{}',
    priority_level INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户订阅表
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES subscription_plans(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    billing_cycle VARCHAR(10) NOT NULL DEFAULT 'monthly',
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    monthly_used INT DEFAULT 0,
    auto_renew BOOLEAN DEFAULT true,
    cancelled_at TIMESTAMP,
    upgrade_from_plan_id UUID,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 权益表
CREATE TABLE entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    entitlement_type VARCHAR(50) NOT NULL,
    quota_limit INT,
    quota_used INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscription_plans_tier ON subscription_plans(tier);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_period ON user_subscriptions(current_period_end);
CREATE INDEX idx_entitlements_user_id ON entitlements(user_id);
CREATE INDEX idx_entitlements_subscription_id ON entitlements(subscription_id);
```

#### 内容质量与专家建议相关表
```sql
-- 专家建议表 (使用 pg_trgm 替代 Pinecone 向量检索)
CREATE TABLE expert_advices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    applicable_genres TEXT[] NOT NULL,
    applicable_lengths TEXT[] NOT NULL,
    applicable_styles TEXT[],
    content TEXT NOT NULL,
    keywords TEXT[],
    quality_score DECIMAL(3, 2),
    usage_count INT DEFAULT 0,
    -- 移除 embedding_vector_id，改用 pg_trgm 全文搜索
    search_text TEXT GENERATED ALWAYS AS (
        content || ' ' || array_to_string(keywords, ' ')
    ) STORED,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建议冲突规则表
CREATE TABLE advice_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advice_id_a UUID REFERENCES expert_advices(id) ON DELETE CASCADE,
    advice_id_b UUID REFERENCES expert_advices(id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL,
    severity VARCHAR(10) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(advice_id_a, advice_id_b)
);

-- 冲突强度规则表
CREATE TABLE conflict_intensity_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    length_tier VARCHAR(20) NOT NULL,
    min_conflict_level INT NOT NULL,
    max_words_per_conflict INT,
    conflict_structure TEXT NOT NULL,
    example TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建议使用记录表
CREATE TABLE advice_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE,
    advice_ids UUID[] NOT NULL,
    combination_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 启用 pg_trgm 扩展用于文本相似度搜索
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_expert_advices_search ON expert_advices USING GIN(search_text gin_trgm_ops);
CREATE INDEX idx_expert_advices_genres ON expert_advices USING GIN(applicable_genres);
CREATE INDEX idx_expert_advices_lengths ON expert_advices USING GIN(applicable_lengths);
CREATE INDEX idx_expert_advices_category ON expert_advices(category);
CREATE INDEX idx_advice_conflicts_a ON advice_conflicts(advice_id_a);
CREATE INDEX idx_advice_conflicts_b ON advice_conflicts(advice_id_b);
CREATE INDEX idx_conflict_rules_tier ON conflict_intensity_rules(length_tier);
CREATE INDEX idx_advice_usage_hash ON advice_usage_records(combination_hash);
CREATE INDEX idx_advice_usage_novel ON advice_usage_records(novel_id);
```

#### 视频评审与记忆点相关表
```sql
-- 视频评审表
CREATE TABLE video_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    review_stage VARCHAR(20) NOT NULL,
    opening_type VARCHAR(20),
    score_opening DECIMAL(3, 1),
    score_completeness DECIMAL(3, 1),
    score_quality DECIMAL(3, 1),
    score_platform_fit DECIMAL(3, 1),
    score_commercial DECIMAL(3, 1),
    total_score DECIMAL(4, 2),
    pass_status VARCHAR(10) NOT NULL DEFAULT 'pending',
    suggestions TEXT,
    reviewer_type VARCHAR(10) NOT NULL,
    reviewer_id VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 记忆点表
CREATE TABLE memory_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    point_type VARCHAR(20) NOT NULL,
    timestamp_start DECIMAL(8, 2),
    timestamp_end DECIMAL(8, 2),
    content TEXT NOT NULL,
    strength_score DECIMAL(3, 1),
    thumbnail_path VARCHAR(500),        -- 本地路径
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_video_reviews_video_id ON video_reviews(video_id);
CREATE INDEX idx_video_reviews_stage ON video_reviews(review_stage);
CREATE INDEX idx_video_reviews_pass ON video_reviews(pass_status);
CREATE INDEX idx_memory_points_video_id ON memory_points(video_id);
CREATE INDEX idx_memory_points_type ON memory_points(point_type);
```

#### 任务队列表 (替代 RabbitMQ)
```sql
-- PostgreSQL 任务队列表
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,       -- novel_generate, video_generate, publish, review...
    payload JSONB NOT NULL,               -- 任务参数
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    priority INT DEFAULT 0,               -- 优先级 (高套餐用户优先)
    max_retries INT DEFAULT 3,
    retry_count INT DEFAULT 0,
    error_message TEXT,
    created_by UUID,                      -- 创建者 user_id
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 死信记录表 (替代 RabbitMQ DLQ)
CREATE TABLE task_dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_task_id UUID REFERENCES task_queue(id),
    task_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    error_message TEXT,
    retry_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_queue_status ON task_queue(status, priority DESC, created_at);
CREATE INDEX idx_task_queue_type ON task_queue(task_type);
CREATE INDEX idx_task_queue_created_by ON task_queue(created_by);
CREATE INDEX idx_task_dead_letters_type ON task_dead_letters(task_type);
```

#### 审计日志表 (替代 Loki)
```sql
-- 审计日志表 (关键操作记录)
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_time ON audit_logs(created_at);

-- 自动清理30天前的审计日志 (磁盘管理)
-- 通过 APScheduler 定时执行:
-- DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '30 days';
```

### 3.3 PostgreSQL 配置优化 (1GB RAM 环境)
```
# postgresql.conf 关键参数

shared_buffers = 128MB          # 总内存的 ~13%
effective_cache_size = 256MB    # OS + PG 缓存总估计
work_mem = 4MB                  # 每个排序/哈希操作
maintenance_work_mem = 64MB     # VACUUM/CREATE INDEX
wal_buffers = 4MB
max_connections = 20            # 严格限制连接数

# WAL 配置 (控制磁盘使用)
max_wal_size = 256MB            # 限制 WAL 文件总量
min_wal_size = 64MB
checkpoint_completion_target = 0.9

# 日志 (最小化磁盘占用)
log_min_duration_statement = 1000   # 只记录 >1s 的慢查询
log_rotation_age = 1d
log_rotation_size = 10MB

# 自动清理
autovacuum = on
autovacuum_max_workers = 1          # 只用 1 个 worker (CPU 限制)
autovacuum_naptime = 60s
```

---

## 4. 缓存策略设计 (无 Redis)

### 4.1 进程内缓存架构
```
缓存层级 (仅 L1 + L2，无外部缓存服务)：

L1: Python 进程内缓存
   实现：cachetools.TTLCache / functools.lru_cache
   零额外内存服务开销，缓存与应用进程共享内存

   ┌──────────────────┬─────────┬───────────┬──────────────────┐
   │  缓存对象         │ 最大条目 │ TTL       │ 实现方式          │
   ├──────────────────┼─────────┼───────────┼──────────────────┤
   │  用户会话信息      │ 100     │ 60min     │ TTLCache         │
   │  套餐配置         │ 20      │ 30min     │ TTLCache         │
   │  权益检查结果      │ 200     │ 5min      │ TTLCache         │
   │  专家建议热门      │ 50      │ 15min     │ TTLCache         │
   │  API 限流计数器   │ 500     │ 1min      │ dict + 定时清理   │
   │  系统配置         │ 30      │ 10min     │ TTLCache         │
   └──────────────────┴─────────┴───────────┴──────────────────┘

   内存估算：每条目约 1-2KB，总计 ~1MB，可忽略不计

L2: PostgreSQL 物化视图 (昂贵查询结果缓存)
   用途：统计报表、热门内容排行等
   刷新策略：APScheduler 定时刷新 (每小时)

   示例：
   CREATE MATERIALIZED VIEW mv_daily_stats AS
   SELECT ... FROM orders ... GROUP BY date;

   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_stats;

❌ 无 L3/CDN 层：初期不需要

缓存更新策略：
- 写后失效：数据更新后清除对应缓存条目
- 懒加载：缓存 miss 时从 DB 加载
- TTL 兜底：即使不主动失效，TTL 到期后自动淘汰
```

### 4.2 缓存代码示例
```python
# app/core/cache.py
from cachetools import TTLCache
import threading

class AppCache:
    """进程内缓存管理器，替代 Redis"""

    def __init__(self):
        self._lock = threading.Lock()
        self.user_sessions = TTLCache(maxsize=100, ttl=3600)
        self.plan_configs = TTLCache(maxsize=20, ttl=1800)
        self.entitlement_checks = TTLCache(maxsize=200, ttl=300)
        self.rate_limits = TTLCache(maxsize=500, ttl=60)

    def get_or_load(self, cache, key, loader_fn):
        """缓存未命中时调用 loader_fn 加载"""
        val = cache.get(key)
        if val is None:
            with self._lock:
                val = cache.get(key)
                if val is None:
                    val = loader_fn()
                    cache[key] = val
        return val

    def invalidate(self, cache, key):
        """主动失效"""
        cache.pop(key, None)

app_cache = AppCache()
```

---

## 5. 任务队列设计 (无 RabbitMQ)

### 5.1 PostgreSQL 任务队列方案
```
方案选择：PostgreSQL task_queue 表 + 轮询消费

优势：
- 零额外服务，复用已有 PostgreSQL
- 事务保证：任务创建与业务操作在同一事务
- 持久化：天然持久，无需担心消息丢失
- 可查询：任务状态可直接 SQL 查询

劣势：
- 轮询有延迟 (可接受，设置 2-5 秒间隔)
- 无 pub/sub 能力 (用 Python blinker 替代)

架构：
  ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
  │  API 请求     │────▶│ task_queue 表    │◀────│  Task Worker  │
  │  (生产者)     │     │   (PostgreSQL)   │     │  (消费者)     │
  │              │     │                 │     │  轮询间隔 3s  │
  │ INSERT INTO  │     │ status=pending  │     │ SELECT FOR    │
  │ task_queue   │     │ → running       │     │ UPDATE SKIP   │
  │              │     │ → completed     │     │ LOCKED        │
  └──────────────┘     └─────────────────┘     └──────────────┘

消费者 SQL (行级锁防止并发消费)：
  WITH next_task AS (
    SELECT id FROM task_queue
    WHERE status = 'pending'
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
  )
  UPDATE task_queue SET status = 'running', started_at = NOW()
  WHERE id = (SELECT id FROM next_task)
  RETURNING *;

重试机制：
  任务失败 → retry_count += 1
  retry_count < max_retries → 重新置为 pending (指数退避)
  retry_count >= max_retries → 移入 task_dead_letters 表

死信处理：
  死信表中的任务由管理员手动检查
  可通过 /api/v1/admin/dead-letters 查看和重试
```

### 5.2 任务类型定义
```
┌───────────────────┬───────────────────────────────────────┐
│  task_type         │ 描述                                  │
├───────────────────┼───────────────────────────────────────┤
│ novel_generate     │ 小说生成 (7-Agent 流水线)              │
│ video_generate     │ 视频生成 (TTS + FFmpeg)               │
│ video_review       │ 视频评审 (AI评审)                     │
│ publish_content    │ 内容发布到平台                         │
│ payment_reconcile  │ 每日对账批处理                         │
│ subscription_check │ 订阅到期检查/续费提醒                  │
│ disk_cleanup       │ 磁盘清理任务                          │
│ token_refresh      │ 平台 OAuth Token 刷新                 │
└───────────────────┴───────────────────────────────────────┘

并发限制：同一时刻最多 1 个任务在执行 (内存约束)
优先级：高套餐用户任务优先级更高
```

### 5.3 FastAPI BackgroundTasks (短任务)
```
对于执行时间 < 30s 的短任务，使用 FastAPI 内置 BackgroundTasks：

适用场景：
- 发送通知邮件
- 更新统计计数器
- 清理临时文件
- Webhook 回调确认

不适用场景 (应使用 task_queue)：
- 小说生成 (分钟级)
- 视频生成 (分钟级)
- AI 评审 (可能耗时较长)
- 对账处理 (批量操作)
```

---

## 6. 通信架构设计

### 6.1 模块间通信 (进程内)
```
通信方式：

1. 直接函数调用 (同步)
   场景：实时性要求高的操作
   示例：用户登录时检查订阅状态
   调用：await subscription_service.check_entitlement(user_id, action)

2. 进程内事件 (异步通知)
   场景：模块间解耦通知
   实现：blinker 信号库
   示例：
     payment_completed = Signal('payment_completed')
     payment_completed.send(order_id=order_id, user_id=user_id)

3. 任务队列 (异步执行)
   场景：耗时操作
   实现：INSERT INTO task_queue
   示例：提交小说生成任务

通信规则：
- 模块间通过 service 层公开函数调用，禁止直接操作其他模块的 ORM
- 共享数据通过 Pydantic schema 传递
- 跨模块事务：在调用方统一管理数据库 session
```

### 6.2 外部通信
```
1. REST API：HTTP/1.1 + JSON
   - 所有客户端 → 服务端通信
   - 统一响应格式：{code, message, data}

2. WebSocket：
   - 任务进度实时推送
   - 通过 FastAPI WebSocket endpoint
   - 路径：/ws/tasks/{task_id}

3. Webhook 接收：
   - 支付网关回调
   - 平台状态通知
   - 路径：/api/v1/webhooks/{provider}
```

### 6.3 API 路由设计 (单进程路径路由)
```
Nginx (:80/443) → FastAPI (:9000)

路由前缀分配：
┌──────────────────────────────┬──────────────────────┐
│  路径                         │ 说明                 │
├──────────────────────────────┼──────────────────────┤
│  /api/v1/users/**             │ 用户管理             │
│  /api/v1/payments/**          │ 支付管理             │
│  /api/v1/novels/**            │ 小说管理             │
│  /api/v1/videos/**            │ 视频管理             │
│  /api/v1/publish/**           │ 发布管理             │
│  /api/v1/subscriptions/**     │ 订阅管理             │
│  /api/v1/quality/**           │ 内容质量             │
│  /api/v1/reviews/**           │ 视频评审             │
│  /api/v1/webhooks/**          │ Webhook 接收         │
│  /api/v1/admin/**             │ 管理后台             │
├──────────────────────────────┼──────────────────────┤
│  /api/web/**                  │ Web端渠道适配         │
│  /api/wx/**                   │ 微信小程序渠道适配    │
│  /api/dy/**                   │ 抖音小程序渠道适配    │
│  /api/app/**                  │ App端渠道适配         │
│  /api/oc/**                   │ OpenClaw渠道适配      │
├──────────────────────────────┼──────────────────────┤
│  /health                      │ 健康检查             │
│  /metrics                     │ 基础指标             │
│  /ws/**                       │ WebSocket            │
└──────────────────────────────┴──────────────────────┘

限流策略 (Python 中间件实现，非 Redis)：
- 用户级：50 请求/分钟 (TTLCache 计数)
- IP级：200 请求/分钟
- 全局：1000 请求/分钟
```

---

## 7. 安全架构设计

### 7.1 认证授权体系
```
认证方式：

1. 用户认证：JWT (JSON Web Token)
   - 令牌类型：access_token + refresh_token
   - 有效期：access_token 1小时，refresh_token 7天
   - 签名算法：HS256
   - 存储：access_token 客户端持有，refresh_token 数据库校验

2. API认证：Bearer Token (OpenClaw)
   - 令牌格式：Bearer {api_key}
   - 权限控制：基于 API 密钥的权限范围
   - IP限制：可配置 IP 白名单

3. 渠道认证：各渠道专用流程
   - 微信：code2session → openid → 绑定/创建用户
   - 抖音：tt.login() → code → server验证 → openid
   - App：手机+短信 / 邮箱+密码 / 第三方 OAuth

授权模型：RBAC (基于角色的访问控制)
- 角色：普通用户、VIP用户、管理员
- 权限：细粒度权限控制
- 套餐关联：不同套餐对应不同权限集
```

### 7.2 数据安全
```
数据传输安全：
- 外部通信：HTTPS (Nginx + Let's Encrypt 免费证书)
- 内部通信：进程内调用，无网络传输

数据存储安全：
- 密码：bcrypt 哈希存储
- API密钥：加密存储 (Fernet 对称加密)
- OAuth Token：加密存储
- 支付信息：不存储卡号等敏感信息，仅存储交易ID

文件安全：
- 文件路径随机化 (UUID 命名)
- Nginx 禁止目录浏览
- 文件访问需认证 (通过 API 下载)
```

### 7.3 安全监控
```
安全事件监控 (写入 audit_logs 表)：

1. 异常登录检测
   - 频繁失败登录 (5次锁定30分钟)
   - 异常 IP 登录

2. API 滥用检测
   - 限流触发记录
   - 异常参数检测

3. 审计日志
   - 所有敏感操作写入 audit_logs 表
   - 30天自动清理 (磁盘约束)
   - 支持按用户/操作/时间查询
```

---

## 8. 套餐订阅子系统架构

### 8.1 订阅系统整体架构
```
┌──────────────────────────────────────────────────────────────────┐
│                        订阅子系统 (subscription 模块)             │
│                     (进程内模块，非独立服务)                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  套餐管理模块  │  │ 订阅生命周期  │  │  权益引擎    │           │
│  │              │  │  管理模块     │  │              │           │
│  │ - 套餐CRUD   │  │ - 创建/激活   │  │ - 权限检查   │           │
│  │ - 定价策略   │  │ - 续费/升降级  │  │ - 配额管理   │           │
│  │ - 功能配置   │  │ - 到期/取消   │  │ - 实时扣费   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│                     ┌──────▼───────┐                              │
│                     │  计费引擎    │                              │
│                     │              │                              │
│                     │ 实际成本计算  │                              │
│                     │ × 加价系数   │                              │
│                     │ = 用户扣费   │                              │
│                     └──────┬───────┘                              │
│                            │                                      │
│                     ┌──────▼───────┐                              │
│                     │  余额管理    │                              │
│                     │              │                              │
│                     │ 余额 = 充值  │                              │
│                     │ - 累计扣费   │                              │
│                     └──────────────┘                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

数据流：
  用户下单 → 支付模块收款 → 余额充值
       → 订阅模块创建/续费订阅 → 权益生效
            → 用户使用功能 → 权益引擎检查配额+余额
                 → 扣费(实际成本×1.1~1.2) → 更新余额
```

### 8.2 套餐层级定义
```
┌────────────┬────────────┬──────────┬────────────────────────┐
│  套餐名称   │ 字数范围    │ 月费(元) │ 包含权益                │
├────────────┼────────────┼──────────┼────────────────────────┤
│  微小说     │ ≤3,000字   │   29     │ 5次/月，基础TTS         │
│  短篇       │ ≤30,000字  │   99     │ 10次/月，高级TTS        │
│  中篇       │ ≤100,000字 │  299     │ 20次/月，全功能          │
│  长篇       │ ≤300,000字 │  599     │ 50次/月，优先队列        │
│  超长篇     │ ≤1,000,000 │  999     │ 不限次，专属资源         │
│  企业       │ 自定义      │ 面议     │ 不限次，SLA保障，API配额  │
└────────────┴────────────┴──────────┴────────────────────────┘
```

### 8.3 订阅生命周期
```
  create → active → renew/upgrade/downgrade → expire → cancel
  
  ┌────────┐   付款成功   ┌────────┐   到期前续费   ┌────────┐
  │ create │─────────────▶│ active │──────────────▶│ renew  │──┐
  └────────┘              └───┬────┘               └────────┘  │
                              │                         ▲      │
                              │ 升级/降级                │      │
                              ▼                         │      │
                         ┌─────────┐                    │      │
                         │ upgrade/│────────────────────┘      │
                         │downgrade│                            │
                         └─────────┘                            │
                              │                                 │
                    到期未续费  │         ┌────────┐             │
                              ▼         │ cancel │◀────用户取消──┘
                         ┌─────────┐    └────────┘
                         │ expired │
                         └─────────┘
```

### 8.4 权益引擎逻辑
```
check_entitlement(user_id, action) →
  1. 查询用户当前有效订阅 (进程内缓存优先，TTL=5min)
  2. 获取套餐对应权益列表
  3. 检查月度使用配额是否充足
  4. 检查余额是否足够本次扣费
  5. 返回 {allowed: bool, reason: str, cost: decimal}

计费模型：
  每次使用实际成本 = AI API调用费 + 存储费 + 计算费
  用户扣费金额 = 实际成本 × 加价系数(1.1~1.2)
  余额 = 累计充值 - 累计扣费
```

### 8.5 套餐升降级策略
```
升级策略：
  - 差价补缴：按剩余天数比例计算差额
  - 立即生效：升级后权益立即可用
  - 配额重置：升级后月度配额按新套餐重置

降级策略：
  - 当期有效：降级在当前周期结束后生效
  - 余额不退：已付差价不退还
  - 配额调整：下个周期按新套餐配额

企业套餐特殊处理：
  - 自定义配额
  - 专属SLA保障
  - 独立API配额
  - 优先技术支持
  - 账单结算（月结/季结）
```

### 8.6 技术选型
```
- 定时任务：APScheduler (到期检查、续费提醒、配额重置)
- 并发控制：PostgreSQL 行级锁 FOR UPDATE (替代 Redis 分布式锁)
- 事件通知：blinker 进程内信号 (替代 RabbitMQ)
- 缓存：TTLCache (用户权益缓存，TTL=5min，变更时主动失效)
```

---

## 9. OpenClaw 集成架构

### 9.1 整体集成架构
```
┌──────────────────────────────────────────────────────────────────┐
│                     OpenClaw 生态                                │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │ OpenClaw CLI │         │ OpenClaw IDE  │                      │
│  │              │         │   插件        │                      │
│  │ openclaw     │         │              │                      │
│  │ ai-novel ... │         │ 可视化面板    │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                               │
│         └────────────┬───────────┘                               │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │ OpenClaw      │                                   │
│              │ Plugin SDK    │                                   │
│              │               │                                   │
│              │ X-API-Key头   │                                   │
│              │ 请求签名      │                                   │
│              └───────┬───────┘                                   │
│                      │                                           │
└──────────────────────┼───────────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Nginx → FastAPI (:9000)                         │
│                                                                  │
│          /api/oc/* 路由 → OpenClaw 渠道适配层                     │
│          X-API-Key 验证 → api_keys 表校验                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 任务管理  │  │ 用户管理  │  │ 内容管理  │  │ 配置管理  │        │
│  │ Task API │  │ User API │  │Content   │  │Config    │        │
│  │          │  │          │  │  API     │  │  API     │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│           直接调用内部 service 层（进程内）                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 OpenClaw 认证体系
```
认证流程：
  1. 用户在后台生成 OpenClaw Plugin Token
  2. Plugin Token 绑定到用户账号 + 权限范围 (api_keys 表)
  3. CLI/插件通过 X-API-Key 头携带 Token
  4. FastAPI 中间件验证 Token 有效性
  5. 请求路由到 /api/oc/* 渠道适配层处理

Token生命周期：
  创建 → 激活 → 使用中 → 刷新/轮转 → 撤销
  
  - 默认有效期：90天
  - 支持手动撤销
  - 支持自动轮转（到期前7天提醒）
  - 最大同时有效Token数：5
```

### 9.3 OpenClaw 专用 API 契约
```
端点定义（通过渠道适配层 /api/oc/ 暴露）：

任务管理：
  POST /api/oc/tasks              -- 创建小说/视频任务
  GET  /api/oc/tasks/{id}         -- 查询任务状态
  GET  /api/oc/tasks/{id}/status  -- 精简状态查询
  POST /api/oc/tasks/{id}/cancel  -- 取消任务
  GET  /api/oc/tasks              -- 列出所有任务

用户管理：
  GET  /api/oc/user/profile       -- 当前用户信息
  GET  /api/oc/user/balance       -- 余额查询
  GET  /api/oc/user/usage         -- 使用统计

内容管理：
  GET  /api/oc/content/{id}       -- 获取内容（小说/视频）
  GET  /api/oc/content/{id}/download -- 下载内容

配置管理：
  GET  /api/oc/config/genres      -- 可用题材列表
  GET  /api/oc/config/styles      -- 可用风格列表
  GET  /api/oc/config/plans       -- 可用套餐列表
```

### 9.4 CLI 工作流
```
openclaw ai-novel create \
  --genre "玄幻" \
  --length "短篇" \
  --style "热血" \
  --title "龙皇觉醒" \
  --chapters 10

openclaw ai-novel status <task-id>
openclaw ai-novel cancel <task-id>
openclaw ai-novel list --status running
openclaw ai-novel download <task-id> --format epub

openclaw ai-video create \
  --source <novel-id> \
  --mode mixed \
  --voice "成熟男声"

openclaw ai-video status <task-id>
openclaw ai-video preview <task-id>
```

### 9.5 数据双向同步
```
同步策略：

OpenClaw → 后端：
  - CLI/插件发起操作 → /api/oc/* → 内部 service 处理
  - 直接调用，无需额外同步

后端 → OpenClaw：
  - 任务状态变更 → WebSocket /ws/tasks/{id} 推送
  - 长轮询备选 (CLI 不支持 WebSocket 时)

状态映射：
  后端状态              OpenClaw状态
  ──────────            ─────────────
  pending      ──────▶  queued
  processing   ──────▶  running
  completed    ──────▶  done
  failed       ──────▶  error
  cancelled    ──────▶  cancelled
```

---

## 10. 多端入口渠道适配层

### 10.1 设计理念 (替代独立 BFF 服务)
```
传统 BFF 模式需要每个渠道独立进程，在 1GB 内存约束下不可行。

替代方案：单进程内渠道适配层
  - 每个渠道一个 Python 模块 (channels/*.py)
  - 注册为独立的 APIRouter，路径前缀区分
  - 共享认证中间件、数据库连接、缓存
  - 渠道特定逻辑在适配层处理
  - 通用业务逻辑调用内部 service

内存节省：5个独立BFF进程 → 1个进程内5个路由模块
预估节省：~500MB+ 内存
```

### 10.2 各渠道适配详设
```
┌─────────────────────────────────────────────────────────────────┐
│                   渠道适配层 (单进程内路由)                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ /api/web/* — Web端适配                                   │    │
│  │ - 认证：邮箱+密码 / 手机+短信 / 第三方OAuth              │    │
│  │ - 支付路由：支付宝（首选）/ 微信支付                      │    │
│  │ - 特性：完整功能集，响应式布局数据                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ /api/wx/* — 微信小程序适配                                │    │
│  │ - 认证：wx.login() → code2session → openid               │    │
│  │         → 绑定已有账号 / 创建新用户 → session token       │    │
│  │ - 支付路由：微信支付（唯一）                               │    │
│  │ - 特性：精简数据，小程序格式适配                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ /api/dy/* — 抖音小程序适配                                │    │
│  │ - 认证：tt.login() → code → server验证 → openid          │    │
│  │         → 绑定/创建用户 → session token                   │    │
│  │ - 支付路由：抖音支付（唯一）                               │    │
│  │ - 特性：短视频场景优化，抖音内容格式                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ /api/app/* — App端适配                                    │    │
│  │ - 认证：手机+短信 / 邮箱+密码 / 微信OAuth / 苹果登录     │    │
│  │ - 支付路由：支付宝 / 微信支付 / Apple IAP(iOS)           │    │
│  │ - 特性：推送通知集成，设备绑定                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ /api/oc/* — OpenClaw适配                                  │    │
│  │ - 认证：X-API-Key (Plugin Token)                          │    │
│  │ - 支付路由：无直接支付（使用余额扣费）                     │    │
│  │ - 特性：面向开发者，最小化响应，批量操作支持               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.3 统一 SSO 架构
```
跨端统一登录（SSO）设计：

核心原则：一个用户，一个账号，多端登录

身份绑定模型：
  ┌──────────────────────────────┐
  │          users 表             │
  │  id, username, email, phone  │
  └──────────────┬───────────────┘
                 │ 1:N
                 ▼
  ┌──────────────────────────────┐
  │   user_auth_bindings 表       │
  │  user_id, provider, open_id  │
  │                              │
  │  示例：                       │
  │  (u1, wechat, wx_openid_xx) │
  │  (u1, douyin, dy_openid_xx) │
  │  (u1, phone,  13812345678)  │
  │  (u1, email,  foo@bar.com)  │
  └──────────────────────────────┘

登录统一流程：
  渠道端发起登录
       │
       ▼
  渠道适配层执行渠道特定认证 (code2session / OAuth / SMS)
       │
       ▼
  获得渠道标识 (openid / phone / email)
       │
       ▼
  查询 user_auth_bindings
       │
  ┌────┴────┐
  │ 已绑定?  │
  ├── 是 ───▶ 返回该用户的统一JWT
  │          │
  └── 否 ───▶ 引导绑定已有账号 或 创建新账号
              │
              ▼
         绑定后返回统一JWT

JWT Payload：
  {
    "sub": "user_uuid",
    "channel": "wechat|douyin|web|app|openclaw",
    "plan_tier": 3,
    "iat": ...,
    "exp": ...
  }
```

### 10.4 渠道支付路由
```
支付路由规则：

  ┌────────────┬──────────────────────────────────┐
  │  入口渠道   │  可用支付方式                      │
  ├────────────┼──────────────────────────────────┤
  │  Web       │  支付宝、微信支付                   │
  │  微信小程序  │  微信支付（强制）                   │
  │  抖音小程序  │  抖音支付（强制）                   │
  │  App(安卓)  │  支付宝、微信支付                   │
  │  App(iOS)  │  Apple IAP、支付宝、微信支付        │
  │  OpenClaw  │  余额扣费（不支持直接支付）          │
  └────────────┴──────────────────────────────────┘

路由逻辑：
  渠道适配层根据渠道类型自动选择可用支付方式列表
  → 前端展示可用支付方式
  → 用户选择 → 适配层调用 payment 模块对应接口
  → payment 模块路由到对应网关

技术实现：
  - 微信SDK：wechatpy
  - 抖音SDK：自行封装 (官方REST API)
  - 所有在同一进程内，无内网HTTP调用开销
```

---

## 11. 支付子系统增强设计

### 11.1 Webhook 幂等处理
```
幂等性保障机制 (使用 PostgreSQL 替代 Redis SETNX)：

  ┌──────────────────────────────────────────────────────────┐
  │  支付网关回调 POST /api/v1/webhooks/{provider}            │
  └──────────────────────┬───────────────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │  验签       │  验证请求来源真实性
                  │ (RSA/HMAC)  │  (支付宝RSA2, 微信HMAC-SHA256)
                  └──────┬──────┘
                         │ 验签通过
                  ┌──────▼──────┐
                  │  幂等检查    │  INSERT INTO webhook_idempotency
                  │  PG UPSERT  │  ON CONFLICT DO NOTHING
                  └──────┬──────┘  (transaction_id 为主键)
                    ┌────┴────┐
                    │ 已处理?  │  (INSERT 返回0行 = 已处理)
                    ├── 是 ───▶ 直接返回 200 OK
                    └── 否 ───┐
                              │
                  ┌───────────▼──────────┐
                  │  事务处理             │
                  │  BEGIN                │
                  │  1. 更新订单状态       │
                  │  2. 更新支付记录       │
                  │  3. 更新用户余额       │
                  │  4. 记录审计日志       │
                  │  COMMIT               │
                  └───────────┬──────────┘
                              │
                  ┌───────────▼──────────┐
                  │  发送进程内事件        │
                  │  payment_completed    │
                  │  (blinker 信号)       │
                  └───────────┬──────────┘
                              │
                       返回 200 OK
```

### 11.2 退款流程详设
```
退款完整流程：

  用户申请退款 ──▶ 创建退款工单(pending)
                        │
                 ┌──────▼──────┐
                 │  自动审核    │  金额≤阈值且无异常 → 自动通过
                 │  (可选)     │  否则 → 人工审核队列
                 └──────┬──────┘
                        │
                 ┌──────▼──────┐
                 │  管理员审核   │
                 │ approved /   │
                 │ rejected    │
                 └──────┬──────┘
                    ┌───┴───┐
                    │通过?   │
                    │       │
              ┌─────┴──┐  ┌─┴──────────┐
              │approved │  │ rejected   │
              └────┬───┘  │ 通知用户    │
                   │      └────────────┘
            ┌──────▼──────┐
            │ 调用支付网关  │
            │ 退款接口     │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │ 网关回调确认  │ (异步，可能延迟数小时)
            └──────┬──────┘
                   │
            ┌──────▼──────────────┐
            │ 扣减用户余额         │
            │ 更新退款状态(completed)│
            │ 生成退款记录          │
            └─────────────────────┘

风控规则：
- 单日退款金额上限
- 异常高频小额充值检测
- 同一IP多账号支付检测
- 支付金额与历史行为偏差检测
```

### 11.3 每日对账系统
```
对账批处理流程（每日凌晨2:00，APScheduler 调度）：

  ┌────────────────┐     ┌────────────────┐
  │ 拉取系统订单    │     │ 拉取网关账单    │
  │ (当日已完成)    │     │ (支付宝/微信/抖)│
  └───────┬────────┘     └───────┬────────┘
          │                      │
          └──────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   逐笔比对   │
              │  order_no ↔  │
              │ transaction  │
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │  匹配    │ │ 系统多   │ │ 网关多   │
    │ (正常)   │ │ (需核查) │ │ (需核查) │
    └─────────┘ └─────────┘ └─────────┘
                     │           │
                     ▼           ▼
              ┌──────────────────┐
              │ 生成对账报告      │
              │ 异常自动告警      │
              │ 写入 reconciliation_records │
              └──────────────────┘

技术实现：
  - 调度：APScheduler (进程内定时任务)
  - 网关对账文件下载：httpx 异步 HTTP
  - 比对算法：内存 Hash Join
  - 告警：日志 + 可选邮件通知
```

### 11.4 分账与收益分成
```
分账模型：

  总收入 ─┬── 平台运营费 (5~10%)
          ├── AI服务成本 (按实际消耗)
          ├── 存储/带宽成本 (按量)
          └── 净利润
               ├── 平台分成 (60~70%)
               └── 创作者分成 (30~40%)  [仅发布收益场景]

分账触发条件：
  - 用户充值：不触发分账
  - 内容发布产生收益：按周期结算
  - 企业客户：按合同约定

技术实现：
  - 支付宝/微信分账API
  - 自动结算周期：T+7 / 月结
```

### 11.5 发票生成
```
发票类型：
  - 增值税普通发票（个人/小规模）
  - 增值税专用发票（企业套餐）

生成流程：
  用户申请发票 → 验证订单/套餐信息 → 调用电子发票服务
  → 生成PDF → 存储到本地文件系统 (/opt/ai-novel-agent/data/invoices/)
  → 站内消息通知用户下载

集成方案：
  - 电子发票服务：航天信息/百望云 API
  - 存储：本地文件系统 (非 MinIO)
  - 通知：站内消息 (初期不做邮件/短信)
```

---

## 12. 内容质量与专家建议系统

### 12.1 系统架构
```
┌──────────────────────────────────────────────────────────────┐
│              内容质量与专家建议系统 (quality 模块)              │
│                                                              │
│  ┌──────────────┐                                           │
│  │  数据采集层   │                                           │
│  │              │                                           │
│  │ Web爬虫      │── 网文大咖博客/教程/访谈                   │
│  │ 人工录入      │── 编辑团队审核后入库                       │
│  │ 用户反馈      │── 使用后评价 → 建议质量迭代                │
│  └──────┬───────┘                                           │
│         │                                                    │
│  ┌──────▼───────┐                                           │
│  │  知识处理层   │                                           │
│  │              │                                           │
│  │ 结构化提取    │── 原始文本 → 结构化建议条目                │
│  │ 文本索引      │── pg_trgm GIN索引 (替代Pinecone向量化)    │
│  │ 标签分类      │── 自动分类到题材/篇幅/风格维度             │
│  │ 冲突检测      │── 两两比对 → 标记冲突对                    │
│  └──────┬───────┘                                           │
│         │                                                    │
│  ┌──────▼───────┐                                           │
│  │  匹配引擎层   │                                           │
│  │              │                                           │
│  │ 输入：genre × length × style                              │
│  │ 候选：pg_trgm相似度搜索 + 标签GIN过滤                     │
│  │ 过滤：冲突检测（排除矛盾对）                               │
│  │ 去重：历史使用记录校验（唯一组合）                          │
│  │ 输出：评分排序的建议集                                     │
│  └──────────────┘                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘

建议匹配 SQL 示例：
  SELECT id, content, similarity(search_text, '目标关键词') AS sim
  FROM expert_advices
  WHERE applicable_genres @> ARRAY['玄幻']
    AND applicable_lengths @> ARRAY['短篇']
    AND is_active = true
    AND similarity(search_text, '目标关键词') > 0.1
  ORDER BY sim DESC, quality_score DESC
  LIMIT 20;
```

### 12.2 冲突检测算法
```
冲突类型：
  1. 直接矛盾：建议A说"开头要慢节奏铺垫"，建议B说"第一段就要爆发冲突"
  2. 风格冲突：建议A推荐"幽默轻松"，建议B推荐"沉重压抑"
  3. 结构冲突：建议A推荐"单线叙事"，建议B推荐"多视角切换"
  4. 弱化冲突：建议A的效果被建议B削弱

检测流程：
  1. 预计算：建议入库时，与现有建议两两比对
  2. 人工审核：高置信度冲突自动标记，低置信度人工确认
  3. 运行时：匹配引擎检索候选后，查询 advice_conflicts 表过滤

冲突严重程度：
  - high：绝对不能同时使用
  - medium：不建议同时使用，但特殊场景可放行
  - low：轻微影响，可以容忍
```

### 12.3 冲突强度规则详设
```
各篇幅冲突强度要求：

微小说 (≤3,000字)：
  - 最低冲突等级：3级
  - 约束：300字内必须出现第一个冲突
  - 结构：单一强冲突，快速解决
  - 节奏：极快，无废笔
  - 示例："开门见冲突，结尾反转"

短篇 (≤30,000字)：
  - 最低冲突等级：3级
  - 约束：每章至少1个冲突点
  - 结构：主线冲突 + 1-2个次要冲突
  - 节奏：快，每1000字内推进一次
  - 示例："多线交织，层层递进"

中篇 (≤100,000字)：
  - 最低冲突等级：4级
  - 约束：复杂冲突网络
  - 结构：主线 + 2-3条副线，交叉影响
  - 节奏：中等，允许适度铺垫
  - 示例："主角内外冲突并行"

长篇 (≤300,000字)：
  - 最低冲突等级：5级
  - 约束：多层冲突架构
  - 结构：卷级冲突 + 章级冲突 + 场景冲突
  - 节奏：有起伏，波浪式推进
  - 示例："史诗级冲突递进"

超长篇 (≤1,000,000字)：
  - 最低冲突等级：6级
  - 约束：史诗级冲突体系
  - 结构：多卷大冲突 + 卷内中冲突 + 章节小冲突
  - 节奏：长线布局，伏笔回收
  - 示例："多势力博弈 + 角色成长弧线"
```

---

## 13. 视频评审与记忆点系统

### 13.1 评审流水线架构
```
┌─────────────────────────────────────────────────────────────────┐
│                  视频评审流水线 (review 模块)                      │
│               任务通过 task_queue 表异步调度                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │  Stage 1: 自动筛查 (100%覆盖)                     │           │
│  │                                                  │           │
│  │  检查项：                                         │           │
│  │  - 视频格式/编码是否合规                           │           │
│  │  - 分辨率是否达标 (≥720p)                         │           │
│  │  - 时长是否在范围内                                │           │
│  │  - 音频是否完整，无静音段                          │           │
│  │  - 字幕是否清晰可读                               │           │
│  │                                                  │           │
│  │  结果：pass → Stage 2 / fail → 退回重新生成       │           │
│  └───────────────────────┬──────────────────────────┘           │
│                          │ pass                                 │
│  ┌───────────────────────▼──────────────────────────┐           │
│  │  Stage 2: AI深度评审 (100%覆盖)                   │           │
│  │                                                  │           │
│  │  评审维度：                                       │           │
│  │  ┌────────────────┬────────┬─────────────┐       │           │
│  │  │ 维度           │ 权重   │ AI评审方式    │       │           │
│  │  ├────────────────┼────────┼─────────────┤       │           │
│  │  │ 开头吸引力      │ 30%   │ 前5秒帧分析   │       │           │
│  │  │ 内容完整性      │ 25%   │ 脚本一致性检查 │       │           │
│  │  │ 制作质量        │ 20%   │ 音画同步检测   │       │           │
│  │  │ 平台适配度      │ 15%   │ 平台规则匹配   │       │           │
│  │  │ 商业价值        │ 10%   │ 热度预测模型   │       │           │
│  │  └────────────────┴────────┴─────────────┘       │           │
│  │                                                  │           │
│  │  输出：综合评分 + 各维度分数 + 改进建议            │           │
│  │  合格线：≥6.0 / 优质线：≥8.0                     │           │
│  └───────────────────────┬──────────────────────────┘           │
│                          │ score ≥ 6.0                          │
│  ┌───────────────────────▼──────────────────────────┐           │
│  │  Stage 3: 人工抽检 (仅高级套餐，10~20%抽样)       │           │
│  │                                                  │           │
│  │  触发条件：                                       │           │
│  │  - 用户套餐 ≥ 长篇级                              │           │
│  │  - AI评分在 6.0~7.5 的边界区间                    │           │
│  │  - 随机抽样                                       │           │
│  │                                                  │           │
│  │  人工操作：                                       │           │
│  │  - 修正AI评分                                     │           │
│  │  - 补充改进建议                                   │           │
│  │  - 最终定级 (pass/fail/excellent)                 │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 13.2 5秒黄金开头评审
```
5秒黄金开头类型：
┌────────────┬────────────────────────────────────────┐
│  开头类型   │ 描述                                   │
├────────────┼────────────────────────────────────────┤
│  悬念型     │ 抛出疑问/悬念，勾起好奇心                │
│  情感型     │ 强烈情感冲击，引发共鸣                   │
│  冲突型     │ 直接展现冲突/矛盾，制造紧张感             │
│  视觉型     │ 震撼画面/特效，吸引眼球                  │
│  音频型     │ 独特音效/BGM/台词，听觉吸引              │
└────────────┴────────────────────────────────────────┘

开头类型识别与评分：

  视频前5秒 ──▶ 帧提取 + 音频提取 + 字幕提取
                    │
              ┌─────▼─────┐
              │ 类型识别    │
              │            │
              │ 悬念型：画面暗示未知、旁白设问
              │ 情感型：强烈配乐+情感画面
              │ 冲突型：紧张场面/对抗/争执
              │ 视觉型：震撼特效/美景/奇观
              │ 音频型：独特音效/抓耳BGM/金句
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ 吸引力评分  │
              │            │
              │ 评估指标：
              │ - 信息密度（5秒内传递了多少信息）
              │ - 情感冲击度
              │ - 悬念/好奇心触发度
              │ - 视听协调度
              │ - 与目标平台风格匹配度
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ 生成改进    │
              │ 建议       │
              └───────────┘
```

### 13.3 记忆点识别与管理
```
记忆点类型与识别方法：

  ┌────────────────┬─────────────────────────────────────────┐
  │ 记忆点类型      │ 识别方法                                │
  ├────────────────┼─────────────────────────────────────────┤
  │ 标志性画面      │ 关键帧提取 + 视觉显著性分析              │
  │ (iconic_frame) │ 色彩/构图/内容独特度评分                  │
  │                │                                         │
  │ 经典台词        │ 字幕提取 + 语义分析                      │
  │ (classic_line) │ 简洁度/节奏感/传播潜力评分                │
  │                │                                         │
  │ 独特音效        │ 音频频谱分析                             │
  │ (unique_sound) │ 与BGM库比对，识别定制化音效               │
  │                │                                         │
  │ 情感高潮        │ 多模态情感分析                           │
  │ (emotion_peak) │ 画面+音频+文字情感强度曲线峰值            │
  │                │                                         │
  │ 视觉符号        │ 目标检测 + 出现频率分析                   │
  │ (visual_symbol)│ 识别反复出现的视觉元素                    │
  └────────────────┴─────────────────────────────────────────┘

记忆点强度评分 (1-10)：
  - 独特性 (30%)：在同类视频中的稀缺程度
  - 情感共鸣 (30%)：引发的情感强度
  - 传播潜力 (20%)：被观众记住和分享的可能性
  - 品牌关联 (20%)：与内容品牌/IP的关联度

应用场景：
  - 自动生成视频封面（选用最佳标志性画面）
  - 自动剪辑预告片（串联高分记忆点）
  - 内容营销素材提取
```

---

## 14. 多平台发布增强架构

### 14.1 平台适配器详设
```
适配器模式架构 (进程内实现，非独立服务)：

  ┌────────────────────────────────────────────────────────────┐
  │                  PublishOrchestrator                       │
  │               (publish 模块内的调度器)                      │
  │                                                            │
  │  职责：                                                    │
  │  - 接收发布请求                                            │
  │  - 执行合规预检                                            │
  │  - 路由到目标平台适配器                                     │
  │  - 管理发布状态机                                          │
  │  - 聚合多平台发布结果                                       │
  └──────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         ▼               ▼               ▼              ▼
  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ DouyinAdpt │  │ BiliAdpt   │  │ XHSAdpt    │  │ WXVideoAdpt│
  ├────────────┤  ├────────────┤  ├────────────┤  ├────────────┤
  │ format()   │  │ format()   │  │ format()   │  │ format()   │
  │ upload()   │  │ upload()   │  │ upload()   │  │ upload()   │
  │ publish()  │  │ publish()  │  │ publish()  │  │ publish()  │
  │ status()   │  │ status()   │  │ status()   │  │ status()   │
  │ analytics()│  │ analytics()│  │ analytics()│  │ analytics()│
  │ compliance │  │ compliance │  │ compliance │  │ compliance │
  │  _check()  │  │  _check()  │  │  _check()  │  │  _check()  │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘

同时支持小说平台适配器：
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ FanqieAdpt │  │ QidianAdpt │  │ JinjiangAdpt│
  ├────────────┤  ├────────────┤  ├────────────┤
  │ format()   │  │ format()   │  │ format()   │
  │ submit()   │  │ submit()   │  │ submit()   │
  │ status()   │  │ status()   │  │ status()   │
  └────────────┘  └────────────┘  └────────────┘

每个适配器负责：
- 平台特定的内容格式转换
- OAuth2 Token管理（含自动刷新）
- 平台API差异屏蔽
- 平台特定合规规则检查
- 发布状态轮询与回调

发布状态链路：
  pending → compliance_check → uploading → processing → live → stats_collecting
```

### 14.2 OAuth2 账号绑定管理
```
Token管理流程：

  用户首次绑定：
    前端跳转平台授权页 → 用户授权 → 回调携带code
    → 后端用code换取 access_token + refresh_token
    → 加密存储到 platform_accounts 表
    → 记录 token_expires_at

  Token自动刷新 (APScheduler 定时任务)：
    检查即将过期的Token (到期前24h)
    → 调用平台refresh接口获取新Token
    → 更新数据库
    → 刷新失败 → 记录日志，标记为 expired

  Token状态：
    active → refreshing → active (正常)
    active → refreshing → expired → 需重新授权
    active → revoked → 需重新授权
```

### 14.3 智能排期引擎
```
排期策略：

  ┌──────────────────────────────────────────────────┐
  │              智能排期引擎                          │
  │           (publish 模块内)                        │
  │                                                  │
  │  输入：                                          │
  │  - 目标平台列表                                   │
  │  - 内容类型（小说/视频）                           │
  │  - 用户偏好（可选）                               │
  │                                                  │
  │  决策因素：                                       │
  │  1. 平台流量高峰时段                              │
  │  2. 目标受众活跃时间                              │
  │  3. 同类内容竞争密度                              │
  │  4. 历史发布效果数据                              │
  │  5. 用户设定的偏好时间                            │
  │                                                  │
  │  输出：                                          │
  │  - 每个平台的最优发布时间                          │
  │  - 置信度评分                                    │
  └──────────────────────────────────────────────────┘

默认最优时段：
  ┌────────────┬────────────────────────────────┐
  │  平台       │  推荐发布时段                   │
  ├────────────┼────────────────────────────────┤
  │  抖音       │  12:00-13:00, 18:00-22:00     │
  │  B站        │  20:00-23:00                  │
  │  小红书      │  11:00-13:00, 19:00-21:00     │
  │  微信视频号   │  7:00-9:00, 12:00-13:00       │
  │  快手       │  11:00-13:00, 17:00-19:00     │
  │  番茄小说    │  20:00-22:00 (周五最佳)        │
  └────────────┴────────────────────────────────┘

平台支持：
  - 小说平台：番茄、起点、晋江
  - 视频平台：抖音、小红书、B站、微信视频号、快手
```

### 14.4 内容合规预检
```
合规检查流程：

  发布前 → 通用合规检查 → 平台特定规则检查 → 结果

  通用合规检查：
  - 敏感词过滤（政治/色情/暴力/违法）
  - 版权检测（AI生成内容声明）
  - 广告法合规（禁用"最"、"第一"等绝对化用语）

  平台特定规则：
  ┌────────────┬────────────────────────────────────┐
  │  平台       │  特定规则                           │
  ├────────────┼────────────────────────────────────┤
  │  抖音       │  视频时长限制，封面要求，标签规范     │
  │  B站        │  分区规范，标签要求，转载声明         │
  │  小红书      │  图文比例，话题标签格式              │
  │  微信视频号   │  内容分类标注，原创声明              │
  │  番茄小说    │  字数要求，章节结构规范              │
  └────────────┴────────────────────────────────────┘

检查结果：
  - pass：可以发布
  - warning：有风险项，建议修改后发布
  - block：存在违规，禁止发布
```

---

## 15. 部署架构设计

### 15.1 服务器资源规划
```
服务器：104.244.90.202 (裸金属 Ubuntu 24.04 LTS)
实际配置：2核 CPU / 1GB RAM / 20GB 磁盘

端口分配：
┌──────────┬──────────────────────────────┐
│  端口     │  服务                         │
├──────────┼──────────────────────────────┤
│  80/443  │  Nginx (反向代理 + SSL终止)    │
│  9000    │  ai-novel-agent (FastAPI主服务) │
│  9090    │  media-agent (已有服务)         │
│  5432    │  PostgreSQL 16                │
└──────────┴──────────────────────────────┘

仅 3 个业务端口 + 1 个数据库端口
❌ 不再有：9001-9005 BFF / 6379 Redis / 5672 RabbitMQ / 9090 Prometheus / 3000 Grafana / 3100 Loki
```

### 15.2 systemd 服务配置
```
# /etc/systemd/system/ai-novel-agent.service
[Unit]
Description=AI Novel Agent FastAPI Service
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-novel-agent
ExecStart=/opt/ai-novel-agent/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9000 \
    --workers 1 \
    --limit-max-requests 10000 \
    --timeout-keep-alive 5
Restart=always
RestartSec=5
MemoryMax=250M
MemoryHigh=200M

Environment="DATABASE_URL=postgresql+asyncpg://postgres:xxx@localhost/ai_novel"
Environment="SECRET_KEY=xxx"

[Install]
WantedBy=multi-user.target
```

```
# 可选：独立 Celery Worker (仅当 asyncio 内部队列不够用时)
# /etc/systemd/system/ai-novel-worker.service
[Unit]
Description=AI Novel Agent Background Worker
After=postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ai-novel-agent
ExecStart=/opt/ai-novel-agent/venv/bin/python -m app.background.task_worker
Restart=always
RestartSec=10
MemoryMax=180M
MemoryHigh=150M

[Install]
WantedBy=multi-user.target
```

### 15.3 Nginx 配置
```nginx
# /etc/nginx/sites-available/ai-novel-agent
server {
    listen 80;
    server_name your-domain.com;

    # SSL 配置 (Let's Encrypt)
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 50M;

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查 & 指标
    location ~ ^/(health|metrics)$ {
        proxy_pass http://127.0.0.1:9000;
    }

    # 静态文件 (直接由 Nginx 提供)
    location /static/ {
        alias /opt/ai-novel-agent/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 禁止目录浏览
    autoindex off;
}
```

### 15.4 部署架构图
```
┌─────────────────────────────────────────────────────────┐
│               Nginx (:80/443)                            │
│               SSL终止 + 反向代理 + 静态文件               │
└──────────┬────────────────────────────────────┬─────────┘
           │                                    │
           ▼                                    ▼
    ┌──────────────┐                   ┌──────────────┐
    │ ai-novel     │                   │ media-agent  │
    │ -agent       │                   │              │
    │ FastAPI      │                   │ uvicorn +    │
    │ :9000        │                   │ celery       │
    │              │                   │ :9090        │
    │ 所有业务模块  │                   │              │
    │ + 渠道适配   │                   │ (已有服务)    │
    │ + 后台任务   │                   │              │
    └──────┬───────┘                   └──────┬───────┘
           │                                  │
           └──────────────┬───────────────────┘
                          │
                   ┌──────▼──────┐
                   │ PostgreSQL  │
                   │   :5432     │
                   │             │
                   │ 两个数据库:  │
                   │ ai_novel    │
                   │ media_agent │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 本地文件系统  │
                   │             │
                   │ /opt/ai-novel-agent/data/  │
                   │ /opt/media-agent/data/     │
                   └─────────────┘
```

---

## 16. 磁盘管理 (关键 — 仅 ~1GB 可用!)

### 16.1 磁盘使用预算
```
总可用空间：~1GB (20GB 磁盘，95% 已用)

预算分配：
┌──────────────────────┬───────────┬─────────────────────────┐
│  用途                 │ 预算      │ 管理策略                 │
├──────────────────────┼───────────┼─────────────────────────┤
│  PostgreSQL WAL      │ ≤256MB    │ max_wal_size=256MB       │
│  小说/视频输出文件     │ ≤300MB    │ FIFO清理，超限删最旧     │
│  临时文件             │ ≤100MB    │ 任务完成后立即清理        │
│  应用日志             │ ≤50MB     │ logrotate 压缩轮转       │
│  发票PDF等            │ ≤50MB     │ 30天后清理               │
│  系统预留             │ ≥200MB    │ 告警阈值                 │
└──────────────────────┴───────────┴─────────────────────────┘
```

### 16.2 自动清理策略
```
1. 任务输出文件清理 (cron: 每6小时)
   - 已完成任务的视频/音频文件：保留 7 天后删除
   - 失败任务的输出：立即删除
   - 临时文件 (/data/temp/)：保留 24 小时后删除

2. 数据库清理 (APScheduler: 每周日凌晨3:00)
   - audit_logs：保留 30 天
   - task_queue (completed/failed)：保留 14 天
   - task_dead_letters：保留 30 天
   - webhook_idempotency：保留 7 天
   - VACUUM FULL：每周执行一次

3. 日志轮转 (logrotate: 每日)
   /opt/ai-novel-agent/logs/*.log {
     daily
     rotate 3
     compress
     delaycompress
     maxsize 10M
     missingok
     notifempty
   }

4. PostgreSQL WAL 管理
   - max_wal_size = 256MB
   - checkpoint_completion_target = 0.9
   - 定期 pg_archivecleanup

5. 紧急清理脚本 (当可用空间 < 200MB 时触发)
   #!/bin/bash
   # scripts/emergency_cleanup.sh
   # 删除所有7天前的输出文件
   find /opt/ai-novel-agent/data/ -mtime +7 -type f -delete
   # 清理日志
   truncate -s 0 /opt/ai-novel-agent/logs/*.log
   # 数据库紧急清理
   psql -c "DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '7 days';"
   psql -c "DELETE FROM task_queue WHERE status IN ('completed','failed') AND created_at < NOW() - INTERVAL '3 days';"
   psql -c "VACUUM FULL;"
```

### 16.3 磁盘监控
```
/health 端点返回磁盘使用情况：

{
  "status": "healthy",
  "disk": {
    "total_gb": 20,
    "used_gb": 19.0,
    "free_gb": 1.0,
    "usage_percent": 95,
    "alert": "warning"  // >90% warning, >95% critical
  }
}

告警级别：
- normal: < 85%
- warning: 85% ~ 95%
- critical: > 95% → 触发紧急清理
- emergency: > 98% → 暂停新任务提交
```

---

## 17. 内存管理

### 17.1 内存预算分配
```
总 RAM：1GB (可用 ~476MB，其余为 OS + 已运行服务)

内存预算：
┌─────────────────────────┬──────────┬──────────────────┐
│  组件                    │ 预算     │ 限制方式          │
├─────────────────────────┼──────────┼──────────────────┤
│  PostgreSQL             │ ~128MB   │ shared_buffers    │
│  ai-novel-agent (主进程) │ ≤200MB   │ systemd MemoryMax │
│  media-agent (已有)      │ ~100MB   │ systemd MemoryMax │
│  Nginx                  │ ~10MB    │ worker数限制      │
│  OS + 系统服务           │ ~100MB   │ -                │
│  Swap 缓冲              │ 4.5GB    │ 已配置            │
├─────────────────────────┼──────────┼──────────────────┤
│  总计                    │ ~538MB   │ 超出部分使用Swap  │
└─────────────────────────┴──────────┴──────────────────┘

关键约束：
- uvicorn workers=1 (单worker，避免多进程内存翻倍)
- 进程内缓存总条目 < 1000 (~1MB)
- SQLAlchemy 连接池：pool_size=3, max_overflow=2
- 大文件处理使用流式读写，不全量加载到内存
```

### 17.2 内存优化策略
```
1. 惰性加载模块
   - 不在启动时导入所有模块
   - 使用 Python importlib 按需加载重模块
   - 例：FFmpeg 处理模块仅在视频任务时加载

2. 流式处理
   - 大文件上传/下载：使用 StreamingResponse
   - 小说内容：分章节流式生成，不缓存全文
   - 视频：流式写入磁盘，不在内存中拼接

3. 连接池限制
   - SQLAlchemy: pool_size=3, max_overflow=2, pool_recycle=300
   - httpx (外部API调用): limits=httpx.Limits(max_connections=5)

4. GC 调优
   - 定期手动触发 gc.collect() (在长任务完成后)
```

---

## 18. 性能优化设计

### 18.1 数据库优化
```
索引优化：
1. 所有 WHERE 条件字段建立索引
2. 复合索引覆盖常用查询模式
3. pg_trgm GIN 索引用于文本搜索
4. 定期 ANALYZE 更新统计信息

查询优化：
1. 游标分页 (keyset pagination) 代替 OFFSET
2. 避免 N+1 查询：使用 SQLAlchemy selectinload/joinedload
3. 批量操作：使用 executemany / COPY
4. 限制结果集：max 20 条/页

连接优化：
- pool_size=3 (基础连接数)
- max_overflow=2 (峰值时可扩到5)
- pool_pre_ping=True (健康检查)
- pool_recycle=300 (5分钟回收)
```

### 18.2 API 响应优化
```
1. 响应压缩：GzipMiddleware (减少带宽)
2. 分页限制：max 20 items/page
3. 字段过滤：支持 ?fields=id,title,status 精简响应
4. 条件请求：ETag / Last-Modified 头
5. 异步IO：全链路 async/await (FastAPI + asyncpg)
```

### 18.3 后台任务优化
```
任务节流：
- 同一时刻最多 1 个长任务在执行
- 任务间设置 5s 冷却间隔 (避免 CPU 100%)
- 高优先级任务可抢占队列位置

AI API 调用优化：
- 批量请求合并
- 结果缓存 (相同参数的生成结果复用)
- 降级策略：高峰期使用低成本模型
- 超时控制：单次 API 调用 max 60s
```

---

## 19. 监控设计 (轻量级)

### 19.1 健康检查端点
```
GET /health

返回：
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2026-04-01T12:00:00Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 5},
    "disk": {"status": "warning", "free_gb": 1.0, "usage_pct": 95},
    "memory": {"status": "ok", "rss_mb": 180, "limit_mb": 250},
    "task_queue": {"pending": 3, "running": 1, "failed_24h": 0}
  }
}

健康状态判定：
- healthy: 所有检查通过
- degraded: 非关键项告警 (如磁盘 >90%)
- unhealthy: 关键项失败 (如数据库连接失败)
```

### 19.2 基础指标端点
```
GET /metrics

返回 (JSON 格式，非 Prometheus 格式)：
{
  "uptime_seconds": 86400,
  "requests_total": 12345,
  "requests_per_minute": 5.2,
  "active_connections": 3,
  "tasks": {
    "total_submitted": 500,
    "completed": 480,
    "failed": 5,
    "pending": 15
  },
  "users": {
    "total": 100,
    "active_today": 15
  },
  "ai_costs": {
    "today_yuan": 12.50,
    "month_yuan": 350.00
  }
}
```

### 19.3 日志体系
```
日志架构 (无 Loki)：

1. 应用日志
   - Python logging → /opt/ai-novel-agent/logs/app.log
   - logrotate: 每日轮转，保留3天，压缩
   - 格式：JSON lines (便于后续分析)

2. 访问日志
   - Nginx access.log → /var/log/nginx/ai-novel-access.log
   - logrotate: 每日轮转，保留3天

3. 系统日志
   - systemd journal (自动管理)
   - journalctl -u ai-novel-agent --since today

4. 审计日志
   - 关键操作 → PostgreSQL audit_logs 表
   - 30天保留

日志级别策略：
  - 生产环境：WARNING 及以上写入文件
  - 调试时：临时调低到 DEBUG
```

### 19.4 告警机制
```
告警方式 (简单 Python 脚本)：

1. 磁盘告警：磁盘 > 95% 时写入日志 + 触发清理
2. 内存告警：RSS > 200MB 时记录
3. 错误告警：连续3个任务失败时记录
4. 数据库告警：连接池耗尽时记录

后续可扩展：
- 邮件通知
- 企业微信/钉钉 Webhook
- 但初期仅日志 + /health 轮询即可
```

---

## 20. 容灾与备份设计

### 20.1 备份策略
```
数据库备份：
- pg_dump 全量备份：每日凌晨4:00
- 备份文件压缩：gzip 压缩
- 保留策略：本地保留3天 (磁盘约束)
- 异地备份：rsync 到开发机 (可选，推荐)

文件备份：
- 小说文本：存在数据库中，随数据库一起备份
- 视频文件：不备份 (可重新生成，磁盘不够)
- 配置文件：Git 版本控制

备份脚本：
  #!/bin/bash
  # scripts/backup.sh (cron: 0 4 * * *)
  BACKUP_DIR=/opt/ai-novel-agent/backups
  pg_dump ai_novel | gzip > $BACKUP_DIR/ai_novel_$(date +%Y%m%d).sql.gz
  find $BACKUP_DIR -name "*.sql.gz" -mtime +3 -delete
```

### 20.2 恢复策略
```
恢复目标：
- RPO (恢复点目标)：24小时 (每日备份)
- RTO (恢复时间目标)：1小时

恢复步骤：
1. 停止 ai-novel-agent 服务
2. 恢复数据库：gunzip + psql 导入
3. 检查文件系统完整性
4. 重启服务
5. 验证 /health 端点
```

---

## 21. 扩容策略

### 21.1 渐进式扩容路线
```
阶段0: 当前 (2核/1GB/20GB)
  - 单 FastAPI 进程
  - PostgreSQL 任务队列
  - 进程内缓存
  - 一切从简

阶段1: 升级服务器 (4核/4GB/50GB) — 收入覆盖成本后
  - uvicorn workers=2
  - 可引入 Redis (会话缓存 + 限流)
  - 更大的 PostgreSQL 缓冲区
  - 更宽裕的磁盘空间
  - 可考虑 Celery + Redis broker

阶段2: 双服务器 (应用 + 数据库分离) — 用户量增长后
  - 应用服务器：4核/4GB
  - 数据库服务器：4核/8GB
  - 可引入 RabbitMQ
  - 可引入 Docker 部署

阶段3: 微服务化 — 团队和流量都增长后
  - 按模块拆分为独立服务
  - Kubernetes 编排
  - 完整监控栈

关键原则：
  只有当收入能覆盖基础设施成本时才升级
  模块化单体的代码结构支持按需拆分
  不要过早优化/过度架构
```

---

## 22. 架构评审检查清单

### 22.1 资源约束检查 (最重要!)
```
✅ 资源约束适配：
- [x] 总内存占用 < 800MB (留200MB给OS)
- [x] 单进程架构，无多服务进程开销
- [x] 无 Redis/RabbitMQ/Pinecone 等额外服务
- [x] 无 Docker 容器化开销
- [x] 磁盘清理策略完善，有紧急清理机制
- [x] PostgreSQL 参数针对 1GB RAM 优化
- [x] 连接池严格限制 (pool_size=3)
- [x] 单 worker 运行 (workers=1)
```

### 22.2 架构原则检查
```
✅ 可维护性检查：
- [x] 模块化设计 (8个内部模块，清晰边界)
- [x] 清晰接口定义 (模块间通过 service 层通信)
- [x] 单进程部署 (一个 systemd service)
- [x] 渐进扩容路线明确

✅ 安全性检查：
- [x] JWT 认证授权
- [x] HTTPS (Nginx + Let's Encrypt)
- [x] 审计日志 (PostgreSQL 表)
- [x] 限流 (进程内中间件)
- [x] Webhook 验签 + 幂等
```

### 22.3 商业化子系统检查
```
✅ 订阅系统检查：
- [x] 套餐层级定义完整（6级）
- [x] 订阅生命周期状态机完备
- [x] 权益引擎实时检查机制
- [x] 计费模型（成本×加价系数）
- [x] 升降级策略明确
- [x] 技术实现适配：TTLCache替代Redis, PG行锁替代Redis分布式锁

✅ 支付系统检查：
- [x] 三方支付网关集成（支付宝/微信/抖音）
- [x] Webhook幂等处理 (PG UPSERT替代Redis SETNX)
- [x] 退款全流程
- [x] 每日对账机制 (APScheduler替代Celery Beat)
- [x] 风控规则
- [x] 发票生成 (本地文件系统替代MinIO)

✅ 多端入口检查：
- [x] 渠道适配层覆盖5个渠道 (替代独立BFF)
- [x] 统一SSO跨端登录
- [x] 渠道支付路由正确
- [x] 各端认证流程完整

✅ OpenClaw集成检查：
- [x] Plugin Token认证
- [x] 专用API契约完备
- [x] CLI工作流覆盖
- [x] 状态双向同步 (WebSocket)

✅ 内容质量检查：
- [x] 专家建议匹配引擎 (pg_trgm替代Pinecone)
- [x] 冲突检测机制
- [x] 唯一性保障
- [x] 冲突强度规则

✅ 视频评审检查：
- [x] 三级评审流水线 (task_queue调度)
- [x] 5秒黄金开头评审
- [x] 记忆点识别
- [x] 评审维度与权重

✅ 多平台发布检查：
- [x] 平台适配器模式 (进程内实现)
- [x] OAuth2 Token管理 (APScheduler刷新)
- [x] 智能排期引擎
- [x] 内容合规预检
```

### 22.4 风险评估
```
🟡 中风险：
- [x] AI 成本控制：已设计成本监控和降级策略
- [x] 磁盘空间：已设计多层清理策略，但仍需密切监控
- [x] 内存压力：重度依赖 Swap，可能影响性能
- [x] 单点故障：单服务器无冗余，备份策略弥补

🟢 低风险：
- [x] 开发复杂度：模块化单体比微服务简单得多
- [x] 部署维护：systemd 管理，运维简单
- [x] 技术栈：FastAPI + PostgreSQL，成熟稳定
- [x] 扩展性：代码结构支持未来拆分

已缓解的原高风险：
- 多服务进程内存爆炸 → 单进程架构
- Docker 磁盘/内存开销 → 裸金属 systemd
- Redis/RabbitMQ 资源争夺 → PostgreSQL 统一承担
```

---

## 23. 建议实施方案

### 23.1 实施阶段
```
阶段1：基础架构搭建（1周）
  - 创建项目骨架 (模块化目录结构)
  - 配置 PostgreSQL (优化参数, 创建表)
  - 启用 pg_trgm 扩展
  - 配置 Nginx 反向代理
  - 部署 systemd 服务
  - 实现 /health + /metrics 端点

阶段2：核心模块开发（4周）
  - auth 模块：JWT认证 + SSO绑定表
  - payment 模块：订单 + Webhook + 退款
  - novel 模块：7-Agent 流水线 + task_queue 集成
  - video 模块：TTS + FFmpeg
  - subscription 模块：套餐 + 权益引擎 + 计费

阶段3：商业化功能（3周）
  - 渠道适配层 (Web + 微信 + OpenClaw 优先)
  - 统一 SSO 实现
  - quality 模块 (专家建议 + pg_trgm 匹配)
  - review 模块 (评审流水线)

阶段4：高级功能（3周）
  - publish 模块 (适配器 + 智能排期)
  - 完善 OpenClaw CLI 集成
  - 抖音 + App 渠道适配
  - 对账 + 发票

阶段5：测试和上线（1周）
  - 端到端测试
  - 磁盘清理策略验证
  - 内存压力测试
  - 生产部署上线
```

### 23.2 立即行动
```
1. 确认架构设计
   - 评审本文档
   - 确认资源约束适配方案

2. 环境准备
   - PostgreSQL 参数调优
   - 启用 pg_trgm 扩展
   - 配置 logrotate
   - 创建磁盘清理 cron

3. 开始阶段1开发
   - 创建项目骨架
   - 实现核心基础设施层 (database, cache, task_queue, file_manager)
```

---

## 24. 设计结论

### 24.1 设计优势
```
1. 资源极致利用：在 2核/1GB/20GB 约束下可稳定运行
2. 零额外基础设施：不需要 Redis/RabbitMQ/Docker/Prometheus
3. 运维简单：单 systemd 服务，一条命令管理
4. 部署快速：venv + systemd，无容器构建时间
5. 模块化设计：代码清晰解耦，未来可拆分
6. 商业化完备：订阅/支付/发票/对账/SSO 全覆盖
7. 渠道统一：单进程路径路由替代5个BFF进程
8. 渐进扩展：明确的扩容路线，按需升级
```

### 24.2 设计取舍
```
1. 单 worker 限制并发：高峰期可能排队
   → 缓解：task_queue + WebSocket 进度推送
2. 无高可用冗余：单点故障风险
   → 缓解：每日备份 + 快速恢复流程
3. 磁盘空间紧张：需要激进的清理策略
   → 缓解：多层自动清理 + 紧急清理机制
4. 重度依赖 Swap：性能可能受影响
   → 缓解：控制内存占用，优化热路径
5. 进程内缓存不共享：重启后缓存丢失
   → 缓解：TTL 短，miss 时从 DB 加载，影响可忽略
```

---

**设计状态**: ✅ 架构设计完成（资源约束适配版）
**设计结论**: 模块化单体架构在 2核/1GB/20GB 服务器约束下可行，所有商业化功能通过轻量级技术替代方案实现
**下一步**: 开始阶段1基础架构搭建，创建项目骨架和核心基础设施层
