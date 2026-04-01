# AI小说生成Agent系统 - 快速部署指南

## 🚀 3分钟快速开始

### 第一步：上传部署包到服务器
```bash
# 在您的本地机器上执行
scp -r deploy_package root@104.244.90.202:/tmp/
# 输入密码，等待上传完成
```

### 第二步：连接到服务器并执行部署
```bash
# 连接到服务器
ssh root@104.244.90.202
# 输入密码登录

# 切换到项目目录
cd /opt/ai-novel-agent

# 复制部署脚本并执行
cp /tmp/deploy_package/execute_deployment.sh .
chmod +x execute_deployment.sh
./execute_deployment.sh
```

### 第三步：验证部署结果
```bash
# 验证服务状态
systemctl status ai-novel-agent

# 验证API健康
curl http://localhost:9000/api/health

# 验证新模块
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "from app.agents.trend.data_source_manager import DataSourceManager; print('✅ 导入成功')"
```

## 📋 详细部署步骤

### 1. 准备阶段 (2分钟)
```bash
# 检查服务器状态
ssh root@104.244.90.202 "systemctl status ai-novel-agent; df -h /opt/"

# 上传部署包
scp -r deploy_package root@104.244.90.202:/tmp/

# 验证上传
ssh root@104.244.90.202 "ls -la /tmp/deploy_package/; du -sh /tmp/deploy_package/"
```

### 2. 执行阶段 (15分钟)
```bash
# 连接到服务器
ssh root@104.244.90.202

# 执行一键部署
cd /opt/ai-novel-agent
cp /tmp/deploy_package/execute_deployment.sh .
chmod +x execute_deployment.sh
./execute_deployment.sh

# 脚本会自动执行以下步骤：
# 1. 检查服务状态
# 2. 创建备份
# 3. 停止服务
# 4. 更新代码
# 5. 安装依赖
# 6. 启动服务
# 7. 验证部署
```

### 3. 验证阶段 (10分钟)
```bash
# 验证1: 服务状态
systemctl status ai-novel-agent

# 验证2: API功能
curl http://localhost:9000/api/health
curl http://localhost:9000/api/config | head -5

# 验证3: 新模块
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "
from app.agents.trend.data_source_manager import DataSourceManager
from app.agents.trend.similarity_calculator import SentenceBERTSimilarity
from app.agents.planner.differentiated_reviewer import DifferentiatedReviewSystem
print('✅ 所有新模块导入成功')
"

# 验证4: 创建测试任务
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "快速部署验证",
    "chapters": 3,
    "genre": "都市现实"
  }'
```

## 🔧 新功能快速测试

### 测试数据源管理器
```bash
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "
import asyncio
from app.agents.trend.data_source_manager import DataSourceManager

async def test():
    manager = DataSourceManager()
    print('✅ 数据源管理器初始化成功')
    status = manager.get_source_status()
    print(f'数据源状态: {status}')

asyncio.run(test())
"
```

### 测试相似度计算
```bash
python -c "
from app.agents.trend.similarity_calculator import SentenceBERTSimilarity

calc = SentenceBERTSimilarity()
result = calc.calculate_similarity('都市现实', '都市言情')
print(f'相似度: {result.similarity:.3f}')
print(f'是否相似: {result.is_similar}')
"
```

### 测试差异化审核
```bash
python -c "
from app.agents.planner.differentiated_reviewer import DifferentiatedReviewSystem

reviewer = DifferentiatedReviewSystem()
print('✅ 差异化审核系统初始化成功')
"
```

## ⚠️ 常见问题快速解决

### 问题1: 部署脚本权限错误
```bash
# 修复权限
chmod +x execute_deployment.sh
chmod +x deploy_check.sh
```

### 问题2: 服务启动失败
```bash
# 查看错误日志
journalctl -u ai-novel-agent -n 50

# 常见解决方法
systemctl daemon-reload
systemctl restart ai-novel-agent
```

### 问题3: 模块导入失败
```bash
# 检查Python路径
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -c "import sys; print(sys.path)"

# 重新安装依赖
pip install -r requirements.txt
pip install numpy scikit-learn
```

### 问题4: API无法访问
```bash
# 检查端口
netstat -tlnp | grep 9000

# 检查服务状态
systemctl status ai-novel-agent

# 手动启动调试
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

## 🔄 快速回滚方案

### 如果部署失败需要回滚
```bash
# 1. 停止服务
systemctl stop ai-novel-agent

# 2. 找到最新备份
LATEST_BACKUP=$(ls -t /opt/ai-novel-agent-backups/backup_*.tar.gz | head -1)

# 3. 恢复备份
cd /opt/ai-novel-agent
rm -rf *
tar -xzf "$LATEST_BACKUP"

# 4. 启动服务
systemctl start ai-novel-agent

# 5. 验证回滚
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
```

## 📊 部署后监控

### 基础监控命令
```bash
# 实时监控日志
journalctl -u ai-novel-agent -f

# 监控资源使用
watch -n 30 "ps aux | grep ai-novel-agent | grep -v grep"

# 监控API响应
watch -n 60 "curl -s -o /dev/null -w '%{http_code} %{time_total}s' http://localhost:9000/api/health"
```

### 性能测试命令
```bash
# 创建性能测试任务
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "性能测试-3章",
    "chapters": 3,
    "genre": "都市现实"
  }'

# 监控执行时间 (目标: ≤6.5分钟)
time curl -s http://localhost:9000/api/tasks/{task_id} > /dev/null
```

## 🎯 成功验证清单

### 部署后立即检查
- [ ] `systemctl status ai-novel-agent` 显示 active (running)
- [ ] `curl http://localhost:9000/api/health` 返回 {"status":"ok"}
- [ ] 新模块导入测试全部通过
- [ ] `python test_after_deployment.py` 测试通过

### 功能验证检查
- [ ] 可以创建新任务 (返回任务ID)
- [ ] 任务状态查询正常
- [ ] 各Agent输出文件正常生成
- [ ] 配置文件加载正常

### 性能基准检查 (24小时内)
- [ ] 3章任务完成时间 ≤6.5分钟
- [ ] 内存使用峰值 <700MB
- [ ] 无严重错误日志
- [ ] API响应时间正常

## 📞 紧急支持

### 遇到问题时执行
```bash
# 1. 查看错误日志
journalctl -u ai-novel-agent -n 100

# 2. 检查服务状态
systemctl status ai-novel-agent

# 3. 检查端口占用
netstat -tlnp | grep 9000

# 4. 检查配置文件
cat /opt/ai-novel-agent/backend/.env | head -10
```

### 需要进一步协助
- 参考: `deploy_package/README.md`
- 详细日志: `journalctl -u ai-novel-agent -f`
- 部署文档: `execute_deployment_final.md`

## 🏁 部署完成标志

### 技术完成标志
- ✅ 服务稳定运行1小时无错误
- ✅ 所有API端点正常响应
- ✅ 新功能模块工作正常
- ✅ 性能指标达到基准

### 业务完成标志
- ✅ 可以正常创建和执行任务
- ✅ 生成的小说文件完整
- ✅ 系统响应时间满足要求
- ✅ 监控告警系统正常工作

---

## 🚀 最终执行命令总结

### 最简单的完整部署流程
```bash
# 1. 上传部署包
scp -r deploy_package root@104.244.90.202:/tmp/

# 2. 连接到服务器
ssh root@104.244.90.202

# 3. 执行一键部署
cd /opt/ai-novel-agent
cp /tmp/deploy_package/execute_deployment.sh .
chmod +x execute_deployment.sh
./execute_deployment.sh

# 4. 验证部署
systemctl status ai-novel-agent
curl http://localhost:9000/api/health
cd backend && source venv/bin/activate
python -c "from app.agents.trend.data_source_manager import DataSourceManager; print('✅ 成功')"
```

### 分步验证命令
```bash
# 验证服务
systemctl status ai-novel-agent

# 验证API
curl http://localhost:9000/api/health

# 验证模块
cd /opt/ai-novel-agent/backend
source venv/bin/activate
python test_new_modules_simple.py

# 创建测试
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"测试","chapters":3,"genre":"都市现实"}'
```

---

**部署状态**: 🟢 **准备就绪**
**预计耗时**: **20-30分钟**
**成功概率**: ⭐⭐⭐⭐⭐ **5/5星**
**风险等级**: 🟡 **中等 (有完整备份)**

**现在可以开始部署！** 🎉

---

*快速指南版本: v1.0*
*目标服务器: 104.244.90.202*
*部署包: deploy_package/*
*一键脚本: execute_deployment.sh*