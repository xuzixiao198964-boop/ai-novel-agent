# 配置文件示例

## 1. 环境变量配置 (.env)

### 1.1 完整的环境变量配置
```bash
# ============================================
# AI Novel Media Agent 环境变量配置
# ============================================

# 应用基本信息
APP_NAME="AI Novel Media Agent"
APP_ENV="production"  # production/development/staging
APP_DEBUG="false"
APP_SECRET_KEY="your-secret-key-change-in-production"
APP_URL="http://104.244.90.202:9000"
APP_TIMEZONE="Asia/Shanghai"

# 数据库配置
DATABASE_URL="postgresql://ai_novel_user:secure_password@localhost:5432/ai_novel_media"
DATABASE_POOL_SIZE="20"
DATABASE_MAX_OVERFLOW="40"
DATABASE_POOL_RECYCLE="3600"
DATABASE_ECHO="false"

# Redis配置
REDIS_URL="redis://localhost:6379/0"
REDIS_PASSWORD=""
REDIS_POOL_SIZE="50"
REDIS_MAX_CONNECTIONS="1000"
REDIS_SOCKET_TIMEOUT="5"
REDIS_SOCKET_CONNECT_TIMEOUT="5"

# AI服务配置
# DeepSeek API
DEEPSEEK_API_KEY="sk-9fcc8f6d0ce94fdbbe66b152b7d3e485"
DEEPSEEK_BASE_URL="https://api.deepseek.com"
DEEPSEEK_MODEL="deepseek-chat"
DEEPSEEK_MAX_TOKENS="4096"
DEEPSEEK_TEMPERATURE="0.7"

# OpenAI API (备用)
OPENAI_API_KEY="sk-your-openai-key"
OPENAI_BASE_URL="https://api.openai.com/v1"
OPENAI_MODEL="gpt-4-turbo-preview"

# 腾讯云TTS
TENCENT_CLOUD_SECRET_ID="your_tencent_secret_id"
TENCENT_CLOUD_SECRET_KEY="your_tencent_secret_key"
TENCENT_TTS_REGION="ap-guangzhou"
TENCENT_TTS_VOICE_TYPE="101016"  # 智瑜-情感女声

# Edge TTS (备用)
EDGE_TTS_VOICE="zh-CN-XiaoxiaoNeural"
EDGE_TTS_RATE="+0%"
EDGE_TTS_VOLUME="+0%"

# 阿里云视频处理
ALIYUN_ACCESS_KEY_ID="your_aliyun_access_key_id"
ALIYUN_ACCESS_KEY_SECRET="your_aliyun_access_key_secret"
ALIYUN_REGION="cn-hangzhou"

# 支付配置
# 支付宝
ALIPAY_APP_ID="your_alipay_app_id"
ALIPAY_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
ALIPAY_SIGN_TYPE="RSA2"
ALIPAY_NOTIFY_URL="${APP_URL}/api/v1/payment/callback/alipay"

# 微信支付
WECHAT_APP_ID="your_wechat_app_id"
WECHAT_MCH_ID="your_wechat_mch_id"
WECHAT_API_KEY="your_wechat_api_key"
WECHAT_CERT_PATH="/path/to/wechat/cert.pem"
WECHAT_KEY_PATH="/path/to/wechat/key.pem"
WECHAT_NOTIFY_URL="${APP_URL}/api/v1/payment/callback/wechat"

# 抖音支付
DOUYIN_APP_ID="your_douyin_app_id"
DOUYIN_MCH_ID="your_douyin_mch_id"
DOUYIN_SALT="your_douyin_salt"
DOUYIN_TOKEN="your_douyin_token"
DOUYIN_NOTIFY_URL="${APP_URL}/api/v1/payment/callback/douyin"

# 存储配置
STORAGE_TYPE="local"  # local/s3/oss/minio
STORAGE_PATH="/opt/ai-novel-media-agent/data"
MAX_UPLOAD_SIZE="104857600"  # 100MB

# S3存储 (如果使用)
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
AWS_REGION="us-east-1"
AWS_BUCKET_NAME="ai-novel-media"
AWS_ENDPOINT_URL=""  # 留空使用AWS，或指定MinIO地址

# 阿里云OSS (如果使用)
OSS_ACCESS_KEY_ID="your_oss_access_key"
OSS_ACCESS_KEY_SECRET="your_oss_secret_key"
OSS_ENDPOINT="oss-cn-hangzhou.aliyuncs.com"
OSS_BUCKET_NAME="ai-novel-media"

# 安全配置
JWT_SECRET_KEY="your-jwt-secret-key-change-in-production"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES="60"
JWT_REFRESH_TOKEN_EXPIRE_DAYS="30"
JWT_REFRESH_TOKEN_COOKIE_NAME="refresh_token"
JWT_REFRESH_TOKEN_COOKIE_SECURE="true"

CORS_ORIGINS='["http://localhost:3000", "http://104.244.90.202", "https://your-domain.com"]'
CORS_ALLOW_CREDENTIALS="true"
CORS_ALLOW_METHODS='["GET", "POST", "PUT", "DELETE", "OPTIONS"]'
CORS_ALLOW_HEADERS='["*"]'

# 速率限制
RATE_LIMIT_ENABLED="true"
RATE_LIMIT_DEFAULT="1000/minute"
RATE_LIMIT_AUTHENTICATED="5000/minute"
RATE_LIMIT_API_KEY="10000/minute"

# 性能配置
WORKER_COUNT="4"  # Uvicorn workers
CELERY_WORKER_COUNT="4"
CELERY_MAX_TASKS_PER_CHILD="1000"
CELERY_TASK_TIME_LIMIT="3600"  # 1小时
CELERY_TASK_SOFT_TIME_LIMIT="3000"  # 50分钟

MAX_CONCURRENT_NOVEL_TASKS="5"
MAX_CONCURRENT_VIDEO_TASKS="3"
TASK_QUEUE_MAX_LENGTH="100"

# 缓存配置
CACHE_ENABLED="true"
CACHE_DEFAULT_TTL="300"  # 5分钟
CACHE_USER_TTL="1800"  # 30分钟
CACHE_NOVEL_TTL="3600"  # 1小时
CACHE_VIDEO_TTL="7200"  # 2小时

# 邮件配置
SMTP_ENABLED="true"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_FROM_NAME="AI Novel Media Agent"
SMTP_FROM_EMAIL="noreply@ai-novel-media.com"
SMTP_USE_TLS="true"

# 短信配置 (可选)
SMS_ENABLED="false"
SMS_PROVIDER="aliyun"  # aliyun/tencent/twilio
SMS_ACCESS_KEY="your_sms_access_key"
SMS_SECRET_KEY="your_sms_secret_key"
SMS_SIGN_NAME="AI创作"
SMS_TEMPLATE_CODE="SMS_123456789"

# 监控配置
PROMETHEUS_ENABLED="true"
PROMETHEUS_PORT="9001"
SENTRY_DSN=""  # Sentry错误监控
LOG_LEVEL="INFO"
LOG_FORMAT="json"  # json/text

# 业务配置
# 价格配置
PRICE_NOVEL_MICRO="0.50"
PRICE_NOVEL_SHORT="2.00"
PRICE_NOVEL_MEDIUM="8.00"
PRICE_NOVEL_LONG="20.00"
PRICE_NOVEL_SUPER="50.00"

PRICE_VIDEO_VOICE_ONLY="0.50"
PRICE_VIDEO_SUBTITLE_ONLY="0.80"
PRICE_VIDEO_ANIMATION="2.00"
PRICE_VIDEO_MIXED="3.00"

PRICE_PUBLISH_NOVEL="0.10"
PRICE_PUBLISH_VIDEO="0.20"

SERVICE_FEE_RATE="0.15"  # 15%服务费

# 内容配置
MAX_NOVEL_CHAPTERS="200"
MAX_NOVEL_WORDS_PER_CHAPTER="5000"
MIN_NOVEL_CONFLICT_SCORE="7.0"
MIN_VIDEO_QUALITY_SCORE="7.5"

# 审核配置
AUTO_REVIEW_ENABLED="true"
MANUAL_REVIEW_THRESHOLD="8.0"  # 低于此分数需要人工审核
SENSITIVE_WORDS_FILE="/path/to/sensitive_words.txt"

# 发布配置
AUTO_PUBLISH_ENABLED="false"
PUBLISH_RETRY_COUNT="3"
PUBLISH_RETRY_DELAY="60"  # 秒

# 平台API配置
# 抖音开放平台
DOUYIN_OPEN_API_KEY="your_douyin_open_api_key"
DOUYIN_OPEN_API_SECRET="your_douyin_open_api_secret"
DOUYIN_OPEN_REDIRECT_URI="${APP_URL}/api/v1/publish/callback/douyin"

# 小红书开放平台
XIAOHONGSHU_APP_KEY="your_xiaohongshu_app_key"
XIAOHONGSHU_APP_SECRET="your_xiaohongshu_app_secret"
XIAOHONGSHU_REDIRECT_URI="${APP_URL}/api/v1/publish/callback/xiaohongshu"

# B站开放平台
BILIBILI_APP_KEY="your_bilibili_app_key"
BILIBILI_APP_SECRET="your_bilibili_app_secret"
BILIBILI_REDIRECT_URI="${APP_URL}/api/v1/publish/callback/bilibili"

# 微信开放平台
WECHAT_OPEN_APP_ID="your_wechat_open_app_id"
WECHAT_OPEN_APP_SECRET="your_wechat_open_app_secret"
WECHAT_OPEN_REDIRECT_URI="${APP_URL}/api/v1/publish/callback/wechat"

# 开发配置 (仅在开发环境设置)
# DEBUG_TOOLBAR_ENABLED="true"
# SQL_ECHO="true"
# CELERY_ALWAYS_EAGER="true"
```

### 1.2 开发环境配置 (.env.development)
```bash
# 开发环境配置
APP_ENV="development"
APP_DEBUG="true"
APP_URL="http://localhost:9000"

# 数据库
DATABASE_URL="postgresql://ai_novel_user:dev_password@localhost:5432/ai_novel_media_dev"

# Redis
REDIS_URL="redis://localhost:6379/1"

# AI服务 (使用测试密钥)
DEEPSEEK_API_KEY="sk-test-key-for-development"
OPENAI_API_KEY="sk-test-openai-key"

# 支付 (测试模式)
ALIPAY_APP_ID="沙箱APP_ID"
ALIPAY_PRIVATE_KEY="沙箱私钥"
ALIPAY_PUBLIC_KEY="沙箱公钥"
ALIPAY_GATEWAY="https://openapi.alipaydev.com/gateway.do"

WECHAT_APP_ID="沙箱APP_ID"
WECHAT_MCH_ID="沙箱商户号"
WECHAT_API_KEY="沙箱API密钥"

# 存储
STORAGE_PATH="./data"

# 安全
JWT_SECRET_KEY="dev-secret-key-only-for-development"
CORS_ORIGINS='["http://localhost:3000", "http://localhost:8080"]'

# 性能
WORKER_COUNT="2"
CELERY_WORKER_COUNT="2"

# 日志
LOG_LEVEL="DEBUG"
LOG_FORMAT="text"

# 开发工具
DEBUG_TOOLBAR_ENABLED="true"
SQL_ECHO="true"
```

## 2. Docker Compose配置 (docker-compose.yml)

### 2.1 完整的生产环境配置
```yaml
version: '3.8'

services:
  # 主API服务
  api:
    build: .
    image: ai-novel-media-agent:latest
    container_name: ai-novel-media-api
    restart: unless-stopped
    ports:
      - "9000:9000"
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - db
      - redis
    networks:
      - ai-novel-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Celery Worker
  celery-worker:
    build: .
    image: ai-novel-media-agent:latest
    container_name: ai-novel-media-worker
    restart: unless-stopped
    command: celery -A app.tasks worker --loglevel=info --concurrency=4
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - db
      - redis
      - api
    networks:
      - ai-novel-network

  # Celery Beat (定时任务)
  celery-beat:
    build: .
    image: ai-novel-media-agent:latest
    container_name: ai-novel-media-beat
    restart: unless-stopped
    command: celery -A app.tasks beat --loglevel=info
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - db
      - redis
    networks:
      - ai-novel-network

  # PostgreSQL数据库
  db:
    image: postgres:15-alpine
    container_name: ai-novel-media-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - ai-novel-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: ai-novel-media-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - ai-novel-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: ai-novel-media-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./ssl:/etc/nginx/ssl
      - ./data/media:/var/www/media:ro
    depends_on:
      - api
    networks:
      - ai-novel-network

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: ai-novel-media-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    networks:
      - ai-novel-network

  # Grafana仪表板
  grafana:
    image: grafana/grafana:latest
    container_name: ai-novel-media-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus
    networks:
      - ai-novel-network

  # MinIO对象存储 (可选)
  minio:
    image: minio/minio:latest
    container_name: ai-novel-media-minio
    restart: unless-stopped
    ports