# 直接部署命令

## 服务器信息
- IP: 10.66.66.3
- 端口: 22
- 用户名: root
- 密码: （由你本地保管，勿提交到 Git）
- 项目路径: /opt/ai-novel-agent
- 服务名称: ai-novel-agent
- API端口: 9000

## 部署步骤命令

### 1. 连接到服务器
```bash
ssh root@10.66.66.3
# 提示时输入 root 密码（或配置 SSH 公钥免密）
```

### 2. 检查当前状态
```bash
# 检查服务状态
systemctl status ai-novel-agent

# 检查磁盘空间
df -h /opt/

# 检查项目大小
du -sh /opt/ai-novel-agent/

# 检查API健康
curl http://localhost:9000/api/health
```

### 3. 上传部署包（从本地机器执行）
```bash
# 在您的本地机器上执行
scp -r deploy_package root@10.66.66.3:/tmp/
# 提示时输入 root 密码
```

### 4. 在服务器上执行部署

#### 4.1 创建备份
```bash
# 创建备份目录
mkdir -p /opt/ai-novel-agent-backups

# 创建时间戳备份
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cd /opt/ai-novel-agent
tar -czf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz .

# 验证备份
ls -lh /opt/ai-novel-agent-backups/
```

#### 4.2 停止服务
```bash
systemctl stop ai-novel-agent
sleep 3

# 确认停止
systemctl status ai-novel-agent
```

#### 4.3 更新代码
```bash
# 备份现有配置和虚拟环境
cp /opt/ai-novel-agent/backend/.env /tmp/.env.backup 2>/dev/null || true
mv /opt/ai-novel-agent/backend/venv /tmp/venv.backup 2>/dev/null || true

# 清空当前目录
cd /opt/ai-novel-agent
find . -maxdepth 1 ! -name '.' ! -name '..' ! -name 'deploy_package' -exec rm -rf {} + 2>/dev/null || true

# 复制新代码
cp -r /tmp/deploy_package/* /opt/ai-novel-agent/

# 恢复虚拟环境
if [ -d "/tmp/venv.backup" ]; then
    rm -rf /opt/ai-novel-agent/backend/venv
    mv /tmp/venv.backup /opt/ai-novel-agent/backend/venv
fi

# 恢复配置
if [ -f "/tmp/.env.backup" ]; then
    cp /tmp/.env.backup /opt/ai-novel-agent/backend/.env
    rm /tmp/.env.backup
fi
```

#### 4.4 安装依赖
```bash
cd /opt/ai-novel-agent/backend
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装requirements.txt中的依赖
pip install -r requirements.txt

# 安装新模块的依赖
pip install numpy scikit-learn

# 检查安装结果
pip list | grep -E "numpy|scikit-learn|pydantic|fastapi|httpx" | head -10
```

#### 4.5 启动服务
```bash
systemctl start ai-novel-agent
sleep 5

# 检查服务状态
systemctl status ai-novel-agent

# 确认服务运行
systemctl is-active ai-novel-agent
```

### 5. 验证部署

#### 5.1 等待服务完全启动
```bash
sleep 10
```

#### 5.2 运行基础测试
```bash
cd /opt/ai-novel-agent
python test_after_deployment.py
```

#### 5.3 验证新模块
```bash
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "
import sys
sys.path.insert(0, '.')

modules_to_test = [
    ('app.agents.trend.data_source_manager', 'DataSourceManager'),
    ('app.agents.trend.similarity_calculator', 'SentenceBERTSimilarity'),
    ('app.agents.planner.differentiated_reviewer', 'DifferentiatedReviewSystem')
]

all_passed = True
for module_path, class_name in modules_to_test:
    try:
        exec(f'from {module_path} import {class_name}')
        print(f'[OK] {class_name} 导入成功')
    except Exception as e:
        print(f'[ERROR] {class_name} 导入失败: {e}')
        all_passed = False

if all_passed:
    print('\\n[OK] 所有新模块导入成功')
else:
    print('\\n[ERROR] 部分模块导入失败')
"
```

#### 5.4 测试API端点
```bash
# 测试健康检查
curl http://localhost:9000/api/health

# 测试配置端点
curl http://localhost:9000/api/config | head -5

# 测试任务创建
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"部署验证测试","chapters":3,"genre":"都市现实"}'
```

### 6. 运行集成测试

#### 6.1 创建集成测试任务
```bash
TASK_RESPONSE=$(curl -s -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"集成测试-3章","chapters":3,"genre":"都市现实","description":"验证完整流程"}')

echo "任务创建响应: $TASK_RESPONSE"

# 提取任务ID
TASK_ID=$(echo "$TASK_RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$TASK_ID" ]; then
    echo "集成测试任务ID: $TASK_ID"
else
    echo "无法提取任务ID"
    exit 1
fi
```

#### 6.2 监控任务执行
```bash
# 监控30分钟（每30秒检查一次）
for i in {1..60}; do
    TASK_STATUS=$(curl -s http://localhost:9000/api/tasks/$TASK_ID)
    
    if echo "$TASK_STATUS" | grep -q '"status":"completed"'; then
        echo "[OK] 集成测试任务完成"
        break
    elif echo "$TASK_STATUS" | grep -q '"status":"failed"'; then
        echo "[ERROR] 集成测试任务失败"
        echo "任务状态: $TASK_STATUS"
        break
    elif echo "$TASK_STATUS" | grep -q '"status":"stopped"'; then
        echo "[ERROR] 集成测试任务停止"
        echo "任务状态: $TASK_STATUS"
        break
    fi
    
    echo "任务执行中... ($i/60)"
    sleep 30
done
```

### 7. 部署完成验证

#### 7.1 最终检查
```bash
# 检查服务状态
systemctl status ai-novel-agent

# 检查API健康
curl http://localhost:9000/api/health

# 检查新模块
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "from app.agents.trend.data_source_manager import DataSourceManager; print('[OK] 数据源管理器导入成功')"

# 检查任务列表
curl http://localhost:9000/api/tasks | head -5
```

#### 7.2 部署成功标志
如果以下所有检查都通过，则部署成功：
1. ✅ 服务状态: active (running)
2. ✅ API健康检查: {"status":"ok"}
3. ✅ 新模块导入: 所有模块可导入
4. ✅ 基础测试: 测试脚本通过
5. ✅ 集成测试: 3章任务完成

### 8. 问题诊断

#### 如果服务启动失败
```bash
# 查看错误日志
journalctl -u ai-novel-agent -n 100

# 检查端口占用
netstat -tlnp | grep 9000

# 手动启动调试
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

#### 如果模块导入失败
```bash
# 检查Python路径
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "import sys; print(sys.path)"

# 检查模块文件
ls -la /opt/ai-novel-agent/backend/app/agents/trend/
ls -la /opt/ai-novel-agent/backend/app/agents/planner/

# 重新安装依赖
pip install -r requirements.txt
pip install numpy scikit-learn
```

#### 如果API无法访问
```bash
# 检查服务是否运行
systemctl status ai-novel-agent

# 检查防火墙
iptables -L -n | grep 9000

# 检查进程
ps aux | grep ai-novel-agent
```

### 9. 回滚方案（如果部署失败）

```bash
# 停止服务
systemctl stop ai-novel-agent

# 找到最新备份
LATEST_BACKUP=$(ls -t /opt/ai-novel-agent-backups/backup_*.tar.gz | head -1)

# 恢复备份
cd /opt/ai-novel-agent
rm -rf *
tar -xzf "$LATEST_BACKUP"

# 启动服务
systemctl start ai-novel-agent

# 验证回滚
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
```

## 一键部署脚本

### 在服务器上执行的一键部署脚本
```bash
#!/bin/bash
# 一键部署脚本

set -e

echo "开始部署..."

# 1. 创建备份
mkdir -p /opt/ai-novel-agent-backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cd /opt/ai-novel-agent
tar -czf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz .

# 2. 停止服务
systemctl stop ai-novel-agent || true
sleep 3

# 3. 更新代码
cp /opt/ai-novel-agent/backend/.env /tmp/.env.backup 2>/dev/null || true
mv /opt/ai-novel-agent/backend/venv /tmp/venv.backup 2>/dev/null || true
cd /opt/ai-novel-agent && find . -maxdepth 1 ! -name '.' ! -name '..' ! -name 'deploy_package' -exec rm -rf {} + 2>/dev/null || true
cp -r /tmp/deploy_package/* /opt/ai-novel-agent/
if [ -d "/tmp/venv.backup" ]; then rm -rf /opt/ai-novel-agent/backend/venv; mv /tmp/venv.backup /opt/ai-novel-agent/backend/venv; fi
if [ -f "/tmp/.env.backup" ]; then cp /tmp/.env.backup /opt/ai-novel-agent/backend/.env; rm /tmp/.env.backup; fi

# 4. 安装依赖
cd /opt/ai-novel-agent/backend
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install numpy scikit-learn

# 5. 启动服务
systemctl start ai-novel-agent
sleep 10

# 6. 验证部署
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
cd /opt/ai-novel-agent && python test_after_deployment.py

echo "部署完成!"
```

## 部署成功后的地址
- **服务地址**: http://10.66.66.3:9000
- **API文档**: http://10.66.66.3:9000/docs
- **健康检查**: http://10.66.66.3:9000/api/health
- **任务API**: http://10.66.66.3:9000/api/tasks

## 注意事项
1. 部署前确保服务器有足够的磁盘空间
2. 部署过程中服务会暂时中断
3. 集成测试可能需要15-30分钟完成
4. 如果遇到问题，参考问题诊断部分
5. 部署失败时使用回滚方案恢复