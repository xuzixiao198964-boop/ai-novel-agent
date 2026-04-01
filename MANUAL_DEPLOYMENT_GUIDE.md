# AI小说生成Agent系统 - 手动部署执行指南

## 🎯 部署目标
将增强的新功能模块部署到104.244.90.202服务器，替换现有项目，并进行全面测试。

## 📋 部署前检查清单

### 1. 服务器状态确认 (执行以下命令)
```bash
# 连接到服务器
ssh root@104.244.90.202

# 检查服务状态
systemctl status ai-novel-agent
# 预期: active (running) - PID: 698317

# 检查磁盘空间
df -h /opt/
# 预期: 有足够空间（当前: 已用12G/19G）

# 检查项目大小
du -sh /opt/ai-novel-agent/
# 预期: ~360MB

# 检查Python环境
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python --version
# 预期: Python 3.x

# 检查API健康
curl http://localhost:9000/api/health
# 预期: {"status":"ok"}
```

### 2. 本地准备确认
```bash
# 确认部署包存在
ls -la deploy_package/
# 预期: 包含backend/, config/, test_after_deployment.py等

# 确认部署包大小
du -sh deploy_package/
# 预期: ~25MB
```

## 🚀 部署执行步骤

### 步骤1: 上传部署包到服务器
```bash
# 从您的本地机器执行（替换{password}为实际密码）
scp -r deploy_package root@104.244.90.202:/tmp/
# 输入密码后等待上传完成
```

### 步骤2: 连接到服务器并执行部署
```bash
# 连接到服务器
ssh root@104.244.90.202
# 输入密码登录
```

### 步骤3: 备份当前项目
```bash
# 在服务器上执行
cd /opt/ai-novel-agent

# 创建时间戳备份
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/ai-novel-agent-backups

# 备份整个项目
tar -czf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz .

echo "备份完成: /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz"
echo "备份大小: $(du -h /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz | cut -f1)"
```

### 步骤4: 停止服务
```bash
# 停止ai-novel-agent服务
systemctl stop ai-novel-agent

# 确认服务已停止
systemctl status ai-novel-agent
# 预期: inactive (dead)
```

### 步骤5: 更新代码
```bash
# 备份现有配置和虚拟环境
cp /opt/ai-novel-agent/backend/.env /tmp/.env.backup 2>/dev/null || true
mv /opt/ai-novel-agent/backend/venv /tmp/venv.backup 2>/dev/null || true

# 清空项目目录（保留备份）
rm -rf /opt/ai-novel-agent/*

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

echo "代码更新完成"
```

### 步骤6: 安装依赖
```bash
cd /opt/ai-novel-agent/backend

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装requirements.txt中的依赖
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "基础依赖安装完成"
fi

# 安装新模块的依赖
echo "安装新模块依赖..."
pip install numpy scikit-learn || echo "注意: numpy/scikit-learn安装可能需要额外处理"

# 检查安装结果
pip list | grep -E "numpy|scikit-learn|pydantic|fastapi"
```

### 步骤7: 启动服务
```bash
# 启动服务
systemctl start ai-novel-agent

# 等待5秒让服务启动
sleep 5

# 检查服务状态
systemctl status ai-novel-agent --no-pager

# 确认服务运行
if systemctl is-active --quiet ai-novel-agent; then
    echo "✅ 服务启动成功"
else
    echo "❌ 服务启动失败，查看日志:"
    journalctl -u ai-novel-agent -n 50
    exit 1
fi
```

### 步骤8: 等待服务完全启动
```bash
echo "等待服务完全启动..."
sleep 10

# 检查API是否可访问
API_RESPONSE=$(curl -s http://localhost:9000/api/health || echo "API不可访问")
echo "API健康检查: $API_RESPONSE"
```

## 🧪 部署后验证

### 验证1: 运行基础测试
```bash
cd /opt/ai-novel-agent

# 运行部署后测试脚本
if [ -f "test_after_deployment.py" ]; then
    echo "运行部署后测试..."
    python test_after_deployment.py
    
    if [ $? -eq 0 ]; then
        echo "✅ 基础测试通过"
    else
        echo "⚠️ 基础测试失败，但继续验证其他功能"
    fi
else
    echo "⚠️ 测试脚本不存在，跳过基础测试"
fi
```

### 验证2: 手动测试新模块
```bash
cd /opt/ai-novel-agent/backend
source venv/bin/activate

# 测试新模块导入
echo "测试新模块导入..."
python -c "
try:
    from app.agents.trend.data_source_manager import DataSourceManager
    from app.agents.trend.similarity_calculator import SentenceBERTSimilarity
    from app.agents.planner.differentiated_reviewer import DifferentiatedReviewSystem
    print('✅ 新模块导入成功')
except Exception as e:
    print(f'❌ 模块导入失败: {e}')
    import traceback
    traceback.print_exc()
"
```

### 验证3: API功能测试
```bash
# 测试健康检查API
echo "测试API端点..."
curl -s http://localhost:9000/api/health | python -m json.tool

# 测试配置API
curl -s http://localhost:9000/api/config | python -m json.tool | head -20

# 测试任务列表API
curl -s http://localhost:9000/api/tasks | python -m json.tool | head -20
```

### 验证4: 创建测试任务
```bash
# 创建3章测试任务
echo "创建测试任务..."
TASK_JSON='{
  "title": "部署验证测试",
  "description": "验证新功能部署后的系统",
  "chapters": 3,
  "genre": "都市现实"
}'

TASK_RESPONSE=$(curl -s -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d "$TASK_JSON")

echo "任务创建响应: $TASK_RESPONSE"

# 提取任务ID
TASK_ID=$(echo "$TASK_RESPONSE" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$TASK_ID" ]; then
    echo "✅ 测试任务创建成功，ID: $TASK_ID"
    
    # 检查任务状态
    echo "等待10秒后检查任务状态..."
    sleep 10
    curl -s http://localhost:9000/api/tasks/$TASK_ID | python -m json.tool
else
    echo "❌ 测试任务创建失败"
fi
```

## 📊 性能监控测试

### 监控1: 检查服务资源使用
```bash
echo "检查服务资源使用..."
# 获取服务PID
SERVICE_PID=$(systemctl show ai-novel-agent --property=MainPID | cut -d= -f2)

if [ "$SERVICE_PID" -gt 0 ]; then
    echo "服务PID: $SERVICE_PID"
    
    # 检查内存使用
    ps -p $SERVICE_PID -o pid,ppid,cmd,%mem,%cpu,rss,vsz --no-headers
    
    # 实时监控（运行10秒）
    echo "实时监控10秒..."
    top -b -n 10 -p $SERVICE_PID | grep $SERVICE_PID
else
    echo "无法获取服务PID"
fi
```

### 监控2: 检查日志
```bash
echo "检查最近日志..."
journalctl -u ai-novel-agent --since "5 minutes ago" --no-pager | tail -50
```

### 监控3: 检查生成的文件
```bash
echo "检查生成的文件..."
if [ -n "$TASK_ID" ]; then
    TASK_DIR="/opt/ai-novel-agent/backend/data/tasks/$TASK_ID"
    if [ -d "$TASK_DIR" ]; then
        echo "任务目录内容:"
        find "$TASK_DIR" -type f -name "*.md" -o -name "*.json" | head -10
        
        echo "文件详情:"
        ls -la "$TASK_DIR"/output/* 2>/dev/null || echo "输出目录尚未生成"
    fi
fi
```

## ⚠️ 问题诊断与修复

### 常见问题1: 服务启动失败
```bash
# 查看详细错误
journalctl -u ai-novel-agent -n 100 --no-pager

# 检查端口占用
netstat -tlnp | grep 9000

# 检查配置文件
cat /opt/ai-novel-agent/backend/.env | head -20

# 手动启动调试
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### 常见问题2: 模块导入失败
```bash
# 检查Python路径
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "import sys; print(sys.path)"

# 检查模块文件
ls -la /opt/ai-novel-agent/backend/app/agents/trend/
ls -la /opt/ai-novel-agent/backend/app/agents/planner/

# 测试单个模块
python -c "from app.agents.trend.data_source_manager import DataSourceManager; print('DataSourceManager导入成功')"
```

### 常见问题3: 依赖安装失败
```bash
# 检查pip版本
pip --version

# 更新pip
pip install --upgrade pip

# 尝试单独安装
pip install numpy --no-cache-dir
pip install scikit-learn --no-cache-dir

# 检查已安装的包
pip list | grep -i "numpy\|scikit"
```

## 🔄 回滚操作（如果需要）

### 快速回滚到备份
```bash
# 停止服务
systemctl stop ai-novel-agent

# 找到最新的备份文件
LATEST_BACKUP=$(ls -t /opt/ai-novel-agent-backups/backup_*.tar.gz | head -1)
echo "恢复备份: $LATEST_BACKUP"

# 清空当前目录
cd /opt/ai-novel-agent
rm -rf *

# 恢复备份
tar -xzf "$LATEST_BACKUP"

# 启动服务
systemctl start ai-novel-agent

# 验证回滚
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
```

## 📝 部署完成检查清单

### 必须完成的项目
- [ ] 服务正常启动并运行
- [ ] API健康检查通过
- [ ] 新模块可以成功导入
- [ ] 基础测试脚本通过
- [ ] 可以创建新任务

### 建议完成的验证
- [ ] 任务可以正常执行
- [ ] 各Agent输出文件正常生成
- [ ] 内存使用在正常范围内（<700MB）
- [ ] 错误日志没有严重错误

### 性能监控项目
- [ ] 3章批次执行时间 ≤6.5分钟
- [ ] 系统响应时间正常
- [ ] 并发处理能力正常

## 🎯 部署完成后的操作

### 1. 监控运行状态（至少2小时）
```bash
# 持续监控日志
journalctl -u ai-novel-agent -f

# 定期检查资源使用
watch -n 30 "ps aux | grep ai-novel-agent | grep -v grep"
```

### 2. 创建完整的测试任务
```bash
# 创建18章完整测试任务
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "完整功能测试",
    "description": "测试18章完整流程",
    "chapters": 18,
    "genre": "玄幻奇幻"
  }'
```

### 3. 更新部署文档
记录部署过程中的：
- 实际执行时间
- 遇到的问题和解决方案
- 性能测试结果
- 建议的优化点

## 📞 紧急联系方式

### 遇到问题时
1. **服务完全无法启动**: 立即回滚到备份
2. **功能异常但服务运行**: 检查日志，尝试修复配置
3. **性能不达标**: 监控资源使用，考虑优化

### 需要支持时
- 查看详细部署文档: `deploy_package/README.md`
- 检查部署计划: `execute_deployment_final.md`
- 参考问题诊断部分

---

## 🏁 部署执行命令总结

### 快速部署命令序列
```bash
# 1. 上传部署包
scp -r deploy_package root@104.244.90.202:/tmp/

# 2. 连接到服务器并执行
ssh root@104.244.90.202

# 3. 在服务器上执行以下命令序列:
cd /opt/ai-novel-agent
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz .
systemctl stop ai-novel-agent
cp -r /tmp/deploy_package/* /opt/ai-novel-agent/
cd /opt/ai-novel-agent/backend && source venv/bin/activate && pip install -r requirements.txt
systemctl start ai-novel-agent
sleep 10
python test_after_deployment.py
```

### 验证命令
```bash
# 验证部署
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
cd /opt/ai-novel-agent/backend && source venv/bin/activate && python -c "from app.agents.trend.data_source_manager import DataSourceManager; print('导入成功')"
```

---

**部署状态**: 🟢 准备就绪  
**预计耗时**: 30-60分钟  
**风险等级**: 🟡 中等（有完整备份）  
**成功概率**: 🟢 高  

**现在可以开始执行部署！** 🚀

---

*最后更新: 2026-03-26*  
*部署版本: 1.0.0*  
*目标服务器: 104.244.90.202*  
*部署包: deploy_package/*