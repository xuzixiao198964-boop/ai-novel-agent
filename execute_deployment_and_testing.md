# AI小说生成Agent系统 - 部署与测试执行计划

## 🎯 执行目标
基于详细设计文档、概要设计和需求文档，将现有代码部署到104.244.90.202服务器，并进行完整的测试验证。

## 📋 当前状态
- **服务器**: 104.244.90.202:9000 (运行中)
- **项目状态**: 文档体系完成，代码需要更新
- **Git状态**: 最新tag `v1.0.0-documentation-complete`

## 🚀 执行步骤

### 阶段1: 本地代码审查与准备 (已完成)
1. ✅ 审查现有代码结构
2. ✅ 创建新增模块框架
3. ✅ 准备部署脚本
4. ✅ 准备测试脚本

### 阶段2: 服务器部署
```bash
# 步骤1: 连接到服务器
ssh root@104.244.90.202

# 步骤2: 备份当前项目
cd /opt/ai-novel-agent
tar -czf /opt/backup_ai_novel_agent_$(date +%Y%m%d_%H%M%S).tar.gz .

# 步骤3: 停止服务
systemctl stop ai-novel-agent

# 步骤4: 更新代码
cd /opt/ai-novel-agent
git stash
git pull origin master

# 步骤5: 安装依赖
cd backend
/opt/ai-novel-agent/venv/bin/pip install -r requirements.txt

# 步骤6: 启动服务
systemctl start ai-novel-agent
systemctl status ai-novel-agent
```

### 阶段3: 基础功能测试
```bash
# 在服务器上运行基础测试
cd /opt/ai-novel-agent/backend
/opt/ai-novel-agent/venv/bin/python tests/unit/test_basic_functionality.py

# 或者使用pytest
/opt/ai-novel-agent/venv/bin/pytest tests/unit/test_basic_functionality.py -v
```

### 阶段4: API功能测试
```bash
# 使用测试脚本验证API
cd /opt/ai-novel-agent
python test_after_deployment.py
```

### 阶段5: 完整流程测试
```bash
# 创建测试任务并监控
curl -X POST http://localhost:9000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"name": "完整流程测试", "chapters": 3, "test_mode": true}'

# 获取任务ID并启动
task_id="获取的任务ID"
curl -X POST http://localhost:9000/api/tasks/$task_id/start

# 监控进度
curl http://localhost:9000/api/tasks/$task_id
```

## 🧪 测试验证点

### 1. 基础功能验证
- [ ] 配置加载正常
- [ ] LLM模块正常工作
- [ ] 所有Agent可正常导入
- [ ] 数据结构完整

### 2. API端点验证
- [ ] `/api/health` 返回正常
- [ ] `/api/config` 返回配置
- [ ] `/api/tasks` 可创建和查询任务
- [ ] 任务状态流转正常

### 3. 完整流程验证
- [ ] TrendAgent生成趋势分析
- [ ] StyleAgent解析风格参数
- [ ] PlannerAgent生成故事总纲
- [ ] WriterAgent生成章节内容
- [ ] PolishAgent润色内容
- [ ] AuditorAgent审核质量
- [ ] ReviserAgent修订问题

### 4. 性能基准验证
- [ ] 3章批次生成时间 ≤6.5分钟
- [ ] 内存使用峰值 <700MB
- [ ] 错误率 <5%
- [ ] 任务完成率 ≥95%

## 🔧 问题处理流程

### 发现问题时:
1. **记录问题**: 详细描述问题现象
2. **定位原因**: 查看日志，分析错误
3. **本地修复**: 在开发环境修复问题
4. **测试验证**: 本地测试修复效果
5. **重新部署**: 更新服务器代码
6. **重新测试**: 验证问题是否解决

### 常见问题处理:
1. **依赖问题**:
   ```bash
   # 重新安装依赖
   /opt/ai-novel-agent/venv/bin/pip install --upgrade -r requirements.txt
   ```

2. **配置问题**:
   ```bash
   # 检查配置文件
   cat /opt/ai-novel-agent/backend/.env
   # 检查config.py
   cat /opt/ai-novel-agent/backend/app/core/config.py
   ```

3. **服务启动问题**:
   ```bash
   # 查看服务日志
   journalctl -u ai-novel-agent -f
   # 手动启动调试
   cd /opt/ai-novel-agent/backend
   /opt/ai-novel-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
   ```

## 📊 监控与验证

### 实时监控:
```bash
# 查看服务状态
systemctl status ai-novel-agent

# 查看实时日志
tail -f /opt/ai-novel-agent/backend/logs/app.log

# 监控系统资源
top -p $(pgrep -f "uvicorn.*9000")
```

### 性能监控:
```bash
# 检查内存使用
ps aux | grep uvicorn | grep -v grep

# 检查磁盘空间
df -h /opt/

# 检查网络连接
netstat -tlnp | grep 9000
```

## 📝 测试报告生成

### 测试完成后生成报告:
```python
# 运行测试并生成报告
cd /opt/ai-novel-agent
python test_after_deployment.py > test_report_$(date +%Y%m%d_%H%M%S).txt

# 检查测试结果
cat test_report_*.txt | grep -E "(✓|✗|通过|失败)"
```

### 报告内容应包括:
1. **测试时间**: 开始和结束时间
2. **测试环境**: 服务器配置、代码版本
3. **测试结果**: 每个测试点的通过/失败状态
4. **性能数据**: 生成时间、内存使用等
5. **发现问题**: 发现的问题和修复情况
6. **建议**: 改进建议和下一步计划

## 🎯 成功标准

### 必须通过:
- [ ] 所有基础功能测试通过
- [ ] 所有API端点正常工作
- [ ] 完整流程可执行完成
- [ ] 性能指标达到基准要求

### 建议通过:
- [ ] 新增模块功能正常
- [ ] 监控告警系统工作
- [ ] 差异化审核功能正常
- [ ] 数据源管理功能正常

## ⚠️ 风险与应对

### 高风险:
1. **部署失败导致服务中断**
   - 应对: 完整备份，快速回滚方案
   
2. **代码不兼容导致功能异常**
   - 应对: 分阶段部署，充分测试

3. **性能不达标影响使用**
   - 应对: 性能监控，及时优化

### 中风险:
1. **依赖版本冲突**
   - 应对: 使用虚拟环境，固定版本

2. **配置错误**
   - 应对: 配置检查脚本，配置验证

3. **数据丢失**
   - 应对: 数据备份，恢复测试

## 📅 时间估算

| 阶段 | 任务 | 时间估算 | 状态 |
|------|------|----------|------|
| 1 | 代码审查与准备 | 2小时 | ✅ 已完成 |
| 2 | 服务器部署 | 1小时 | 🔄 待执行 |
| 3 | 基础功能测试 | 1小时 | 🔄 待执行 |
| 4 | API功能测试 | 2小时 | 🔄 待执行 |
| 5 | 完整流程测试 | 3小时 | 🔄 待执行 |
| 6 | 问题修复与优化 | 3小时 | 🔄 待执行 |
| 7 | 最终验证与报告 | 1小时 | 🔄 待执行 |
| **总计** | | **13小时** | |

## 🚨 紧急联系人

- **系统管理员**: 负责服务器访问和部署
- **开发人员**: 负责代码修复和优化
- **测试人员**: 负责测试执行和验证
- **项目经理**: 负责协调和决策

## 📞 沟通计划

1. **部署开始前**: 通知所有相关人员
2. **部署过程中**: 实时更新进度
3. **发现问题时**: 立即通知开发人员
4. **测试完成后**: 发送测试报告
5. **项目完成时**: 总结会议

---

**执行建议**: 建议在业务低峰期执行部署和测试，确保有足够的时间处理可能出现的问题。建议分两天执行：第一天部署和基础测试，第二天完整流程测试和优化。