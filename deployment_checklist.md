# AI小说生成Agent系统 - 部署检查清单

## 📋 部署前准备

### 服务器访问
- [ ] 确认服务器IP: 104.244.90.202
- [ ] 确认SSH端口: 22
- [ ] 确认用户名: root
- [ ] 准备SSH密钥或密码
- [ ] 测试SSH连接: `ssh root@104.244.90.202`

### 项目状态
- [ ] 确认Git仓库: https://github.com/xuzixiao198964-boop/ai-novel-agent
- [ ] 确认最新tag: `v1.0.0-documentation-complete`
- [ ] 确认部署路径: `/opt/ai-novel-agent`
- [ ] 确认服务名称: `ai-novel-agent`

### 备份计划
- [ ] 备份目录: `/opt/ai-novel-agent-backups`
- [ ] 备份命令: `tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz .`
- [ ] 备份验证: 检查备份文件大小和完整性

## 🚀 部署执行

### 步骤1: 连接到服务器
```bash
ssh root@104.244.90.202
cd /opt/ai-novel-agent
```

### 步骤2: 检查当前状态
- [ ] 检查服务状态: `systemctl status ai-novel-agent`
- [ ] 检查进程: `ps aux | grep uvicorn | grep -v grep`
- [ ] 检查端口: `netstat -tlnp | grep 9000`
- [ ] 检查日志: `tail -f /opt/ai-novel-agent/backend/logs/app.log`

### 步骤3: 创建备份
- [ ] 创建备份目录: `mkdir -p /opt/ai-novel-agent-backups`
- [ ] 执行备份: `tar -czf /opt/ai-novel-agent-backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz .`
- [ ] 验证备份: `ls -lh /opt/ai-novel-agent-backups/backup_*.tar.gz`

### 步骤4: 停止服务
- [ ] 停止服务: `systemctl stop ai-novel-agent`
- [ ] 确认停止: `systemctl status ai-novel-agent`
- [ ] 确认进程结束: `ps aux | grep uvicorn | grep -v grep`

### 步骤5: 更新代码
- [ ] 保存当前更改: `git stash`
- [ ] 拉取最新代码: `git pull origin master`
- [ ] 检查更新: `git log --oneline -3`
- [ ] 确认tag: `git tag -l`

### 步骤6: 安装依赖
- [ ] 进入backend目录: `cd backend`
- [ ] 检查requirements: `cat requirements.txt | head -20`
- [ ] 安装依赖: `/opt/ai-novel-agent/venv/bin/pip install -r requirements.txt`
- [ ] 验证安装: `/opt/ai-novel-agent/venv/bin/pip list | grep -E "(httpx|pydantic|fastapi)"`

### 步骤7: 启动服务
- [ ] 启动服务: `systemctl start ai-novel-agent`
- [ ] 检查状态: `systemctl status ai-novel-agent`
- [ ] 检查进程: `ps aux | grep uvicorn | grep -v grep`
- [ ] 检查端口: `netstat -tlnp | grep 9000`

## 🧪 部署后测试

### 基础测试
- [ ] 健康检查: `curl http://localhost:9000/api/health`
- [ ] 配置检查: `curl http://localhost:9000/api/config`
- [ ] 任务列表: `curl http://localhost:9000/api/tasks`

### 功能测试
- [ ] 创建测试任务: 
  ```bash
  curl -X POST http://localhost:9000/api/tasks \
    -H "Content-Type: application/json" \
    -d '{"name": "部署测试", "chapters": 3, "test_mode": true}'
  ```
- [ ] 启动任务: `curl -X POST http://localhost:9000/api/tasks/{task_id}/start`
- [ ] 监控进度: `curl http://localhost:9000/api/tasks/{task_id}`

### 性能测试
- [ ] 检查响应时间: `time curl -s http://localhost:9000/api/health > /dev/null`
- [ ] 检查内存使用: `ps aux | grep uvicorn | grep -v grep | awk '{print $4,$5,$6}'`
- [ ] 检查错误日志: `tail -20 /opt/ai-novel-agent/backend/logs/app.log`

## 🔧 问题排查

### 服务无法启动
1. 检查日志: `journalctl -u ai-novel-agent -f`
2. 手动启动调试:
   ```bash
   cd /opt/ai-novel-agent/backend
   /opt/ai-novel-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
   ```

### API无法访问
1. 检查服务状态: `systemctl status ai-novel-agent`
2. 检查端口监听: `netstat -tlnp | grep 9000`
3. 检查防火墙: `iptables -L -n | grep 9000`

### 依赖问题
1. 重新安装依赖:
   ```bash
   cd /opt/ai-novel-agent/backend
   /opt/ai-novel-agent/venv/bin/pip install --upgrade -r requirements.txt
   ```
2. 检查Python版本: `/opt/ai-novel-agent/venv/bin/python --version`

### 配置问题
1. 检查环境变量: `cat /opt/ai-novel-agent/backend/.env`
2. 检查配置文件: `cat /opt/ai-novel-agent/backend/app/core/config.py`

## 📊 监控指标

### 实时监控
- [ ] CPU使用率: `< 80%`
- [ ] 内存使用: `< 700MB`
- [ ] 磁盘空间: `> 1GB`
- [ ] 网络连接: `正常`

### 服务指标
- [ ] 响应时间: `< 2秒`
- [ ] 错误率: `< 5%`
- [ ] 可用性: `> 99%`

### 业务指标
- [ ] 任务完成率: `> 95%`
- [ ] 生成质量: `> 80分`
- [ ] 用户满意度: `> 4/5`

## 📝 文档更新

### 部署文档
- [ ] 更新部署步骤
- [ ] 记录遇到的问题
- [ ] 记录解决方案
- [ ] 更新配置说明

### 测试报告
- [ ] 记录测试结果
- [ ] 记录性能数据
- [ ] 记录发现的问题
- [ ] 记录改进建议

### 运维文档
- [ ] 更新监控指标
- [ ] 更新告警规则
- [ ] 更新应急预案
- [ ] 更新维护计划

## 🎯 完成标准

### 必须完成
- [ ] 服务正常运行
- [ ] API可正常访问
- [ ] 基础功能正常
- [ ] 性能指标达标

### 建议完成
- [ ] 完整流程测试通过
- [ ] 监控系统正常
- [ ] 文档更新完成
- [ ] 团队培训完成

## ⏰ 时间记录

### 开始时间
- 日期: ________
- 时间: ________

### 各阶段时间
1. 部署前准备: ________
2. 备份创建: ________
3. 代码更新: ________
4. 依赖安装: ________
5. 服务启动: ________
6. 基础测试: ________
7. 功能测试: ________
8. 性能测试: ________
9. 问题修复: ________
10. 文档更新: ________

### 结束时间
- 日期: ________
- 时间: ________

### 总耗时
- 总计: ________

## 👥 参与人员

### 部署团队
- 负责人: ________
- 开发人员: ________
- 测试人员: ________
- 运维人员: ________

### 联系方式
- 紧急联系人: ________
- 联系电话: ________
- 备用联系人: ________
- 备用电话: ________

## 📞 沟通记录

### 部署前沟通
- 时间: ________
- 内容: ________
- 参与人: ________

### 部署中沟通
- 时间: ________
- 内容: ________
- 参与人: ________

### 部署后沟通
- 时间: ________
- 内容: ________
- 参与人: ________

---

**检查人**: ________  
**检查日期**: ________  
**备注**: ________