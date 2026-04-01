# 部署和配置文档

## 1. 服务器环境要求

### 1.1 硬件要求
```
最低配置:
- CPU: 4核
- 内存: 8GB
- 存储: 100GB SSD
- 带宽: 100Mbps

推荐配置:
- CPU: 8核
- 内存: 16GB
- 存储: 200GB SSD
- 带宽: 1Gbps

生产环境:
- CPU: 16核
- 内存: 32GB
- 存储: 500GB SSD (RAID 1)
- 带宽: 1Gbps (独享)
```

### 1.2 软件要求
```
操作系统:
- Ubuntu 22.04 LTS (推荐)
- CentOS 8+
- Debian 11+

运行时环境:
- Python 3.9+
- Node.js 18+ (前端可选)
- Redis 7+
- PostgreSQL 15+
- Nginx 1.20+

Python包:
- FastAPI 0.104+
- SQLAlchemy 2.0+
- Celery 5.3+
- Redis-py 5.0+
- aiohttp 3.9+
- websockets 12.0+
```

## 2. 部署步骤

### 2.1 环境准备
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget vim htop net-tools

# 安装Python
sudo apt install -y python3.9 python3.9-dev python3.9-venv
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 安装Redis
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 安装Nginx
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 2.2 数据库配置
```bash
# 切换到postgres用户
sudo -i -u postgres

# 创建数据库和用户
psql -c "CREATE USER ai_novel_user WITH PASSWORD 'secure_password';"
psql -c "CREATE DATABASE ai_novel_media OWNER ai_novel_user;"
psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_novel_media TO ai_novel_user;"

# 退出postgres用户
exit
```

### 2.3 项目部署
```bash
# 创建项目目录
sudo mkdir -p /opt/ai-novel-media-agent
sudo chown $USER:$USER /opt/ai-novel-media-agent
cd /opt/ai-novel-media-agent

# 克隆代码
git clone https://github.com/your-repo/ai-novel-media-agent.git .

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

### 2.4 环境变量配置
```bash
# 创建环境变量文件
cat > .env << EOF
# 应用配置
APP_NAME="AI Novel Media Agent"
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your_secret_key_here
APP_URL=http://104.244.90.202:9000

# 数据库配置
DATABASE_URL=postgresql://ai_novel_user:secure_password@localhost:5432/ai_novel_media
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_POOL_SIZE=50

# AI服务配置
DEEPSEEK_API_KEY=sk-9fcc8f6d0ce94fdbbe66b152b7d3e485
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=sk-your-openai-key
TENCENT_CLOUD_SECRET_ID=your_tencent_secret_id
TENCENT_CLOUD_SECRET_KEY=your_tencent_secret_key

# 支付配置
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=your_alipay_private_key
ALIPAY_PUBLIC_KEY=your_alipay_public_key
WECHAT_APP_ID=your_wechat_app_id
WECHAT_MCH_ID=your_wechat_mch_id
WECHAT_API_KEY=your_wechat_api_key

# 存储配置
STORAGE_TYPE=local  # local/s3/oss
STORAGE_PATH=/opt/ai-novel-media-agent/data
MAX_UPLOAD_SIZE=104857600  # 100MB

# 安全配置
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=["http://localhost:3000", "http://104.244.90.202"]

# 性能配置
WORKER_COUNT=4
MAX_CONCURRENT_TASKS=10
TASK_TIMEOUT_SECONDS=3600
API_RATE_LIMIT=1000  # 每分钟请求数
EOF

# 设置文件权限
chmod 600 .env
```

### 2.5 数据库迁移
```bash
# 激活虚拟环境
source venv/bin/activate

# 运行数据库迁移
python -m alembic upgrade head

# 创建初始数据
python scripts/create_initial_data.py
```

### 2.6 服务配置

#### 2.6.1 Systemd服务文件
```bash
# 创建主服务文件
sudo tee /etc/systemd/system/ai-novel-media.service << EOF
[Unit]
Description=AI Novel Media Agent API Service
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/ai-novel-media-agent
Environment="PATH=/opt/ai-novel-media-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ai-novel-media-agent/.env
ExecStart=/opt/ai-novel-media-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000 --workers 4
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-media

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/ai-novel-media-agent/data

[Install]
WantedBy=multi-user.target
EOF

# 创建Celery Worker服务
sudo tee /etc/systemd/system/ai-novel-media-worker.service << EOF
[Unit]
Description=AI Novel Media Agent Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/ai-novel-media-agent
Environment="PATH=/opt/ai-novel-media-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ai-novel-media-agent/.env
ExecStart=/opt/ai-novel-media-agent/venv/bin/celery -A app.tasks worker --loglevel=info --concurrency=4
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-media-worker

[Install]
WantedBy=multi-user.target
EOF

# 创建Celery Beat服务（定时任务）
sudo tee /etc/systemd/system/ai-novel-media-beat.service << EOF
[Unit]
Description=AI Novel Media Agent Celery Beat
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=/opt/ai-novel-media-agent
Environment="PATH=/opt/ai-novel-media-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ai-novel-media-agent/.env
ExecStart=/opt/ai-novel-media-agent/venv/bin/celery -A app.tasks beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-media-beat

[Install]
WantedBy=multi-user.target
EOF
```

#### 2.6.2 Nginx配置
```bash
# 创建Nginx站点配置
sudo tee /etc/nginx/sites-available/ai-novel-media << EOF
server {
    listen 80;
    server_name 104.244.90.202;
    
    # 重定向到HTTPS（如果启用）
    # return 301 https://\$server_name\$request_uri;
    
    # 静态文件
    location /static/ {
        alias /opt/ai-novel-media-agent/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 媒体文件
    location /media/ {
        alias /opt/ai-novel-media-agent/data/media/;
        expires 1h;
        add_header Cache-Control "public";
        
        # 限制文件大小
        client_max_body_size 100M;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:9000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # 超时设置
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # 主页
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # 访问日志
    access_log /var/log/nginx/ai-novel-media-access.log;
    error_log /var/log/nginx/ai-novel-media-error.log;
}

# HTTPS配置（如果启用）
# server {
#     listen 443 ssl http2;
#     server_name 104.244.90.202;
#     
#     ssl_certificate /etc/letsencrypt/live/104.244.90.202/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/104.244.90.202/privkey.pem;
#     
#     # SSL配置
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
#     ssl_prefer_server_ciphers off;
#     ssl_session_cache shared:SSL:10m;
#     ssl_session_timeout 10m;
#     
#     # HSTS
#     add_header Strict-Transport-Security "max-age=63072000" always;
#     
#     # 其他配置与HTTP相同
#     ...
# }
EOF

# 启用站点
sudo ln -sf /etc/nginx/sites-available/ai-novel-media /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2.7 启动服务
```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ai-novel-media
sudo systemctl start ai-novel-media-worker
sudo systemctl start ai-novel-media-beat

# 设置开机自启
sudo systemctl enable ai-novel-media
sudo systemctl enable ai-novel-media-worker
sudo systemctl enable ai-novel-media-beat

# 检查服务状态
sudo systemctl status ai-novel-media
sudo systemctl status ai-novel-media-worker
sudo systemctl status ai-novel-media-beat
```

### 2.8 防火墙配置
```bash
# 启用防火墙
sudo ufw enable

# 开放必要端口
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS (如果启用)
sudo ufw allow 9000/tcp    # API端口

# 查看防火墙状态
sudo ufw status verbose
```

## 3. 监控和日志

### 3.1 日志配置
```python
# logging_config.py
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import os

def setup_logging():
    # 创建日志目录
    log_dir = "/var/log/ai-novel-media"
    os.makedirs(log_dir, exist_ok=True)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 文件处理器（按大小轮转）
    file_handler = RotatingFileHandler(
        f"{log_dir}/app.log",
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 错误日志单独文件
    error_handler = RotatingFileHandler(
        f"{log_dir}/error.log",
        maxBytes=10485760,
        backupCount=10
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    
    # 系统日志
    syslog_handler = SysLogHandler(address='/dev/log')
    syslog_handler.setFormatter(formatter)
    syslog_handler.setLevel(logging.WARNING)
    
    # 控制台输出（开发环境）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(syslog_handler)
    
    # 开发环境添加控制台输出
    if os.getenv('APP_ENV') == 'development':
        root_logger.addHandler(console_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)
```

### 3.2 监控配置

#### 3.2.1 Prometheus配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'ai-novel-media'
    static_configs:
      - targets: ['localhost:9000']
    metrics_path: '/metrics'
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
      
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['localhost:9187']
      
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['localhost:9121']
```

#### 3.2.2 Grafana仪表板
```json
{
  "dashboard": {
    "title": "AI Novel Media Agent监控",
    "panels": [
      {
        "title": "API请求率",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "任务队列长度",
        "targets": [
          {
            "expr": "celery_queue_length",
            "legendFormat": "{{queue}}"
          }
        ]
      },
      {
        "title": "用户余额分布",
        "targets": [
          {
            "expr": "user_balance",
            "legendFormat": "用户{{user_id}}"
          }
        ]
      }
    ]
  }
}
```

### 3.3 健康检查端点
```python
# health_check.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
