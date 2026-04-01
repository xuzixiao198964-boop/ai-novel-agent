# AI Novel Media Agent 数据库详细设计

## 设计信息
- **设计阶段**: 详细设计 - 数据库设计
- **设计日期**: 2026-04-01
- **设计模型**: Claude 3.5 Sonnet (via Cursor)
- **工程方法**: OpenClaw软件工程化全流程
- **设计状态**: 🗄️ 进行中

## 1. 数据库设计原则

### 1.1 设计目标
```
1. 数据一致性：保证数据准确性和完整性
2. 性能优化：支持高并发访问
3. 可扩展性：支持数据量增长
4. 安全性：数据安全存储和访问
5. 可维护性：清晰的表结构和关系
```

### 1.2 技术选型
```
主数据库：PostgreSQL 15
- 理由：功能丰富，ACID支持完善，JSONB支持好

缓存数据库：Redis 7
- 理由：性能优秀，数据结构丰富，持久化支持

文件存储：MinIO/S3
- 理由：对象存储，扩展性好，成本可控

监控数据库：TimescaleDB (可选)
- 理由：时序数据优化，监控数据存储
```

## 2. 数据库架构设计

### 2.1 数据库分库分表策略
```
分库策略：
1. 业务分库：
   - 用户库：用户相关数据
   - 内容库：小说、视频等内容数据
   - 交易库：支付、订单等交易数据
   - 日志库：操作日志、系统日志

2. 读写分离：
   - 主库：写操作
   - 从库：读操作
   - 只读副本：报表和分析查询

分表策略：
1. 水平分表：
   - 按用户ID分表：用户相关表
   - 按时间分表：日志表、监控表
   - 按类型分表：内容表

2. 垂直分表：
   - 热点字段分离：频繁访问字段单独存储
   - 大字段分离：文本、JSON等大字段单独存储
```

### 2.2 数据库连接池配置
```
连接池配置：
- 最大连接数：100
- 最小连接数：10
- 连接超时：30秒
- 空闲超时：10分钟
- 测试查询：SELECT 1

服务连接分配：
- 用户服务：20连接
- 小说服务：30连接
- 视频服务：20连接
- 支付服务：15连接
- 发布服务：15连接
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

## 4. Redis 缓存 Key 设计

### 4.1 Key 命名规范

```
命名格式：{业务域}:{子域}:{标识}
分隔符：冒号 (:)
所有 key 必须设置 TTL，防止内存泄漏
```

### 4.2 会话缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `session:{session_id}` | Hash | 30min | 用户会话数据：user_id, role, ip, device |
| `session:user:{user_id}` | Set | 30min | 用户所有活跃 session_id 集合 |
| `session:refresh:{refresh_token}` | String | 7d | refresh_token → session_id 映射 |

```redis
-- 示例：存储会话
HSET session:abc123 user_id "uuid-xxx" role "user" ip "1.2.3.4"
EXPIRE session:abc123 1800

-- 示例：查询用户所有会话
SMEMBERS session:user:uuid-xxx
```

### 4.3 限流缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `rate:{api_path}:{user_id}` | String(counter) | 1min | API 调用频率限制 |
| `rate:login:{ip}` | String(counter) | 15min | 登录尝试频率限制 |
| `rate:captcha:{phone}` | String(counter) | 1h | 验证码发送频率限制 |
| `rate:global:{api_path}` | String(counter) | 1s | 全局 API QPS 限制 |

```redis
-- 示例：滑动窗口限流
INCR rate:/api/novels:uuid-xxx
EXPIRE rate:/api/novels:uuid-xxx 60

-- 限流配置参考：
-- 普通用户：60次/分钟
-- VIP用户：120次/分钟
-- 企业用户：600次/分钟
```

### 4.4 任务进度缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `task:novel:{novel_id}` | Hash | 24h | 小说生成进度：progress, agent, chapter, status |
| `task:video:{video_id}` | Hash | 24h | 视频生成进度：progress, step, status |
| `task:publish:{publish_id}` | Hash | 12h | 发布任务进度 |
| `task:queue:priority:{level}` | Sorted Set | 永久 | 优先级任务队列 |

```redis
-- 示例：更新小说生成进度
HSET task:novel:uuid-xxx progress 45 agent "WriterAgent" chapter 3 status "running"
EXPIRE task:novel:uuid-xxx 86400

-- 示例：优先级队列
ZADD task:queue:priority:high <timestamp> "novel:uuid-xxx"
```

### 4.5 余额与配额缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `balance:{user_id}` | String | 5min | 用户余额缓存（短TTL保证一致性） |
| `quota:{user_id}:novel_words` | Hash | 10min | 小说字数配额：total, used |
| `quota:{user_id}:video_minutes` | Hash | 10min | 视频分钟配额 |
| `quota:{user_id}:publish_count` | Hash | 10min | 发布次数配额 |

```redis
-- 示例：余额缓存（读时写入，写时失效）
SET balance:uuid-xxx "158.50" EX 300
-- 扣费后立即删除缓存
DEL balance:uuid-xxx
```

### 4.6 热点数据缓存

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `content:hot:list` | Sorted Set | 5min | 内容广场热门列表 |
| `content:detail:{content_id}` | Hash | 10min | 内容详情缓存 |
| `plan:list` | String(JSON) | 1h | 套餐列表缓存 |
| `advice:pool:{genre}` | List | 30min | 按体裁的建议池 |

---

## 5. 数据迁移策略

### 5.1 从单库到商业化架构的迁移路径

```
阶段一：表结构扩展（低风险）
├── 1. 新增套餐/订阅/权益相关表
├── 2. 新增退款/对账表
├── 3. 新增内容广场相关表
├── 4. 新增通知/审计表
└── 5. 新增多端渠道表

阶段二：数据迁移（中风险）
├── 1. 现有用户补充默认免费套餐订阅记录
├── 2. 历史订单数据补充 invoice 关联
├── 3. 已发布内容同步到 public_contents
└── 4. 现有设备信息迁移到 user_devices

阶段三：读写切换（高风险）
├── 1. 双写模式：新旧表同时写入
├── 2. 灰度验证：10% → 50% → 100% 流量切换
├── 3. 旧表降级为只读
└── 4. 清理旧表冗余字段
```

### 5.2 迁移脚本模板

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

### 5.3 回滚方案

```
每次迁移前：
1. 完整数据库备份（pg_dump）
2. 记录当前 schema 版本号
3. 准备回滚 SQL 脚本

回滚执行：
1. 停止应用写入
2. 执行回滚 SQL
3. 恢复应用
4. 验证数据完整性
```

---

## 6. 备份与归档策略

### 6.1 备份策略

```
全量备份：
- 频率：每日 03:00（低峰期）
- 方式：pg_dump --format=custom
- 保留：最近 30 天
- 存储：本地 + 异地对象存储（S3/MinIO）

增量备份：
- 频率：每小时
- 方式：WAL 日志归档
- 保留：最近 7 天
- 用途：时间点恢复（PITR）

逻辑备份：
- 频率：每周日 03:00
- 方式：pg_dump --format=plain
- 保留：最近 12 周
- 用途：跨版本迁移、审计
```

### 6.2 归档策略

```
冷数据归档规则：
1. audit_logs：超过 90 天的记录迁移到归档表/外部存储
2. system_monitoring：超过 30 天的记录按月压缩归档
3. novel_generation_logs / video_generation_logs：超过 60 天归档
4. content_interactions：已删除内容的互动记录 30 天后清除

归档实现：
- 使用 PostgreSQL 表分区 + 分区拆卸（DETACH PARTITION）
- 冷数据导出为 Parquet 格式存入对象存储
- 保留归档索引表用于历史查询

示例（审计日志月度归档）：
ALTER TABLE audit_logs DETACH PARTITION audit_logs_2026_01;
-- 导出为 Parquet 后删除分区表
```

### 6.3 数据保留策略

| 数据类型 | 热数据（在线） | 温数据（近线） | 冷数据（归档） |
|----------|---------------|---------------|---------------|
| 用户数据 | 永久 | - | 注销后 180 天 |
| 订单/支付 | 2 年 | 2-5 年 | 5 年+ |
| 小说/视频 | 永久 | - | 用户删除后 30 天 |
| 审计日志 | 90 天 | 90天-1年 | 1-5 年 |
| 监控数据 | 30 天 | 30-90 天 | 90 天后丢弃 |
| 通知 | 30 天 | 30-90 天 | 90 天后丢弃 |

---

## 7. 索引优化说明

### 7.1 索引设计原则

```
1. 覆盖索引优先：高频查询字段组合建立复合索引
2. 部分索引优化：WHERE 子句过滤低基数字段
3. JSONB 索引：使用 GIN 索引加速 JSON 字段查询
4. 数组索引：使用 GIN 索引加速数组字段包含查询
5. 避免过度索引：每张表索引数不超过 8 个
```

### 7.2 核心查询索引优化

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

### 7.3 慢查询监控与索引维护

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

### 7.4 分区表索引策略

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

## 8. ER 关系总览

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

system_monitoring（独立，系统级监控）
```

---

> **文档版本**: v1.0
> **最后更新**: 2026-04-01
> **设计状态**: 🗄️ 完成