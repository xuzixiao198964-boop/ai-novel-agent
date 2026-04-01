# AI Novel Media Agent 架构设计文档

## 设计信息
- **设计阶段**: 架构设计
- **设计日期**: 2026-04-01
- **设计模型**: Claude 3.5 Sonnet (via Cursor)
- **工程方法**: OpenClaw软件工程化全流程
- **设计状态**: 🏗️ 进行中

## 1. 架构设计原则

### 1.1 设计目标
```
1. 高可用性：系统可用性 > 99.5%
2. 可扩展性：支持水平扩展
3. 可维护性：模块化设计，清晰边界
4. 安全性：多层次安全防护
5. 性能：API响应时间 < 500ms
6. 成本效益：优化资源使用，控制成本
```

### 1.2 架构风格选择
```
选择：微服务架构 + 事件驱动
理由：
1. 业务复杂度高，需要独立演进
2. 不同服务有不同技术需求
3. 需要高可用和弹性伸缩
4. 团队可以并行开发
```

## 2. 系统架构概览

### 2.1 整体架构图
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               客户端层                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Web前端  │  │ 微信小程序 │  │ 抖音小程序 │  │ Native   │  │ OpenClaw │     │
│  │ (React)  │  │          │  │          │  │  App     │  │  插件    │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │              │              │              │              │          │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────┘
        │              │              │              │              │
        ▼              ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BFF层 (Backend For Frontend)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Web BFF  │  │ 微信 BFF  │  │ 抖音 BFF  │  │ App BFF  │  │ OpenClaw │     │
│  │          │  │ code2sess │  │ OAuth    │  │ SMS/OAuth│  │  BFF     │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │              │              │              │              │          │
│       └──────────────┴──────────────┴──────┬───────┴──────────────┘          │
│                                            │ 统一Token                       │
└────────────────────────────────────────────┼────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               API网关层                                     │
│                    ┌──────────────────────────────┐                         │
│                    │   Kong/NGINX + JWT            │                         │
│                    │   负载均衡 + 认证 + 限流       │                         │
│                    └──────────────┬───────────────┘                         │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             业务服务层                                       │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ 用户服务  │ 支付服务  │ 小说服务  │ 视频服务  │ 发布服务  │ 订阅服务  │内容质量  │
│ User Svc │ Pay Svc  │Novel Svc │Video Svc │Pub Svc  │Sub Svc  │Quality   │
│          │          │          │          │         │         │  Svc     │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┤
│                          视频评审服务 Video Review Svc                       │
└──────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬────────────┘
       │       │       │       │       │       │       │       │
       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           共享服务层                                         │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────────┤
│   认证服务    │   配置服务    │   消息队列    │   文件存储    │   缓存服务      │
│  Auth Service│ Config Svc   │ Message Queue│ File Storage │   Cache       │
│              │              │   RabbitMQ   │   MinIO/S3   │   Redis       │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────┬────────┘
       │               │               │               │               │
       ▼               ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据存储层                                         │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────────┤
│   主数据库    │   分析数据库   │   向量数据库   │   对象存储    │   日志存储      │
│  PostgreSQL  │  PostgreSQL  │   Pinecone   │   MinIO/S3   │    Loki       │
│   (业务数据)  │  (分析数据)   │  (AI向量)    │  (媒体文件)   │   (日志)       │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────────┘
```

### 2.2 服务拆分设计

#### 服务1：用户服务 (User Service)
```
职责：
- 用户注册、登录、认证
- 用户信息管理
- 余额管理
- API密钥管理

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (users表)
- 缓存：Redis (会话缓存)
- 通信：REST API + WebSocket

接口：
- POST /api/v1/users/register
- POST /api/v1/users/login
- GET  /api/v1/users/{id}
- PUT  /api/v1/users/{id}
- GET  /api/v1/users/{id}/balance
- POST /api/v1/users/{id}/recharge
- POST /api/v1/users/{id}/apikeys
```

#### 服务2：支付服务 (Payment Service)
```
职责：
- 订单管理
- 支付处理（支付宝/微信支付/抖音支付）
- 退款处理（用户申请→管理员审核→网关退款→余额调整）
- 对账系统（每日批量对账）
- 发票生成
- Webhook回调处理（幂等性保障）
- 分账/收益分成
- 风控检测

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (orders, payments, refunds, invoices表)
- 外部集成：支付宝、微信支付、抖音支付
- 消息队列：RabbitMQ (支付结果通知)

Webhook处理流程：
  支付网关 ──POST──▶ /api/v1/payments/webhooks/{provider}
                          │
                    ┌──────▼──────┐
                    │ 验签 + 幂等 │
                    │ 检查        │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐     ┌──────────────┐
                    │ 更新订单状态 │────▶│ 发送MQ通知    │
                    └──────┬──────┘     └──────────────┘
                           │
                    ┌──────▼──────┐
                    │ 更新用户余额 │
                    └─────────────┘

退款流程：
  用户申请退款 → 创建退款工单(pending)
       → 管理员审核(approved/rejected)
       → 调用支付网关退款接口
       → 网关回调确认 → 扣减用户余额
       → 更新退款状态(completed)

风控规则：
- 单日退款金额上限
- 异常高频小额充值检测
- 同一IP多账号支付检测
- 支付金额与历史行为偏差检测

接口：
- POST /api/v1/payments/orders
- GET  /api/v1/payments/orders/{id}
- POST /api/v1/payments/{id}/refund
- GET  /api/v1/payments/reconciliation
- POST /api/v1/payments/webhooks/{provider}
- GET  /api/v1/payments/invoices
- POST /api/v1/payments/invoices/{id}/generate
- GET  /api/v1/payments/refunds
- GET  /api/v1/payments/refunds/{id}
- PUT  /api/v1/payments/refunds/{id}/review
```

#### 服务3：小说服务 (Novel Service)
```
职责：
- 小说生成任务管理
- 7个Agent流水线调度
- 内容存储和管理
- 质量审核

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (novels, chapters表)
- AI集成：DeepSeek API
- 消息队列：RabbitMQ (任务队列)
- 缓存：Redis (内容缓存)

Agent流水线：
1. TrendAgent → 2. StyleAgent → 3. PlannerAgent → 
4. WriterAgent → 5. PolishAgent → 6. AuditorAgent → 7. ReviserAgent

接口：
- POST /api/v1/novels
- GET  /api/v1/novels/{id}
- GET  /api/v1/novels/{id}/progress
- POST /api/v1/novels/{id}/cancel
- GET  /api/v1/novels/{id}/chapters
```

#### 服务4：视频服务 (Video Service)
```
职责：
- 视频生成任务管理
- TTS服务集成
- 视频处理
- 质量评审

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (videos表)
- TTS服务：腾讯云TTS、Edge TTS
- 视频处理：FFmpeg、MoviePy
- 存储：MinIO/S3 (视频文件)
- GPU：可选（用于视频渲染）

生成模式：
1. 仅配音模式 (Voice Only)
2. 仅字幕模式 (Subtitle Only)
3. 动画模式 (Animation)
4. 混合模式 (Mixed)
5. 资讯转视频模式 (News to Video)

接口：
- POST /api/v1/videos
- GET  /api/v1/videos/{id}
- GET  /api/v1/videos/{id}/progress
- GET  /api/v1/videos/{id}/preview
```

#### 服务5：发布服务 (Publish Service)
```
职责：
- 内容发布管理
- 平台API集成（适配器模式）
- 发布状态监控与全链路追踪
- 数据分析
- 智能排期（按平台最优发布时间）
- 内容合规检查（平台特定规则预检）

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (publish_records表)
- 平台集成：抖音、小红书、B站、微信视频号API
- 消息队列：RabbitMQ (发布任务)
- 存储：MinIO/S3 (发布内容)

平台适配器架构：
  ┌─────────────────────────────────────────────┐
  │            PublishOrchestrator               │
  │      (统一发布调度 + 智能排期引擎)            │
  └──────────────────┬──────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ 抖音     │  │ B站     │  │ 小红书   │  ...更多适配器
  │ Adapter  │  │ Adapter │  │ Adapter │
  └────┬────┘  └────┬────┘  └────┬────┘
       │            │            │
       ▼            ▼            ▼
    平台API       平台API       平台API

每个适配器负责：
- 平台特定的内容格式转换
- OAuth2 Token管理（含自动刷新）
- 平台API差异屏蔽
- 平台特定合规规则检查
- 发布状态轮询与回调

发布状态链路：
  pending → compliance_check → uploading → processing → live → stats_collecting

智能排期策略：
- 抖音：工作日 12:00-13:00, 18:00-22:00
- B站：晚间 20:00-23:00
- 小红书：午间 11:00-13:00, 晚间 19:00-21:00
- 可根据历史数据自动优化发布时间

平台支持：
- 小说平台：番茄、起点、晋江
- 视频平台：抖音、小红书、B站、微信视频号、快手

接口：
- POST /api/v1/publish
- GET  /api/v1/publish/{id}
- GET  /api/v1/publish/{id}/status
- DELETE /api/v1/publish/{id}
- GET  /api/v1/publish/{id}/analytics
- POST /api/v1/publish/schedule
- GET  /api/v1/publish/platforms
- POST /api/v1/publish/compliance-check
```

#### 服务6：监控服务 (Monitoring Service)
```
职责：
- 系统监控
- 业务监控
- 告警管理
- 日志收集

技术栈：
- 监控：Prometheus + Grafana
- 日志：Loki + Promtail
- 告警：Alertmanager
- 追踪：Jaeger (可选)

监控指标：
1. 系统指标：CPU、内存、磁盘、网络
2. 应用指标：响应时间、错误率、吞吐量
3. 业务指标：用户数、任务数、收入
4. 自定义指标：AI调用成本、内容质量评分
```

#### 服务7：订阅服务 (Subscription Service)
```
职责：
- 套餐管理（微小说/短篇/中篇/长篇/超长篇/企业）
- 订阅生命周期管理
- 权益引擎（基于有效套餐判断用户权限）
- 计费扣费（按次从余额扣减，余额 = 充值金额 - 累计成本 × 1.1~1.2）

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (subscription_plans, user_subscriptions, entitlements表)
- 缓存：Redis (权益缓存)
- 消息队列：RabbitMQ (订阅事件通知)

套餐层级定义：
┌────────────┬────────────┬──────────┬────────────────────────┐
│  套餐名称   │ 字数范围    │ 月费(元) │ 包含权益                │
├────────────┼────────────┼──────────┼────────────────────────┤
│  微小说     │ ≤3,000字   │   29     │ 5次/月，基础TTS         │
│  短篇       │ ≤30,000字  │   99     │ 10次/月，高级TTS        │
│  中篇       │ ≤100,000字 │  299     │ 20次/月，全功能          │
│  长篇       │ ≤300,000字 │  599     │ 50次/月，优先队列        │
│  超长篇     │ ≤1,000,000 │  999     │ 不限次，专属资源         │
│  企业       │ 自定义      │ 面议     │ 不限次，SLA保障，API配额  │
└────────────┴────────────┴──────────┴────────────────────────┘

订阅生命周期：
  create → active → renew/upgrade/downgrade → expire → cancel
  
  ┌────────┐   付款成功   ┌────────┐   到期前续费   ┌────────┐
  │ create │─────────────▶│ active │──────────────▶│ renew  │──┐
  └────────┘              └───┬────┘               └────────┘  │
                              │                         ▲      │
                              │ 升级/降级                │      │
                              ▼                         │      │
                         ┌─────────┐                    │      │
                         │ upgrade/│────────────────────┘      │
                         │downgrade│                            │
                         └─────────┘                            │
                              │                                 │
                    到期未续费  │         ┌────────┐             │
                              ▼         │ cancel │◀────用户取消──┘
                         ┌─────────┐    └────────┘
                         │ expired │
                         └─────────┘

权益引擎逻辑：
  check_entitlement(user_id, action) →
    1. 查询用户当前有效订阅
    2. 获取套餐对应权益列表
    3. 检查月度使用配额是否充足
    4. 检查余额是否足够本次扣费
    5. 返回 {allowed: bool, reason: str, cost: decimal}

计费模型：
  每次使用实际成本 = AI API调用费 + 存储费 + 计算费
  用户扣费金额 = 实际成本 × 加价系数(1.1~1.2)
  余额 = 累计充值 - 累计扣费

接口：
- GET  /api/v1/subscriptions/plans
- POST /api/v1/subscriptions
- GET  /api/v1/subscriptions/{id}
- PUT  /api/v1/subscriptions/{id}/upgrade
- PUT  /api/v1/subscriptions/{id}/downgrade
- POST /api/v1/subscriptions/{id}/renew
- POST /api/v1/subscriptions/{id}/cancel
- GET  /api/v1/subscriptions/{id}/entitlements
- POST /api/v1/subscriptions/check-entitlement
- GET  /api/v1/subscriptions/{id}/usage
```

#### 服务8：内容质量服务 (Content Quality Service)
```
职责：
- 专家建议数据库管理（网文大咖写作技巧采集）
- 建议匹配引擎（题材×篇幅×风格 → 兼容建议集）
- 冲突检测（确保选中建议间不矛盾）
- 唯一性保障（每部小说方案使用唯一组合）
- 冲突强度规则管理

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (expert_advices, advice_conflicts表)
- 向量数据库：Pinecone (建议语义检索)
- 缓存：Redis (热门建议缓存)

建议匹配流程：
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ 用户输入参数   │───▶│ 建议候选检索   │───▶│ 冲突检测过滤  │
  │ genre×length  │    │ (语义+标签)   │    │              │
  │ ×style        │    └──────────────┘    └──────┬───────┘
  └──────────────┘                                │
                                           ┌──────▼───────┐
                                           │ 唯一性校验    │
                                           │ (历史去重)    │
                                           └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │ 输出建议集    │
                                           │ (排序+评分)   │
                                           └──────────────┘

冲突强度规则：
- 微小说(≤3000字)：≥3级冲突/300字内必须出现，节奏极快
- 短篇(≤30000字)：多线冲突交织，每章至少1个冲突点
- 中篇(≤100000字)：复杂冲突网络，主线+2-3条副线
- 长篇(≤300000字)：多层冲突架构，角色弧线完整
- 超长篇(≤1000000字)：史诗级冲突体系，多卷结构

专家建议来源：
- 网文大咖经验（网络爬取+人工审核）
- 文学理论知识库
- 平台热门作品分析
- 用户反馈迭代

接口：
- GET  /api/v1/quality/advices
- POST /api/v1/quality/advices/match
- GET  /api/v1/quality/advices/{id}
- POST /api/v1/quality/advices/check-conflicts
- GET  /api/v1/quality/conflict-rules
- POST /api/v1/quality/uniqueness-check
```

#### 服务9：视频评审服务 (Video Review Service)
```
职责：
- 5秒黄金开头评审
- 多维度评审打分
- 评审流水线管理（自动筛查→AI深度评审→人工抽检）
- 记忆点元素识别与管理

技术栈：
- 框架：FastAPI
- 数据库：PostgreSQL (video_reviews, memory_points表)
- AI集成：DeepSeek (内容分析), SiliconFlow (视觉分析)
- 消息队列：RabbitMQ (评审任务)

5秒黄金开头类型：
┌────────────┬────────────────────────────────────────┐
│  开头类型   │ 描述                                   │
├────────────┼────────────────────────────────────────┤
│  悬念型     │ 抛出疑问/悬念，勾起好奇心                │
│  情感型     │ 强烈情感冲击，引发共鸣                   │
│  冲突型     │ 直接展现冲突/矛盾，制造紧张感             │
│  视觉型     │ 震撼画面/特效，吸引眼球                  │
│  音频型     │ 独特音效/BGM/台词，听觉吸引              │
└────────────┴────────────────────────────────────────┘

评审维度与权重：
  ┌─────────────────────────────────────────────┐
  │  评审维度           │ 权重  │ 评分范围        │
  ├─────────────────────┼───────┼────────────────┤
  │  开头吸引力          │  30%  │ 1-10           │
  │  内容完整性          │  25%  │ 1-10           │
  │  制作质量            │  20%  │ 1-10           │
  │  平台适配度          │  15%  │ 1-10           │
  │  商业价值            │  10%  │ 1-10           │
  └─────────────────────┴───────┴────────────────┘
  
  综合评分 = Σ(维度评分 × 权重)
  合格线：综合评分 ≥ 6.0
  优质线：综合评分 ≥ 8.0

评审流水线：
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │  自动筛查     │───▶│ AI深度评审    │───▶│ 人工抽检      │
  │ (基础规则)    │    │ (多维度打分)  │    │ (高级套餐)    │
  │ 100%覆盖     │    │ 100%覆盖     │    │ 10~20%抽样   │
  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
         │                   │                    │
         ▼                   ▼                    ▼
    不合格直接退回       生成评审报告          人工修正评分
    (格式/时长/分辨率)   附改进建议            最终定级

记忆点元素：
- 标志性画面：具有辨识度的视觉场景
- 经典台词：朗朗上口、易于传播的对白
- 独特音效：定制化音效/BGM片段
- 情感高潮：引发强烈情感共鸣的片段
- 视觉符号：反复出现的视觉标识

接口：
- POST /api/v1/reviews
- GET  /api/v1/reviews/{id}
- GET  /api/v1/reviews/{id}/report
- POST /api/v1/reviews/{id}/human-review
- GET  /api/v1/reviews/stats
- POST /api/v1/reviews/memory-points
- GET  /api/v1/reviews/{id}/memory-points
```

## 3. 数据架构设计

### 3.1 数据库设计原则
```
1. 数据分离：
   - 业务数据：PostgreSQL
   - 缓存数据：Redis
   - 文件数据：MinIO/S3
   - 向量数据：Pinecone (可选)

2. 读写分离：
   - 主库：写操作
   - 从库：读操作
   - 缓存层：热点数据

3. 数据分区：
   - 按时间分区：日志数据
   - 按用户分区：用户数据
   - 按类型分区：内容数据
```

### 3.2 核心数据表设计

#### 用户相关表
```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- API密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions JSONB DEFAULT '[]',
    ip_restrictions CIDR[],
    usage_limits JSONB,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key ON api_keys(key);
```

#### 支付相关表
```sql
-- 订单表
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    order_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'CNY',
    status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(20),
    transaction_id VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 支付记录表
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_transaction_id ON payments(transaction_id);
```

#### 内容相关表
```sql
-- 小说表
CREATE TABLE novels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    genre VARCHAR(50) NOT NULL,
    chapters INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress INT DEFAULT 0,
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 章节表
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(255),
    content TEXT,
    word_count INT,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(novel_id, chapter_number)
);

-- 视频表
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(20) NOT NULL, -- 'novel', 'external', 'news'
    source_id UUID,
    title VARCHAR(255) NOT NULL,
    generation_mode VARCHAR(20) NOT NULL,
    duration INT, -- 秒
    file_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'pending',
    progress INT DEFAULT 0,
    estimated_cost DECIMAL(10, 2),
    actual_cost DECIMAL(10, 2),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_novels_user_id ON novels(user_id);
CREATE INDEX idx_novels_status ON novels(status);
CREATE INDEX idx_chapters_novel_id ON chapters(novel_id);
CREATE INDEX idx_videos_user_id ON videos(user_id);
CREATE INDEX idx_videos_source ON videos(source_type, source_id);
```

#### 发布相关表
```sql
-- 发布记录表
CREATE TABLE publish_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(20) NOT NULL, -- 'novel', 'video'
    content_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    platform_account_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    publish_time TIMESTAMP,
    platform_content_id VARCHAR(100),
    analytics JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 平台账号表
CREATE TABLE platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    permissions JSONB,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, platform, account_id)
);

-- 创建索引
CREATE INDEX idx_publish_records_user_id ON publish_records(user_id);
CREATE INDEX idx_publish_records_content ON publish_records(content_type, content_id);
CREATE INDEX idx_publish_records_platform ON publish_records(platform);
CREATE INDEX idx_platform_accounts_user_id ON platform_accounts(user_id);
```

#### 订阅与权益相关表
```sql
-- 套餐定义表
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,           -- 微小说/短篇/中篇/长篇/超长篇/企业
    tier INT NOT NULL,                   -- 1-6 套餐等级
    max_word_count INT,                  -- 最大字数限制，NULL表示不限
    monthly_quota INT,                   -- 月度使用次数配额，NULL表示不限
    monthly_price DECIMAL(10, 2),        -- 月费
    yearly_price DECIMAL(10, 2),         -- 年费（可选优惠）
    markup_ratio DECIMAL(4, 2) DEFAULT 1.15, -- 加价系数
    features JSONB NOT NULL DEFAULT '{}', -- 包含的功能特性
    priority_level INT DEFAULT 0,        -- 任务队列优先级
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户订阅表
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES subscription_plans(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 状态: pending, active, expired, cancelled, upgrading, downgrading
    billing_cycle VARCHAR(10) NOT NULL DEFAULT 'monthly', -- monthly/yearly
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    monthly_used INT DEFAULT 0,          -- 当月已使用次数
    auto_renew BOOLEAN DEFAULT true,
    cancelled_at TIMESTAMP,
    upgrade_from_plan_id UUID,           -- 升级前的套餐
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 权益表
CREATE TABLE entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    entitlement_type VARCHAR(50) NOT NULL,
    -- 类型: novel_generation, video_generation, tts_premium, priority_queue, api_access
    quota_limit INT,                     -- 配额上限，NULL表示不限
    quota_used INT DEFAULT 0,            -- 已使用配额
    is_active BOOLEAN DEFAULT true,
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 发票表
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES user_subscriptions(id),
    order_id UUID REFERENCES orders(id),
    invoice_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    invoice_type VARCHAR(20) NOT NULL,   -- 增值税普通发票/专用发票
    title VARCHAR(255) NOT NULL,         -- 发票抬头
    tax_number VARCHAR(30),              -- 税号
    status VARCHAR(20) DEFAULT 'pending',
    -- 状态: pending, issued, sent, void
    issued_at TIMESTAMP,
    pdf_path VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 退款记录表
CREATE TABLE refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refund_no VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    -- 状态: pending, approved, rejected, processing, completed, failed
    reviewed_by UUID,                    -- 审核管理员ID
    reviewed_at TIMESTAMP,
    review_note TEXT,
    gateway_refund_id VARCHAR(100),      -- 支付网关退款ID
    completed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 对账记录表
CREATE TABLE reconciliation_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_date DATE NOT NULL,
    payment_provider VARCHAR(20) NOT NULL, -- alipay/wechat/douyin
    total_orders INT DEFAULT 0,
    total_amount DECIMAL(12, 2) DEFAULT 0.00,
    matched_count INT DEFAULT 0,
    mismatched_count INT DEFAULT 0,
    missing_in_system INT DEFAULT 0,
    missing_in_gateway INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reconciliation_date, payment_provider)
);

-- 创建索引
CREATE INDEX idx_subscription_plans_tier ON subscription_plans(tier);
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_period ON user_subscriptions(current_period_end);
CREATE INDEX idx_entitlements_user_id ON entitlements(user_id);
CREATE INDEX idx_entitlements_subscription_id ON entitlements(subscription_id);
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE INDEX idx_invoices_invoice_no ON invoices(invoice_no);
CREATE INDEX idx_refunds_order_id ON refunds(order_id);
CREATE INDEX idx_refunds_user_id ON refunds(user_id);
CREATE INDEX idx_refunds_status ON refunds(status);
CREATE INDEX idx_reconciliation_date ON reconciliation_records(reconciliation_date);
```

#### 内容质量与专家建议相关表
```sql
-- 专家建议表
CREATE TABLE expert_advices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100) NOT NULL,        -- 建议来源（大咖名/平台/理论）
    category VARCHAR(50) NOT NULL,       -- 分类：开头技巧/人物塑造/情节推进/结尾设计...
    applicable_genres TEXT[] NOT NULL,    -- 适用题材：['玄幻','都市','言情'...]
    applicable_lengths TEXT[] NOT NULL,   -- 适用篇幅：['微小说','短篇','中篇'...]
    applicable_styles TEXT[],            -- 适用风格：['幽默','严肃','悬疑'...]
    content TEXT NOT NULL,               -- 建议内容
    keywords TEXT[],                     -- 关键词标签
    quality_score DECIMAL(3, 2),         -- 建议质量评分 0-10
    usage_count INT DEFAULT 0,           -- 被使用次数
    embedding_vector_id VARCHAR(100),    -- Pinecone向量ID
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建议冲突规则表
CREATE TABLE advice_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advice_id_a UUID REFERENCES expert_advices(id) ON DELETE CASCADE,
    advice_id_b UUID REFERENCES expert_advices(id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL,  -- 类型：矛盾/重复/弱化
    severity VARCHAR(10) NOT NULL,       -- 严重程度：high/medium/low
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(advice_id_a, advice_id_b)
);

-- 冲突强度规则表
CREATE TABLE conflict_intensity_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    length_tier VARCHAR(20) NOT NULL,    -- 微小说/短篇/中篇/长篇/超长篇
    min_conflict_level INT NOT NULL,     -- 最低冲突等级
    max_words_per_conflict INT,          -- 每N字至少一个冲突点
    conflict_structure TEXT NOT NULL,    -- 冲突结构描述
    example TEXT,                        -- 示例
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建议使用记录表（用于唯一性保障）
CREATE TABLE advice_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    novel_id UUID REFERENCES novels(id) ON DELETE CASCADE,
    advice_ids UUID[] NOT NULL,          -- 使用的建议ID组合
    combination_hash VARCHAR(64) NOT NULL, -- 组合哈希，用于快速去重
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_expert_advices_genres ON expert_advices USING GIN(applicable_genres);
CREATE INDEX idx_expert_advices_lengths ON expert_advices USING GIN(applicable_lengths);
CREATE INDEX idx_expert_advices_category ON expert_advices(category);
CREATE INDEX idx_advice_conflicts_a ON advice_conflicts(advice_id_a);
CREATE INDEX idx_advice_conflicts_b ON advice_conflicts(advice_id_b);
CREATE INDEX idx_conflict_rules_tier ON conflict_intensity_rules(length_tier);
CREATE INDEX idx_advice_usage_hash ON advice_usage_records(combination_hash);
CREATE INDEX idx_advice_usage_novel ON advice_usage_records(novel_id);
```

#### 视频评审与记忆点相关表
```sql
-- 视频评审表
CREATE TABLE video_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    review_stage VARCHAR(20) NOT NULL,   -- auto_screen / ai_deep / human_sample
    opening_type VARCHAR(20),            -- 悬念/情感/冲突/视觉/音频
    score_opening DECIMAL(3, 1),         -- 开头吸引力 (权重30%)
    score_completeness DECIMAL(3, 1),    -- 完整性 (权重25%)
    score_quality DECIMAL(3, 1),         -- 制作质量 (权重20%)
    score_platform_fit DECIMAL(3, 1),    -- 平台适配 (权重15%)
    score_commercial DECIMAL(3, 1),      -- 商业价值 (权重10%)
    total_score DECIMAL(4, 2),           -- 加权综合分
    pass_status VARCHAR(10) NOT NULL DEFAULT 'pending',
    -- pass_status: pending / pass / fail / excellent
    suggestions TEXT,                    -- 改进建议
    reviewer_type VARCHAR(10) NOT NULL,  -- ai / human
    reviewer_id VARCHAR(100),            -- 评审者标识
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 记忆点表
CREATE TABLE memory_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    point_type VARCHAR(20) NOT NULL,
    -- 类型: iconic_frame / classic_line / unique_sound / emotional_peak / visual_symbol
    timestamp_start DECIMAL(8, 2),       -- 出现时间点（秒）
    timestamp_end DECIMAL(8, 2),         -- 结束时间点（秒）
    content TEXT NOT NULL,               -- 记忆点内容描述
    strength_score DECIMAL(3, 1),        -- 记忆强度评分 1-10
    thumbnail_path VARCHAR(500),         -- 缩略图路径（标志性画面）
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_video_reviews_video_id ON video_reviews(video_id);
CREATE INDEX idx_video_reviews_stage ON video_reviews(review_stage);
CREATE INDEX idx_video_reviews_pass ON video_reviews(pass_status);
CREATE INDEX idx_memory_points_video_id ON memory_points(video_id);
CREATE INDEX idx_memory_points_type ON memory_points(point_type);
```

### 3.3 缓存策略设计
```
缓存层级：
1. L1缓存：本地内存缓存（服务内）
   - 缓存时间：5分钟
   - 缓存内容：用户会话、配置信息
   - 淘汰策略：LRU

2. L2缓存：Redis集群
   - 缓存时间：根据数据类型
   - 缓存内容：
     * 用户信息：30分钟
     * 热点内容：1小时
     * 任务状态：实时更新
     * API响应：5分钟
   - 淘汰策略：TTL + LRU

3. L3缓存：CDN（可选）
   - 缓存时间：静态资源长期缓存
   - 缓存内容：图片、视频、前端资源
   - 淘汰策略：版本控制

缓存更新策略：
- 写后更新：数据更新后立即更新缓存
- 懒加载：首次访问时加载到缓存
- 预加载：预测热点数据提前加载
```

## 4. 通信架构设计

### 4.1 服务间通信
```
通信方式：
1. 同步通信：REST API
   - 使用场景：实时性要求高的操作
   - 示例：用户登录、支付确认

2. 异步通信：消息队列
   - 使用场景：耗时操作、事件通知
   - 示例：小说生成、视频处理、发布任务

3. 实时通信：WebSocket
   - 使用场景：进度通知、实时聊天
   - 示例：任务进度更新、客服聊天

通信协议：
- REST API：HTTP/1.1 + JSON
- 消息队列：AMQP (RabbitMQ)
- WebSocket：WS/WSS
- gRPC：可选（高性能场景）
```

### 4.2 消息队列设计
```
消息队列架构：
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  生产者     │───▶│ RabbitMQ    │───▶│  消费者     │
│ (服务)      │    │  集群       │    │ (Worker)    │
└─────────────┘    └─────────────┘    └─────────────┘

交换机和队列：
1. 任务队列 (task_queue)
   - 交换机类型：direct
   - 路由键：task.{service}.{type}
   - 队列：task_novel, task_video, task_publish
   - 持久化：是

2. 事件队列 (event_queue)
   - 交换机类型：fanout
   - 路由键：event.{type}
   - 队列：event_notification, event_audit, event_analytics
   - 持久化：是

3. 死信队列 (dlq)
   - 处理失败的消息
   - 重试机制：3次重试后进入死信队列
   - 告警：死信队列有消息时触发告警
```

### 4.3 API网关设计
```
网关功能：
1. 路由转发：根据路径转发到对应服务
2. 认证授权：JWT验证，权限检查
3. 限流熔断：防止服务过载
4. 日志记录：请求日志，审计日志
5. 监控指标：收集API调用指标

路由配置：
/api/v1/users/**          → 用户服务
/api/v1/payments/**       → 支付服务
/api/v1/novels/**         → 小说服务
/api/v1/videos/**         → 视频服务
/api/v1/publish/**        → 发布服务
/api/v1/monitor/**        → 监控服务
/api/v1/subscriptions/**  → 订阅服务
/api/v1/quality/**        → 内容质量服务
/api/v1/reviews/**        → 视频评审服务
/api/openclaw/**          → OpenClaw BFF

限流策略：
- 用户级限流：100请求/分钟
- IP级限流：1000请求/分钟
- 服务级限流：根据服务容量动态调整
```

## 5. 安全架构设计

### 5.1 认证授权体系
```
认证方式：
1. 用户认证：JWT (JSON Web Token)
   - 令牌类型：access_token + refresh_token
   - 有效期：access_token 1小时，refresh_token 7天
   - 签名算法：HS256

2. API认证：Bearer Token
   - 令牌格式：Bearer {api_key}
   - 权限控制：基于API密钥的权限范围
   - IP限制：可配置IP白名单

3. 服务间认证：mTLS (可选)
   - 内部服务通信加密
   - 双向证书验证

授权模型：RBAC (基于角色的访问控制)
- 角色：普通用户、VIP用户、管理员
- 权限：细粒度权限控制
- 继承：角色继承权限
```

### 5.2 数据安全
```
数据传输安全：
- 外部通信：HTTPS (TLS 1.3)
- 内部通信：HTTPS或私有网络
- 敏感数据：端到端加密

数据存储安全：
- 数据库加密：透明数据加密
- 文件加密：存储时加密
- 备份加密：备份文件加密

敏感信息处理：
- 密码：bcrypt哈希存储
- API密钥：加密存储
- 支付信息：PCI DSS合规
```

### 5.3 安全监控
```
安全事件监控：
1. 异常登录检测
   - 异地登录
   - 频繁失败登录
   - 异常时间登录

2. API滥用检测
   - 异常调用频率
   - 异常参数
   - 恶意爬虫

3. 数据泄露检测
   - 敏感数据外传
   - 异常数据访问
   - 权限滥用

安全审计：
- 操作日志：记录所有敏感操作
- 访问日志：记录所有API访问
- 变更日志：记录所有配置变更
```

## 6. 套餐订阅子系统架构

### 6.1 订阅系统整体架构
```
┌──────────────────────────────────────────────────────────────────┐
│                        订阅子系统                                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  套餐管理模块  │  │ 订阅生命周期  │  │  权益引擎    │           │
│  │              │  │  管理模块     │  │              │           │
│  │ - 套餐CRUD   │  │ - 创建/激活   │  │ - 权限检查   │           │
│  │ - 定价策略   │  │ - 续费/升降级  │  │ - 配额管理   │           │
│  │ - 功能配置   │  │ - 到期/取消   │  │ - 实时扣费   │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│                     ┌──────▼───────┐                              │
│                     │  计费引擎    │                              │
│                     │              │                              │
│                     │ 实际成本计算  │                              │
│                     │ × 加价系数   │                              │
│                     │ = 用户扣费   │                              │
│                     └──────┬───────┘                              │
│                            │                                      │
│                     ┌──────▼───────┐                              │
│                     │  余额管理    │                              │
│                     │              │                              │
│                     │ 余额 = 充值  │                              │
│                     │ - 累计扣费   │                              │
│                     └──────────────┘                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

数据流：
  用户下单 → 支付服务收款 → 余额充值
       → 订阅服务创建/续费订阅 → 权益生效
            → 用户使用功能 → 权益引擎检查配额+余额
                 → 扣费(实际成本×1.1~1.2) → 更新余额
```

### 6.2 套餐升降级策略
```
升级策略：
  - 差价补缴：按剩余天数比例计算差额
  - 立即生效：升级后权益立即可用
  - 配额重置：升级后月度配额按新套餐重置

降级策略：
  - 当期有效：降级在当前周期结束后生效
  - 余额不退：已付差价不退还
  - 配额调整：下个周期按新套餐配额

企业套餐特殊处理：
  - 自定义配额
  - 专属SLA保障
  - 独立API配额
  - 优先技术支持
  - 账单结算（月结/季结）
```

### 6.3 技术选型
```
- 定时任务：APScheduler (到期检查、续费提醒、配额重置)
- 分布式锁：Redis (防止并发订阅操作)
- 事件通知：RabbitMQ (订阅状态变更 → 通知用户服务/其他服务)
- 缓存：Redis (用户权益缓存，TTL=5min，变更时主动失效)
```

## 7. OpenClaw集成架构

### 7.1 整体集成架构
```
┌──────────────────────────────────────────────────────────────────┐
│                     OpenClaw 生态                                │
│                                                                  │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │ OpenClaw CLI │         │ OpenClaw IDE  │                      │
│  │              │         │   插件        │                      │
│  │ openclaw     │         │              │                      │
│  │ ai-novel ... │         │ 可视化面板    │                      │
│  └──────┬───────┘         └──────┬───────┘                      │
│         │                        │                               │
│         └────────────┬───────────┘                               │
│                      │                                           │
│              ┌───────▼───────┐                                   │
│              │ OpenClaw      │                                   │
│              │ Plugin SDK    │                                   │
│              │               │                                   │
│              │ X-API-Key头   │                                   │
│              │ 请求签名      │                                   │
│              └───────┬───────┘                                   │
│                      │                                           │
└──────────────────────┼───────────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    API Gateway                                   │
│                /api/openclaw/* 路由                               │
│                X-API-Key 验证                                    │
│                Plugin Token 生命周期管理                          │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                  OpenClaw BFF                                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ 任务管理  │  │ 用户管理  │  │ 内容管理  │  │ 配置管理  │        │
│  │ Task API │  │ User API │  │Content   │  │Config    │        │
│  │          │  │          │  │  API     │  │  API     │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
└───────────────────────┬──────────────────────────────────────────┘
                        │
                        ▼
                   后端业务服务层
```

### 7.2 OpenClaw认证体系
```
认证流程：
  1. 用户在后台生成 OpenClaw Plugin Token
  2. Plugin Token 绑定到用户账号 + 权限范围
  3. CLI/插件通过 X-API-Key 头携带 Token
  4. API Gateway 验证 Token 有效性
  5. 请求转发到 OpenClaw BFF 处理

Token生命周期：
  创建 → 激活 → 使用中 → 刷新/轮转 → 撤销
  
  - 默认有效期：90天
  - 支持手动撤销
  - 支持自动轮转（到期前7天提醒）
  - 最大同时有效Token数：5
```

### 7.3 OpenClaw专用API契约
```
端点定义：

任务管理：
  POST /api/openclaw/tasks              -- 创建小说/视频任务
  GET  /api/openclaw/tasks/{id}         -- 查询任务状态
  GET  /api/openclaw/tasks/{id}/status  -- 精简状态查询
  POST /api/openclaw/tasks/{id}/cancel  -- 取消任务
  GET  /api/openclaw/tasks              -- 列出所有任务

用户管理：
  GET  /api/openclaw/user/profile       -- 当前用户信息
  GET  /api/openclaw/user/balance       -- 余额查询
  GET  /api/openclaw/user/usage         -- 使用统计

内容管理：
  GET  /api/openclaw/content/{id}       -- 获取内容（小说/视频）
  GET  /api/openclaw/content/{id}/download -- 下载内容

配置管理：
  GET  /api/openclaw/config/genres      -- 可用题材列表
  GET  /api/openclaw/config/styles      -- 可用风格列表
  GET  /api/openclaw/config/plans       -- 可用套餐列表
```

### 7.4 CLI工作流
```
openclaw ai-novel create \
  --genre "玄幻" \
  --length "短篇" \
  --style "热血" \
  --title "龙皇觉醒" \
  --chapters 10

openclaw ai-novel status <task-id>
openclaw ai-novel cancel <task-id>
openclaw ai-novel list --status running
openclaw ai-novel download <task-id> --format epub

openclaw ai-video create \
  --source <novel-id> \
  --mode mixed \
  --voice "成熟男声"

openclaw ai-video status <task-id>
openclaw ai-video preview <task-id>
```

### 7.5 数据双向同步
```
同步策略：

OpenClaw → 后端：
  - CLI/插件发起操作 → OpenClaw BFF → 后端服务
  - 直接调用，无需额外同步

后端 → OpenClaw：
  - 任务状态变更 → WebSocket / SSE 推送
  - 重要事件 → Webhook回调到OpenClaw

状态映射：
  后端状态              OpenClaw状态
  ──────────            ─────────────
  pending      ──────▶  queued
  processing   ──────▶  running
  completed    ──────▶  done
  failed       ──────▶  error
  cancelled    ──────▶  cancelled
```

### 7.6 技术选型
```
- Plugin SDK：Python (与OpenClaw生态一致)
- 通信协议：HTTPS + WebSocket (状态推送)
- 序列化：JSON
- 认证：X-API-Key + HMAC签名 (可选)
- 限流：独立限流策略 (区分CLI和插件来源)
```

## 8. 多端入口BFF层架构

### 8.1 BFF层设计理念
```
BFF (Backend For Frontend) 模式：
  每个前端入口拥有独立的BFF服务，负责：
  - 渠道特定的认证流程
  - 数据聚合与裁剪（只返回前端需要的字段）
  - 协议适配（微信/抖音特定协议处理）
  - 渠道特定的支付路由

为什么不是单一API网关：
  - 各渠道认证流程差异大（OAuth、code2session、SMS等）
  - 各渠道返回数据格式需求不同
  - 支付渠道与入口强绑定
  - 平台审核要求不同的接口行为
```

### 8.2 各渠道BFF详设
```
┌─────────────────────────────────────────────────────────────────┐
│                        BFF 服务矩阵                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Web BFF                                                 │    │
│  │ - 认证：邮箱+密码 / 手机+短信 / 第三方OAuth            │    │
│  │ - 支付路由：支付宝（首选）/ 微信支付                     │    │
│  │ - 特性：完整功能集，响应式布局数据                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 微信小程序 BFF                                          │    │
│  │ - 认证：wx.login() → code2session → openid              │    │
│  │         → 绑定已有账号 / 创建新用户 → session token      │    │
│  │ - 支付路由：微信支付（唯一）                              │    │
│  │ - 特性：精简数据，小程序格式适配                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 抖音小程序 BFF                                          │    │
│  │ - 认证：tt.login() → code → server验证 → openid         │    │
│  │         → 绑定/创建用户 → session token                  │    │
│  │ - 支付路由：抖音支付（唯一）                              │    │
│  │ - 特性：短视频场景优化，抖音内容格式                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ App BFF                                                 │    │
│  │ - 认证：手机+短信 / 邮箱+密码 / 微信OAuth / 苹果登录    │    │
│  │ - 支付路由：支付宝 / 微信支付 / Apple IAP(iOS)          │    │
│  │ - 特性：推送通知集成，设备绑定                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ OpenClaw BFF                                            │    │
│  │ - 认证：X-API-Key (Plugin Token)                        │    │
│  │ - 支付路由：无直接支付（使用余额扣费）                    │    │
│  │ - 特性：面向开发者，最小化响应，批量操作支持              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 统一SSO架构
```
跨端统一登录（SSO）设计：

核心原则：一个用户，一个账号，多端登录

身份绑定模型：
  ┌──────────────────────────────┐
  │          users 表             │
  │  id, username, email, phone  │
  └──────────────┬───────────────┘
                 │ 1:N
                 ▼
  ┌──────────────────────────────┐
  │     user_auth_bindings 表     │
  │  user_id, provider, open_id  │
  │                              │
  │  示例：                       │
  │  (u1, wechat, wx_openid_xx) │
  │  (u1, douyin, dy_openid_xx) │
  │  (u1, phone,  13812345678)  │
  │  (u1, email,  foo@bar.com)  │
  └──────────────────────────────┘

登录统一流程：
  渠道端发起登录
       │
       ▼
  BFF执行渠道特定认证 (code2session / OAuth / SMS)
       │
       ▼
  获得渠道标识 (openid / phone / email)
       │
       ▼
  查询 user_auth_bindings
       │
  ┌────┴────┐
  │ 已绑定?  │
  ├── 是 ───▶ 返回该用户的统一JWT
  │          │
  └── 否 ───▶ 引导绑定已有账号 或 创建新账号
              │
              ▼
         绑定后返回统一JWT

JWT Payload：
  {
    "sub": "user_uuid",
    "channel": "wechat|douyin|web|app|openclaw",
    "plan_tier": 3,
    "iat": ...,
    "exp": ...
  }
```

### 8.4 渠道支付路由
```
支付路由规则：

  ┌────────────┬──────────────────────────────────┐
  │  入口渠道   │  可用支付方式                      │
  ├────────────┼──────────────────────────────────┤
  │  Web       │  支付宝、微信支付                   │
  │  微信小程序  │  微信支付（强制）                   │
  │  抖音小程序  │  抖音支付（强制）                   │
  │  App(安卓)  │  支付宝、微信支付                   │
  │  App(iOS)  │  Apple IAP、支付宝、微信支付        │
  │  OpenClaw  │  余额扣费（不支持直接支付）          │
  └────────────┴──────────────────────────────────┘

路由逻辑：
  BFF层根据渠道类型自动选择可用支付方式列表
  → 前端展示可用支付方式
  → 用户选择 → BFF调用对应支付服务接口
  → 支付服务路由到对应网关
```

### 8.5 技术选型
```
- 框架：FastAPI (每个BFF独立部署)
- 部署：Docker容器，按渠道独立伸缩
- 通信：BFF → 后端服务 via REST (内网)
- 缓存：Redis (渠道会话缓存)
- 微信SDK：wechatpy
- 抖音SDK：自行封装 (官方REST API)
```

## 9. 支付子系统增强设计

### 9.1 Webhook幂等处理
```
幂等性保障机制：

  ┌──────────────────────────────────────────────────────────┐
  │  支付网关回调 POST /api/v1/payments/webhooks/{provider}  │
  └──────────────────────┬───────────────────────────────────┘
                         │
                  ┌──────▼──────┐
                  │  验签       │  验证请求来源真实性
                  │ (RSA/HMAC)  │  (支付宝RSA2, 微信HMAC-SHA256)
                  └──────┬──────┘
                         │ 验签通过
                  ┌──────▼──────┐
                  │  幂等检查    │  以 transaction_id 为幂等键
                  │  Redis SETNX │  SET key NX EX 86400
                  └──────┬──────┘
                    ┌────┴────┐
                    │ 已处理?  │
                    ├── 是 ───▶ 直接返回 200 OK
                    └── 否 ───┐
                              │
                  ┌───────────▼──────────┐
                  │  事务处理             │
                  │  BEGIN                │
                  │  1. 更新订单状态       │
                  │  2. 更新支付记录       │
                  │  3. 更新用户余额       │
                  │  4. 记录操作日志       │
                  │  COMMIT               │
                  └───────────┬──────────┘
                              │
                  ┌───────────▼──────────┐
                  │  发送MQ事件通知       │
                  │  payment.completed    │
                  └───────────┬──────────┘
                              │
                       返回 200 OK
```

### 9.2 退款流程详设
```
退款完整流程：

  用户申请退款 ──▶ 创建退款工单(pending)
                        │
                 ┌──────▼──────┐
                 │  自动审核    │  金额≤阈值且无异常 → 自动通过
                 │  (可选)     │  否则 → 人工审核队列
                 └──────┬──────┘
                        │
                 ┌──────▼──────┐
                 │  管理员审核   │
                 │ approved /   │
                 │ rejected    │
                 └──────┬──────┘
                    ┌───┴───┐
                    │通过?   │
                    │       │
              ┌─────┴──┐  ┌─┴──────────┐
              │approved │  │ rejected   │
              └────┬───┘  │ 通知用户    │
                   │      └────────────┘
            ┌──────▼──────┐
            │ 调用支付网关  │
            │ 退款接口     │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │ 网关回调确认  │ (异步，可能延迟数小时)
            └──────┬──────┘
                   │
            ┌──────▼──────────────┐
            │ 扣减用户余额         │
            │ 更新退款状态(completed)│
            │ 生成退款发票          │
            └─────────────────────┘
```

### 9.3 每日对账系统
```
对账批处理流程（每日凌晨2:00执行）：

  ┌────────────────┐     ┌────────────────┐
  │ 拉取系统订单    │     │ 拉取网关账单    │
  │ (当日已完成)    │     │ (支付宝/微信/抖)│
  └───────┬────────┘     └───────┬────────┘
          │                      │
          └──────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   逐笔比对   │
              │  order_no ↔  │
              │ transaction  │
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │  匹配    │ │ 系统多   │ │ 网关多   │
    │ (正常)   │ │ (需核查) │ │ (需核查) │
    └─────────┘ └─────────┘ └─────────┘
                     │           │
                     ▼           ▼
              ┌──────────────────┐
              │ 生成对账报告      │
              │ 异常自动告警      │
              │ 记录到reconciliation_records │
              └──────────────────┘

技术实现：
  - 调度：APScheduler / Celery Beat
  - 网关对账文件下载：异步HTTP
  - 比对算法：内存Hash Join
  - 告警：邮件 + 企业微信通知
```

### 9.4 分账与收益分成
```
分账模型：

  总收入 ─┬── 平台运营费 (5~10%)
          ├── AI服务成本 (按实际消耗)
          ├── 存储/带宽成本 (按量)
          └── 净利润
               ├── 平台分成 (60~70%)
               └── 创作者分成 (30~40%)  [仅发布收益场景]

分账触发条件：
  - 用户充值：不触发分账
  - 内容发布产生收益：按周期结算
  - 企业客户：按合同约定

技术实现：
  - 支付宝/微信分账API
  - 自动结算周期：T+7 / 月结
```

### 9.5 发票生成
```
发票类型：
  - 增值税普通发票（个人/小规模）
  - 增值税专用发票（企业套餐）

生成流程：
  用户申请发票 → 验证订单/套餐信息 → 调用电子发票服务
  → 生成PDF → 存储到MinIO → 邮件/短信通知用户

集成方案：
  - 电子发票服务：航天信息/百望云 API
  - 存储：MinIO/S3
  - 通知：邮件 + 站内消息
```

## 10. 内容质量与专家建议系统

### 10.1 系统架构
```
┌──────────────────────────────────────────────────────────────┐
│                  内容质量与专家建议系统                        │
│                                                              │
│  ┌──────────────┐                                           │
│  │  数据采集层   │                                           │
│  │              │                                           │
│  │ Web爬虫      │── 网文大咖博客/教程/访谈                   │
│  │ 人工录入      │── 编辑团队审核后入库                       │
│  │ 用户反馈      │── 使用后评价 → 建议质量迭代                │
│  └──────┬───────┘                                           │
│         │                                                    │
│  ┌──────▼───────┐                                           │
│  │  知识处理层   │                                           │
│  │              │                                           │
│  │ 结构化提取    │── 原始文本 → 结构化建议条目                │
│  │ 向量化存储    │── Embedding → Pinecone                    │
│  │ 标签分类      │── 自动分类到题材/篇幅/风格维度             │
│  │ 冲突检测      │── 两两比对 → 标记冲突对                    │
│  └──────┬───────┘                                           │
│         │                                                    │
│  ┌──────▼───────┐                                           │
│  │  匹配引擎层   │                                           │
│  │              │                                           │
│  │ 输入：genre × length × style                              │
│  │ 候选：语义检索 + 标签过滤                                  │
│  │ 过滤：冲突检测（排除矛盾对）                               │
│  │ 去重：历史使用记录校验（唯一组合）                          │
│  │ 输出：评分排序的建议集                                     │
│  └──────────────┘                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 冲突检测算法
```
冲突类型：
  1. 直接矛盾：建议A说"开头要慢节奏铺垫"，建议B说"第一段就要爆发冲突"
  2. 风格冲突：建议A推荐"幽默轻松"，建议B推荐"沉重压抑"
  3. 结构冲突：建议A推荐"单线叙事"，建议B推荐"多视角切换"
  4. 弱化冲突：建议A的效果被建议B削弱

检测流程：
  1. 预计算：建议入库时，与现有建议两两比对
  2. 人工审核：高置信度冲突自动标记，低置信度人工确认
  3. 运行时：匹配引擎检索候选后，查询conflict表过滤

冲突严重程度：
  - high：绝对不能同时使用
  - medium：不建议同时使用，但特殊场景可放行
  - low：轻微影响，可以容忍
```

### 10.3 冲突强度规则详设
```
各篇幅冲突强度要求：

微小说 (≤3,000字)：
  - 最低冲突等级：3级
  - 约束：300字内必须出现第一个冲突
  - 结构：单一强冲突，快速解决
  - 节奏：极快，无废笔
  - 示例："开门见冲突，结尾反转"

短篇 (≤30,000字)：
  - 最低冲突等级：3级
  - 约束：每章至少1个冲突点
  - 结构：主线冲突 + 1-2个次要冲突
  - 节奏：快，每1000字内推进一次
  - 示例："多线交织，层层递进"

中篇 (≤100,000字)：
  - 最低冲突等级：4级
  - 约束：复杂冲突网络
  - 结构：主线 + 2-3条副线，交叉影响
  - 节奏：中等，允许适度铺垫
  - 示例："主角内外冲突并行"

长篇 (≤300,000字)：
  - 最低冲突等级：5级
  - 约束：多层冲突架构
  - 结构：卷级冲突 + 章级冲突 + 场景冲突
  - 节奏：有起伏，波浪式推进
  - 示例："史诗级冲突递进"

超长篇 (≤1,000,000字)：
  - 最低冲突等级：6级
  - 约束：史诗级冲突体系
  - 结构：多卷大冲突 + 卷内中冲突 + 章节小冲突
  - 节奏：长线布局，伏笔回收
  - 示例："多势力博弈 + 角色成长弧线"
```

## 11. 视频评审与记忆点系统

### 11.1 评审流水线架构
```
┌─────────────────────────────────────────────────────────────────┐
│                      视频评审流水线                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │  Stage 1: 自动筛查 (100%覆盖)                     │           │
│  │                                                  │           │
│  │  检查项：                                         │           │
│  │  - 视频格式/编码是否合规                           │           │
│  │  - 分辨率是否达标 (≥720p)                         │           │
│  │  - 时长是否在范围内                                │           │
│  │  - 音频是否完整，无静音段                          │           │
│  │  - 字幕是否清晰可读                               │           │
│  │                                                  │           │
│  │  结果：pass → Stage 2 / fail → 退回重新生成       │           │
│  └───────────────────────┬──────────────────────────┘           │
│                          │ pass                                 │
│  ┌───────────────────────▼──────────────────────────┐           │
│  │  Stage 2: AI深度评审 (100%覆盖)                   │           │
│  │                                                  │           │
│  │  评审维度：                                       │           │
│  │  ┌────────────────┬────────┬─────────────┐       │           │
│  │  │ 维度           │ 权重   │ AI评审方式    │       │           │
│  │  ├────────────────┼────────┼─────────────┤       │           │
│  │  │ 开头吸引力      │ 30%   │ 前5秒帧分析   │       │           │
│  │  │ 内容完整性      │ 25%   │ 脚本一致性检查 │       │           │
│  │  │ 制作质量        │ 20%   │ 音画同步检测   │       │           │
│  │  │ 平台适配度      │ 15%   │ 平台规则匹配   │       │           │
│  │  │ 商业价值        │ 10%   │ 热度预测模型   │       │           │
│  │  └────────────────┴────────┴─────────────┘       │           │
│  │                                                  │           │
│  │  输出：综合评分 + 各维度分数 + 改进建议            │           │
│  │  合格线：≥6.0 / 优质线：≥8.0                     │           │
│  └───────────────────────┬──────────────────────────┘           │
│                          │ score ≥ 6.0                          │
│  ┌───────────────────────▼──────────────────────────┐           │
│  │  Stage 3: 人工抽检 (仅高级套餐，10~20%抽样)       │           │
│  │                                                  │           │
│  │  触发条件：                                       │           │
│  │  - 用户套餐 ≥ 长篇级                              │           │
│  │  - AI评分在 6.0~7.5 的边界区间                    │           │
│  │  - 随机抽样                                       │           │
│  │                                                  │           │
│  │  人工操作：                                       │           │
│  │  - 修正AI评分                                     │           │
│  │  - 补充改进建议                                   │           │
│  │  - 最终定级 (pass/fail/excellent)                 │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 5秒黄金开头评审
```
开头类型识别与评分：

  视频前5秒 ──▶ 帧提取 + 音频提取 + 字幕提取
                    │
              ┌─────▼─────┐
              │ 类型识别    │
              │            │
              │ 悬念型：画面暗示未知、旁白设问   │
              │ 情感型：强烈配乐+情感画面         │
              │ 冲突型：紧张场面/对抗/争执        │
              │ 视觉型：震撼特效/美景/奇观        │
              │ 音频型：独特音效/抓耳BGM/金句     │
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ 吸引力评分  │
              │            │
              │ 评估指标：                        │
              │ - 信息密度（5秒内传递了多少信息）  │
              │ - 情感冲击度                       │
              │ - 悬念/好奇心触发度                 │
              │ - 视听协调度                       │
              │ - 与目标平台风格匹配度              │
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │ 生成改进    │
              │ 建议       │
              └───────────┘
```

### 11.3 记忆点识别与管理
```
记忆点类型与识别方法：

  ┌────────────────┬─────────────────────────────────────────┐
  │ 记忆点类型      │ 识别方法                                │
  ├────────────────┼─────────────────────────────────────────┤
  │ 标志性画面      │ 关键帧提取 + 视觉显著性分析              │
  │ (iconic_frame) │ 色彩/构图/内容独特度评分                  │
  │                │                                         │
  │ 经典台词        │ 字幕提取 + 语义分析                      │
  │ (classic_line) │ 简洁度/节奏感/传播潜力评分                │
  │                │                                         │
  │ 独特音效        │ 音频频谱分析                             │
  │ (unique_sound) │ 与BGM库比对，识别定制化音效               │
  │                │                                         │
  │ 情感高潮        │ 多模态情感分析                           │
  │ (emotion_peak) │ 画面+音频+文字情感强度曲线峰值            │
  │                │                                         │
  │ 视觉符号        │ 目标检测 + 出现频率分析                   │
  │ (visual_symbol)│ 识别反复出现的视觉元素                    │
  └────────────────┴─────────────────────────────────────────┘

记忆点强度评分 (1-10)：
  - 独特性 (30%)：在同类视频中的稀缺程度
  - 情感共鸣 (30%)：引发的情感强度
  - 传播潜力 (20%)：被观众记住和分享的可能性
  - 品牌关联 (20%)：与内容品牌/IP的关联度

应用场景：
  - 自动生成视频封面（选用最佳标志性画面）
  - 自动剪辑预告片（串联高分记忆点）
  - 内容营销素材提取
```

## 12. 多平台发布增强架构

### 12.1 平台适配器详设
```
适配器模式架构：

  ┌────────────────────────────────────────────────────────────┐
  │                  PublishOrchestrator                       │
  │                                                            │
  │  职责：                                                    │
  │  - 接收发布请求                                            │
  │  - 执行合规预检                                            │
  │  - 路由到目标平台适配器                                     │
  │  - 管理发布状态机                                          │
  │  - 聚合多平台发布结果                                       │
  └──────────────────────┬─────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         ▼               ▼               ▼              ▼
  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ DouyinAdpt │  │ BiliAdpt   │  │ XHSAdpt    │  │ WXVideoAdpt│
  ├────────────┤  ├────────────┤  ├────────────┤  ├────────────┤
  │ format()   │  │ format()   │  │ format()   │  │ format()   │
  │ upload()   │  │ upload()   │  │ upload()   │  │ upload()   │
  │ publish()  │  │ publish()  │  │ publish()  │  │ publish()  │
  │ status()   │  │ status()   │  │ status()   │  │ status()   │
  │ analytics()│  │ analytics()│  │ analytics()│  │ analytics()│
  │ compliance │  │ compliance │  │ compliance │  │ compliance │
  │  _check()  │  │  _check()  │  │  _check()  │  │  _check()  │
  └────────────┘  └────────────┘  └────────────┘  └────────────┘

同时支持小说平台适配器：
  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │ FanqieAdpt │  │ QidianAdpt │  │ JinjiangAdpt│
  ├────────────┤  ├────────────┤  ├────────────┤
  │ format()   │  │ format()   │  │ format()   │
  │ submit()   │  │ submit()   │  │ submit()   │
  │ status()   │  │ status()   │  │ status()   │
  └────────────┘  └────────────┘  └────────────┘
```

### 12.2 OAuth2账号绑定管理
```
Token管理流程：

  用户首次绑定：
    前端跳转平台授权页 → 用户授权 → 回调携带code
    → 后端用code换取 access_token + refresh_token
    → 加密存储到 platform_accounts 表
    → 记录 token_expires_at

  Token自动刷新：
    定时任务检查即将过期的Token (到期前24h)
    → 调用平台refresh接口获取新Token
    → 更新数据库
    → 刷新失败 → 通知用户重新授权

  Token状态：
    active → refreshing → active (正常)
    active → refreshing → expired → 需重新授权
    active → revoked → 需重新授权
```

### 12.3 智能排期引擎
```
排期策略：

  ┌──────────────────────────────────────────────────┐
  │              智能排期引擎                          │
  │                                                  │
  │  输入：                                          │
  │  - 目标平台列表                                   │
  │  - 内容类型（小说/视频）                           │
  │  - 用户偏好（可选）                               │
  │                                                  │
  │  决策因素：                                       │
  │  1. 平台流量高峰时段                              │
  │  2. 目标受众活跃时间                              │
  │  3. 同类内容竞争密度                              │
  │  4. 历史发布效果数据                              │
  │  5. 用户设定的偏好时间                            │
  │                                                  │
  │  输出：                                          │
  │  - 每个平台的最优发布时间                          │
  │  - 置信度评分                                    │
  └──────────────────────────────────────────────────┘

默认最优时段：
  ┌────────────┬────────────────────────────────┐
  │  平台       │  推荐发布时段                   │
  ├────────────┼────────────────────────────────┤
  │  抖音       │  12:00-13:00, 18:00-22:00     │
  │  B站        │  20:00-23:00                  │
  │  小红书      │  11:00-13:00, 19:00-21:00     │
  │  微信视频号   │  7:00-9:00, 12:00-13:00       │
  │  快手       │  11:00-13:00, 17:00-19:00     │
  │  番茄小说    │  20:00-22:00 (周五最佳)        │
  └────────────┴────────────────────────────────┘
```

### 12.4 内容合规预检
```
合规检查流程：

  发布前 → 通用合规检查 → 平台特定规则检查 → 结果

  通用合规检查：
  - 敏感词过滤（政治/色情/暴力/违法）
  - 版权检测（AI生成内容声明）
  - 广告法合规（禁用"最"、"第一"等绝对化用语）

  平台特定规则：
  ┌────────────┬────────────────────────────────────┐
  │  平台       │  特定规则                           │
  ├────────────┼────────────────────────────────────┤
  │  抖音       │  视频时长限制，封面要求，标签规范     │
  │  B站        │  分区规范，标签要求，转载声明         │
  │  小红书      │  图文比例，话题标签格式              │
  │  微信视频号   │  内容分类标注，原创声明              │
  │  番茄小说    │  字数要求，章节结构规范              │
  └────────────┴────────────────────────────────────┘

检查结果：
  - pass：可以发布
  - warning：有风险项，建议修改后发布
  - block：存在违规，禁止发布
```

## 13. 部署架构设计

### 13.1 服务器规划
```
服务器配置：104.244.90.202 (远程VPS)
建议配置：
- CPU：8核
- 内存：16GB
- 存储：200GB SSD
- 带宽：100Mbps

端口分配：
- 80/443:  Nginx (反向代理)
- 9000:    主服务 (FastAPI)
- 9001:    Web BFF
- 9002:    微信 BFF
- 9003:    抖音 BFF
- 9004:    App BFF
- 9005:    OpenClaw BFF
- 9010:    订阅服务
- 9011:    内容质量服务
- 9012:    视频评审服务
- 9013:    内容审核服务
- 9020:    支付Webhook接收器
- 8001:    前端服务
- 5432:    PostgreSQL
- 6379:    Redis
- 5672:    RabbitMQ
- 9090:    Prometheus
- 3000:    Grafana
- 3100:    Loki
```

### 13.2 容器化部署
```
Docker Compose配置：
version: '3.8'

services:
  # 数据库服务
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_novel_media
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"

  # 业务服务
  user_service:
    build: ./backend/user_service
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      - postgres
      - redis

  novel_service:
    build: ./backend/novel_service
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD}@rabbitmq:5672
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    depends_on:
      - postgres
      - rabbitmq

  # BFF服务
  web_bff:
    build: ./backend/bff/web
    ports:
      - "9001:9001"
    depends_on:
      - user_service
      - novel_service

  wechat_bff:
    build: ./backend/bff/wechat
    ports:
      - "9002:9002"
    environment:
      WECHAT_APP_ID: ${WECHAT_APP_ID}
      WECHAT_APP_SECRET: ${WECHAT_APP_SECRET}
    depends_on:
      - user_service

  douyin_bff:
    build: ./backend/bff/douyin
    ports:
      - "9003:9003"
    environment:
      DOUYIN_APP_ID: ${DOUYIN_APP_ID}
      DOUYIN_APP_SECRET: ${DOUYIN_APP_SECRET}
    depends_on:
      - user_service

  openclaw_bff:
    build: ./backend/bff/openclaw
    ports:
      - "9005:9005"
    depends_on:
      - user_service
      - novel_service

  # 新增业务服务
  subscription_service:
    build: ./backend/subscription_service
    ports:
      - "9010:9010"
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/2
    depends_on:
      - postgres
      - redis

  content_quality_service:
    build: ./backend/content_quality_service
    ports:
      - "9011:9011"
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      PINECONE_API_KEY: ${PINECONE_API_KEY}
    depends_on:
      - postgres

  video_review_service:
    build: ./backend/video_review_service
    ports:
      - "9012:9012"
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD}@rabbitmq:5672
    depends_on:
      - postgres
      - rabbitmq

  content_moderation_service:
    build: ./backend/content_moderation_service
    ports:
      - "9013:9013"
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
    depends_on:
      - postgres

  # 支付Webhook接收器（独立部署，高可用）
  payment_webhook_receiver:
    build: ./backend/payment_webhook
    ports:
      - "9020:9020"
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      RABBITMQ_URL: amqp://admin:${RABBITMQ_PASSWORD}@rabbitmq:5672
    depends_on:
      - postgres
      - redis
      - rabbitmq

  # 对账批处理任务
  reconciliation_worker:
    build: ./backend/reconciliation_worker
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres:5432/ai_novel_media
      ALIPAY_RECONCILIATION_URL: ${ALIPAY_RECONCILIATION_URL}
      WECHAT_RECONCILIATION_URL: ${WECHAT_RECONCILIATION_URL}
    depends_on:
      - postgres

  # 更多服务...
```

### 13.3 部署架构图
```
┌─────────────────────────────────────────────────────────────────┐
│                    Nginx (80/443)                               │
│                    SSL终止 + 反向代理                            │
└─────┬─────────┬─────────┬─────────┬─────────┬─────────────────┘
      │         │         │         │         │
      ▼         ▼         ▼         ▼         ▼
  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
  │WebBFF │ │微信BFF│ │抖音BFF│ │AppBFF │ │OCBFF  │
  │:9001  │ │:9002  │ │:9003  │ │:9004  │ │:9005  │
  └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
      │         │         │         │         │
      └─────────┴─────────┴────┬────┴─────────┘
                               │
                        ┌──────▼──────┐
                        │  API Gateway │
                        │  Kong/内部   │
                        └──────┬──────┘
                               │
      ┌──────────┬─────────────┼──────────┬──────────┐
      ▼          ▼             ▼          ▼          ▼
  ┌───────┐ ┌───────┐    ┌───────┐  ┌───────┐ ┌───────┐
  │用户Svc│ │支付Svc│    │小说Svc│  │视频Svc│ │订阅Svc│
  └───────┘ └───────┘    └───────┘  └───────┘ └───────┘
      ┌───────────┐ ┌───────────┐ ┌───────────┐
      │内容质量Svc │ │视频评审Svc │ │发布Svc    │
      └───────────┘ └───────────┘ └───────────┘
                               │
  独立部署组件：               │
  ┌───────────────┐  ┌────────┴──────┐  ┌──────────────┐
  │ Webhook接收器  │  │ 对账批处理    │  │ 内容审核Svc   │
  │ :9020         │  │ (定时任务)    │  │ :9013        │
  └───────────────┘  └───────────────┘  └──────────────┘
```

### 13.4 监控部署
```
监控栈部署：
1. Prometheus：指标收集
   - 配置服务发现
   - 设置采集频率
   - 配置存储策略

2. Grafana：数据可视化
   - 配置数据源
   - 创建监控面板
   - 设置告警规则

3. Loki：日志收集
   - 配置日志采集
   - 设置日志保留策略
   - 集成Grafana

4. Alertmanager：告警管理
   - 配置告警规则
   - 设置告警渠道
   - 配置告警分组
```

## 14. 性能优化设计

### 14.1 数据库优化
```
索引优化：
1. 查询分析：分析慢查询，创建合适索引
2. 复合索引：对常用查询条件创建复合索引
3. 覆盖索引：让查询只需要访问索引

查询优化：
1. 分页优化：使用游标分页代替偏移分页
2. 连接优化：避免N+1查询问题
3. 批量操作：使用批量插入/更新

分区策略：
1. 时间分区：按创建时间分区
2. 范围分区：按用户ID范围分区
3. 列表分区：按类型分区
```

### 14.2 缓存优化
```
缓存策略：
1. 热点数据识别：监控访问模式，识别热点数据
2. 缓存预热：系统启动时预加载热点数据
3. 缓存穿透防护：布隆过滤器或空值缓存
4. 缓存雪崩防护：随机过期时间，热点数据永不过期

缓存更新：
1. 写后更新：数据更新后立即更新缓存
2. 异步更新：通过消息队列异步更新缓存
3. 懒更新：首次访问时更新缓存
```

### 14.3 服务优化
```
服务拆分：
1. 读写分离：读服务和写服务分离
2. 热点分离：将热点功能拆分为独立服务
3. 异步处理：耗时操作异步化

资源优化：
1. 连接池：数据库连接池，HTTP连接池
2. 线程池：合理配置线程池大小
3. 内存管理：监控内存使用，防止内存泄漏
```

## 15. 容灾设计

### 15.1 高可用设计
```
服务高可用：
1. 多实例部署：每个服务至少2个实例
2. 负载均衡：使用负载均衡器分发流量
3. 健康检查：定期检查服务健康状态
4. 自动故障转移：故障时自动切换到备用实例

数据高可用：
1. 主从复制：数据库主从复制
2. 数据备份：定期全量备份 + 增量备份
3. 异地备份：备份到不同地理位置
```

### 15.2 灾难恢复
```
恢复目标：
- RPO (恢复点目标)：1小时
- RTO (恢复时间目标)：4小时

恢复策略：
1. 数据恢复：从备份恢复数据
2. 服务恢复：重新部署服务
3. 验证恢复：验证系统功能正常

恢复测试：
- 定期进行恢复演练
- 记录恢复时间和问题
- 优化恢复流程
```

## 16. 成本优化设计

### 16.1 资源成本优化
```
服务器优化：
1. 弹性伸缩：根据负载自动调整实例数量
2. 资源复用：共享资源，提高利用率
3. 预留实例：长期使用的资源使用预留实例

存储优化：
1. 数据生命周期管理：自动归档冷数据
2. 压缩存储：对可压缩数据进行压缩
3. 去重存储：对重复数据进行去重
```

### 16.2 AI成本优化
```
API调用优化：
1. 批量处理：合并多个请求为批量请求
2. 缓存结果：缓存AI生成结果
3. 降级策略：质量要求不高时使用低成本模型

成本监控：
1. 实时监控：监控API调用成本
2. 预算控制：设置预算上限
3. 成本分析：分析成本构成，优化策略
```

## 17. 架构评审检查清单

### 17.1 架构原则检查
```
✅ 高可用性检查：
- [ ] 服务多实例部署
- [ ] 负载均衡配置
- [ ] 故障转移机制
- [ ] 健康检查配置

✅ 可扩展性检查：
- [ ] 服务无状态设计
- [ ] 水平扩展支持
- [ ] 数据库分片支持
- [ ] 缓存分层设计

✅ 可维护性检查：
- [ ] 模块化设计
- [ ] 清晰接口定义
- [ ] 完善文档
- [ ] 自动化部署

✅ 安全性检查：
- [ ] 认证授权机制
- [ ] 数据加密传输
- [ ] 安全监控
- [ ] 审计日志
```

### 17.2 技术选型检查
```
✅ 框架选型：
- [ ] FastAPI：适合API服务，性能优秀
- [ ] React：前端生态丰富，性能优秀
- [ ] PostgreSQL：功能丰富，可靠性高

✅ 中间件选型：
- [ ] Redis：缓存性能优秀，功能丰富
- [ ] RabbitMQ：消息队列成熟稳定
- [ ] Nginx：反向代理性能优秀

✅ 监控选型：
- [ ] Prometheus：监控标准，生态丰富
- [ ] Grafana：可视化功能强大
- [ ] Loki：日志收集效率高
```

### 17.3 商业化子系统检查
```
✅ 订阅系统检查：
- [ ] 套餐层级定义完整（6级）
- [ ] 订阅生命周期状态机完备
- [ ] 权益引擎实时检查机制
- [ ] 计费模型（成本×加价系数）
- [ ] 升降级策略明确

✅ 支付系统检查：
- [ ] 三方支付网关集成（支付宝/微信/抖音）
- [ ] Webhook幂等处理
- [ ] 退款全流程
- [ ] 每日对账机制
- [ ] 风控规则
- [ ] 发票生成

✅ 多端入口检查：
- [ ] BFF层各渠道覆盖
- [ ] 统一SSO跨端登录
- [ ] 渠道支付路由正确
- [ ] 各端认证流程完整

✅ OpenClaw集成检查：
- [ ] Plugin Token认证
- [ ] 专用API契约完备
- [ ] CLI工作流覆盖
- [ ] 状态双向同步

✅ 内容质量检查：
- [ ] 专家建议匹配引擎
- [ ] 冲突检测机制
- [ ] 唯一性保障
- [ ] 冲突强度规则

✅ 视频评审检查：
- [ ] 三级评审流水线
- [ ] 5秒黄金开头评审
- [ ] 记忆点识别
- [ ] 评审维度与权重

✅ 多平台发布检查：
- [ ] 平台适配器模式
- [ ] OAuth2 Token管理
- [ ] 智能排期引擎
- [ ] 内容合规预检
```

### 17.4 风险评估检查
```
🔴 高风险：
- [ ] 视频处理性能风险：已设计GPU支持和分布式处理
- [ ] 多平台API集成风险：已设计抽象适配层
- [ ] AI成本控制风险：已设计成本监控和优化策略
- [ ] 支付安全风险：已设计幂等+验签+风控

🟡 中风险：
- [ ] 系统复杂度风险：已采用微服务架构，模块化设计
- [ ] 团队技能风险：技术栈选择成熟技术，降低学习成本
- [ ] 时间进度风险：已制定分阶段实施计划
- [ ] 多端兼容性风险：已设计BFF层隔离各端差异
- [ ] 内容合规风险：已设计多层审核机制

🟢 低风险：
- [ ] 用户系统开发风险：使用成熟框架和模式
- [ ] 基础架构风险：使用成熟的开源组件
- [ ] 订阅系统风险：业务模型清晰，状态机明确
```

## 18. 设计结论

### 18.1 设计优势
```
1. 微服务架构：支持独立部署和扩展
2. 事件驱动：提高系统响应性和可扩展性
3. 分层设计：清晰的责任分离
4. 安全设计：多层次安全防护
5. 监控完善：全面的监控和告警
6. 成本优化：资源使用和AI成本优化
7. BFF模式：各渠道独立适配，统一SSO
8. 商业化完备：订阅/支付/发票/对账全链路
9. 内容质量保障：专家建议+冲突检测+评审流水线
10. 开放生态：OpenClaw深度集成，CLI工作流支持
```

### 18.2 设计挑战
```
1. 分布式系统复杂度：需要完善的监控和运维
2. 数据一致性：需要设计合理的一致性方案
3. 性能优化：需要持续的监控和优化
4. 成本控制：需要精细的成本管理
5. 多端维护成本：5个BFF服务需要独立维护
6. 支付合规：需持续跟踪各支付渠道政策变化
7. 内容审核准确性：需持续优化审核规则和模型
```

### 18.3 建议实施方案
```
阶段1：基础架构搭建（2周）
  - 搭建基础服务框架
  - 配置数据库和缓存
  - 部署监控系统

阶段2：核心服务开发（6周）
  - 开发用户服务和支付服务（含Webhook、退款、对账）
  - 集成AI小说生成服务
  - 开发基础视频服务
  - 开发订阅服务和权益引擎

阶段3：商业化功能开发（4周）
  - 开发BFF层（Web + 微信 + OpenClaw优先）
  - 统一SSO实现
  - 内容质量服务和专家建议库
  - 视频评审流水线

阶段4：高级功能开发（4周）
  - 开发发布服务（适配器+智能排期）
  - 完善OpenClaw集成和CLI
  - 抖音BFF + App BFF
  - 分账/发票系统

阶段5：测试和部署（2周）
  - 系统测试和优化
  - 生产环境部署
  - 用户培训和上线
```

## 19. 下一步行动

### 19.1 立即行动
```
1. 确认架构设计
   - 评审架构设计文档
   - 确认技术选型
   - 制定详细实施计划

2. 准备开发环境
   - 搭建开发环境
   - 配置版本控制
   - 准备CI/CD流水线
```

### 19.2 短期行动（1-2周）
```
1. 详细设计阶段
   - 数据库详细设计
   - API详细设计
   - 模块详细设计

2. 开发准备
   - 创建项目脚手架
   - 制定开发规范
   - 分配开发任务
```

### 19.3 中期行动（3-18周）
```
1. 开发实施
   - 按照迭代计划开发
   - 持续集成测试
   - 定期进度评审

2. 质量保证
   - 编写自动化测试
   - 进行代码审查
   - 监控代码质量
```

---

**设计状态**: ✅ 架构设计完成（含商业化子系统增强）  
**设计结论**: 架构设计合理可行，已覆盖套餐订阅、OpenClaw集成、多端BFF、支付增强、内容质量、视频评审、多平台发布等商业化需求  
**下一步**: 开始详细设计阶段，制定API规范和数据库详细设计

###
