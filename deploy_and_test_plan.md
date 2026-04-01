# AI小说生成Agent系统 - 部署与测试计划

## 1. 目标
基于详细设计文档、概要设计和需求文档，全面审查现有代码，部署到104.244.90.202服务器，并进行完整的单元测试和集成测试。

## 2. 当前服务器状态
- **服务器**: 104.244.90.202:9000
- **服务状态**: 运行中 (PID: 698317)
- **API状态**: 健康检查通过，配置接口有500错误
- **磁盘空间**: 19G总空间，已用12G，可用6.3G
- **项目大小**: 360MB

## 3. 部署策略

### 3.1 备份现有项目
```bash
# 在服务器上执行
cd /opt/ai-novel-agent
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz .
```

### 3.2 代码审查与更新
基于详细设计文档，需要更新的模块：

#### **需要新增的模块**
1. **TrendAgent增强**:
   - `data_source_manager.py` - 多平台数据源管理
   - `similarity_calculator.py` - 相似度计算
   - `quality_validator.py` - 数据质量验证
   - `fallback_handler.py` - 降级处理

2. **PlannerAgent增强**:
   - `differentiated_reviewer.py` - 差异化审核器
   - `genre_type_detector.py` - 题材类型检测器

3. **新增Agent**:
   - `MonitorAgent/` - 监控Agent
   - `AlertAgent/` - 告警Agent

#### **需要更新的现有模块**
1. **config.py** - 添加新配置项
2. **trend.py** - 集成数据源管理
3. **planner.py** - 集成差异化审核
4. **所有Agent** - 添加监控指标收集

### 3.3 部署步骤
```bash
# 步骤1: 停止当前服务
systemctl stop ai-novel-agent

# 步骤2: 备份当前代码
cd /opt/ai-novel-agent
git stash
git pull origin master

# 步骤3: 安装新依赖
cd backend
/opt/ai-novel-agent/venv/bin/pip install -r requirements.txt

# 步骤4: 启动服务
systemctl start ai-novel-agent
systemctl status ai-novel-agent
```

## 4. 测试策略

### 4.1 单元测试 (基于测试文档)
```bash
# 运行所有单元测试
cd backend
/opt/ai-novel-agent/venv/bin/pytest tests/unit/ -v

# 重点测试模块
/opt/ai-novel-agent/venv/bin/pytest tests/unit/test_trend_data_source_manager.py -v
/opt/ai-novel-agent/venv/bin/pytest tests/unit/test_planner_differentiated_reviewer.py -v
/opt/ai-novel-agent/venv/bin/pytest tests/unit/test_monitoring_alert_system.py -v
```

### 4.2 集成测试
```bash
# 完整流水线测试
cd backend
/opt/ai-novel-agent/venv/bin/pytest tests/integration/test_full_pipeline.py -v

# 3章批次测试
/opt/ai-novel-agent/venv/bin/pytest tests/integration/test_3chapter_batch.py -v

# 监控告警测试
/opt/ai-novel-agent/venv/bin/pytest tests/integration/test_monitoring_alert.py -v
```

### 4.3 性能测试
```bash
# 基于服务器基准的性能测试
cd backend
/opt/ai-novel-agent/venv/bin/pytest tests/performance/test_batch_performance.py -v

# 并发测试
/opt/ai-novel-agent/venv/bin/pytest tests/performance/test_concurrency.py -v

# 内存使用测试
/opt/ai-novel-agent/venv/bin/pytest tests/performance/test_memory_usage.py -v
```

## 5. 问题修复流程

### 5.1 问题分类
1. **严重问题** (阻止部署):
   - 编译错误
   - 关键依赖缺失
   - 配置错误

2. **功能问题** (需要修复):
   - 单元测试失败
   - 接口不兼容
   - 逻辑错误

3. **性能问题** (需要优化):
   - 超出性能基准
   - 内存泄漏
   - 并发问题

### 5.2 修复流程
```
发现问题 → 本地修复 → 提交代码 → 重新部署 → 重新测试
    ↓
验证通过 → 进入下一阶段
    ↓
验证失败 → 分析原因 → 重新修复
```

## 6. 监控验证

### 6.1 监控指标验证
1. **性能指标**:
   - 批次生成时间: ≤6.5分钟 (平均)
   - 内存使用: ≤550MB (平均), 峰值<700MB
   - 错误率: <5%

2. **质量指标**:
   - 生成质量: ≥80分
   - 审核准确率: ≥85%
   - 任务完成率: ≥95%

3. **业务指标**:
   - 题材覆盖率: ≥8个大类
   - 创新题材比例: ≥30%
   - 读者偏好匹配度: ≥70%

### 6.2 告警验证
1. **三级告警触发测试**:
   - 严重告警: 模拟批次>10分钟
   - 警告告警: 模拟内存>600MB
   - 信息告警: 模拟完成率<95%

2. **自动恢复测试**:
   - 性能恢复: 模拟高负载后恢复
   - 质量恢复: 模拟质量下降后恢复
   - 系统恢复: 模拟服务重启

## 7. 时间计划

### 第1天: 代码审查与准备
- 审查现有代码结构
- 创建新增模块框架
- 准备部署脚本

### 第2天: 服务器部署
- 备份现有项目
- 部署更新代码
- 配置环境

### 第3天: 单元测试
- 执行所有单元测试
- 修复发现的问题
- 验证接口兼容性

### 第4天: 集成测试
- 执行完整流水线测试
- 验证3章批次机制
- 测试监控告警系统

### 第5天: 性能测试与优化
- 执行性能基准测试
- 优化性能问题
- 验证监控指标

### 第6天: 最终验证
- 完整系统验证
- 监控告警验证
- 文档更新

## 8. 风险评估与缓解

### 8.1 风险
1. **部署失败风险**: 服务无法启动
2. **兼容性风险**: 新模块与现有代码不兼容
3. **性能风险**: 超出服务器能力
4. **数据风险**: 数据丢失或损坏

### 8.2 缓解措施
1. **完整备份**: 部署前完整备份
2. **逐步部署**: 分阶段部署，先测试后生产
3. **监控预警**: 实时监控，及时发现问题
4. **回滚计划**: 准备快速回滚方案

## 9. 成功标准

### 9.1 技术标准
- ✅ 所有单元测试通过
- ✅ 所有集成测试通过
- ✅ 性能指标达标
- ✅ 监控告警正常工作

### 9.2 功能标准
- ✅ 7个Agent协同工作正常
- ✅ 3章批次机制正常工作
- ✅ 差异化审核正常工作
- ✅ 数据源管理正常工作

### 9.3 业务标准
- ✅ 能生成完整小说
- ✅ 质量达到要求标准
- ✅ 系统稳定运行
- ✅ 监控数据完整

## 10. 交付物

1. **部署报告**: 部署过程和结果
2. **测试报告**: 所有测试结果
3. **性能报告**: 性能基准数据
4. **问题报告**: 发现和修复的问题
5. **监控报告**: 监控系统运行情况
6. **最终验证报告**: 系统整体验证结果