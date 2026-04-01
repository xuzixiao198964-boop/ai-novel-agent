# AI Novel Media Agent 项目结构

## 项目目录结构

```
ai-novel-media-agent/
├── app/                            # 应用代码
│   ├── __init__.py
│   ├── main.py                     # FastAPI应用入口
│   ├── config.py                   # 配置管理
│   ├── database.py                 # 数据库连接
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py                 # 用户模型
│   │   ├── novel.py                # 小说模型
│   │   ├── video.py                # 视频模型
│   │   ├── task.py                 # 任务模型
│   │   ├── payment.py              # 支付模型
│   │   ├── api_key.py              # API Key模型
│   │   └── publish.py              # 发布模型
│   ├── schemas/                    # Pydantic模式
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── novel.py
│   │   ├── video.py
│   │   ├── task.py
│   │   ├── payment.py
│   │   └── publish.py
│   ├── api/                        # API路由
│   │   ├── __init__.py
│   │   ├── v1/                     # API版本1
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 认证API
│   │   │   ├── user.py             # 用户API
│   │   │   ├── novel.py            # 小说API
│   │   │   ├── video.py            # 视频API
│   │   │   ├── task.py             # 任务API
│   │   │   ├── payment.py          # 支付API
│   │   │   ├── api_key.py          # API Key管理
│   │   │   ├── publish.py          # 发布API
│   │   │   └── websocket.py        # WebSocket API
│   │   └── openclaw.py             # OpenClaw专用API
│   ├── core/                       # 核心模块
│   │   ├── __init__.py
│   │   ├── security.py             # 安全相关
│   │   ├── exceptions.py           # 异常处理
│   │   ├── logging_config.py       # 日志配置
│   │   ├── metrics.py              # 监控指标
│   │   └── cache.py                # 缓存管理
│   ├── services/                   # 业务服务
│   │   ├── __init__.py
│   │   ├── auth_service.py         # 认证服务
│   │   ├── user_service.py         # 用户服务
│   │   ├── novel_service.py        # 小说服务
│   │   ├── video_service.py        # 视频服务
│   │   ├── payment_service.py      # 支付服务
│   │   ├── api_key_service.py      # API Key服务
│   │   ├── publish_service.py      # 发布服务
│   │   └── cost_calculator.py      # 成本计算
│   ├── agents/                     # AI Agent模块
│   │   ├── __init__.py
│   │   ├── trend_agent.py          # 趋势分析Agent
│   │   ├── style_agent.py          # 风格解析Agent
│   │   ├── planner_agent.py        # 策划Agent
│   │   ├── writer_agent.py         # 写作Agent
│   │   ├── polish_agent.py         # 润色Agent
│   │   ├── auditor_agent.py        # 审核Agent
│   │   ├── reviser_agent.py        # 修订Agent
│   │   └── video_agent.py          # 视频生成Agent
│   ├── tasks/                      # Celery任务
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery应用
│   │   ├── novel_tasks.py          # 小说生成任务
│   │   ├── video_tasks.py          # 视频生成任务
│   │   ├── publish_tasks.py        # 发布任务
│   │   └── notification_tasks.py   # 通知任务
│   ├── utils/                      # 工具函数
│   │   ├── __init__.py
│   │   ├── file_utils.py           # 文件处理
│   │   ├── text_utils.py           # 文本处理
│   │   ├── video_utils.py          # 视频处理
│   │   ├── payment_utils.py        # 支付工具
│   │   └── validation.py           # 数据验证
│   ├── dependencies/               # FastAPI依赖
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证依赖
│   │   ├── database.py             # 数据库依赖
│   │   └── rate_limit.py           # 限流依赖
│   └── middleware/                 # 中间件
│       ├── __init__.py
│       ├── logging_middleware.py   # 日志中间件
│       ├── cors_middleware.py      # CORS中间件
│       └── error_middleware.py     # 错误处理中间件
├── alembic/                        # 数据库迁移
│   ├── versions/                   # 迁移版本
│   ├── env.py
│   └── README.md
├── scripts/                        # 部署和管理脚本
│   ├── deploy.sh                   # 部署脚本
│   ├── backup.sh                   # 备份脚本
│   ├── restore.sh                  # 恢复脚本
│   ├── migrate.sh                  # 迁移脚本
│   ├── create_initial_data.py      # 初始数据
│   └── health_check.py             # 健康检查
├── tests/                          # 测试代码
│   ├── __init__.py
│   ├── conftest.py                 # 测试配置
│   ├── test_auth.py                # 认证测试
│   ├── test_novel.py               # 小说测试
│   ├── test_video.py               # 视频测试
│   ├── test_payment.py             # 支付测试
│   └── test_api_key.py             # API Key测试
├── static/                         # 静态文件
│   ├── css/                        # CSS样式
│   │   ├── main.css
│   │   ├── home.css
│   │   └── api-docs.css
│   ├── js/                         # JavaScript
│   │   ├── main.js
│   │   ├── api-key-manager.js
│   │   └── price-calculator.js
│   ├── images/                     # 图片资源
│   │   ├── logo.png
│   │   ├── hero-bg.jpg
│   │   └── icons/
│   └── fonts/                      # 字体文件
├── templates/                      # HTML模板
│   ├── base.html                   # 基础模板
│   ├── home.html                   # 主页
│   ├── api-docs.html               # API文档
│   ├── openclaw-integration.html   # OpenClaw集成
│   └── api-key-management.html     # API Key管理
├── data/                           # 数据存储
│   ├── media/                      # 媒体文件
│   │   ├── novels/                 # 小说文件
│   │   ├── videos/                 # 视频文件
│   │   ├── images/                 # 图片文件
│   │   └── temp/                   # 临时文件
│   ├── logs/                       # 应用日志
│   ├── backups/                    # 备份文件
│   └── cache/                      # 缓存数据
├── docs/                           # 文档
│   ├── api/                        # API文档
│   │   ├── v1/                     # v1 API文档
│   │   └── openclaw.md             # OpenClaw集成文档
│   ├── deployment/                 # 部署文档
│   ├── user-guide/                 # 用户指南
│   └── developer-guide/            # 开发者指南
├── .env.example                    # 环境变量示例
├── .gitignore                      # Git忽略文件
├── requirements.txt                # Python依赖
├── requirements-dev.txt            # 开发依赖
├── pyproject.toml                  # 项目配置
├── Dockerfile                      # Docker配置
├── docker-compose.yml              # Docker Compose配置
├── README.md                       # 项目说明
└── LICENSE                         # 许可证
```

## 核心模块详细说明

### 1. 数据模型 (app/models/)

#### 1.1 用户模型 (user.py)
```python
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    
    # 账户信息
    balance = Column(Float, default=0.0)
    total_recharged = Column(Float, default=0.0)
    total_consumed = Column(Float, default=0.0)
    
    # 状态信息
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # 设置
    settings = Column(JSON, default={
        "language": "zh-CN",
        "timezone": "Asia/Shanghai",
        "notification_email": True,
        "notification_push": True
    })
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    novels = relationship("Novel", back_populates="user")
    videos = relationship("Video", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
```

#### 1.2 小说模型 (novel.py)
```python
class Novel(Base):
    __tablename__ = "novels"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    genre = Column(String, nullable=False)  # fantasy/romance/sci-fi等
    
    # 生成参数
    chapters = Column(Integer, nullable=False)
    conflict_level = Column(String, default="medium")  # low/medium/high
    expert_advice = Column(Boolean, default=True)
    writing_style = Column(String, default="modern")
    custom_prompt = Column(String, nullable=True)
    
    # 生成结果
    total_words = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    conflict_score = Column(Float, default=0.0)
    metadata = Column(JSON, default={})  # 元数据
    
    # 状态
    status = Column(String, default="pending")  # pending/running/completed/failed/cancelled
    progress = Column(JSON, default={
        "current_step": 0,
        "total_steps": 7,
        "percent": 0,
        "message": ""
    })
    
    # 成本
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    service_fee = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # 文件路径
    full_text_path = Column(String, nullable=True)
    epub_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    user = relationship("User", back_populates="novels")
    chapters_rel = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="novel")
    audits = relationship("NovelAudit", back_populates="novel", cascade="all, delete-orphan")
```

#### 1.3 API Key模型 (api_key.py)
```python
class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    key = Column(String, unique=True, index=True, nullable=False)
    
    # 权限
    permissions = Column(JSON, default=[])  # 权限列表
    ip_restriction = Column(String, nullable=True)  # IP限制
    
    # 配额
    quotas = Column(JSON, default={
        "daily": None,
        "monthly": None,
        "cost": None
    })
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # 状态
    status = Column(String, default="active")  # active/expired/revoked
    is_default = Column(Boolean, default=False)
    
    # 有效期
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关系
    user = relationship("User", back_populates="api_keys")
    usage_logs = relationship("ApiKeyUsageLog", back_populates="api_key", cascade="all, delete-orphan")
```

### 2. 业务服务 (app/services/)

#### 2.1 小说服务 (novel_service.py)
```python
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import Novel, Chapter, NovelAudit
from app.schemas import NovelCreate, NovelUpdate
from app.agents import (
    TrendAgent, StyleAgent, PlannerAgent, 
    WriterAgent, PolishAgent, AuditorAgent, ReviserAgent
)
from app.tasks.novel_tasks import create_novel_task
from app.utils.cost_calculator import calculate_novel_cost

class NovelService:
    def __init__(self, db: Session):
        self.db = db
        self.trend_agent = TrendAgent()
        self.style_agent = StyleAgent()
        self.planner_agent = PlannerAgent()
        self.writer_agent = WriterAgent()
        self.polish_agent = PolishAgent()
        self.auditor_agent = AuditorAgent()
        self.reviser_agent = ReviserAgent()
    
    def create_novel(self, user_id: str, novel_data: NovelCreate) -> Novel:
        """创建小说生成任务"""
        # 计算预估成本
        estimated_cost = calculate_novel_cost(
            chapters=novel_data.chapters,
            conflict_level=novel_data.conflict_level,
            expert_advice=novel_data.expert_advice
        )
        
        # 创建小说记录
        novel = Novel(
            user_id=user_id,
            title=novel_data.title,
            genre=novel_data.genre,
            chapters=novel_data.chapters,
            conflict_level=novel_data.conflict_level,
            expert_advice=novel_data.expert_advice,
            writing_style=novel_data.writing_style,
            custom_prompt=novel_data.custom_prompt,
            estimated_cost=estimated_cost,
            status="pending"
        )
        
        self.db.add(novel)
        self.db.commit()
        self.db.refresh(novel)
        
        # 启动异步任务
        create_novel_task.delay(novel.id)
        
        return novel
    
    def get_novel_progress(self, novel_id: str, user_id: str) -> Dict[str, Any]:
        """获取小说生成进度"""
        novel = self.db.query(Novel).filter(
            Novel.id == novel_id,
            Novel.user_id == user_id
        ).first()
        
        if not novel:
            raise ValueError("小说不存在或无权访问")
        
        return {
            "id": novel.id,
            "status": novel.status,
            "progress": novel.progress,
            "cost_so_far": novel.actual_cost,
            "created_at": novel.created_at,
            "updated_at": novel.updated_at
        }
    
    def generate_novel_sync(self, novel_id: str) -> Novel:
        """同步生成小说（用于测试）"""
        novel = self.db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            raise ValueError("小说不存在")
        
        try:
            # 更新状态为运行中
            novel.status = "running"
            novel.started_at = datetime.now()
