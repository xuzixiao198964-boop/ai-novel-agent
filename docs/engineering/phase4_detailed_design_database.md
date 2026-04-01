# AI Novel Media Agent 数据库详细设计

## 设计信息
- **设计阶段**: 详细设计 - 数据库设计
- **设计日期**: 2026-04-01
- **设计模型**: Claude 3.5 Sonnet (via Cursor)
- **工程方法**: OpenClaw软件工程化全流程
- **设计状态**: 🗄️ 已更新（单机优化版）

## 1. 数据库设计原则

### 1.1 设计目标
```
1. 数据一致性：保证数据准确性和完整性
2. 资源节约：适配 1GB 内存 / 20GB 磁盘的 VPS 环境
3. 最少依赖：仅使用 PostgreSQL + 本地文件系统，无 Redis/MinIO/Docker
4. 安全性：数据安全存储和访问
5. 可维护性：清晰的表结构和关系，自动化运维脚本
```

### 1.2 技术选型
```
主数据库：PostgreSQL 15
- 理由：功能丰富，ACID支持完善，JSONB支持好
- 同时承担任务队列（task_queue表）、幂等键、缓存等职责

进程内缓存：Python cachetools
- 理由：零额外依赖，内存占用可控，适合单机部署
- 使用 TTLCache / LRUCache 替代 Redis 缓存

文件存储：本地文件系统
- 理由：单机部署，无需对象存储服务，减少运维复杂度
- 路径：/opt/ai-novel-agent/data/

部署方式：systemd 直接管理
- 理由：1GB内存VPS，无法承受Docker额外开销
```

## 2. 数据库架构设计

### 2.1 单库架构策略
```
部署环境：1GB 内存 VPS，单机 PostgreSQL
架构原则：单库单实例，不分库不分表

表分区策略（仅用于日志类大表）：
1. 按月分区：
   - audit_logs：审计日志按月分区
   - system_monitoring：监控数据按月分区
   - novel_generation_logs：小说生成日志按月分区
   - video_generation_logs：视频生成日志按月分区
2. 超过3个月的分区数据归档后删除，控制磁盘占用

注意事项：
- 当前规模不需要读写分离和分库分表
- 所有表使用同一个 PostgreSQL 数据库
- 通过索引优化和进程内缓存保证查询性能
```

### 2.2 数据库连接池配置（SQLAlchemy）
```
PostgreSQL max_connections = 20（1GB内存约束）

SQLAlchemy 连接池配置：
- pool_size = 3          # 常驻连接数
- max_overflow = 2       # 允许临时额外连接
- pool_timeout = 30      # 等待连接超时（秒）
- pool_recycle = 1800    # 连接回收时间（秒）
- pool_pre_ping = True   # 使用前检测连接有效性

连接预算分配（总计 ≤ 20）：
- FastAPI 主进程：3 + 2 overflow = 最多5连接
- Celery Worker：2连接（轻量任务处理）
- 管理/维护：1连接（pg_dump、手动查询等）
- 预留缓冲：~12连接（应对突发）
- 总计：约 6~8 活跃连接，远低于 max_connections 上限
```

```python
# SQLAlchemy 引擎配置示例
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+asyncpg://user:pass@localhost/ai_novel_agent",
    pool_size=3,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

## 3. 核心数据表设计

### 3.1 用户模块表

#### 用户表 (users)
```sql
CREATE TABLE users (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    
    -- 安全信息
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(32),
    
    -- 账户信息
    balance DECIMAL(10, 2) DEFAULT 0.00 CHECK (balance >= 0),
    currency VARCHAR(3) DEFAULT 'CNY',
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'vip', 'admin')),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'deleted')),
    
    -- 个人信息
    avatar_url VARCHAR(500),
    nickname VARCHAR(100),
    real_name VARCHAR(100),
    id_card VARCHAR(18),
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other', 'unknown')),
    birthday DATE,
    country VARCHAR(50),
    province VARCHAR(50),
    city VARCHAR(50),
    
    -- 统计信息
    total_recharge DECIMAL(10, 2) DEFAULT 0.00,
    total_consumption DECIMAL(10, 2) DEFAULT 0.00,
    novel_count INT DEFAULT 0,
    video_count INT DEFAULT 0,
    publish_count INT DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_active_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT chk_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_phone CHECK (phone ~ '^\+?[1-9]\d{1,14}$')
);

-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_last_active_at ON users(last_active_at);
CREATE INDEX idx_users_metadata ON users USING gin(metadata);
```

#### API密钥表 (api_keys)
```sql
CREATE TABLE api_keys (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    name VARCHAR(100) NOT NULL,
    
    -- 权限配置
    permissions JSONB DEFAULT '[]',
    ip_restrictions CIDR[],
    referer_restrictions VARCHAR(255)[],
    
    -- 使用限制
    usage_limits JSONB DEFAULT '{
        "daily_calls": 1000,
        "monthly_calls": 30000,
        "daily_cost": 100.00,
        "monthly_cost": 3000.00
    }',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'expired')),
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_reason VARCHAR(255),
    
    -- 使用统计
    total_calls BIGINT DEFAULT 0,
    daily_calls INT DEFAULT 0,
    monthly_calls INT DEFAULT 0,
    total_cost DECIMAL(10, 2) DEFAULT 0.00,
    daily_cost DECIMAL(10, 2) DEFAULT 0.00,
    monthly_cost DECIMAL(10, 2) DEFAULT 0.00,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT chk_expires_at CHECK (expires_at IS NULL OR expires_at > created_at)
);

-- 创建索引
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_status ON api_keys(status);
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at);
CREATE INDEX idx_api_keys_created_at ON api_keys(created_at);
CREATE INDEX idx_api_keys_permissions ON api_keys USING gin(permissions);
```

#### 用户会话表 (user_sessions)
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB DEFAULT '{}',
    ip_address INET,
    user_agent VARCHAR(500),
    
    -- 令牌信息
    access_token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    refresh_token_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT chk_token_expiry CHECK (
        access_token_expires_at > created_at AND 
        refresh_token_expires_at > access_token_expires_at
    )
);

-- 创建索引
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions(access_token_expires_at);
CREATE INDEX idx_user_sessions_refresh_expires ON user_sessions(refresh_token_expires_at);
CREATE INDEX idx_user_sessions_created_at ON user_sessions(created_at);
```

### 3.2 支付模块表

#### 订单表 (orders)
```sql
CREATE TABLE orders (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    
    -- 订单信息
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('recharge', 'consumption', 'refund')),
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'CNY',
    description VARCHAR(500),
    
    -- 支付信息
    payment_method VARCHAR(20) CHECK (payment_method IN ('alipay', 'wechat', 'douyin', 'balance')),
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (
        payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded', 'cancelled')
    ),
    transaction_id VARCHAR(100),
    payment_gateway_response JSONB,
    
    -- 退款信息
    refund_amount DECIMAL(10, 2) DEFAULT 0.00 CHECK (refund_amount >= 0 AND refund_amount <= amount),
    refund_reason VARCHAR(255),
    refunded_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT chk_refund CHECK (
        (order_type = 'refund' AND refund_amount = amount) OR 
        (order_type != 'refund' AND refund_amount <= amount)
    )
);

-- 创建索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_orders_payment_status ON orders(payment_status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_order_type ON orders(order_type);
CREATE INDEX idx_orders_metadata ON orders USING gin(metadata);
```

#### 支付记录表 (payment_records)
```sql
CREATE TABLE payment_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 支付信息
    payment_method VARCHAR(20) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'CNY',
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    gateway_transaction_id VARCHAR(100),
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'refunded')
    ),
    failure_reason VARCHAR(255),
    
    -- 网关响应
    gateway_request JSONB,
    gateway_response JSONB,
    gateway_notification JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 索引
    CONSTRAINT fk_payment_records_order FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- 创建索引
CREATE INDEX idx_payment_records_order_id ON payment_records(order_id);
CREATE INDEX idx_payment_records_user_id ON payment_records(user_id);
CREATE INDEX idx_payment_records_transaction_id ON payment_records(transaction_id);
CREATE INDEX idx_payment_records_status ON payment_records(status);
CREATE INDEX idx_payment_records_created_at ON payment_records(created_at);
```

#### 消费记录表 (consumption_records)
```sql
CREATE TABLE consumption_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 消费信息
    consumption_type VARCHAR(50) NOT NULL CHECK (
        consumption_type IN (
            'novel_generation', 'video_generation', 'publish_task',
            'api_call', 'storage_usage', 'premium_feature'
        )
    ),
    description VARCHAR(500) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'CNY',
    
    -- 余额变化
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    
    -- 关联资源
    resource_type VARCHAR(50),  -- novel, video, publish, etc.
    resource_id UUID,
    
    -- 详情
    details JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT chk_balance CHECK (balance_after = balance_before - amount),
    CONSTRAINT fk_consumption_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建索引
CREATE INDEX idx_consumption_records_user_id ON consumption_records(user_id);
CREATE INDEX idx_consumption_records_type ON consumption_records(consumption_type);
CREATE INDEX idx_consumption_records_created_at ON consumption_records(created_at);
CREATE INDEX idx_consumption_records_resource ON consumption_records(resource_type, resource_id);
CREATE INDEX idx_consumption_records_details ON consumption_records USING gin(details);
```

### 3.3 小说模块表

#### 小说表 (novels)
```sql
CREATE TABLE novels (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    
    -- 基本信息
    genre VARCHAR(50) NOT NULL CHECK (genre IN (
        'fantasy', 'romance', 'sci_fi', 'urban', 'historical',
        'mystery', 'horror', 'adventure', 'comedy', 'drama'
    )),
    language VARCHAR(10) DEFAULT 'zh-CN',
    
    -- 规模信息
    target_chapters INT NOT NULL CHECK (target_chapters > 0),
    target_words_per_chapter INT NOT NULL CHECK (target_words_per_chapter >= 1000),
    estimated_total_words INT GENERATED ALWAYS AS (target_chapters * target_words_per_chapter) STORED,
    
    -- 生成配置
    conflict_level VARCHAR(10) DEFAULT 'medium' CHECK (conflict_level IN ('low', 'medium', 'high')),
    expert_advice BOOLEAN DEFAULT FALSE,
    style_reference_novel_id UUID REFERENCES novels(id),
    custom_prompt TEXT,
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')
    ),
    progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    current_agent VARCHAR(50),
    current_chapter INT DEFAULT 0,
    
    -- 成本信息
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2) DEFAULT 0.00,
    
    -- 质量评分
    quality_score DECIMAL(3, 1) CHECK (quality_score >= 0 AND quality_score <= 5),
    audit_result JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT chk_progress CHECK (
        (status = 'pending' AND progress = 0) OR
        (status = 'running' AND progress > 0 AND progress < 100) OR
        (status IN ('completed', 'failed', 'cancelled') AND progress = 100)
    )
);

-- 创建索引
CREATE INDEX idx_novels_user_id ON novels(user_id);
CREATE INDEX idx_novels_status ON novels(status);
CREATE INDEX idx_novels_genre ON novels(genre);
CREATE INDEX idx_novels_created_at ON novels(created_at);
CREATE INDEX idx_novels_progress ON novels(progress);
CREATE INDEX idx_novels_metadata ON novels USING gin(metadata);
```

#### 章节表 (chapters)
```sql
CREATE TABLE chapters (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL CHECK (chapter_number > 0),
    
    -- 内容信息
    title VARCHAR(255),
    content TEXT NOT NULL,
    summary TEXT,
    word_count INT NOT NULL CHECK (word_count > 0),
    
    -- 生成信息
    generation_config JSONB DEFAULT '{}',
    ai_model_used VARCHAR(100),
    ai_prompt TEXT,
    ai_response JSONB,
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'generating', 'completed', 'failed', 'revising')
    ),
    revision_count INT DEFAULT 0,
    
    -- 质量信息
    readability_score DECIMAL(3, 1) CHECK (readability_score >= 0 AND readability_score <= 5),
    coherence_score DECIMAL(3, 1) CHECK (coherence_score >= 0 AND coherence_score <= 5),
    creativity_score DECIMAL(3, 1) CHECK (creativity_score >= 0 AND creativity_score <= 5),
    audit_comments TEXT[],
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generated_at TIMESTAMP WITH TIME ZONE,
    audited_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 约束
    UNIQUE(novel_id, chapter_number),
    CONSTRAINT chk_word_count CHECK (word_count >= 500)
);

-- 创建索引
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_chapters_chapter_number ON chapters(chapter_number);
CREATE INDEX idx_chapters_status ON chapters(status);
CREATE INDEX idx_chapters_created_at ON chapters(created_at);
CREATE INDEX idx_chapters_metadata ON chapters USING gin(metadata);
```

#### 小说生成日志表 (novel_generation_logs)
```sql
CREATE TABLE novel_generation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES chapters(id) ON DELETE SET NULL,
    
    -- 日志信息
    agent_name VARCHAR(50) NOT NULL CHECK (agent_name IN (
        'TrendAgent', 'StyleAgent', 'PlannerAgent', 'WriterAgent',
        'PolishAgent', 'AuditorAgent', 'ReviserAgent'
    )),
    log_level VARCHAR(10) DEFAULT 'info' CHECK (log_level IN ('debug', 'info', 'warning', 'error')),
    message TEXT NOT NULL,
    
    -- 执行信息
    execution_time_ms INT CHECK (execution_time_ms >= 0),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    error_stack TEXT,
    
    -- 输入输出
    input_data JSONB,
    output_data JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT fk_novel_generation_logs_novel FOREIGN KEY (novel_id) REFERENCES novels(id)
);

-- 创建索引
CREATE INDEX idx_novel_generation_logs_novel_id ON novel_generation_logs(novel_id);
CREATE INDEX idx_novel_generation_logs_chapter_id ON novel_generation_logs(chapter_id);
CREATE INDEX idx_novel_generation_logs_agent_name ON novel_generation_logs(agent_name);
CREATE INDEX idx_novel_generation_logs_created_at ON novel_generation_logs(created_at);
CREATE INDEX idx_novel_generation_logs_log_level ON novel_generation_logs(log_level);
```

### 3.4 视频模块表

#### 视频表 (videos)
```sql
CREATE TABLE videos (
    -- 主键和标识
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    
    -- 源信息
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('novel', 'external', 'news')),
    source_id UUID,  -- 小说ID或外部内容ID
    source_content TEXT,
    
    -- 生成配置
    generation_mode VARCHAR(20) NOT NULL CHECK (generation_mode IN (
        'voice_only', 'subtitle_only', 'animation', 'mixed', 'news_to_video'
    )),
    duration_seconds INT NOT NULL CHECK (duration_seconds > 0 AND duration_seconds <= 3600),
    
    -- 风格配置
    voice_style VARCHAR(50) DEFAULT 'standard' CHECK (voice_style IN (
        'standard', 'warm', 'professional', 'cheerful', 'serious', 'storytelling'
    )),
    subtitle_style VARCHAR(50) DEFAULT 'modern' CHECK (subtitle_style IN (
        'classic', 'modern', 'minimalist', 'elegant', 'bold'
    )),
    animation_style VARCHAR(50) DEFAULT 'cartoon' CHECK (animation_style IN (
        'cartoon', 'realistic', 'anime', 'whiteboard', 'infographic'
    )),
    
    -- 记忆点配置
    memory_points_enabled BOOLEAN DEFAULT TRUE,
    memory_points_config JSONB DEFAULT '{
        "opening_hook": true,
        "emotional_peak": true,
        "knowledge_highlight": true,
        "call_to_action": true
    }',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'rendering', 'completed', 'failed', 'cancelled')
    ),
    progress INT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    current_step VARCHAR(50),
    
    -- 文件信息
    file_path VARCHAR(500),
    file_size BIGINT CHECK (file_size >= 0),
    file_format VARCHAR(10) DEFAULT 'mp4',
    thumbnail_path VARCHAR(500),
    preview_path VARCHAR(500),
    
    -- 成本信息
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2) DEFAULT 0.00,
    
    -- 质量信息
    video_quality_score DECIMAL(3, 1) CHECK (video_quality_score >= 0 AND video_quality_score <= 5),
    audio_quality_score DECIMAL(3, 1) CHECK (audio_quality_score >= 0 AND audio_quality_score <= 5),
    content_quality_score DECIMAL(3, 1) CHECK (content_quality_score >= 0 AND content_quality_score <= 5),
    audit_result JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT chk_source CHECK (
        (source_type = 'novel' AND source_id IS NOT NULL) OR
        (source_type IN ('external', 'news') AND source_content IS NOT NULL)
    )
);

-- 创建索引
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_source ON videos(source_type, source_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_generation_mode ON videos(generation_mode);
CREATE INDEX idx_videos_created_at ON videos(created_at);
CREATE INDEX idx_videos_metadata ON videos USING gin(metadata);
```

#### 视频片段表 (video_segments)
```sql
CREATE TABLE video_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    segment_index INT NOT NULL CHECK (segment_index >= 0),
    
    -- 内容信息
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('voice', 'subtitle', 'animation', 'mixed')),
    content_text TEXT,
    content_duration_seconds INT NOT NULL CHECK (content_duration_seconds > 0),
    
    -- 文件信息
    audio_file_path VARCHAR(500),
    subtitle_file_path VARCHAR(500),
    animation_file_path VARCHAR(500),
    combined_file_path VARCHAR(500),
    
    -- 时间信息
    start_time_seconds INT NOT NULL CHECK (start_time_seconds >= 0),
    end_time_seconds INT NOT NULL CHECK (end_time_seconds > start_time_seconds),
    
    -- 质量信息
    segment_quality_score DECIMAL(3, 1) CHECK (segment_quality_score >= 0 AND segment_quality_score <= 5),
    is_memory_point BOOLEAN DEFAULT FALSE,
    memory_point_type VARCHAR(50) CHECK (memory_point_type IN (
        'opening_hook', 'emotional_peak', 'knowledge_highlight', 'call_to_action'
    )),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(video_id, segment_index),
    CONSTRAINT fk_video_segments_video FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- 创建索引
CREATE INDEX idx_video_segments_video_id ON video_segments(video_id);
CREATE INDEX idx_video_segments_segment_index ON video_segments(segment_index);
CREATE INDEX idx_video_segments_content_type ON video_segments(content_type);
CREATE INDEX idx_video_segments_is_memory_point ON video_segments(is_memory_point);
```

#### 视频生成日志表 (video_generation_logs)
```sql
CREATE TABLE video_generation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    segment_id UUID REFERENCES video_segments(id) ON DELETE SET NULL,
    
    -- 日志信息
    process_name VARCHAR(50) NOT NULL CHECK (process_name IN (
        'tts_generation', 'subtitle_generation', 'animation_generation',
        'video_rendering', 'quality_check', 'memory_point_detection'
    )),
    log_level VARCHAR(10) DEFAULT 'info' CHECK (log_level IN ('debug', 'info', 'warning', 'error')),
    message TEXT NOT NULL,
    
    -- 执行信息
    execution_time_ms INT CHECK (execution_time_ms >= 0),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    error_stack TEXT,
    
    -- 资源使用
    cpu_usage_percent DECIMAL(5, 2) CHECK (cpu_usage_percent >= 0 AND cpu_usage_percent <= 100),
    memory_usage_mb INT CHECK (memory_usage_mb >= 0),
    gpu_usage_percent DECIMAL(5, 2) CHECK (gpu_usage_percent >= 0 AND gpu_usage_percent <= 100),
    
    -- 输入输出
    input_data JSONB,
    output_data JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT fk_video_generation_logs_video FOREIGN KEY (video_id) REFERENCES videos(id)
);

-- 创建索引
CREATE INDEX idx_video_generation_logs_video_id ON video_generation_logs(video_id);
CREATE INDEX idx_video_generation_logs_segment_id ON video_generation_logs(segment_id);
CREATE INDEX idx_video_generation_logs_process_name ON video_generation_logs(process_name);
CREATE INDEX idx_video_generation_logs_created_at ON video_generation_logs(created_at);
```

### 3.5 发布模块表

#### 平台账号表 (platform_accounts)
```sql
CREATE TABLE platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 平台信息
    platform VARCHAR(50) NOT NULL CHECK (platform IN (
        'douyin', 'xiaohongshu', 'bilibili', 'wechat_video', 'kuaishou',
        'fanqie', 'qidian', 'jinjiang', 'self_hosted'
    )),
    platform_account_id VARCHAR(100) NOT NULL,
    platform_account_name VARCHAR(255),
    
    -- 认证信息
    auth_type VARCHAR(20) DEFAULT 'oauth2' CHECK (auth_type IN ('oauth2', 'api_key', 'cookie')),
    access_token TEXT,
    refresh_token TEXT,
    api_key TEXT,
    api_secret TEXT,
    
    -- 令牌信息
    token_expires_at TIMESTAMP WITH TIME ZONE,
    token_refreshed_at TIMESTAMP WITH TIME ZONE,
    
    -- 权限信息
    permissions JSONB DEFAULT '[]',
    scopes JSONB DEFAULT '[]',
    
    -- 状态信息
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'expired', 'revoked')),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_status VARCHAR(20) DEFAULT 'pending' CHECK (sync_status IN ('pending', 'syncing', 'success', 'failed')),
    
    -- 统计信息
    total_published INT DEFAULT 0,
    last_published_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 约束
    UNIQUE(user_id, platform, platform_account_id),
    CONSTRAINT fk_platform_accounts_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建索引
CREATE INDEX idx_platform_accounts_user_id ON platform_accounts(user_id);
CREATE INDEX idx_platform_accounts_platform ON platform_accounts(platform);
CREATE INDEX idx_platform_accounts_status ON platform_accounts(status);
CREATE INDEX idx_platform_accounts_created_at ON platform_accounts(created_at);
```

#### 发布记录表 (publish_records)
```sql
CREATE TABLE publish_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 内容信息
    content_type VARCHAR(20) NOT NULL CHECK (content_type IN ('novel', 'video')),
    content_id UUID NOT NULL,
    content_title VARCHAR(255),
    
    -- 发布配置
    publish_strategy VARCHAR(20) DEFAULT 'immediate' CHECK (publish_strategy IN ('immediate', 'scheduled', 'draft')),
    scheduled_publish_time TIMESTAMP WITH TIME ZONE,
    privacy_setting VARCHAR(20) DEFAULT 'public' CHECK (privacy_setting IN ('public', 'followers', 'private')),
    
    -- 平台信息
    target_platforms JSONB NOT NULL DEFAULT '[]',  -- 平台列表
    platform_configs JSONB DEFAULT '{}',  -- 各平台特定配置
    
    -- 发布内容
    publish_title VARCHAR(255),
    publish_description TEXT,
    hashtags VARCHAR(255)[],
    cover_image_url VARCHAR(500),
    
    -- 状态信息
    overall_status VARCHAR(20) DEFAULT 'pending' CHECK (overall_status IN (
        'pending', 'processing', 'partial_success', 'completed', 'failed', 'cancelled'
    )),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 索引
    CONSTRAINT fk_publish_records_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建索引
CREATE INDEX idx_publish_records_user_id ON publish_records(user_id);
CREATE INDEX idx_publish_records_content ON publish_records(content_type, content_id);
CREATE INDEX idx_publish_records_overall_status ON publish_records(overall_status);
CREATE INDEX idx_publish_records_created_at ON publish_records(created_at);
CREATE INDEX idx_publish_records_scheduled_time ON publish_records(scheduled_publish_time);
```

#### 平台发布详情表 (platform_publish_details)
```sql
CREATE TABLE platform_publish_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publish_record_id UUID NOT NULL REFERENCES publish_records(id) ON DELETE CASCADE,
    
    -- 平台信息
    platform VARCHAR(50) NOT NULL,
    platform_account_id UUID NOT NULL REFERENCES platform_accounts(id) ON DELETE CASCADE,
    
    -- 发布状态
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'uploading', 'processing', 'published', 'failed', 'cancelled'
    )),
    platform_content_id VARCHAR(100),  -- 平台返回的内容ID
    platform_content_url VARCHAR(500),  -- 平台内容URL
    
    -- 发布结果
    publish_result JSONB,  -- 平台返回的完整结果
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- 审核信息
    review_status VARCHAR(20) CHECK (review_status IN ('pending', 'approved', 'rejected', 'under_review')),
    review_comments TEXT,
    
    -- 统计信息
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    share_count INT DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    -- 约束
    UNIQUE(publish_record_id, platform, platform_account_id),
    CONSTRAINT fk_platform_publish_details_publish FOREIGN KEY (publish_record_id) REFERENCES publish_records(id),
    CONSTRAINT fk_platform_publish_details_account FOREIGN KEY (platform_account_id) REFERENCES platform_accounts(id)
);

-- 创建索引
CREATE INDEX idx_platform_publish_details_publish_id ON platform_publish_details(publish_record_id);
CREATE INDEX idx_platform_publish_details_platform ON platform_publish_details(platform);
CREATE INDEX idx_platform_publish_details_status ON platform_publish_details(status);
CREATE INDEX idx_platform_publish_details_created_at ON platform_publish_details(created_at);
```

### 3.6 系统监控表

#### 系统监控表 (system_monitoring)
```sql
CREATE TABLE system_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 监控信息
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(20) NOT NULL CHECK (metric_type IN ('gauge', 'counter', 'histogram', 'summary')),
    metric_value DECIMAL(15, 4) NOT NULL,
    unit VARCHAR(20),
    
    -- 来源信息
    service_name VARCHAR(50) NOT NULL CHECK (service_name IN (
        'novel_service', 'video_service', 'payment_service',
        'publish_service', 'user_service', 'gateway'
    )),
    host VARCHAR(100),
    instance_id VARCHAR(100),
    
    -- 标签
    tags JSONB DEFAULT '{}',
    
    -- 阈值告警
    threshold_warning DECIMAL(15, 4),
    threshold_critical DECIMAL(15, 4),
    alert_status VARCHAR(20) DEFAULT 'normal' CHECK (alert_status IN ('normal', 'warning', 'critical', 'resolved')),
    
    -- 时间戳
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT chk_threshold CHECK (
        threshold_warning IS NULL OR threshold_critical IS NULL OR
        threshold_critical >= threshold_warning
    )
);

-- 创建索引
CREATE INDEX idx_system_monitoring_metric_name ON system_monitoring(metric_name);
CREATE INDEX idx_system_monitoring_service ON system_monitoring(service_name);
CREATE INDEX idx_system_monitoring_recorded_at ON system_monitoring(recorded_at);
CREATE INDEX idx_system_monitoring_alert_status ON system_monitoring(alert_status);
CREATE INDEX idx_system_monitoring_tags ON system_monitoring USING gin(tags);

-- 按时间分区（建议按月分区）
-- CREATE TABLE system_monitoring_2026_04 PARTITION OF system_monitoring
--     FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| metric_name | VARCHAR(100) | 监控指标名称，如 `cpu_usage`、`api_latency_p99` |
| metric_type | VARCHAR(20) | 指标类型：gauge(瞬时值)/counter(累计值)/histogram/summary |
| metric_value | DECIMAL(15,4) | 指标数值 |
| unit | VARCHAR(20) | 单位：percent、ms、bytes 等 |
| service_name | VARCHAR(50) | 来源服务名 |
| host | VARCHAR(100) | 主机名或 IP |
| tags | JSONB | 灵活标签，如 `{"endpoint": "/api/novels", "method": "POST"}` |
| alert_status | VARCHAR(20) | 告警状态 |
| recorded_at | TIMESTAMP | 记录时间 |

---

### 3.7 套餐订阅模块表

#### 套餐计划表 (subscription_plans)
```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    name VARCHAR(50) UNIQUE NOT NULL CHECK (name IN (
        '微小说', '短篇', '中篇', '长篇', '超长篇', '企业'
    )),
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- 价格信息
    price_monthly DECIMAL(10, 2) NOT NULL CHECK (price_monthly >= 0),
    price_yearly DECIMAL(10, 2) CHECK (price_yearly >= 0),
    original_price DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'CNY',
    
    -- 配额信息
    novel_word_quota INT NOT NULL CHECK (novel_word_quota >= 0),
    video_minute_quota INT NOT NULL CHECK (video_minute_quota >= 0),
    publish_count_quota INT NOT NULL CHECK (publish_count_quota >= 0),
    
    -- 功能配置
    features_json JSONB NOT NULL DEFAULT '{
        "ai_models": ["deepseek"],
        "voice_styles": ["standard"],
        "export_formats": ["txt"],
        "priority_queue": false,
        "dedicated_support": false,
        "api_access": false,
        "custom_domain": false
    }',
    
    -- 优先级
    priority_level INT NOT NULL DEFAULT 0 CHECK (priority_level >= 0 AND priority_level <= 10),
    sort_order INT DEFAULT 0,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_subscription_plans_name ON subscription_plans(name);
CREATE INDEX idx_subscription_plans_is_active ON subscription_plans(is_active);
CREATE INDEX idx_subscription_plans_priority ON subscription_plans(priority_level);
CREATE INDEX idx_subscription_plans_sort ON subscription_plans(sort_order);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(50) | 套餐内部名：微小说/短篇/中篇/长篇/超长篇/企业 |
| display_name | VARCHAR(100) | 前端展示名称 |
| price_monthly | DECIMAL(10,2) | 月付价格（元） |
| price_yearly | DECIMAL(10,2) | 年付价格（元），通常有折扣 |
| novel_word_quota | INT | 每月小说字数配额 |
| video_minute_quota | INT | 每月视频分钟配额 |
| publish_count_quota | INT | 每月发布次数配额 |
| features_json | JSONB | 功能权限配置 |
| priority_level | INT | 任务队列优先级，0最低10最高 |
| is_active | BOOLEAN | 是否上架 |

**示例数据：**
```sql
INSERT INTO subscription_plans (name, display_name, price_monthly, price_yearly, novel_word_quota, video_minute_quota, publish_count_quota, features_json, priority_level) VALUES
('微小说', '微小说套餐', 9.90, 99.00, 50000, 10, 5, '{"ai_models":["deepseek"],"voice_styles":["standard"],"export_formats":["txt"],"priority_queue":false,"dedicated_support":false,"api_access":false}', 1),
('短篇', '短篇套餐', 29.90, 299.00, 200000, 30, 15, '{"ai_models":["deepseek","gpt4"],"voice_styles":["standard","warm"],"export_formats":["txt","epub"],"priority_queue":false,"dedicated_support":false,"api_access":false}', 2),
('中篇', '中篇套餐', 69.90, 699.00, 500000, 60, 30, '{"ai_models":["deepseek","gpt4","claude"],"voice_styles":["standard","warm","professional"],"export_formats":["txt","epub","pdf"],"priority_queue":true,"dedicated_support":false,"api_access":false}', 4),
('长篇', '长篇套餐', 149.90, 1499.00, 2000000, 120, 60, '{"ai_models":["deepseek","gpt4","claude"],"voice_styles":["standard","warm","professional","storytelling"],"export_formats":["txt","epub","pdf"],"priority_queue":true,"dedicated_support":true,"api_access":false}', 6),
('超长篇', '超长篇套餐', 299.90, 2999.00, 5000000, 300, 120, '{"ai_models":["deepseek","gpt4","claude"],"voice_styles":["standard","warm","professional","storytelling","cheerful"],"export_formats":["txt","epub","pdf","docx"],"priority_queue":true,"dedicated_support":true,"api_access":true}', 8),
('企业', '企业定制套餐', 999.00, 9999.00, 20000000, 1000, 500, '{"ai_models":["deepseek","gpt4","claude"],"voice_styles":["all"],"export_formats":["all"],"priority_queue":true,"dedicated_support":true,"api_access":true,"custom_domain":true}', 10);
```

#### 用户订阅表 (user_subscriptions)
```sql
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    
    -- 订阅状态
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (
        status IN ('active', 'expired', 'cancelled', 'suspended')
    ),
    
    -- 时间周期
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    
    -- 续费配置
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(20) CHECK (payment_method IN ('alipay', 'wechat', 'douyin', 'balance')),
    billing_cycle VARCHAR(10) DEFAULT 'monthly' CHECK (billing_cycle IN ('monthly', 'yearly')),
    
    -- 关联订单
    order_id UUID REFERENCES orders(id),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT chk_subscription_dates CHECK (expires_at > started_at),
    CONSTRAINT chk_cancel_date CHECK (cancelled_at IS NULL OR cancelled_at >= started_at)
);

-- 创建索引
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_plan_id ON user_subscriptions(plan_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_expires_at ON user_subscriptions(expires_at);
CREATE INDEX idx_user_subscriptions_auto_renew ON user_subscriptions(auto_renew) WHERE auto_renew = TRUE;
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 关联用户（外键 → users.id） |
| plan_id | UUID | 关联套餐计划（外键 → subscription_plans.id） |
| status | VARCHAR(20) | 订阅状态：active(生效)/expired(过期)/cancelled(取消)/suspended(暂停) |
| started_at | TIMESTAMP | 生效时间 |
| expires_at | TIMESTAMP | 到期时间 |
| auto_renew | BOOLEAN | 是否自动续费 |
| payment_method | VARCHAR(20) | 续费支付方式 |
| billing_cycle | VARCHAR(10) | 计费周期：月/年 |
| order_id | UUID | 关联付款订单 |

#### 权益额度表 (entitlements)
```sql
CREATE TABLE entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    
    -- 资源类型
    resource_type VARCHAR(30) NOT NULL CHECK (
        resource_type IN ('novel_words', 'video_minutes', 'publish_count')
    ),
    
    -- 配额信息
    total_quota INT NOT NULL CHECK (total_quota >= 0),
    used_quota INT NOT NULL DEFAULT 0 CHECK (used_quota >= 0),
    
    -- 重置周期
    reset_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_reset_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(subscription_id, resource_type),
    CONSTRAINT chk_quota CHECK (used_quota <= total_quota)
);

-- 创建索引
CREATE INDEX idx_entitlements_subscription_id ON entitlements(subscription_id);
CREATE INDEX idx_entitlements_resource_type ON entitlements(resource_type);
CREATE INDEX idx_entitlements_reset_at ON entitlements(reset_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| subscription_id | UUID | 关联订阅（外键 → user_subscriptions.id） |
| resource_type | VARCHAR(30) | 资源类型：novel_words(小说字数)/video_minutes(视频分钟)/publish_count(发布次数) |
| total_quota | INT | 总配额 |
| used_quota | INT | 已使用配额 |
| reset_at | TIMESTAMP | 下次重置时间（通常为下个计费周期开始） |

#### 发票表 (invoices)
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    
    -- 发票信息
    invoice_no VARCHAR(50) UNIQUE NOT NULL,
    invoice_type VARCHAR(20) NOT NULL CHECK (
        invoice_type IN ('personal', 'company', 'vat_special')
    ),
    
    -- 金额
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    tax_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (tax_amount >= 0),
    total_amount DECIMAL(10, 2) GENERATED ALWAYS AS (amount + tax_amount) STORED,
    currency VARCHAR(3) DEFAULT 'CNY',
    
    -- 开票信息
    buyer_name VARCHAR(255) NOT NULL,
    buyer_tax_id VARCHAR(50),
    buyer_address VARCHAR(500),
    buyer_phone VARCHAR(20),
    buyer_bank VARCHAR(255),
    buyer_bank_account VARCHAR(50),
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'issued', 'cancelled', 'void')
    ),
    
    -- 文件
    pdf_url VARCHAR(500),
    
    -- 时间戳
    issued_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'
);

-- 创建索引
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_order_id ON invoices(order_id);
CREATE INDEX idx_invoices_invoice_no ON invoices(invoice_no);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_created_at ON invoices(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 关联用户（外键 → users.id） |
| order_id | UUID | 关联订单（外键 → orders.id） |
| invoice_no | VARCHAR(50) | 发票编号（唯一） |
| invoice_type | VARCHAR(20) | 发票类型：personal(个人)/company(企业普票)/vat_special(增值税专票) |
| amount | DECIMAL(10,2) | 不含税金额 |
| tax_amount | DECIMAL(10,2) | 税额 |
| total_amount | DECIMAL(10,2) | 价税合计（自动计算） |
| status | VARCHAR(20) | 发票状态 |
| pdf_url | VARCHAR(500) | 电子发票 PDF 下载地址 |

---

### 3.8 退款与对账模块表

#### 退款表 (refunds)
```sql
CREATE TABLE refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 退款信息
    refund_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'CNY',
    reason VARCHAR(500) NOT NULL,
    reason_type VARCHAR(30) CHECK (reason_type IN (
        'quality_issue', 'service_unavailable', 'duplicate_payment',
        'user_request', 'system_error', 'other'
    )),
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'approved', 'rejected', 'processing', 'completed', 'failed')
    ),
    reject_reason VARCHAR(500),
    
    -- 网关信息
    gateway_refund_id VARCHAR(100),
    gateway_response JSONB,
    
    -- 处理信息
    processed_by UUID REFERENCES users(id),
    
    -- 时间戳
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'
);

-- 创建索引
CREATE INDEX idx_refunds_order_id ON refunds(order_id);
CREATE INDEX idx_refunds_user_id ON refunds(user_id);
CREATE INDEX idx_refunds_refund_no ON refunds(refund_no);
CREATE INDEX idx_refunds_status ON refunds(status);
CREATE INDEX idx_refunds_requested_at ON refunds(requested_at);
CREATE INDEX idx_refunds_created_at ON refunds(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| order_id | UUID | 原始订单（外键 → orders.id） |
| user_id | UUID | 申请用户（外键 → users.id） |
| refund_no | VARCHAR(50) | 退款单号（唯一） |
| amount | DECIMAL(10,2) | 退款金额 |
| reason | VARCHAR(500) | 退款原因描述 |
| reason_type | VARCHAR(30) | 退款原因分类 |
| status | VARCHAR(20) | 退款状态：pending→approved→processing→completed |
| gateway_refund_id | VARCHAR(100) | 支付网关退款流水号 |
| processed_by | UUID | 审核人员（管理员 user_id） |

#### 对账记录表 (reconciliation_records)
```sql
CREATE TABLE reconciliation_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 对账信息
    reconciliation_date DATE NOT NULL,
    gateway VARCHAR(20) NOT NULL CHECK (gateway IN ('alipay', 'wechat', 'douyin')),
    
    -- 统计数据
    total_orders INT NOT NULL DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    matched_count INT NOT NULL DEFAULT 0,
    matched_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    unmatched_count INT NOT NULL DEFAULT 0,
    unmatched_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    
    -- 差异明细
    discrepancies JSONB DEFAULT '[]',
    
    -- 状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'matched', 'discrepancy', 'resolved')
    ),
    
    -- 报告
    report_url VARCHAR(500),
    notes TEXT,
    
    -- 处理信息
    reconciled_by UUID REFERENCES users(id),
    
    -- 时间戳
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(reconciliation_date, gateway)
);

-- 创建索引
CREATE INDEX idx_reconciliation_date ON reconciliation_records(reconciliation_date);
CREATE INDEX idx_reconciliation_gateway ON reconciliation_records(gateway);
CREATE INDEX idx_reconciliation_status ON reconciliation_records(status);
CREATE INDEX idx_reconciliation_created_at ON reconciliation_records(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| reconciliation_date | DATE | 对账日期 |
| gateway | VARCHAR(20) | 支付渠道：alipay/wechat/douyin |
| total_orders | INT | 当日总订单数 |
| total_amount | DECIMAL(12,2) | 当日总金额 |
| matched_count | INT | 匹配笔数 |
| unmatched_count | INT | 不匹配笔数 |
| discrepancies | JSONB | 差异明细列表 |
| status | VARCHAR(20) | 对账状态 |
| report_url | VARCHAR(500) | 对账报告下载地址 |

**示例数据：**
```sql
INSERT INTO reconciliation_records (reconciliation_date, gateway, total_orders, total_amount, matched_count, matched_amount, unmatched_count, unmatched_amount, status) VALUES
('2026-03-31', 'alipay', 156, 12580.00, 155, 12530.00, 1, 50.00, 'discrepancy'),
('2026-03-31', 'wechat', 203, 18920.00, 203, 18920.00, 0, 0.00, 'matched');
```

---

### 3.9 专家建议模块表

#### 专家建议表 (expert_advices)
```sql
CREATE TABLE expert_advices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 来源信息
    source_url VARCHAR(500),
    source_platform VARCHAR(50),
    author_name VARCHAR(100),
    
    -- 分类标签
    genre_tags VARCHAR(50)[] DEFAULT '{}',
    length_tags VARCHAR(50)[] DEFAULT '{}',
    style_tags VARCHAR(50)[] DEFAULT '{}',
    
    -- 内容
    advice_title VARCHAR(255),
    advice_content TEXT NOT NULL,
    advice_summary TEXT,
    
    -- 质量评估
    quality_score DECIMAL(3, 1) CHECK (quality_score >= 0 AND quality_score <= 5),
    relevance_score DECIMAL(3, 1) CHECK (relevance_score >= 0 AND relevance_score <= 5),
    
    -- 抓取信息
    scraped_at TIMESTAMP WITH TIME ZONE,
    scraper_version VARCHAR(20),
    raw_data JSONB,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    -- 使用统计
    usage_count INT DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_expert_advices_genre_tags ON expert_advices USING gin(genre_tags);
CREATE INDEX idx_expert_advices_length_tags ON expert_advices USING gin(length_tags);
CREATE INDEX idx_expert_advices_style_tags ON expert_advices USING gin(style_tags);
CREATE INDEX idx_expert_advices_quality ON expert_advices(quality_score);
CREATE INDEX idx_expert_advices_is_active ON expert_advices(is_active);
CREATE INDEX idx_expert_advices_scraped_at ON expert_advices(scraped_at);
CREATE INDEX idx_expert_advices_created_at ON expert_advices(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| source_url | VARCHAR(500) | 建议来源网址 |
| author_name | VARCHAR(100) | 建议作者 |
| genre_tags | VARCHAR(50)[] | 适用体裁标签数组，如 `{fantasy,romance}` |
| length_tags | VARCHAR(50)[] | 适用篇幅标签数组，如 `{短篇,中篇}` |
| style_tags | VARCHAR(50)[] | 适用风格标签数组，如 `{轻松,悬疑}` |
| advice_content | TEXT | 建议正文内容 |
| quality_score | DECIMAL(3,1) | 质量评分 0~5 |
| scraped_at | TIMESTAMP | 抓取时间 |
| is_active | BOOLEAN | 是否有效 |

#### 建议使用记录表 (advice_usage_records)
```sql
CREATE TABLE advice_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    advice_id UUID NOT NULL REFERENCES expert_advices(id) ON DELETE CASCADE,
    
    -- 使用信息
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    usage_context VARCHAR(50) CHECK (usage_context IN (
        'trend_analysis', 'style_reference', 'plot_planning', 'writing_guide', 'revision'
    )),
    effectiveness_score DECIMAL(3, 1) CHECK (effectiveness_score >= 0 AND effectiveness_score <= 5),
    
    -- 约束：同一小说不重复使用同一条建议
    UNIQUE(novel_id, advice_id),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_advice_usage_novel_id ON advice_usage_records(novel_id);
CREATE INDEX idx_advice_usage_advice_id ON advice_usage_records(advice_id);
CREATE INDEX idx_advice_usage_used_at ON advice_usage_records(used_at);
CREATE INDEX idx_advice_usage_context ON advice_usage_records(usage_context);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| novel_id | UUID | 使用建议的小说（外键 → novels.id） |
| advice_id | UUID | 被使用的建议（外键 → expert_advices.id） |
| used_at | TIMESTAMP | 使用时间 |
| usage_context | VARCHAR(50) | 使用场景 |
| effectiveness_score | DECIMAL(3,1) | 建议在本次使用中的效果评分 |

> **唯一约束说明**：`UNIQUE(novel_id, advice_id)` 确保同一条专家建议不会在同一部小说中被重复引用。

---

### 3.10 视频评审模块表

#### 视频评审表 (video_reviews)
```sql
CREATE TABLE video_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- 评审人信息
    reviewer_type VARCHAR(10) NOT NULL CHECK (reviewer_type IN ('auto', 'ai', 'human')),
    reviewer_id UUID REFERENCES users(id),
    
    -- 评分维度（每项 0~100 分）
    opening_score INT CHECK (opening_score >= 0 AND opening_score <= 100),
    completeness_score INT CHECK (completeness_score >= 0 AND completeness_score <= 100),
    quality_score INT CHECK (quality_score >= 0 AND quality_score <= 100),
    platform_score INT CHECK (platform_score >= 0 AND platform_score <= 100),
    commercial_score INT CHECK (commercial_score >= 0 AND commercial_score <= 100),
    
    -- 综合评分
    total_score INT GENERATED ALWAYS AS (
        COALESCE(opening_score, 0) * 20 / 100 +
        COALESCE(completeness_score, 0) * 20 / 100 +
        COALESCE(quality_score, 0) * 25 / 100 +
        COALESCE(platform_score, 0) * 20 / 100 +
        COALESCE(commercial_score, 0) * 15 / 100
    ) STORED,
    
    -- 通过判定
    pass BOOLEAN NOT NULL DEFAULT FALSE,
    pass_threshold INT DEFAULT 60,
    
    -- 评审详情
    review_notes TEXT,
    detailed_scores JSONB DEFAULT '{}',
    suggestions TEXT[],
    
    -- 时间戳
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_video_reviews_video_id ON video_reviews(video_id);
CREATE INDEX idx_video_reviews_reviewer_type ON video_reviews(reviewer_type);
CREATE INDEX idx_video_reviews_pass ON video_reviews(pass);
CREATE INDEX idx_video_reviews_total_score ON video_reviews(total_score);
CREATE INDEX idx_video_reviews_reviewed_at ON video_reviews(reviewed_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| video_id | UUID | 评审的视频（外键 → videos.id） |
| reviewer_type | VARCHAR(10) | 评审者类型：auto(自动规则)/ai(AI评审)/human(人工) |
| opening_score | INT | 开头吸引力评分 (0~100) |
| completeness_score | INT | 内容完整性评分 (0~100) |
| quality_score | INT | 画质音质评分 (0~100) |
| platform_score | INT | 平台适配度评分 (0~100) |
| commercial_score | INT | 商业价值评分 (0~100) |
| total_score | INT | 加权综合分（自动计算，权重：开头20%/完整20%/质量25%/平台20%/商业15%）|
| pass | BOOLEAN | 是否通过 |
| review_notes | TEXT | 评审备注 |

#### 记忆点表 (memory_points)
```sql
CREATE TABLE memory_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    
    -- 记忆点信息
    point_type VARCHAR(30) NOT NULL CHECK (point_type IN (
        'iconic_frame', 'classic_line', 'unique_sound',
        'emotional_peak', 'plot_twist', 'visual_effect'
    )),
    
    -- 时间位置
    timestamp_ms INT NOT NULL CHECK (timestamp_ms >= 0),
    duration_ms INT CHECK (duration_ms > 0),
    
    -- 描述
    description TEXT NOT NULL,
    content_text VARCHAR(500),
    
    -- 置信度
    confidence_score DECIMAL(3, 2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- 检测信息
    detected_by VARCHAR(20) CHECK (detected_by IN ('auto', 'ai', 'human')),
    detection_model VARCHAR(100),
    
    -- 元数据
    metadata JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_memory_points_video_id ON memory_points(video_id);
CREATE INDEX idx_memory_points_point_type ON memory_points(point_type);
CREATE INDEX idx_memory_points_timestamp ON memory_points(timestamp_ms);
CREATE INDEX idx_memory_points_confidence ON memory_points(confidence_score);
CREATE INDEX idx_memory_points_created_at ON memory_points(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| video_id | UUID | 所属视频（外键 → videos.id） |
| point_type | VARCHAR(30) | 记忆点类型：iconic_frame(标志性画面)/classic_line(经典台词)/unique_sound(独特音效)/emotional_peak(情感高潮)/plot_twist(情节转折)/visual_effect(视觉特效) |
| timestamp_ms | INT | 在视频中的时间位置（毫秒） |
| duration_ms | INT | 记忆点持续时长（毫秒） |
| description | TEXT | 记忆点描述 |
| confidence_score | DECIMAL(3,2) | 置信度 0.00~1.00 |
| detected_by | VARCHAR(20) | 检测方式 |

---

### 3.11 内容广场模块表

#### 公开内容表 (public_contents)
```sql
CREATE TABLE public_contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 内容信息
    content_type VARCHAR(10) NOT NULL CHECK (content_type IN ('novel', 'video')),
    content_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    cover_url VARCHAR(500),
    
    -- 发布设置
    is_public BOOLEAN DEFAULT TRUE,
    allow_comment BOOLEAN DEFAULT TRUE,
    allow_collect BOOLEAN DEFAULT TRUE,
    
    -- 分类标签
    category VARCHAR(50),
    tags VARCHAR(50)[] DEFAULT '{}',
    
    -- 统计信息
    view_count INT DEFAULT 0 CHECK (view_count >= 0),
    like_count INT DEFAULT 0 CHECK (like_count >= 0),
    collect_count INT DEFAULT 0 CHECK (collect_count >= 0),
    comment_count INT DEFAULT 0 CHECK (comment_count >= 0),
    share_count INT DEFAULT 0 CHECK (share_count >= 0),
    
    -- 排序与推荐
    hot_score DECIMAL(10, 2) DEFAULT 0.00,
    is_featured BOOLEAN DEFAULT FALSE,
    is_top BOOLEAN DEFAULT FALSE,
    
    -- 时间戳
    published_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(content_type, content_id)
);

-- 创建索引
CREATE INDEX idx_public_contents_user_id ON public_contents(user_id);
CREATE INDEX idx_public_contents_content ON public_contents(content_type, content_id);
CREATE INDEX idx_public_contents_is_public ON public_contents(is_public);
CREATE INDEX idx_public_contents_category ON public_contents(category);
CREATE INDEX idx_public_contents_tags ON public_contents USING gin(tags);
CREATE INDEX idx_public_contents_hot_score ON public_contents(hot_score DESC);
CREATE INDEX idx_public_contents_published_at ON public_contents(published_at);
CREATE INDEX idx_public_contents_is_featured ON public_contents(is_featured) WHERE is_featured = TRUE;
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 发布者（外键 → users.id） |
| content_type | VARCHAR(10) | 内容类型：novel/video |
| content_id | UUID | 关联的小说或视频 ID |
| title | VARCHAR(255) | 展示标题 |
| cover_url | VARCHAR(500) | 封面图 URL |
| is_public | BOOLEAN | 是否公开可见 |
| view_count | INT | 浏览量 |
| like_count | INT | 点赞数 |
| collect_count | INT | 收藏数 |
| hot_score | DECIMAL(10,2) | 热度分（由 view_count/like/collect 加权计算，定时更新） |
| is_featured | BOOLEAN | 编辑精选 |

#### 内容互动表 (content_interactions)
```sql
CREATE TABLE content_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES public_contents(id) ON DELETE CASCADE,
    
    -- 互动类型
    interaction_type VARCHAR(20) NOT NULL CHECK (
        interaction_type IN ('like', 'collect', 'comment', 'share')
    ),
    
    -- 评论内容（仅 comment 类型时有值）
    comment_text TEXT,
    parent_comment_id UUID REFERENCES content_interactions(id) ON DELETE CASCADE,
    
    -- 状态
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束：like/collect 类型每用户每内容只能一次
    CONSTRAINT uq_like_collect UNIQUE NULLS NOT DISTINCT (
        user_id, content_id, interaction_type
    ) -- PostgreSQL 15+ 支持 NULLS NOT DISTINCT
);

-- 创建索引
CREATE INDEX idx_content_interactions_user_id ON content_interactions(user_id);
CREATE INDEX idx_content_interactions_content_id ON content_interactions(content_id);
CREATE INDEX idx_content_interactions_type ON content_interactions(interaction_type);
CREATE INDEX idx_content_interactions_parent ON content_interactions(parent_comment_id);
CREATE INDEX idx_content_interactions_created_at ON content_interactions(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 互动用户（外键 → users.id） |
| content_id | UUID | 互动内容（外键 → public_contents.id） |
| interaction_type | VARCHAR(20) | 互动类型：like(点赞)/collect(收藏)/comment(评论)/share(分享) |
| comment_text | TEXT | 评论正文（仅 comment 类型） |
| parent_comment_id | UUID | 父评论 ID（支持楼中楼回复） |
| is_deleted | BOOLEAN | 软删除标记 |

> **唯一约束说明**：对于 like/collect 类型，通过唯一约束防止用户对同一内容重复点赞或收藏。comment/share 可以多次操作。实际可在应用层控制。

#### 内容举报表 (content_reports)
```sql
CREATE TABLE content_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES public_contents(id) ON DELETE CASCADE,
    
    -- 举报信息
    reason VARCHAR(30) NOT NULL CHECK (reason IN (
        'spam', 'abuse', 'copyright', 'inappropriate', 'misinformation', 'other'
    )),
    description TEXT,
    evidence_urls VARCHAR(500)[],
    
    -- 处理信息
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'reviewing', 'resolved', 'dismissed')
    ),
    handled_by UUID REFERENCES users(id),
    handle_result VARCHAR(50),
    handle_notes TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    handled_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束：同一用户对同一内容只能举报一次
    UNIQUE(reporter_id, content_id)
);

-- 创建索引
CREATE INDEX idx_content_reports_reporter_id ON content_reports(reporter_id);
CREATE INDEX idx_content_reports_content_id ON content_reports(content_id);
CREATE INDEX idx_content_reports_status ON content_reports(status);
CREATE INDEX idx_content_reports_reason ON content_reports(reason);
CREATE INDEX idx_content_reports_created_at ON content_reports(created_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| reporter_id | UUID | 举报者（外键 → users.id） |
| content_id | UUID | 被举报内容（外键 → public_contents.id） |
| reason | VARCHAR(30) | 举报原因分类：spam(垃圾)/abuse(滥用)/copyright(侵权)/inappropriate(不当)/misinformation(虚假) |
| status | VARCHAR(20) | 处理状态：pending(待审)/reviewing(审核中)/resolved(已处理)/dismissed(已驳回) |
| handled_by | UUID | 处理人（管理员 user_id） |

---

### 3.12 通知与审计模块表

#### 通知表 (notifications)
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 通知信息
    type VARCHAR(20) NOT NULL CHECK (type IN ('system', 'payment', 'task', 'publish', 'social', 'promotion')),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    
    -- 关联资源
    resource_type VARCHAR(50),
    resource_id UUID,
    action_url VARCHAR(500),
    
    -- 状态
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- 发送渠道
    channels VARCHAR(20)[] DEFAULT '{in_app}',
    
    -- 优先级
    priority VARCHAR(10) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- 元数据
    metadata JSONB DEFAULT '{}'
);

-- 创建索引
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_priority ON notifications(priority);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 接收用户（外键 → users.id） |
| type | VARCHAR(20) | 通知类型：system(系统)/payment(支付)/task(任务)/publish(发布)/social(社交)/promotion(营销) |
| title | VARCHAR(255) | 通知标题 |
| content | TEXT | 通知正文 |
| resource_type | VARCHAR(50) | 关联资源类型（novel/video/order 等） |
| resource_id | UUID | 关联资源 ID |
| action_url | VARCHAR(500) | 点击跳转地址 |
| is_read | BOOLEAN | 是否已读 |
| channels | VARCHAR(20)[] | 发送渠道列表：in_app/push/sms/email |
| priority | VARCHAR(10) | 优先级 |

#### 审计日志表 (audit_logs)
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- 操作信息
    action VARCHAR(50) NOT NULL CHECK (action IN (
        'login', 'logout', 'register', 'password_change',
        'create', 'update', 'delete', 'publish', 'unpublish',
        'payment', 'refund', 'subscription_change',
        'export', 'import', 'admin_action'
    )),
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    
    -- 请求信息
    ip_address INET,
    user_agent VARCHAR(500),
    request_method VARCHAR(10),
    request_path VARCHAR(500),
    
    -- 操作详情
    details_json JSONB DEFAULT '{}',
    old_value JSONB,
    new_value JSONB,
    
    -- 结果
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_ip_address ON audit_logs(ip_address);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_success ON audit_logs(success);
CREATE INDEX idx_audit_logs_details ON audit_logs USING gin(details_json);

-- 按月分区（审计日志数据量大，建议分区）
-- CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs
--     FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 操作用户（外键 → users.id，可为 NULL 表示系统操作） |
| action | VARCHAR(50) | 操作类型 |
| resource_type | VARCHAR(50) | 资源类型：user/novel/video/order/subscription 等 |
| resource_id | UUID | 被操作的资源 ID |
| ip_address | INET | 请求来源 IP |
| user_agent | VARCHAR(500) | 浏览器/客户端标识 |
| details_json | JSONB | 操作详情（灵活存储变更快照等） |
| old_value | JSONB | 变更前值（用于变更审计） |
| new_value | JSONB | 变更后值 |
| success | BOOLEAN | 操作是否成功 |

---

### 3.13 多端渠道模块表

#### 用户设备表 (user_devices)
```sql
CREATE TABLE user_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 设备信息
    device_type VARCHAR(20) NOT NULL CHECK (device_type IN (
        'web', 'wechat_mp', 'douyin_mp', 'app_ios', 'app_android'
    )),
    device_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(100),
    device_model VARCHAR(100),
    os_version VARCHAR(50),
    app_version VARCHAR(20),
    
    -- 推送信息
    push_token VARCHAR(500),
    push_enabled BOOLEAN DEFAULT TRUE,
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(user_id, device_type, device_id)
);

-- 创建索引
CREATE INDEX idx_user_devices_user_id ON user_devices(user_id);
CREATE INDEX idx_user_devices_device_type ON user_devices(device_type);
CREATE INDEX idx_user_devices_is_active ON user_devices(is_active);
CREATE INDEX idx_user_devices_last_active_at ON user_devices(last_active_at);
CREATE INDEX idx_user_devices_push_token ON user_devices(push_token) WHERE push_token IS NOT NULL;
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户（外键 → users.id） |
| device_type | VARCHAR(20) | 设备类型：web/wechat_mp(微信小程序)/douyin_mp(抖音小程序)/app_ios/app_android |
| device_id | VARCHAR(255) | 设备唯一标识 |
| device_name | VARCHAR(100) | 设备名称（用户自定义或自动识别） |
| push_token | VARCHAR(500) | 推送令牌（用于消息推送） |
| push_enabled | BOOLEAN | 是否开启推送 |
| is_active | BOOLEAN | 设备是否活跃 |
| last_active_at | TIMESTAMP | 最后活跃时间 |

#### 渠道用户绑定表 (channel_users)
```sql
CREATE TABLE channel_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 渠道信息
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('wechat', 'douyin', 'phone', 'apple', 'google')),
    channel_user_id VARCHAR(255) NOT NULL,
    channel_nickname VARCHAR(100),
    channel_avatar_url VARCHAR(500),
    
    -- 认证信息
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- 绑定信息
    bind_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    unbind_at TIMESTAMP WITH TIME ZONE,
    is_primary BOOLEAN DEFAULT FALSE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    UNIQUE(channel, channel_user_id),
    UNIQUE(user_id, channel)
);

-- 创建索引
CREATE INDEX idx_channel_users_user_id ON channel_users(user_id);
CREATE INDEX idx_channel_users_channel ON channel_users(channel);
CREATE INDEX idx_channel_users_channel_uid ON channel_users(channel, channel_user_id);
CREATE INDEX idx_channel_users_bind_at ON channel_users(bind_at);
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 系统用户（外键 → users.id） |
| channel | VARCHAR(20) | 渠道类型：wechat/douyin/phone/apple/google |
| channel_user_id | VARCHAR(255) | 渠道用户标识（微信 openid、抖音 openid、手机号等） |
| channel_nickname | VARCHAR(100) | 渠道昵称 |
| channel_avatar_url | VARCHAR(500) | 渠道头像 |
| bind_at | TIMESTAMP | 绑定时间 |
| is_primary | BOOLEAN | 是否主登录渠道 |

> **唯一约束说明**：
> - `UNIQUE(channel, channel_user_id)`：同一渠道的 openid 全局唯一，不可绑定多个系统账户。
> - `UNIQUE(user_id, channel)`：一个用户在同一渠道只能绑定一个账号。

---

### 3.14 基础设施表（替代 Redis/RabbitMQ）

#### 任务队列表 (task_queue)

> 使用 PostgreSQL 表替代 RabbitMQ/Celery Broker，实现轻量级任务队列。
> Worker 通过 `SELECT ... FOR UPDATE SKIP LOCKED` 实现并发安全的任务获取。

```sql
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,    -- novel_generation/video_generation/publish/etc
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending/processing/completed/failed
    priority INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    retry_count INT DEFAULT 0,
    locked_by VARCHAR(100),            -- worker ID
    locked_at TIMESTAMP,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_queue_status_priority ON task_queue(status, priority DESC, scheduled_at);
CREATE INDEX idx_task_queue_locked ON task_queue(locked_by, locked_at);
```

**任务获取示例（Worker 端）：**
```sql
-- 获取一个待处理任务（并发安全）
UPDATE task_queue
SET status = 'processing',
    locked_by = 'worker-1',
    locked_at = CURRENT_TIMESTAMP,
    started_at = CURRENT_TIMESTAMP
WHERE id = (
    SELECT id FROM task_queue
    WHERE status = 'pending'
      AND scheduled_at <= CURRENT_TIMESTAMP
    ORDER BY priority DESC, scheduled_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING *;

-- 任务完成
UPDATE task_queue SET status = 'completed', completed_at = CURRENT_TIMESTAMP
WHERE id = $1;

-- 任务失败（自动重试）
UPDATE task_queue
SET status = CASE WHEN retry_count + 1 >= max_retries THEN 'failed' ELSE 'pending' END,
    retry_count = retry_count + 1,
    locked_by = NULL,
    locked_at = NULL,
    error_message = $2,
    scheduled_at = CURRENT_TIMESTAMP + INTERVAL '30 seconds' * (retry_count + 1)  -- 指数退避
WHERE id = $1;
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| task_type | VARCHAR(50) | 任务类型：novel_generation/video_generation/publish/tts 等 |
| payload | JSONB | 任务参数（如 novel_id、配置等） |
| status | VARCHAR(20) | 任务状态：pending(待执行)/processing(执行中)/completed(完成)/failed(失败) |
| priority | INT | 优先级，数字越大越优先 |
| max_retries | INT | 最大重试次数 |
| retry_count | INT | 已重试次数 |
| locked_by | VARCHAR(100) | 锁定该任务的 Worker ID |
| locked_at | TIMESTAMP | 锁定时间（用于检测僵死任务） |
| scheduled_at | TIMESTAMP | 计划执行时间（支持延迟任务） |

#### 幂等键表 (idempotent_keys)

> 替代 Redis SETNX，用于防止重复提交（如重复支付、重复生成）。

```sql
CREATE TABLE idempotent_keys (
    key VARCHAR(255) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 定期清理过期的幂等键
-- DELETE FROM idempotent_keys WHERE created_at < NOW() - INTERVAL '7 days';
```

**使用示例：**
```sql
-- 尝试插入幂等键（如果已存在则说明是重复请求）
INSERT INTO idempotent_keys (key) VALUES ('payment:order:uuid-xxx')
ON CONFLICT (key) DO NOTHING
RETURNING key;
-- 返回空 = 重复请求，返回key = 首次请求
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| key | VARCHAR(255) | 幂等键，格式：`{业务}:{操作}:{ID}`，如 `payment:order:uuid-xxx` |
| created_at | TIMESTAMP | 创建时间，用于定期清理过期键 |

#### 缓存条目表 (cache_entries)

> PostgreSQL 持久化缓存，用于跨进程共享的缓存场景（如 Celery Worker 需要读取的数据）。
> 进程内 cachetools 无法跨进程共享时的降级方案。

```sql
CREATE TABLE cache_entries (
    cache_key VARCHAR(255) PRIMARY KEY,
    cache_value JSONB,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cache_expires ON cache_entries(expires_at);

-- 定期清理过期缓存
-- DELETE FROM cache_entries WHERE expires_at < NOW();
```

**使用示例：**
```sql
-- 写入/更新缓存
INSERT INTO cache_entries (cache_key, cache_value, expires_at)
VALUES ('hot_content_list', '{"items": [...]}', NOW() + INTERVAL '5 minutes')
ON CONFLICT (cache_key) DO UPDATE
SET cache_value = EXCLUDED.cache_value,
    expires_at = EXCLUDED.expires_at;

-- 读取缓存（仅返回未过期的）
SELECT cache_value FROM cache_entries
WHERE cache_key = 'hot_content_list' AND expires_at > NOW();
```

**字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| cache_key | VARCHAR(255) | 缓存键名 |
| cache_value | JSONB | 缓存值（JSON格式） |
| expires_at | TIMESTAMP | 过期时间 |
| created_at | TIMESTAMP | 创建时间 |

---

## 4. 进程内缓存策略

> 使用 Python `cachetools` 库替代 Redis，零额外服务依赖，适合 1GB 内存单机部署。
> 对于需要持久化的缓存场景，使用 PostgreSQL `cache_entries` 表（见 3.14 节）。

### 4.1 缓存架构设计

```
缓存层级：
1. L1 - 进程内缓存（cachetools）：热点数据，毫秒级访问
2. L2 - PostgreSQL cache_entries 表：持久化缓存，需要跨进程共享的数据
3. L3 - PostgreSQL 原始表：最终数据源

缓存失效策略：
- TTL 过期：cachetools.TTLCache 自动过期
- LRU 淘汰：cachetools.LRUCache 按访问频率淘汰
- 主动失效：数据更新时手动清除对应缓存
```

### 4.2 cachetools 缓存配置

```python
from cachetools import TTLCache, LRUCache
from cachetools import cached
import threading

# 全局缓存实例（线程安全）
_lock = threading.Lock()

# 会话缓存：最多200个会话，30分钟过期
session_cache = TTLCache(maxsize=200, ttl=1800)

# 用户信息缓存：最多100个用户，10分钟过期
user_cache = TTLCache(maxsize=100, ttl=600)

# 套餐列表缓存：1小时过期
plan_cache = TTLCache(maxsize=10, ttl=3600)

# 热门内容缓存：5分钟过期
hot_content_cache = TTLCache(maxsize=50, ttl=300)

# 配额缓存：5分钟过期（短TTL保证一致性）
quota_cache = TTLCache(maxsize=200, ttl=300)

# 限流计数器：1分钟窗口
rate_limit_cache = TTLCache(maxsize=500, ttl=60)

# 建议池缓存：30分钟过期
advice_cache = TTLCache(maxsize=20, ttl=1800)
```

### 4.3 缓存使用示例

```python
# 会话缓存
def get_session(session_id: str) -> dict | None:
    with _lock:
        return session_cache.get(session_id)

def set_session(session_id: str, data: dict):
    with _lock:
        session_cache[session_id] = data

def invalidate_session(session_id: str):
    with _lock:
        session_cache.pop(session_id, None)

# 限流（简单计数器）
def check_rate_limit(key: str, max_calls: int = 60) -> bool:
    with _lock:
        count = rate_limit_cache.get(key, 0)
        if count >= max_calls:
            return False
        rate_limit_cache[key] = count + 1
        return True

# 带缓存装饰器的查询
@cached(cache=plan_cache, lock=_lock)
def get_subscription_plans():
    """套餐列表缓存，1小时自动刷新"""
    return db.query(SubscriptionPlan).filter_by(is_active=True).all()
```

### 4.4 缓存内存预算

```
总内存预算：≤ 50MB（进程内缓存）

各缓存估算：
- session_cache (200条 × ~1KB)    ≈ 200KB
- user_cache (100条 × ~2KB)       ≈ 200KB
- plan_cache (10条 × ~1KB)        ≈ 10KB
- hot_content_cache (50条 × ~2KB) ≈ 100KB
- quota_cache (200条 × ~0.5KB)    ≈ 100KB
- rate_limit_cache (500条 × ~0.1KB) ≈ 50KB
- advice_cache (20条 × ~5KB)      ≈ 100KB
总计：≈ 1MB（远低于预算，留有充足余量）

注意：cachetools 的 maxsize 已限制条目数量，不会无限增长
```

### 4.5 缓存与数据库配合

```
写操作流程（Cache-Aside 模式）：
1. 更新数据库
2. 删除对应缓存条目
3. 下次读取时重新从数据库加载

读操作流程：
1. 查询进程内缓存
2. 缓存命中 → 直接返回
3. 缓存未命中 → 查询数据库 → 写入缓存 → 返回

跨进程共享场景（如Celery Worker需要读取）：
- 使用 cache_entries 表（PostgreSQL）作为共享缓存层
- 或直接查询原始表（大多数场景下足够快）
```

---

## 5. PostgreSQL 性能调优（1GB 内存环境）

### 5.1 postgresql.conf 关键参数

```sql
-- postgresql.conf 关键参数（1GB 内存 VPS 优化）
shared_buffers = 128MB          -- 总内存的12%
effective_cache_size = 256MB    -- 总内存的25%
work_mem = 4MB                  -- 每个排序/哈希操作
maintenance_work_mem = 64MB     -- VACUUM/CREATE INDEX
max_connections = 20            -- 减少连接数节省内存
wal_buffers = 4MB
max_wal_size = 256MB            -- 控制WAL磁盘占用
min_wal_size = 64MB
checkpoint_timeout = 10min
random_page_cost = 1.1          -- SSD优化
effective_io_concurrency = 200  -- SSD优化
```

### 5.2 内存分配预算

```
总可用内存：1024MB

PostgreSQL:
  shared_buffers:      128MB
  OS cache (effective): 256MB
  maintenance_work_mem: 64MB（仅维护时使用）
  work_mem × 连接数:    4MB × 20 = 80MB（理论最大值）
  其他开销:             ~50MB
  小计:                ~320MB（常态）/ ~580MB（峰值）

应用层：
  FastAPI 进程:         ~150MB
  Celery Worker:        ~100MB
  系统 + 其他:          ~100MB
  小计:                ~350MB

总计常态：~670MB，留有约 350MB 作为 OS 缓存和缓冲
```

### 5.3 自动 VACUUM 配置

```sql
-- 避免 VACUUM 占用过多资源
autovacuum_max_workers = 2              -- 默认3，减少到2
autovacuum_naptime = 60                 -- 检查间隔60秒
autovacuum_vacuum_cost_delay = 20ms     -- 限制IO速率
autovacuum_vacuum_cost_limit = 200      -- 限制IO速率
autovacuum_vacuum_threshold = 50        -- 最少变更行数
autovacuum_vacuum_scale_factor = 0.1    -- 变更比例阈值
```

---

## 6. 磁盘空间管理策略（20GB 约束）

### 6.1 磁盘空间预算

```
总可用磁盘：20GB

预算分配：
- PostgreSQL 数据:      3GB（含索引）
- WAL 日志:             512MB（max_wal_size=256MB × 2）
- PostgreSQL 备份:      300MB（最近3份 × ~100MB）
- 应用数据文件:         10GB（小说/视频/音频等）
- 临时文件:             1GB（生成过程中间文件）
- 系统 + 应用程序:      3GB
- 预留缓冲:             ~2GB
总计:                   ~20GB
```

### 6.2 数据库大小控制

```sql
-- 查看数据库大小
SELECT pg_size_pretty(pg_database_size('ai_novel_agent'));

-- 查看各表大小（含索引）
SELECT 
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- 定期执行 VACUUM FULL 回收空间（会锁表，低峰期执行）
VACUUM FULL audit_logs;
VACUUM FULL system_monitoring;
VACUUM FULL novel_generation_logs;
VACUUM FULL video_generation_logs;

-- 使用 pg_repack 在线回收空间（不锁表，推荐）
-- sudo apt install postgresql-15-repack
-- pg_repack -d ai_novel_agent -t audit_logs
```

### 6.3 表分区与老数据归档

```sql
-- 将 audit_logs 改为按月分区表
CREATE TABLE audit_logs_partitioned (
    LIKE audit_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE audit_logs_2026_04 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE audit_logs_2026_05 PARTITION OF audit_logs_partitioned
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- 归档超过3个月的数据
-- 1. 导出老分区
-- pg_dump -t audit_logs_2026_01 ai_novel_agent | gzip > /opt/ai-novel-agent/data/backups/audit_logs_2026_01.sql.gz
-- 2. 删除老分区
-- ALTER TABLE audit_logs_partitioned DETACH PARTITION audit_logs_2026_01;
-- DROP TABLE audit_logs_2026_01;
```

### 6.4 WAL 清理策略

```sql
-- WAL 大小由以下参数控制
max_wal_size = 256MB    -- 触发 checkpoint 的 WAL 上限
min_wal_size = 64MB     -- 回收 WAL 后保留的最小值
checkpoint_timeout = 10min

-- 查看当前 WAL 占用
SELECT pg_size_pretty(sum(size)) FROM pg_ls_waldir();
```

### 6.5 自动清理 cron 脚本

```bash
#!/bin/bash
# /opt/ai-novel-agent/scripts/db_maintenance.sh
# 每天凌晨 3:00 执行：crontab -e → 0 3 * * * /opt/ai-novel-agent/scripts/db_maintenance.sh

set -e
DB_NAME="ai_novel_agent"
LOG_FILE="/opt/ai-novel-agent/logs/db_maintenance.log"
BACKUP_DIR="/opt/ai-novel-agent/data/backups"

echo "$(date '+%Y-%m-%d %H:%M:%S') === 开始数据库维护 ===" >> "$LOG_FILE"

# 1. 清理过期幂等键（保留7天）
psql -d "$DB_NAME" -c "DELETE FROM idempotent_keys WHERE created_at < NOW() - INTERVAL '7 days';" >> "$LOG_FILE" 2>&1

# 2. 清理过期缓存条目
psql -d "$DB_NAME" -c "DELETE FROM cache_entries WHERE expires_at < NOW();" >> "$LOG_FILE" 2>&1

# 3. 清理已完成超过7天的任务记录
psql -d "$DB_NAME" -c "DELETE FROM task_queue WHERE status IN ('completed', 'failed') AND completed_at < NOW() - INTERVAL '7 days';" >> "$LOG_FILE" 2>&1

# 4. 清理超过90天的审计日志（如未使用分区表）
psql -d "$DB_NAME" -c "DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '90 days';" >> "$LOG_FILE" 2>&1

# 5. 清理超过30天的监控数据
psql -d "$DB_NAME" -c "DELETE FROM system_monitoring WHERE recorded_at < NOW() - INTERVAL '30 days';" >> "$LOG_FILE" 2>&1

# 6. 清理超过60天的生成日志
psql -d "$DB_NAME" -c "DELETE FROM novel_generation_logs WHERE created_at < NOW() - INTERVAL '60 days';" >> "$LOG_FILE" 2>&1
psql -d "$DB_NAME" -c "DELETE FROM video_generation_logs WHERE created_at < NOW() - INTERVAL '60 days';" >> "$LOG_FILE" 2>&1

# 7. 清理超过30天的通知
psql -d "$DB_NAME" -c "DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '30 days';" >> "$LOG_FILE" 2>&1

# 8. 清理临时文件目录
find /opt/ai-novel-agent/data/temp/ -type f -mtime +1 -delete 2>> "$LOG_FILE"

# 9. VACUUM ANALYZE（回收空间并更新统计信息）
psql -d "$DB_NAME" -c "VACUUM ANALYZE;" >> "$LOG_FILE" 2>&1

# 10. 显示当前数据库大小
psql -d "$DB_NAME" -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME')) AS db_size;" >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') === 数据库维护完成 ===" >> "$LOG_FILE"
```

---

## 7. 文件存储目录结构

> 使用本地文件系统替代 MinIO/S3 对象存储，适合单机部署场景。

### 7.1 目录结构

```
/opt/ai-novel-agent/data/
├── novels/           # 小说文件 (markdown/json)
├── videos/           # 视频文件 (mp4)
├── audio/            # 音频文件 (mp3)
├── covers/           # 封面图片
├── exports/          # 导出文件 (epub/pdf)
├── temp/             # 临时文件 (定期清理)
└── backups/          # 数据库备份 (仅保留最近3份)
```

### 7.2 文件命名规范

```
文件路径格式：{类型}/{用户ID前2位}/{用户ID}/{文件ID}.{扩展名}

示例：
novels/ab/abcd1234-.../novel-uuid.json
videos/ab/abcd1234-.../video-uuid.mp4
covers/ab/abcd1234-.../cover-uuid.jpg

优点：
- 按用户ID分散目录，避免单目录文件过多
- 文件ID全局唯一，防止冲突
- 目录层级固定，方便定位和清理
```

### 7.3 磁盘空间监控

```bash
# 查看各目录占用
du -sh /opt/ai-novel-agent/data/*/

# 告警：磁盘使用超过80%时通知
DISK_USAGE=$(df /opt/ai-novel-agent/data | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "磁盘使用率告警: ${DISK_USAGE}%" >> /opt/ai-novel-agent/logs/disk_alert.log
fi
```

---

## 8. 数据迁移策略

### 8.1 从单库到商业化架构的迁移路径

```
部署环境：1GB 内存 VPS，裸机部署（systemd 管理服务）
数据库：单机 PostgreSQL 15，无需 Docker

阶段一：表结构扩展（低风险）
├── 1. 新增套餐/订阅/权益相关表
├── 2. 新增退款/对账表
├── 3. 新增内容广场相关表
├── 4. 新增通知/审计表
├── 5. 新增多端渠道表
└── 6. 新增基础设施表（task_queue/idempotent_keys/cache_entries）

阶段二：数据迁移（中风险）
├── 1. 现有用户补充默认免费套餐订阅记录
├── 2. 历史订单数据补充 invoice 关联
├── 3. 已发布内容同步到 public_contents
└── 4. 现有设备信息迁移到 user_devices

注意事项：
- 所有服务通过 systemd 管理，不使用 Docker
- 资源有限，迁移期间需暂停非关键服务，减少内存/CPU竞争
- 每次迁移前必须 pg_dump 备份
- 大表迁移分批进行，避免长事务锁表
```

### 8.2 迁移脚本模板

```sql
-- 阶段一：为现有用户创建默认免费订阅
INSERT INTO user_subscriptions (user_id, plan_id, status, started_at, expires_at, auto_renew)
SELECT 
    u.id,
    (SELECT id FROM subscription_plans WHERE name = '微小说'),
    'active',
    u.created_at,
    u.created_at + INTERVAL '100 years',
    FALSE
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_subscriptions us WHERE us.user_id = u.id
);

-- 阶段一：为新订阅创建权益记录
INSERT INTO entitlements (subscription_id, resource_type, total_quota, used_quota, reset_at)
SELECT 
    us.id,
    rt.resource_type,
    CASE rt.resource_type
        WHEN 'novel_words' THEN sp.novel_word_quota
        WHEN 'video_minutes' THEN sp.video_minute_quota
        WHEN 'publish_count' THEN sp.publish_count_quota
    END,
    0,
    DATE_TRUNC('month', CURRENT_TIMESTAMP) + INTERVAL '1 month'
FROM user_subscriptions us
JOIN subscription_plans sp ON sp.id = us.plan_id
CROSS JOIN (VALUES ('novel_words'), ('video_minutes'), ('publish_count')) AS rt(resource_type)
WHERE NOT EXISTS (
    SELECT 1 FROM entitlements e WHERE e.subscription_id = us.id AND e.resource_type = rt.resource_type
);
```

### 8.3 回滚方案

```
每次迁移前：
1. pg_dump 完整备份到 /opt/ai-novel-agent/data/backups/
2. 记录当前 schema 版本号
3. 准备回滚 SQL 脚本

回滚执行：
1. systemctl stop ai-novel-agent（停止应用）
2. 执行回滚 SQL 或 pg_restore 恢复
3. systemctl start ai-novel-agent（恢复应用）
4. 验证数据完整性
```

---

## 9. 备份与归档策略

### 9.1 备份策略（磁盘约束下的方案）

```
部署约束：20GB 磁盘，无异地存储
备份大小预估：约 100MB/份（压缩后）
仅保留最近 3 份备份，总占用约 300MB

每周全量备份（周日 03:00）：
- 方式：pg_dump --format=custom --compress=9
- 保留：最近 3 份
- 存储：/opt/ai-novel-agent/data/backups/

每日 WAL 归档：
- 方式：archive_command 归档 WAL 段
- 保留：最近 7 天（约 200MB）
- 用途：时间点恢复（PITR）
```

### 9.2 备份脚本

```bash
#!/bin/bash
# /opt/ai-novel-agent/scripts/backup.sh
# 每周日凌晨 3:30 执行：crontab -e → 30 3 * * 0 /opt/ai-novel-agent/scripts/backup.sh

set -e
DB_NAME="ai_novel_agent"
BACKUP_DIR="/opt/ai-novel-agent/data/backups"
LOG_FILE="/opt/ai-novel-agent/logs/backup.log"
MAX_BACKUPS=3
DATE=$(date '+%Y%m%d_%H%M%S')

echo "$(date '+%Y-%m-%d %H:%M:%S') === 开始数据库备份 ===" >> "$LOG_FILE"

# 1. 执行全量备份（压缩）
pg_dump -Fc -Z 9 -d "$DB_NAME" -f "${BACKUP_DIR}/full_${DATE}.dump" 2>> "$LOG_FILE"

# 2. 显示备份大小
BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/full_${DATE}.dump" | cut -f1)
echo "备份完成: full_${DATE}.dump (${BACKUP_SIZE})" >> "$LOG_FILE"

# 3. 删除多余备份（只保留最近3份）
cd "$BACKUP_DIR"
ls -t full_*.dump 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f
echo "清理旧备份完成，当前保留 $(ls full_*.dump 2>/dev/null | wc -l) 份" >> "$LOG_FILE"

# 4. 清理超过7天的 WAL 归档
find "${BACKUP_DIR}/wal/" -type f -mtime +7 -delete 2>> "$LOG_FILE"

# 5. 显示备份目录总大小
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "备份目录总大小: ${TOTAL_SIZE}" >> "$LOG_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') === 数据库备份完成 ===" >> "$LOG_FILE"
```

### 9.3 WAL 归档配置

```sql
-- postgresql.conf WAL 归档配置
archive_mode = on
archive_command = 'cp %p /opt/ai-novel-agent/data/backups/wal/%f'
archive_timeout = 300   -- 5分钟强制归档（即使WAL未写满）
```

### 9.4 恢复流程

```bash
# 1. 停止服务
sudo systemctl stop ai-novel-agent
sudo systemctl stop postgresql

# 2. 恢复全量备份
pg_restore -d ai_novel_agent -c /opt/ai-novel-agent/data/backups/full_YYYYMMDD.dump

# 3. 如需时间点恢复（PITR）
# 配置 recovery.conf 或 postgresql.conf
# restore_command = 'cp /opt/ai-novel-agent/data/backups/wal/%f %p'
# recovery_target_time = '2026-04-01 12:00:00'

# 4. 重启服务
sudo systemctl start postgresql
sudo systemctl start ai-novel-agent
```

### 9.5 数据保留与归档策略

```
磁盘约束下的数据保留规则：
- 用户/订单/小说/视频核心数据：在线永久保留
- audit_logs：在线保留 90 天，导出压缩后删除
- system_monitoring：在线保留 30 天，直接删除
- generation_logs：在线保留 60 天，直接删除
- notifications：在线保留 30 天，直接删除
- task_queue 已完成任务：保留 7 天
- idempotent_keys：保留 7 天
- cache_entries：自动过期清理
- temp 目录：保留 1 天

归档实现：
- 使用 db_maintenance.sh 脚本定期清理（见 6.5 节）
- 重要数据（audit_logs）导出为 gzip 压缩 SQL 后删除
- 不使用对象存储，所有归档文件保存在本地 backups 目录
```

---

## 10. 索引优化说明

### 10.1 索引设计原则

```
1. 覆盖索引优先：高频查询字段组合建立复合索引
2. 部分索引优化：WHERE 子句过滤低基数字段
3. JSONB 索引：使用 GIN 索引加速 JSON 字段查询
4. 数组索引：使用 GIN 索引加速数组字段包含查询
5. 避免过度索引：每张表索引数不超过 8 个
```

### 10.2 核心查询索引优化

```sql
-- 高频查询 1：用户查看自己的小说列表（按创建时间倒序）
CREATE INDEX idx_novels_user_created ON novels(user_id, created_at DESC);

-- 高频查询 2：内容广场热门列表（公开+热度排序）
CREATE INDEX idx_public_hot ON public_contents(hot_score DESC, published_at DESC) 
    WHERE is_public = TRUE;

-- 高频查询 3：用户未读通知数量
CREATE INDEX idx_notifications_unread ON notifications(user_id) 
    WHERE is_read = FALSE;

-- 高频查询 4：待处理退款列表
CREATE INDEX idx_refunds_pending ON refunds(requested_at DESC) 
    WHERE status = 'pending';

-- 高频查询 5：用户当前有效订阅
CREATE INDEX idx_subscriptions_active ON user_subscriptions(user_id) 
    WHERE status = 'active';

-- 高频查询 6：配额检查（扣费前检查剩余配额）
CREATE INDEX idx_entitlements_check ON entitlements(subscription_id, resource_type)
    WHERE used_quota < total_quota;

-- 高频查询 7：按体裁查找专家建议
CREATE INDEX idx_advices_genre_active ON expert_advices USING gin(genre_tags)
    WHERE is_active = TRUE;

-- 高频查询 8：每日对账记录
CREATE INDEX idx_reconciliation_daily ON reconciliation_records(reconciliation_date DESC, gateway);
```

### 10.3 慢查询监控与索引维护

```sql
-- 开启慢查询日志
ALTER SYSTEM SET log_min_duration_statement = 200;  -- 200ms 以上记录

-- 查看未使用的索引
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY relname;

-- 查看索引膨胀
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- 定期 REINDEX（建议在低峰期）
-- REINDEX INDEX CONCURRENTLY idx_audit_logs_created_at;

-- 定期 VACUUM ANALYZE
-- VACUUM ANALYZE novels;
-- VACUUM ANALYZE videos;
```

### 10.4 分区表索引策略

```
分区表索引注意事项：
1. 每个分区自动继承父表索引定义
2. 全局唯一索引必须包含分区键
3. 本地索引优于全局索引（查询通常包含分区键）

推荐分区的表：
- audit_logs：按月分区（created_at）
- system_monitoring：按月分区（recorded_at）
- novel_generation_logs：按月分区（created_at）
- video_generation_logs：按月分区（created_at）
```

---

## 11. ER 关系总览

```
users ─┬── user_sessions
       ├── api_keys
       ├── orders ──── payment_records
       │           └── refunds
       │           └── invoices
       ├── consumption_records
       ├── novels ──── chapters
       │           └── novel_generation_logs
       │           └── advice_usage_records ── expert_advices
       ├── videos ──── video_segments
       │           └── video_generation_logs
       │           └── video_reviews
       │           └── memory_points
       ├── platform_accounts
       ├── publish_records ── platform_publish_details
       ├── user_subscriptions ── entitlements
       │   └── subscription_plans
       ├── public_contents ── content_interactions
       │                  └── content_reports
       ├── notifications
       ├── audit_logs
       ├── user_devices
       ├── channel_users
       └── reconciliation_records（独立，按日期+网关维度）

基础设施表（独立，无外键关联）：
├── task_queue          -- 任务队列（替代 RabbitMQ）
├── idempotent_keys     -- 幂等键（替代 Redis SETNX）
└── cache_entries       -- 持久化缓存（替代 Redis 缓存）

system_monitoring（独立，系统级监控）

文件存储（本地文件系统）：
/opt/ai-novel-agent/data/
├── novels/    videos/    audio/
├── covers/    exports/   temp/
└── backups/
```

---

> **文档版本**: v2.0（单机优化版：移除Redis/MinIO/Docker，适配1GB内存+20GB磁盘VPS）
> **最后更新**: 2026-04-01
> **设计状态**: 🗄️ 完成