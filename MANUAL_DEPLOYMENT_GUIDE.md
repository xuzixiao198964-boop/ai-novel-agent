# AI小说生成Agent系统 - 裸机部署指南

## 概述
将AI小说生成Agent系统从Docker迁移到裸机Ubuntu服务器，直接在服务器上运行Python服务，使用9000端口。

## 服务器信息
- IP地址: `104.244.90.202`
- 用户名: `root`
- 当前密码: 需要确认（原密码 `C66ffUMycDn2` 可能已失效）
- 项目目录: `/opt/ai-novel-agent-bare`

## 部署步骤

### 步骤1: 登录服务器
```bash
ssh root@104.244.90.202
```

### 步骤2: 更新系统并安装基础依赖
```bash
# 更新系统
apt-get update
apt-get upgrade -y

# 安装基础工具
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    supervisor \
    curl \
    wget \
    vim

# 升级pip
pip3 install --upgrade pip
```

### 步骤3: 创建项目目录
```bash
# 创建项目目录
mkdir -p /opt/ai-novel-agent-bare
cd /opt/ai-novel-agent-bare

# 创建子目录结构
mkdir -p backend/data
mkdir -p backend/logs
mkdir -p backend/static
mkdir -p scripts
mkdir -p deploy

# 设置权限
chmod 755 /opt/ai-novel-agent-bare
```

### 步骤4: 上传项目文件
从本地机器上传文件到服务器：

#### 方法A: 使用scp（从本地执行）
```bash
# 从Windows PowerShell执行
cd E:\work\ai-novel-agent

# 上传后端代码
scp -r backend\* root@104.244.90.202:/opt/ai-novel-agent-bare/backend/

# 上传脚本
scp -r scripts\* root@104.244.90.202:/opt/ai-novel-agent-bare/scripts/

# 上传部署脚本
scp -r deploy\* root@104.244.90.202:/opt/ai-novel-agent-bare/deploy/

# 上传配置文件
scp README.md root@104.244.90.202:/opt/ai-novel-agent-bare/
```

#### 方法B: 直接在服务器上克隆（如果有Git访问）
```bash
cd /opt/ai-novel-agent-bare
git clone <repository-url> .
# 或者从本地复制后上传
```

### 步骤5: 创建环境配置文件
```bash
cd /opt/ai-novel-agent-bare/backend

# 创建.env文件
cat > .env << 'EOF'
# DeepSeek API 配置
MOCK_LLM=0
LLM_PROVIDER=openai_compatible
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=sk-7bfa809eeac74e168ee642d4e71b0958
LLM_MODEL=deepseek-chat

# 服务配置
AGENT_INTERVAL_SECONDS=2.0
STEP_INTERVAL_SECONDS=0.5
PORT=9000

# 数据目录
DATA_DIR=/opt/ai-novel-agent-bare/backend/data
LOG_DIR=/opt/ai-novel-agent-bare/backend/logs

# 可选：网页密码保护
# WEB_PASSWORD=your_password_here
EOF

# 设置权限
chmod 600 .env
```

### 步骤6: 设置Python虚拟环境
```bash
cd /opt/ai-novel-agent-bare/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境并安装依赖
source venv/bin/activate

# 安装基础依赖
pip install --upgrade pip
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest

# 退出虚拟环境
deactivate
```

### 步骤7: 测试服务运行
```bash
cd /opt/ai-novel-agent-bare/backend

# 临时运行服务测试
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# 在另一个终端测试
curl http://localhost:9000/api/health
# 应该返回: {"status":"ok"}
```

### 步骤8: 创建Systemd服务
```bash
# 创建服务文件
cat > /etc/systemd/system/ai-novel-agent.service << 'EOF'
[Unit]
Description=AI Novel Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent-bare/backend
Environment="PATH=/opt/ai-novel-agent-bare/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ai-novel-agent-bare/backend/.env
ExecStart=/opt/ai-novel-agent-bare/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-agent

[Install]
WantedBy=multi-user.target
EOF

# 重载systemd配置
systemctl daemon-reload

# 启用并启动服务
systemctl enable ai-novel-agent.service
systemctl start ai-novel-agent.service

# 检查服务状态
systemctl status ai-novel-agent.service

# 查看日志
journalctl -u ai-novel-agent.service -f
```

### 步骤9: 配置Nginx反向代理（可选）
```bash
# 创建Nginx配置
cat > /etc/nginx/sites-available/ai-novel-agent << 'EOF'
server {
    listen 80;
    server_name 104.244.90.202;
    
    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /opt/ai-novel-agent-bare/backend/static/;
    }
}
EOF

# 启用站点
ln -sf /etc/nginx/sites-available/ai-novel-agent /etc/nginx/sites-enabled/

# 测试Nginx配置
nginx -t

# 重启Nginx
systemctl restart nginx
```

### 步骤10: 清理Docker残留（如果存在）
```bash
# 停止并删除Docker容器
docker stop $(docker ps -a -q --filter "name=ai-novel-agent") 2>/dev/null || true
docker rm $(docker ps -a -q --filter "name=ai-novel-agent") 2>/dev/null || true

# 停止Docker服务（如果不使用Docker）
systemctl stop docker 2>/dev/null || true
systemctl disable docker 2>/dev/null || true

# 清理旧的项目目录（如果存在）
rm -rf /opt/ai-novel-agent 2>/dev/null || true
```

### 步骤11: 防火墙配置
```bash
# 允许9000端口
ufw allow 9000/tcp
ufw allow 80/tcp  # 如果使用Nginx
ufw reload
```

## 验证部署

### 测试API端点
```bash
# 健康检查
curl http://104.244.90.202:9000/api/health

# 获取配置
curl http://104.244.90.202:9000/api/config

# 创建测试任务
curl -X POST http://104.244.90.202:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name": "测试任务"}'
```

### 检查服务状态
```bash
# 查看服务状态
systemctl status ai-novel-agent.service

# 查看实时日志
journalctl -u ai-novel-agent.service -f

# 检查端口监听
ss -tlnp | grep :9000

# 检查进程
ps aux | grep uvicorn
```

## 故障排除

### 常见问题1: 端口被占用
```bash
# 检查哪个进程占用9000端口
lsof -i :9000
ss -tlnp | grep :9000

# 如果被占用，停止相关进程
kill <PID>
```

### 常见问题2: Python依赖问题
```bash
cd /opt/ai-novel-agent-bare/backend
source venv/bin/activate

# 重新安装依赖
pip install --force-reinstall -r requirements.txt

# 检查Python版本
python --version
```

### 常见问题3: 权限问题
```bash
# 检查目录权限
ls -la /opt/ai-novel-agent-bare/

# 修复权限
chown -R root:root /opt/ai-novel-agent-bare/
chmod -R 755 /opt/ai-novel-agent-bare/backend/data
chmod -R 755 /opt/ai-novel-agent-bare/backend/logs
```

### 常见问题4: DeepSeek API连接失败
```bash
# 在服务器上测试API连通性
curl -X POST https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-7bfa809eeac74e168ee642d4e71b0958" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-chat", "messages": [{"role": "user", "content": "test"}], "max_tokens": 5}'
```

## 维护命令

### 重启服务
```bash
systemctl restart ai-novel-agent.service
```

### 停止服务
```bash
systemctl stop ai-novel-agent.service
```

### 查看日志
```bash
# 查看全部日志
journalctl -u ai-novel-agent.service

# 查看最近100行
journalctl -u ai-novel-agent.service -n 100

# 实时查看日志
journalctl -u ai-novel-agent.service -f
```

### 更新代码
```bash
# 停止服务
systemctl stop ai-novel-agent.service

# 备份当前代码
cp -r /opt/ai-novel-agent-bare /opt/ai-novel-agent-bare-backup-$(date +%Y%m%d)

# 上传新代码（从本地）
# scp -r backend\* root@104.244.90.202:/opt/ai-novel-agent-bare/backend/

# 重启服务
systemctl start ai-novel-agent.service
```

## 安全建议

1. **更改SSH密码**: 部署完成后更改root密码
2. **使用SSH密钥**: 禁用密码登录，使用SSH密钥
3. **防火墙配置**: 只开放必要端口
4. **定期更新**: 定期更新系统和Python包
5. **日志监控**: 设置日志监控和告警
6. **备份**: 定期备份项目数据和配置

## 联系支持
如有问题，请参考项目README或联系维护人员。