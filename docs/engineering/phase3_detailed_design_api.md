# AI Novel Media Agent API详细设计

## 设计信息
- **设计阶段**: 详细设计 - API设计
- **设计日期**: 2026-04-01
- **设计模型**: Claude 3.5 Sonnet (via Cursor)
- **工程方法**: OpenClaw软件工程化全流程
- **设计状态**: 📝 进行中

## 服务器环境约束
- 服务器：104.244.90.202 (Ubuntu 24.04 裸机)
- CPU：2核 / 内存：1GB / 磁盘：20GB
- 架构：模块化单体(Modular Monolith) - 单FastAPI进程
- 数据库：PostgreSQL 16 (唯一持久化存储)
- 缓存：进程内缓存(cachetools.TTLCache)，无Redis
- 任务队列：PostgreSQL任务表 + Celery(database backend)
- 部署：systemd服务，非Docker

## 1. API设计原则

### 1.1 设计规范
```
1. RESTful设计原则
   - 资源导向：以资源为中心设计API
   - 统一接口：使用标准HTTP方法
   - 无状态：每个请求包含所有必要信息

2. 版本控制
   - 版本前缀：/api/v1/
   - 向后兼容：新版本不破坏旧版本
   - 版本迁移：提供迁移指南

3. 响应格式
   - 成功响应：HTTP 200 + JSON
   - 错误响应：HTTP 4xx/5xx + 错误信息
   - 分页响应：包含分页信息

4. 认证授权
   - 认证方式：Bearer Token
   - 权限控制：基于角色的访问控制
   - 速率限制：防止API滥用
```

### 1.2 通用响应格式
```json
// 成功响应格式
{
  "code": 200,
  "message": "success",
  "data": {
    // 业务数据
  },
  "timestamp": "2026-04-01T12:00:00Z",
  "request_id": "req_1234567890"
}

// 错误响应格式
{
  "code": 400,
  "message": "参数错误",
  "errors": [
    {
      "field": "username",
      "message": "用户名不能为空"
    }
  ],
  "timestamp": "2026-04-01T12:00:00Z",
  "request_id": "req_1234567890"
}

// 分页响应格式
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 100,
      "total_pages": 5
    }
  },
  "timestamp": "2026-04-01T12:00:00Z",
  "request_id": "req_1234567890"
}
```

## 2. 认证授权API

### 2.1 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

请求体：
{
  "username": "user123",
  "email": "user@example.com",
  "phone": "+8613800138000",
  "password": "SecurePass123!",
  "invite_code": "INVITE123"  // 可选
}

响应体：
{
  "code": 201,
  "message": "注册成功",
  "data": {
    "user_id": "user_1234567890",
    "username": "user123",
    "email": "user@example.com",
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

### 2.2 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

请求体：
{
  "identifier": "user123",  // 用户名、邮箱或手机号
  "password": "SecurePass123!",
  "remember_me": true  // 可选，延长token有效期
}

响应体：
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "user_1234567890",
      "username": "user123",
      "email": "user@example.com",
      "balance": 0.00,
      "role": "user"
    }
  }
}
```

### 2.3 令牌刷新
```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}

响应体：
{
  "code": 200,
  "message": "令牌刷新成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

### 2.4 用户登出
```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "登出成功"
}
```

## 3. 用户管理API

### 3.1 获取用户信息
```http
GET /api/v1/users/me
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "user_1234567890",
    "username": "user123",
    "email": "user@example.com",
    "phone": "+8613800138000",
    "avatar": "https://example.com/avatars/user123.jpg",
    "balance": 100.50,
    "role": "user",
    "status": "active",
    "created_at": "2026-04-01T12:00:00Z",
    "last_login_at": "2026-04-01T14:30:00Z"
  }
}
```

### 3.2 更新用户信息
```http
PUT /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "username": "new_username",  // 可选
  "email": "new@example.com",  // 可选
  "phone": "+8613800138001",   // 可选
  "avatar": "https://example.com/new_avatar.jpg"  // 可选
}

响应体：
{
  "code": 200,
  "message": "用户信息更新成功",
  "data": {
    "id": "user_1234567890",
    "username": "new_username",
    "email": "new@example.com",
    "updated_at": "2026-04-01T15:00:00Z"
  }
}
```

### 3.3 修改密码
```http
PUT /api/v1/users/me/password
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "old_password": "OldPass123!",
  "new_password": "NewPass456!"
}

响应体：
{
  "code": 200,
  "message": "密码修改成功"
}
```

### 3.4 获取用户余额
```http
GET /api/v1/users/me/balance
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "balance": 100.50,
    "currency": "CNY",
    "last_recharge": "2026-04-01T10:00:00Z",
    "last_consumption": "2026-04-01T11:30:00Z"
  }
}
```

## 4. 支付系统API

### 4.1 创建充值订单
```http
POST /api/v1/payments/recharge
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "amount": 100.00,
  "currency": "CNY",
  "payment_method": "alipay",  // alipay, wechat, douyin
  "return_url": "https://example.com/return"  // 支付完成返回URL
}

响应体：
{
  "code": 201,
  "message": "订单创建成功",
  "data": {
    "order_id": "order_1234567890",
    "order_no": "202604011200001",
    "amount": 100.00,
    "currency": "CNY",
    "payment_method": "alipay",
    "status": "pending",
    "payment_url": "https://alipay.com/pay?order=...",  // 支付链接
    "qr_code": "data:image/png;base64,...",  // 支付二维码
    "expires_at": "2026-04-01T12:30:00Z"
  }
}
```

### 4.2 查询订单状态
```http
GET /api/v1/payments/orders/{order_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "order_1234567890",
    "order_no": "202604011200001",
    "amount": 100.00,
    "currency": "CNY",
    "payment_method": "alipay",
    "status": "completed",
    "transaction_id": "202604011200001001",
    "paid_at": "2026-04-01T12:05:00Z",
    "created_at": "2026-04-01T12:00:00Z",
    "completed_at": "2026-04-01T12:05:00Z"
  }
}
```

### 4.3 获取充值记录
```http
GET /api/v1/payments/recharge-records
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&start_date=2026-04-01&end_date=2026-04-30

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "order_id": "order_1234567890",
        "order_no": "202604011200001",
        "amount": 100.00,
        "currency": "CNY",
        "payment_method": "alipay",
        "status": "completed",
        "created_at": "2026-04-01T12:00:00Z",
        "completed_at": "2026-04-01T12:05:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

### 4.4 获取消费记录
```http
GET /api/v1/payments/consumption-records
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&start_date=2026-04-01&end_date=2026-04-30

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "consume_1234567890",
        "type": "novel_generation",
        "description": "中篇小说生成",
        "amount": 8.00,
        "currency": "CNY",
        "balance_before": 100.50,
        "balance_after": 92.50,
        "metadata": {
          "novel_id": "novel_1234567890",
          "title": "AI创作的奇幻冒险",
          "chapters": 18
        },
        "created_at": "2026-04-01T13:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

## 5. 小说生成API

### 5.1 创建小说生成任务
```http
POST /api/v1/novels
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "title": "AI创作的奇幻冒险",
  "genre": "fantasy",  // fantasy, romance, sci_fi, urban, historical
  "chapters": 18,
  "words_per_chapter": 3000,
  "conflict_level": "high",  // low, medium, high
  "expert_advice": true,
  "style_reference": "reference_novel_id",  // 可选，参考小说ID
  "custom_prompt": "需要包含魔法学校和龙元素",  // 可选，自定义提示
  "estimated_cost": 8.00  // 系统计算，用户确认
}

响应体：
{
  "code": 201,
  "message": "小说生成任务创建成功",
  "data": {
    "novel_id": "novel_1234567890",
    "title": "AI创作的奇幻冒险",
    "genre": "fantasy",
    "chapters": 18,
    "status": "pending",
    "progress": 0,
    "estimated_cost": 8.00,
    "current_balance": 100.50,
    "estimated_balance_after": 92.50,
    "estimated_completion_time": "2026-04-01T14:00:00Z",
    "created_at": "2026-04-01T13:00:00Z"
  }
}
```

### 5.2 获取小说详情
```http
GET /api/v1/novels/{novel_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "novel_id": "novel_1234567890",
    "title": "AI创作的奇幻冒险",
    "genre": "fantasy",
    "chapters": 18,
    "status": "running",
    "progress": 45,
    "current_step": "WriterAgent",
    "total_steps": 7,
    "estimated_cost": 8.00,
    "actual_cost": 3.60,
    "created_at": "2026-04-01T13:00:00Z",
    "started_at": "2026-04-01T13:01:00Z",
    "estimated_completion_time": "2026-04-01T14:00:00Z",
    "metadata": {
      "conflict_level": "high",
      "expert_advice": true,
      "style_reference": "reference_novel_id"
    }
  }
}
```

### 5.3 获取小说进度
```http
GET /api/v1/novels/{novel_id}/progress
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "novel_id": "novel_1234567890",
    "status": "running",
    "progress": 45,
    "current_step": "WriterAgent",
    "current_step_progress": 60,
    "total_steps": 7,
    "message": "正在生成第8章：魔法学校的秘密",
    "estimated_completion_time": "2026-04-01T14:00:00Z",
    "updated_at": "2026-04-01T13:30:00Z"
  }
}
```

### 5.4 获取小说章节
```http
GET /api/v1/novels/{novel_id}/chapters
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=10

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "chapter_id": "chapter_1234567890",
        "chapter_number": 1,
        "title": "第一章：异世界的召唤",
        "content": "在一个平凡的下午，高中生李明突然被传送到一个充满魔法的世界...",
        "word_count": 3120,
        "status": "completed",
        "created_at": "2026-04-01T13:05:00Z",
        "updated_at": "2026-04-01T13:10:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 10,
      "total": 18,
      "total_pages": 2
    }
  }
}
```

### 5.5 取消小说生成
```http
POST /api/v1/novels/{novel_id}/cancel
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "小说生成任务已取消",
  "data": {
    "novel_id": "novel_1234567890",
    "status": "cancelled",
    "refund_amount": 4.40,  // 根据进度退款
    "refunded_at": "2026-04-01T13:35:00Z"
  }
}
```

## 6. 视频生成API

### 6.1 创建视频生成任务
```http
POST /api/v1/videos
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "source_type": "novel",  // novel, external, news
  "source_id": "novel_1234567890",  // 小说ID或外部内容URL
  "title": "AI奇幻冒险动画版",
  "generation_mode": "animation",  // voice_only, subtitle_only, animation, mixed
  "duration": 180,  // 秒
  "memory_points": true,  // 是否启用记忆点设计
  "voice_style": "warm",  // warm, professional, cheerful, serious
  "subtitle_style": "modern",  // classic, modern, minimalist
  "animation_style": "cartoon",  // cartoon, realistic, anime
  "estimated_cost": 6.00  // 系统计算，用户确认
}

响应体：
{
  "code": 201,
  "message": "视频生成任务创建成功",
  "data": {
    "video_id": "video_1234567890",
    "title": "AI奇幻冒险动画版",
    "source_type": "novel",
    "source_id": "novel_1234567890",
    "generation_mode": "animation",
    "duration": 180,
    "status": "pending",
    "progress": 0,
    "estimated_cost": 6.00,
    "current_balance": 92.50,
    "estimated_balance_after": 86.50,
    "estimated_completion_time": "2026-04-01T15:30:00Z",
    "created_at": "2026-04-01T14:00:00Z"
  }
}
```

### 6.2 获取视频详情
```http
GET /api/v1/videos/{video_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "video_id": "video_1234567890",
    "title": "AI奇幻冒险动画版",
    "source_type": "novel",
    "source_id": "novel_1234567890",
    "generation_mode": "animation",
    "duration": 180,
    "status": "running",
    "progress": 60,
    "current_step": "video_rendering",
    "total_steps": 5,
    "estimated_cost": 6.00,
    "actual_cost": 3.60,
    "file_url": "https://storage.example.com/videos/video_1234567890_preview.mp4",  // 预览URL
    "file_size": 104857600,  // 文件大小，字节
    "created_at": "2026-04-01T14:00:00Z",
    "started_at": "2026-04-01T14:01:00Z",
    "estimated_completion_time": "2026-04-01T15:30:00Z",
    "metadata": {
      "memory_points": true,
      "voice_style": "warm",
      "animation_style": "cartoon"
    }
  }
}
```

### 6.3 获取视频进度
```http
GET /api/v1/videos/{video_id}/progress
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "video_id": "video_1234567890",
    "status": "running",
    "progress": 60,
    "current_step": "video_rendering",
    "current_step_progress": 75,
    "total_steps": 5,
    "message": "正在渲染视频画面，预计剩余时间15分钟",
    "estimated_completion_time": "2026-04-01T15:30:00Z",
    "updated_at": "2026-04-01T14:45:00Z"
  }
}
```

### 6.4 获取视频预览
```http
GET /api/v1/videos/{video_id}/preview
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "video_id": "video_1234567890",
    "preview_url": "https://storage.example.com/videos/video_1234567890_preview_30s.mp4",
    "preview_duration": 30,
    "thumbnail_url": "https://storage.example.com/videos/video_1234567890_thumbnail.jpg",
    "created_at": "2026-04-01T15:00:00Z"
  }
}
```

### 6.5 取消视频生成
```http
POST /api/v1/videos/{video_id}/cancel
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "视频生成任务已取消",
  "data": {
    "video_id": "video_1234567890",
    "status": "cancelled",
    "refund_amount": 2.40,  // 根据进度退款
    "refunded_at": "2026-04-01T14:50:00Z"
  }
}
```

## 7. 发布管理API

### 7.1 创建发布任务
```http
POST /api/v1/publish
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "content_type": "video",  // novel, video
  "content_id": "video_1234567890",
  "platforms": ["douyin", "xiaohongshu"],
  "publish_time": "2026-04-01T16:00:00Z",  // 立即发布传"immediate"
  "privacy": "public",  // public, followers, private
  "hashtags": ["#AI创作", "#奇幻冒险", "#动画"],
  "description": "这是一部由AI生成的奇幻冒险动画，讲述了一个普通高中生被传送到魔法世界的故事。",
  "estimated_cost": 0.40  // 发布费用
}

响应体：
{
  "code": 201,
  "message": "发布任务创建成功",
  "data": {
    "publish_id": "publish_1234567890",
    "content_type": "video",
    "content_id": "video_1234567890",
    "platforms": ["douyin", "xiaohongshu"],
    "status": "pending",
    "publish_time": "2026-04-01T16:00:00Z",
    "estimated_cost": 0.40,
    "current_balance": 86.50,
    "estimated_balance_after": 86.10,
    "created_at": "2026-04-01T15:30:00Z"
  }
}
```

### 7.2 获取发布状态
```http
GET /api/v1/publish/{publish_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "publish_id": "publish_1234567890",
    "content_type": "video",
    "content_id": "video_1234567890",
    "platforms": [
      {
        "platform": "douyin",
        "status": "published",
        "platform_content_id": "douyin_1234567890",
        "platform_url": "https://www.douyin.com/video/1234567890",
        "published_at": "2026-04-01T16:00:05Z"
      },
      {
        "platform": "xiaohongshu",
        "status": "failed",
        "error_message": "内容审核未通过",
        "failed_at": "2026-04-01T16:00:10Z"
      }
    ],
    "overall_status": "partial_success",
    "created_at": "2026-04-01T15:30:00Z",
    "completed_at": "2026-04-01T16:00:15Z"
  }
}
```

### 7.3 取消发布任务
```http
DELETE /api/v1/publish/{publish_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "发布任务已取消",
  "data": {
    "publish_id": "publish_1234567890",
    "status": "cancelled",
    "cancelled_at": "2026-04-01T15:45:00Z"
  }
}
```

### 7.4 获取发布记录
```http
GET /api/v1/publish/records
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&content_type=video&platform=douyin

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "publish_id": "publish_1234567890",
        "content_type": "video",
        "content_id": "video_1234567890",
        "title": "AI奇幻冒险动画版",
        "platforms": ["douyin", "xiaohongshu"],
        "overall_status": "partial_success",
        "created_at": "2026-04-01T15:30:00Z",
        "completed_at": "2026-04-01T16:00:15Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

## 8. API密钥管理API

### 8.1 创建API密钥
```http
POST /api/v1/apikeys
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "name": "生产环境密钥",
  "permissions": ["novel_read", "novel_write", "video_read"],
  "ip_restrictions": ["192.168.1.0/24"],
  "usage_limits": {
    "daily": 1000,
    "monthly": 30000,
    "cost": 1000.00
  },
  "expires_in_days": 30  // 0表示永不过期
}

响应体：
{
  "code": 201,
  "message": "API密钥创建成功",
  "data": {
    "key_id": "key_1234567890",
    "name": "生产环境密钥",
    "api_key": "ak_example_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  // 只显示一次
    "permissions": ["novel_read", "novel_write", "video_read"],
    "created_at": "2026-04-01T12:00:00Z",
    "expires_at": "2026-05-01T12:00:00Z",
    "warning": "请立即保存此密钥，关闭后将无法再次查看"
  }
}
```

### 8.2 获取API密钥列表
```http
GET /api/v1/apikeys
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&status=active

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "key_id": "key_1234567890",
        "name": "生产环境密钥",
        "permissions": ["novel_read", "novel_write", "video_read"],
        "status": "active",
        "created_at": "2026-04-01T12:00:00Z",
        "expires_at": "2026-05-01T12:00:00Z",
        "last_used_at": "2026-04-01T14:30:00Z",
        "usage_stats": {
          "daily_calls": 150,
          "monthly_calls": 4500,
          "total_cost": 450.00
        }
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

### 8.3 撤销API密钥
```http
DELETE /api/v1/apikeys/{key_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "API密钥已撤销",
  "data": {
    "key_id": "key_1234567890",
    "status": "revoked",
    "revoked_at": "2026-04-01T16:30:00Z"
  }
}
```

## 9. 平台账号管理API

### 9.1 绑定平台账号
```http
POST /api/v1/platforms/accounts
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "platform": "douyin",
  "auth_code": "auth_code_from_platform",  // 平台授权码
  "permissions": ["publish", "read", "manage"]  // 请求的权限
}

响应体：
{
  "code": 201,
  "message": "平台账号绑定成功",
  "data": {
    "account_id": "account_1234567890",
    "platform": "douyin",
    "account_name": "抖音用户123",
    "permissions": ["publish", "read"],
    "status": "active",
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

### 9.2 获取平台账号列表
```http
GET /api/v1/platforms/accounts
Authorization: Bearer {access_token}
查询参数：
?platform=douyin

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "account_id": "account_1234567890",
        "platform": "douyin",
        "account_name": "抖音用户123",
        "permissions": ["publish", "read"],
        "status": "active",
        "created_at": "2026-04-01T12:00:00Z",
        "last_used_at": "2026-04-01T14:30:00Z"
      }
    ]
  }
}
```

### 9.3 解绑平台账号
```http
DELETE /api/v1/platforms/accounts/{account_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "平台账号已解绑",
  "data": {
    "account_id": "account_1234567890",
    "platform": "douyin",
    "unbound_at": "2026-04-01T17:00:00Z"
  }
}
```

## 10. 实时通信API

### 10.1 WebSocket连接
```
连接URL：ws://104.244.90.202:9000/ws
认证参数：token={access_token}

消息格式：
{
  "type": "subscribe",  // subscribe, unsubscribe, message
  "channel": "task_progress",  // task_progress, notifications, chat
  "data": {
    "task_id": "novel_1234567890"
  }
}

推送消息格式：
{
  "type": "progress_update",
  "channel": "task_progress",
  "data": {
    "task_id": "novel_1234567890",
    "task_type": "novel",
    "progress": 45,
    "message": "正在生成第8章",
    "timestamp": "2026-04-01T13:30:00Z"
  }
}
```

### 10.2 通知API
```http
GET /api/v1/notifications
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&unread_only=true

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "notification_id": "notif_1234567890",
        "type": "task_completed",
        "title": "小说生成完成",
        "content": "您的小说《AI创作的奇幻冒险》已生成完成",
        "data": {
          "novel_id": "novel_1234567890",
          "title": "AI创作的奇幻冒险"
        },
        "read": false,
        "created_at": "2026-04-01T14:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1,
      "total_pages": 1
    }
  }
}
```

### 10.3 标记通知为已读
```http
PUT /api/v1/notifications/{notification_id}/read
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "通知已标记为已读"
}
```

## 11. 系统管理API（管理员）

### 11.1 获取系统状态
```http
GET /api/v1/admin/system/status
Authorization: Bearer {admin_access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "system": {
      "uptime": "7d 12h 30m",
      "version": "1.0.0",
      "status": "healthy"
    },
    "services": {
      "user_service": { "status": "up", "response_time": "50ms" },
      "novel_service": { "status": "up", "response_time": "120ms" },
      "video_service": { "status": "up", "response_time": "200ms" }
    },
    "resources": {
      "cpu_usage": "45%",
      "memory_usage": "65%",
      "disk_usage": "40%"
    },
    "business": {
      "total_users": 1000,
      "active_users": 300,
      "today_tasks": 50,
      "today_income": 500.00
    }
  }
}
```

### 11.2 获取任务统计
```http
GET /api/v1/admin/tasks/stats
Authorization: Bearer {admin_access_token}
查询参数：
?start_date=2026-04-01&end_date=2026-04-30

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "overview": {
      "total_tasks": 5000,
      "completed_tasks": 4200,
      "failed_tasks": 300,
      "cancelled_tasks": 200,
      "running_tasks": 300
    },
    "by_type": {
      "novel_generation": {
        "total": 2500,
        "completed": 2100,
        "failed": 150,
        "avg_duration": "45m",
        "total_cost": 20000.00
      },
      "video_generation": {
        "total": 2000,
        "completed": 1700,
        "failed": 120,
        "avg_duration": "90m",
        "total_cost": 12000.00
      },
      "publish": {
        "total": 500,
        "completed": 400,
        "failed": 30,
        "avg_duration": "5m",
        "total_cost": 200.00
      }
    },
    "daily_trend": [
      {
        "date": "2026-04-01",
        "total": 180,
        "completed": 150,
        "failed": 10,
        "income": 1500.00
      }
    ],
    "period": {
      "start_date": "2026-04-01",
      "end_date": "2026-04-30"
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_DATE_RANGE | 日期范围参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 403 | FORBIDDEN | 无管理员权限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 11.3 用户管理列表
```http
GET /api/v1/admin/users
Authorization: Bearer {admin_access_token}
查询参数：
?page=1&page_size=20&status=active&keyword=user123&sort_by=created_at&sort_order=desc

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "user_1234567890",
        "username": "user123",
        "email": "user@example.com",
        "phone": "+8613800138000",
        "role": "user",
        "status": "active",
        "balance": 100.50,
        "total_recharge": 500.00,
        "total_consumption": 399.50,
        "task_count": {
          "novel": 15,
          "video": 10,
          "publish": 8
        },
        "subscription": {
          "package_name": "专业版",
          "expires_at": "2026-05-01T00:00:00Z"
        },
        "created_at": "2026-03-01T10:00:00Z",
        "last_login_at": "2026-04-01T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 1000,
      "total_pages": 50
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 403 | FORBIDDEN | 无管理员权限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 11.4 收入报表
```http
GET /api/v1/admin/revenue
Authorization: Bearer {admin_access_token}
查询参数：
?start_date=2026-04-01&end_date=2026-04-30&group_by=day

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "summary": {
      "total_income": 50000.00,
      "total_recharge": 55000.00,
      "total_refund": 5000.00,
      "net_income": 50000.00,
      "total_consumption": 42000.00,
      "platform_fee": 8000.00
    },
    "by_payment_method": {
      "alipay": 25000.00,
      "wechat": 20000.00,
      "douyin": 5000.00
    },
    "by_service": {
      "novel_generation": 20000.00,
      "video_generation": 15000.00,
      "subscription": 8000.00,
      "publish": 2000.00,
      "other": 5000.00
    },
    "daily_trend": [
      {
        "date": "2026-04-01",
        "income": 1800.00,
        "recharge": 2000.00,
        "refund": 200.00,
        "consumption": 1500.00
      }
    ],
    "period": {
      "start_date": "2026-04-01",
      "end_date": "2026-04-30"
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_DATE_RANGE | 日期范围参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 403 | FORBIDDEN | 无管理员权限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 11.5 内容审核
```http
POST /api/v1/admin/content/moderate
Authorization: Bearer {admin_access_token}
Content-Type: application/json

请求体：
{
  "content_id": "novel_1234567890",
  "content_type": "novel",
  "action": "approve",
  "reason": "",
  "reviewer_note": "内容符合规范"
}

响应体：
{
  "code": 200,
  "message": "审核操作成功",
  "data": {
    "content_id": "novel_1234567890",
    "content_type": "novel",
    "previous_status": "pending_review",
    "current_status": "approved",
    "action": "approve",
    "reviewer": "admin_001",
    "reviewed_at": "2026-04-01T16:00:00Z"
  }
}
```

**请求参数说明：**
- `action`: 审核动作，可选值 `approve`（通过）、`reject`（拒绝）、`flag`（标记待处理）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_ACTION | 审核动作无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 403 | FORBIDDEN | 无管理员权限 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 409 | ALREADY_MODERATED | 内容已被审核 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 11.6 对账管理
```http
GET /api/v1/admin/reconciliation
Authorization: Bearer {admin_access_token}
查询参数：
?date=2026-04-01&payment_method=alipay&status=mismatch

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "date": "2026-04-01",
    "summary": {
      "total_orders": 500,
      "matched": 490,
      "mismatched": 8,
      "pending": 2,
      "system_total": 50000.00,
      "platform_total": 49800.00,
      "difference": 200.00
    },
    "mismatched_items": [
      {
        "order_id": "order_9876543210",
        "order_no": "202604011500001",
        "system_amount": 100.00,
        "platform_amount": 0.00,
        "payment_method": "alipay",
        "mismatch_type": "platform_missing",
        "description": "平台端未查到对应交易记录",
        "created_at": "2026-04-01T15:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 8,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_DATE | 日期参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 403 | FORBIDDEN | 无管理员权限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 12. 套餐订阅API

### 12.1 获取套餐列表
```http
GET /api/v1/packages
Authorization: Bearer {access_token}（可选，登录后可显示个性化推荐）
查询参数：
?category=individual&status=active

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "package_id": "pkg_free",
        "name": "免费体验版",
        "category": "individual",
        "description": "适合初次体验的用户",
        "price": 0.00,
        "original_price": 0.00,
        "currency": "CNY",
        "billing_cycle": "month",
        "features": {
          "novel_quota": 3,
          "video_quota": 1,
          "publish_quota": 2,
          "max_chapters": 10,
          "max_video_duration": 60,
          "priority": "low",
          "support_level": "community"
        },
        "is_recommended": false,
        "sort_order": 1,
        "status": "active"
      },
      {
        "package_id": "pkg_pro",
        "name": "专业版",
        "category": "individual",
        "description": "适合内容创作者",
        "price": 99.00,
        "original_price": 129.00,
        "currency": "CNY",
        "billing_cycle": "month",
        "features": {
          "novel_quota": 50,
          "video_quota": 20,
          "publish_quota": 100,
          "max_chapters": 100,
          "max_video_duration": 600,
          "priority": "high",
          "support_level": "email"
        },
        "is_recommended": true,
        "sort_order": 2,
        "status": "active"
      }
    ]
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.2 获取套餐详情
```http
GET /api/v1/packages/{package_id}
Authorization: Bearer {access_token}（可选）

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "package_id": "pkg_pro",
    "name": "专业版",
    "category": "individual",
    "description": "适合内容创作者，提供更多生成配额和优先处理",
    "price": 99.00,
    "original_price": 129.00,
    "currency": "CNY",
    "billing_cycle": "month",
    "features": {
      "novel_quota": 50,
      "video_quota": 20,
      "publish_quota": 100,
      "max_chapters": 100,
      "max_video_duration": 600,
      "priority": "high",
      "support_level": "email",
      "custom_voice": true,
      "advanced_style": true,
      "api_access": true
    },
    "comparison": {
      "vs_free": ["配额提升16倍", "优先队列", "邮件支持", "自定义语音"],
      "vs_enterprise": ["无专属客服", "无定制功能", "无SLA保障"]
    },
    "is_recommended": true,
    "status": "active",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 404 | PACKAGE_NOT_FOUND | 套餐不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.3 订阅套餐
```http
POST /api/v1/subscriptions
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "package_id": "pkg_pro",
  "billing_cycle": "month",
  "payment_method": "alipay",
  "coupon_code": "WELCOME2026",
  "auto_renew": true
}

响应体：
{
  "code": 201,
  "message": "订阅创建成功",
  "data": {
    "subscription_id": "sub_1234567890",
    "package_id": "pkg_pro",
    "package_name": "专业版",
    "billing_cycle": "month",
    "price": 99.00,
    "discount": 20.00,
    "actual_price": 79.00,
    "currency": "CNY",
    "auto_renew": true,
    "status": "pending_payment",
    "payment_url": "https://alipay.com/pay?order=...",
    "qr_code": "data:image/png;base64,...",
    "starts_at": null,
    "expires_at": null,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | PACKAGE_NOT_FOUND | 套餐不存在 |
| 409 | ALREADY_SUBSCRIBED | 已存在有效订阅 |
| 422 | COUPON_INVALID | 优惠券无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.4 获取当前订阅
```http
GET /api/v1/subscriptions/current
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "subscription_id": "sub_1234567890",
    "package_id": "pkg_pro",
    "package_name": "专业版",
    "billing_cycle": "month",
    "price": 99.00,
    "currency": "CNY",
    "auto_renew": true,
    "status": "active",
    "starts_at": "2026-04-01T12:00:00Z",
    "expires_at": "2026-05-01T12:00:00Z",
    "usage": {
      "novel_used": 12,
      "novel_quota": 50,
      "video_used": 5,
      "video_quota": 20,
      "publish_used": 30,
      "publish_quota": 100
    },
    "next_billing": {
      "date": "2026-05-01T12:00:00Z",
      "amount": 99.00
    },
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | NO_ACTIVE_SUBSCRIPTION | 无有效订阅 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.5 升级套餐
```http
PUT /api/v1/subscriptions/{subscription_id}/upgrade
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "target_package_id": "pkg_enterprise",
  "payment_method": "alipay",
  "prorate": true
}

响应体：
{
  "code": 200,
  "message": "套餐升级成功",
  "data": {
    "subscription_id": "sub_1234567890",
    "previous_package": "pkg_pro",
    "new_package": "pkg_enterprise",
    "prorate_credit": 50.00,
    "upgrade_cost": 149.00,
    "actual_payment": 99.00,
    "payment_url": "https://alipay.com/pay?order=...",
    "status": "pending_payment",
    "effective_at": "2026-04-01T16:00:00Z"
  }
}
```

**请求参数说明：**
- `prorate`: 是否按剩余天数折算已付费用

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_UPGRADE | 不能升级到同级或低级套餐 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | SUBSCRIPTION_NOT_FOUND | 订阅不存在 |
| 404 | PACKAGE_NOT_FOUND | 目标套餐不存在 |
| 409 | UPGRADE_IN_PROGRESS | 已有升级操作进行中 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.6 降级套餐
```http
PUT /api/v1/subscriptions/{subscription_id}/downgrade
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "target_package_id": "pkg_free"
}

响应体：
{
  "code": 200,
  "message": "套餐降级已预约",
  "data": {
    "subscription_id": "sub_1234567890",
    "current_package": "pkg_pro",
    "target_package": "pkg_free",
    "effective_at": "2026-05-01T12:00:00Z",
    "note": "降级将在当前计费周期结束后生效，届时超出新套餐配额的功能将受限"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_DOWNGRADE | 不能降级到同级或高级套餐 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | SUBSCRIPTION_NOT_FOUND | 订阅不存在 |
| 404 | PACKAGE_NOT_FOUND | 目标套餐不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.7 续费
```http
POST /api/v1/subscriptions/{subscription_id}/renew
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "months": 3,
  "payment_method": "wechat",
  "coupon_code": ""
}

响应体：
{
  "code": 200,
  "message": "续费成功",
  "data": {
    "subscription_id": "sub_1234567890",
    "package_name": "专业版",
    "renewed_months": 3,
    "price_per_month": 99.00,
    "total_price": 267.30,
    "discount": 29.70,
    "discount_note": "季度续费享9折优惠",
    "payment_url": "https://wx.tenpay.com/pay?order=...",
    "new_expires_at": "2026-08-01T12:00:00Z",
    "created_at": "2026-04-01T16:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_MONTHS | 续费月数无效（支持1/3/6/12） |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | SUBSCRIPTION_NOT_FOUND | 订阅不存在 |
| 422 | COUPON_INVALID | 优惠券无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.8 取消订阅
```http
DELETE /api/v1/subscriptions/{subscription_id}
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "reason": "价格太贵",
  "feedback": "希望提供更多灵活的按次付费选项"
}

响应体：
{
  "code": 200,
  "message": "订阅已取消",
  "data": {
    "subscription_id": "sub_1234567890",
    "status": "cancelled",
    "effective_at": "2026-05-01T12:00:00Z",
    "refund_amount": 0.00,
    "note": "订阅将在当前计费周期结束后失效，剩余配额可继续使用至到期日",
    "cancelled_at": "2026-04-01T16:30:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | SUBSCRIPTION_NOT_FOUND | 订阅不存在 |
| 409 | ALREADY_CANCELLED | 订阅已取消 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.9 获取发票列表
```http
GET /api/v1/invoices
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&status=issued&start_date=2026-01-01&end_date=2026-04-30

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "invoice_id": "inv_1234567890",
        "invoice_no": "FP202604010001",
        "type": "electronic",
        "title": "个人",
        "amount": 99.00,
        "tax_amount": 5.61,
        "status": "issued",
        "related_orders": ["order_1234567890"],
        "download_url": "https://storage.example.com/invoices/inv_1234567890.pdf",
        "issued_at": "2026-04-02T10:00:00Z",
        "created_at": "2026-04-01T16:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 5,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 12.10 申请开票
```http
POST /api/v1/invoices
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "type": "electronic",
  "title_type": "company",
  "title": "XX科技有限公司",
  "tax_id": "91110000MA01XXXXX",
  "bank_name": "中国工商银行北京支行",
  "bank_account": "0200001234567890",
  "address": "北京市朝阳区XXX",
  "phone": "010-12345678",
  "email": "finance@example.com",
  "order_ids": ["order_1234567890", "order_0987654321"],
  "remark": ""
}

响应体：
{
  "code": 201,
  "message": "开票申请已提交",
  "data": {
    "invoice_id": "inv_2345678901",
    "type": "electronic",
    "title": "XX科技有限公司",
    "amount": 198.00,
    "tax_amount": 11.22,
    "status": "processing",
    "estimated_issue_time": "2026-04-03T10:00:00Z",
    "created_at": "2026-04-01T17:00:00Z"
  }
}
```

**请求参数说明：**
- `type`: 发票类型，`electronic`（电子发票）、`paper`（纸质发票）
- `title_type`: 抬头类型，`personal`（个人）、`company`（企业）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 400 | INVALID_TAX_ID | 税号格式不正确 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | ORDER_NOT_FOUND | 关联订单不存在 |
| 409 | ALREADY_INVOICED | 订单已开票 |
| 422 | AMOUNT_TOO_LOW | 开票金额不满足最低要求 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 13. OpenClaw专用API

> OpenClaw接口使用API Key认证，通过 `X-API-Key` 请求头传递密钥，不使用Bearer Token。

### 13.1 提交任务
```http
POST /api/v1/openclaw/tasks
X-API-Key: {api_key}
Content-Type: application/json

请求体：
{
  "task_type": "novel_to_video",
  "params": {
    "title": "AI奇幻冒险",
    "genre": "fantasy",
    "chapters": 10,
    "words_per_chapter": 3000,
    "video_mode": "animation",
    "voice_style": "warm",
    "animation_style": "anime"
  },
  "priority": "normal",
  "callback_url": "https://client.example.com/webhook/task-complete",
  "idempotency_key": "idem_abc123"
}

响应体：
{
  "code": 201,
  "message": "任务提交成功",
  "data": {
    "task_id": "task_oc_1234567890",
    "task_type": "novel_to_video",
    "status": "queued",
    "priority": "normal",
    "estimated_cost": 14.00,
    "estimated_duration": "120m",
    "queue_position": 5,
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**请求参数说明：**
- `task_type`: 任务类型，`novel`（仅生成小说）、`video`（仅生成视频）、`novel_to_video`（小说+视频全流程）
- `priority`: 优先级，`low`、`normal`、`high`（高优先级额外收费）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 402 | INSUFFICIENT_BALANCE | 余额不足 |
| 409 | IDEMPOTENCY_CONFLICT | 幂等键冲突，任务已提交 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.2 获取任务详情
```http
GET /api/v1/openclaw/tasks/{task_id}
X-API-Key: {api_key}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_oc_1234567890",
    "task_type": "novel_to_video",
    "status": "running",
    "progress": 55,
    "current_stage": "video_generation",
    "stages": [
      {"name": "novel_generation", "status": "completed", "progress": 100},
      {"name": "video_generation", "status": "running", "progress": 30},
      {"name": "publish", "status": "pending", "progress": 0}
    ],
    "params": {
      "title": "AI奇幻冒险",
      "genre": "fantasy",
      "chapters": 10
    },
    "result": {
      "novel_id": "novel_oc_1234567890",
      "video_id": null
    },
    "cost": {
      "estimated": 14.00,
      "actual": 7.70
    },
    "created_at": "2026-04-01T12:00:00Z",
    "started_at": "2026-04-01T12:02:00Z",
    "estimated_completion_time": "2026-04-01T14:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 404 | TASK_NOT_FOUND | 任务不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.3 获取实时进度
```http
GET /api/v1/openclaw/tasks/{task_id}/progress
X-API-Key: {api_key}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "task_oc_1234567890",
    "status": "running",
    "progress": 55,
    "current_stage": "video_generation",
    "current_stage_progress": 30,
    "message": "正在生成第3段视频画面",
    "logs": [
      {"time": "2026-04-01T12:02:00Z", "level": "info", "message": "任务开始执行"},
      {"time": "2026-04-01T12:05:00Z", "level": "info", "message": "小说大纲生成完成"},
      {"time": "2026-04-01T12:45:00Z", "level": "info", "message": "小说生成完成，共10章"},
      {"time": "2026-04-01T12:46:00Z", "level": "info", "message": "开始生成视频"}
    ],
    "estimated_remaining": "45m",
    "updated_at": "2026-04-01T13:15:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 404 | TASK_NOT_FOUND | 任务不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.4 取消任务
```http
POST /api/v1/openclaw/tasks/{task_id}/cancel
X-API-Key: {api_key}
Content-Type: application/json

请求体：
{
  "reason": "不再需要此任务"
}

响应体：
{
  "code": 200,
  "message": "任务取消成功",
  "data": {
    "task_id": "task_oc_1234567890",
    "previous_status": "running",
    "status": "cancelled",
    "refund_amount": 6.30,
    "refund_note": "已按完成进度55%计算退款",
    "cancelled_at": "2026-04-01T13:20:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 404 | TASK_NOT_FOUND | 任务不存在 |
| 409 | TASK_NOT_CANCELLABLE | 任务已完成或已取消，无法取消 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.5 余额查询
```http
GET /api/v1/openclaw/user/balance
X-API-Key: {api_key}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "balance": 256.80,
    "currency": "CNY",
    "frozen_amount": 14.00,
    "available_amount": 242.80,
    "total_recharge": 500.00,
    "total_consumption": 243.20,
    "last_recharge_at": "2026-04-01T10:00:00Z",
    "last_consumption_at": "2026-04-01T12:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.6 套餐信息
```http
GET /api/v1/openclaw/user/packages
X-API-Key: {api_key}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "current_package": {
      "package_id": "pkg_pro",
      "name": "专业版",
      "expires_at": "2026-05-01T12:00:00Z"
    },
    "usage": {
      "novel_used": 12,
      "novel_quota": 50,
      "video_used": 5,
      "video_quota": 20,
      "publish_used": 30,
      "publish_quota": 100
    },
    "api_limits": {
      "daily_calls": 150,
      "daily_limit": 1000,
      "monthly_calls": 4500,
      "monthly_limit": 30000
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.7 充值
```http
POST /api/v1/openclaw/user/recharge
X-API-Key: {api_key}
Content-Type: application/json

请求体：
{
  "amount": 200.00,
  "payment_method": "alipay",
  "return_url": "https://client.example.com/recharge/callback"
}

响应体：
{
  "code": 201,
  "message": "充值订单创建成功",
  "data": {
    "order_id": "order_oc_1234567890",
    "amount": 200.00,
    "currency": "CNY",
    "payment_method": "alipay",
    "status": "pending",
    "payment_url": "https://alipay.com/pay?order=...",
    "expires_at": "2026-04-01T12:30:00Z",
    "created_at": "2026-04-01T12:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_AMOUNT | 充值金额无效（最低10元） |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 400 | INVALID_PAYMENT_METHOD | 支付方式不支持 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.8 小说列表
```http
GET /api/v1/openclaw/novels
X-API-Key: {api_key}
查询参数：
?page=1&page_size=20&status=completed&genre=fantasy

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "novel_id": "novel_oc_1234567890",
        "title": "AI奇幻冒险",
        "genre": "fantasy",
        "chapters": 10,
        "total_words": 30000,
        "status": "completed",
        "cost": 5.00,
        "created_at": "2026-04-01T12:00:00Z",
        "completed_at": "2026-04-01T12:45:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 15,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.9 章节列表
```http
GET /api/v1/openclaw/novels/{novel_id}/chapters
X-API-Key: {api_key}
查询参数：
?page=1&page_size=50

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "novel_id": "novel_oc_1234567890",
    "title": "AI奇幻冒险",
    "items": [
      {
        "chapter_id": "chapter_oc_001",
        "chapter_number": 1,
        "title": "第一章：异世界的召唤",
        "content": "在一个平凡的下午...",
        "word_count": 3120,
        "status": "completed",
        "created_at": "2026-04-01T12:05:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total": 10,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 404 | NOVEL_NOT_FOUND | 小说不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.10 视频列表
```http
GET /api/v1/openclaw/videos
X-API-Key: {api_key}
查询参数：
?page=1&page_size=20&status=completed

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "video_id": "video_oc_1234567890",
        "title": "AI奇幻冒险动画版",
        "source_novel_id": "novel_oc_1234567890",
        "duration": 180,
        "file_size": 104857600,
        "file_url": "https://storage.example.com/videos/video_oc_1234567890.mp4",
        "thumbnail_url": "https://storage.example.com/videos/video_oc_1234567890_thumb.jpg",
        "status": "completed",
        "cost": 9.00,
        "created_at": "2026-04-01T12:46:00Z",
        "completed_at": "2026-04-01T14:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 8,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.11 发布内容
```http
POST /api/v1/openclaw/publish
X-API-Key: {api_key}
Content-Type: application/json

请求体：
{
  "content_type": "video",
  "content_id": "video_oc_1234567890",
  "platforms": ["douyin", "xiaohongshu"],
  "publish_time": "immediate",
  "title": "AI奇幻冒险动画版",
  "description": "由AI生成的奇幻冒险动画短片",
  "hashtags": ["#AI创作", "#奇幻冒险"],
  "privacy": "public"
}

响应体：
{
  "code": 201,
  "message": "发布任务创建成功",
  "data": {
    "publish_id": "pub_oc_1234567890",
    "content_type": "video",
    "content_id": "video_oc_1234567890",
    "platforms": ["douyin", "xiaohongshu"],
    "status": "publishing",
    "estimated_cost": 0.40,
    "created_at": "2026-04-01T14:10:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 402 | INSUFFICIENT_BALANCE | 余额不足 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 422 | PLATFORM_NOT_BOUND | 目标平台账号未绑定 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.12 获取系统配置
```http
GET /api/v1/openclaw/config
X-API-Key: {api_key}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "pricing": {
      "novel_per_chapter": 0.50,
      "video_per_minute": 2.00,
      "publish_per_platform": 0.20,
      "high_priority_multiplier": 1.5
    },
    "limits": {
      "max_chapters": 100,
      "max_video_duration": 600,
      "max_concurrent_tasks": 5,
      "max_file_size": 2147483648
    },
    "supported_genres": ["fantasy", "romance", "sci_fi", "urban", "historical", "mystery", "horror"],
    "supported_platforms": ["douyin", "xiaohongshu", "bilibili", "kuaishou", "weibo"],
    "voice_styles": ["warm", "professional", "cheerful", "serious", "storytelling"],
    "animation_styles": ["cartoon", "realistic", "anime", "watercolor", "pixel"],
    "system_notice": "",
    "maintenance_window": null
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 13.13 更新配置
```http
POST /api/v1/openclaw/config/update
X-API-Key: {api_key}
Content-Type: application/json

请求体：
{
  "callback_url": "https://client.example.com/webhook/new-callback",
  "default_priority": "normal",
  "default_voice_style": "warm",
  "default_animation_style": "anime",
  "auto_publish": false,
  "notification_email": "dev@example.com"
}

响应体：
{
  "code": 200,
  "message": "配置更新成功",
  "data": {
    "callback_url": "https://client.example.com/webhook/new-callback",
    "default_priority": "normal",
    "default_voice_style": "warm",
    "default_animation_style": "anime",
    "auto_publish": false,
    "notification_email": "dev@example.com",
    "updated_at": "2026-04-01T15:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 400 | INVALID_CALLBACK_URL | 回调地址格式无效 |
| 401 | INVALID_API_KEY | API Key无效或已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 14. 多端认证API

### 14.1 微信登录
```http
POST /api/v1/auth/wechat
Content-Type: application/json

请求体：
{
  "code": "wechat_auth_code_from_client",
  "platform": "mini_program",
  "encrypted_data": "...",
  "iv": "..."
}

响应体：
{
  "code": 200,
  "message": "微信登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "is_new_user": false,
    "user": {
      "id": "user_1234567890",
      "username": "微信用户_abc123",
      "avatar": "https://thirdwx.qlogo.cn/...",
      "balance": 100.50,
      "role": "user"
    }
  }
}
```

**请求参数说明：**
- `platform`: 微信端类型，`mini_program`（小程序）、`official_account`（公众号）、`open_platform`（开放平台）
- `encrypted_data` / `iv`: 小程序获取手机号时使用，可选

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_CODE | 微信授权码无效 |
| 400 | WECHAT_AUTH_FAILED | 微信认证失败（code2session返回错误） |
| 422 | DECRYPT_FAILED | 加密数据解密失败 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 14.2 抖音登录
```http
POST /api/v1/auth/douyin
Content-Type: application/json

请求体：
{
  "code": "douyin_auth_code_from_client",
  "anonymous_code": ""
}

响应体：
{
  "code": 200,
  "message": "抖音登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "is_new_user": true,
    "user": {
      "id": "user_2345678901",
      "username": "抖音用户_def456",
      "avatar": "https://p3.douyinpic.com/...",
      "balance": 0.00,
      "role": "user"
    }
  }
}
```

**请求参数说明：**
- `anonymous_code`: 抖音匿名登录码，用于静默登录场景，可选

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_CODE | 抖音授权码无效 |
| 400 | DOUYIN_AUTH_FAILED | 抖音认证失败 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 14.3 手机号验证码登录
```http
POST /api/v1/auth/phone
Content-Type: application/json

请求体：
{
  "phone": "+8613800138000",
  "code": "123456",
  "scene": "login"
}

响应体：
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "is_new_user": false,
    "user": {
      "id": "user_1234567890",
      "username": "user123",
      "phone": "+8613800138000",
      "balance": 100.50,
      "role": "user"
    }
  }
}
```

**请求参数说明：**
- `scene`: 场景，`login`（登录/注册）、`bind`（绑定手机号）、`reset_password`（重置密码）
- 验证码需通过独立的发送验证码接口获取

**前置接口 - 发送验证码：**
```http
POST /api/v1/auth/phone/send-code
Content-Type: application/json

请求体：
{
  "phone": "+8613800138000",
  "scene": "login"
}

响应体：
{
  "code": 200,
  "message": "验证码已发送",
  "data": {
    "expires_in": 300,
    "resend_after": 60
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PHONE | 手机号格式不正确 |
| 400 | INVALID_CODE | 验证码错误或已过期 |
| 429 | CODE_SEND_TOO_FREQUENT | 验证码发送过于频繁 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 14.4 绑定第三方账号
```http
POST /api/v1/auth/bind
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "provider": "wechat",
  "code": "wechat_auth_code",
  "platform": "mini_program"
}

响应体：
{
  "code": 200,
  "message": "绑定成功",
  "data": {
    "binding_id": "bind_1234567890",
    "provider": "wechat",
    "provider_user_id": "wx_openid_abc123",
    "provider_nickname": "微信昵称",
    "provider_avatar": "https://thirdwx.qlogo.cn/...",
    "bound_at": "2026-04-01T12:00:00Z"
  }
}
```

**请求参数说明：**
- `provider`: 第三方平台，`wechat`、`douyin`、`qq`、`weibo`、`apple`

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_CODE | 授权码无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 409 | ALREADY_BOUND | 该第三方账号已绑定其他用户 |
| 409 | PROVIDER_ALREADY_BOUND | 当前用户已绑定该平台的其他账号 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 14.5 已绑定账号列表
```http
GET /api/v1/auth/bindings
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "binding_id": "bind_1234567890",
        "provider": "wechat",
        "provider_nickname": "微信昵称",
        "provider_avatar": "https://thirdwx.qlogo.cn/...",
        "bound_at": "2026-04-01T12:00:00Z"
      },
      {
        "binding_id": "bind_2345678901",
        "provider": "douyin",
        "provider_nickname": "抖音昵称",
        "provider_avatar": "https://p3.douyinpic.com/...",
        "bound_at": "2026-03-15T08:00:00Z"
      }
    ],
    "supported_providers": ["wechat", "douyin", "qq", "weibo", "apple"]
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 15. 支付增强API

### 15.1 支付宝支付回调
```http
POST /api/v1/payments/webhook/alipay
Content-Type: application/x-www-form-urlencoded

请求体（支付宝异步通知标准参数）：
{
  "notify_time": "2026-04-01 12:05:00",
  "notify_type": "trade_status_sync",
  "notify_id": "ac05099524730693a8b330c5ecXXXX",
  "app_id": "2026XXXXXXXXXX",
  "charset": "utf-8",
  "version": "1.0",
  "sign_type": "RSA2",
  "sign": "...",
  "trade_no": "2026040122001XXXXXXX",
  "out_trade_no": "202604011200001",
  "trade_status": "TRADE_SUCCESS",
  "total_amount": "100.00",
  "buyer_id": "2088XXXXXXXX"
}

响应体（固定返回格式）：
success
```

**认证方式：** 无Bearer Token，通过支付宝签名验证请求合法性

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_SIGN | 签名验证失败 |
| 400 | INVALID_PARAMS | 通知参数不完整 |
| 404 | ORDER_NOT_FOUND | 对应订单不存在 |
| 409 | ORDER_ALREADY_PROCESSED | 订单已处理 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 15.2 微信支付回调
```http
POST /api/v1/payments/webhook/wechat
Content-Type: application/json

请求头（微信支付V3签名）：
Wechatpay-Timestamp: 1617019200
Wechatpay-Nonce: fdasflkja484w
Wechatpay-Signature: xxxxxxxx
Wechatpay-Serial: XXXXXXXXXX

请求体（微信支付V3通知标准格式）：
{
  "id": "EV-2026040112000000001",
  "create_time": "2026-04-01T12:05:00+08:00",
  "resource_type": "encrypt-resource",
  "event_type": "TRANSACTION.SUCCESS",
  "summary": "支付成功",
  "resource": {
    "original_type": "transaction",
    "algorithm": "AEAD_AES_256_GCM",
    "ciphertext": "...",
    "associated_data": "transaction",
    "nonce": "fdasflkja484w"
  }
}

响应体：
{
  "code": "SUCCESS",
  "message": "成功"
}
```

**认证方式：** 无Bearer Token，通过微信支付V3签名验证请求合法性

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_SIGN | 签名验证失败 |
| 400 | DECRYPT_FAILED | 通知数据解密失败 |
| 404 | ORDER_NOT_FOUND | 对应订单不存在 |
| 409 | ORDER_ALREADY_PROCESSED | 订单已处理 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 15.3 抖音支付回调
```http
POST /api/v1/payments/webhook/douyin
Content-Type: application/json

请求体（抖音支付异步通知标准格式）：
{
  "timestamp": "1617019200",
  "nonce": "fdasflkja484w",
  "msg": "{\"appid\":\"ttXXXXXX\",\"cp_orderno\":\"202604011200001\",\"cp_extra\":\"\",\"way\":\"2\",\"channel_no\":\"2026040112000001\",\"payment_order_no\":\"PO2026040112000001\",\"total_amount\":10000,\"status\":\"SUCCESS\"}",
  "msg_signature": "xxxxxxxx",
  "type": "payment"
}

响应体：
{
  "err_no": 0,
  "err_tips": "success"
}
```

**认证方式：** 无Bearer Token，通过抖音支付签名验证请求合法性

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_SIGN | 签名验证失败 |
| 400 | INVALID_MSG | 通知消息解析失败 |
| 404 | ORDER_NOT_FOUND | 对应订单不存在 |
| 409 | ORDER_ALREADY_PROCESSED | 订单已处理 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 15.4 申请退款
```http
POST /api/v1/refunds
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "order_id": "order_1234567890",
  "reason": "服务不满意",
  "refund_amount": 50.00,
  "description": "视频生成质量未达到预期"
}

响应体：
{
  "code": 201,
  "message": "退款申请已提交",
  "data": {
    "refund_id": "refund_1234567890",
    "order_id": "order_1234567890",
    "refund_amount": 50.00,
    "currency": "CNY",
    "reason": "服务不满意",
    "status": "pending",
    "estimated_process_time": "1-3个工作日",
    "created_at": "2026-04-01T16:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 400 | REFUND_AMOUNT_EXCEEDED | 退款金额超过订单金额 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | ORDER_NOT_FOUND | 订单不存在 |
| 409 | REFUND_ALREADY_REQUESTED | 已有退款申请进行中 |
| 422 | REFUND_PERIOD_EXPIRED | 已超过可退款期限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 15.5 退款状态查询
```http
GET /api/v1/refunds/{refund_id}
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "refund_id": "refund_1234567890",
    "order_id": "order_1234567890",
    "refund_amount": 50.00,
    "currency": "CNY",
    "reason": "服务不满意",
    "status": "approved",
    "refund_method": "original_payment",
    "payment_method": "alipay",
    "process_note": "退款已原路退回",
    "created_at": "2026-04-01T16:00:00Z",
    "approved_at": "2026-04-02T10:00:00Z",
    "refunded_at": "2026-04-02T10:05:00Z"
  }
}
```

**响应字段说明：**
- `status`: 退款状态，`pending`（待审核）、`approved`（已批准）、`refunded`（已退款）、`rejected`（已拒绝）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | REFUND_NOT_FOUND | 退款记录不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 15.6 每日对账报告
```http
GET /api/v1/reconciliation/daily
Authorization: Bearer {access_token}
查询参数：
?date=2026-04-01

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "date": "2026-04-01",
    "summary": {
      "total_income": 1500.00,
      "total_recharge": 1800.00,
      "total_consumption": 1500.00,
      "total_refund": 300.00,
      "balance_change": 0.00
    },
    "transactions": [
      {
        "transaction_id": "txn_1234567890",
        "type": "recharge",
        "amount": 100.00,
        "payment_method": "alipay",
        "order_id": "order_1234567890",
        "status": "completed",
        "created_at": "2026-04-01T10:00:00Z"
      },
      {
        "transaction_id": "txn_2345678901",
        "type": "consumption",
        "amount": -8.00,
        "service": "novel_generation",
        "related_id": "novel_1234567890",
        "status": "completed",
        "created_at": "2026-04-01T13:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total": 25,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_DATE | 日期参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | REPORT_NOT_READY | 当日对账报告尚未生成 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 16. 内容广场API

### 16.1 广场内容列表
```http
GET /api/v1/square/contents
Authorization: Bearer {access_token}（可选，登录后可显示个性化推荐和互动状态）
查询参数：
?page=1&page_size=20&category=video&sort_by=hot&genre=fantasy

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "content_id": "sq_1234567890",
        "content_type": "video",
        "title": "AI奇幻冒险动画版",
        "description": "由AI生成的奇幻冒险动画短片，讲述了高中生李明的异世界之旅",
        "cover_url": "https://storage.example.com/covers/sq_1234567890.jpg",
        "preview_url": "https://storage.example.com/previews/sq_1234567890.mp4",
        "genre": "fantasy",
        "duration": 180,
        "author": {
          "user_id": "user_1234567890",
          "username": "创作达人",
          "avatar": "https://example.com/avatars/user123.jpg",
          "is_verified": true
        },
        "stats": {
          "likes": 1250,
          "collects": 340,
          "comments": 89,
          "views": 15600,
          "shares": 56
        },
        "interaction": {
          "is_liked": false,
          "is_collected": true
        },
        "tags": ["AI创作", "奇幻", "动画"],
        "created_at": "2026-04-01T16:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 500,
      "total_pages": 25
    }
  }
}
```

**查询参数说明：**
- `category`: 内容类型，`all`（全部）、`novel`（小说）、`video`（视频）
- `sort_by`: 排序方式，`hot`（热门）、`new`（最新）、`recommended`（推荐）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 16.2 点赞
```http
POST /api/v1/square/contents/{content_id}/like
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "点赞成功",
  "data": {
    "content_id": "sq_1234567890",
    "is_liked": true,
    "total_likes": 1251
  }
}
```

**说明：** 再次调用同一接口执行取消点赞操作（Toggle行为）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 16.3 收藏
```http
POST /api/v1/square/contents/{content_id}/collect
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "收藏成功",
  "data": {
    "content_id": "sq_1234567890",
    "is_collected": true,
    "total_collects": 341
  }
}
```

**说明：** 再次调用同一接口执行取消收藏操作（Toggle行为）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 16.4 评论
```http
POST /api/v1/square/contents/{content_id}/comment
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "content": "这个视频做得太棒了！画风很喜欢",
  "parent_id": null
}

响应体：
{
  "code": 201,
  "message": "评论成功",
  "data": {
    "comment_id": "cmt_1234567890",
    "content_id": "sq_1234567890",
    "content": "这个视频做得太棒了！画风很喜欢",
    "parent_id": null,
    "author": {
      "user_id": "user_1234567890",
      "username": "user123",
      "avatar": "https://example.com/avatars/user123.jpg"
    },
    "created_at": "2026-04-01T17:00:00Z"
  }
}
```

**请求参数说明：**
- `parent_id`: 回复评论时填写父评论ID，顶级评论传 `null`

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_CONTENT | 评论内容为空或超过长度限制 |
| 400 | CONTAINS_SENSITIVE_WORDS | 评论包含敏感词 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 404 | PARENT_COMMENT_NOT_FOUND | 父评论不存在 |
| 429 | COMMENT_TOO_FREQUENT | 评论过于频繁 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 16.5 举报
```http
POST /api/v1/square/contents/{content_id}/report
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "reason": "inappropriate",
  "description": "内容包含不当信息",
  "screenshots": ["https://storage.example.com/reports/screenshot1.jpg"]
}

响应体：
{
  "code": 201,
  "message": "举报已提交",
  "data": {
    "report_id": "rpt_1234567890",
    "content_id": "sq_1234567890",
    "reason": "inappropriate",
    "status": "pending",
    "created_at": "2026-04-01T17:30:00Z"
  }
}
```

**请求参数说明：**
- `reason`: 举报原因，`inappropriate`（不当内容）、`copyright`（侵权）、`spam`（垃圾信息）、`violence`（暴力）、`other`（其他）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_REASON | 举报原因无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 409 | ALREADY_REPORTED | 您已举报过该内容 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 16.6 排行榜
```http
GET /api/v1/square/rankings
Authorization: Bearer {access_token}（可选）
查询参数：
?type=hot&period=week&category=video&limit=50

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "ranking_type": "hot",
    "period": "week",
    "period_range": {
      "start": "2026-03-25T00:00:00Z",
      "end": "2026-04-01T00:00:00Z"
    },
    "items": [
      {
        "rank": 1,
        "content_id": "sq_1234567890",
        "content_type": "video",
        "title": "AI奇幻冒险动画版",
        "cover_url": "https://storage.example.com/covers/sq_1234567890.jpg",
        "author": {
          "user_id": "user_1234567890",
          "username": "创作达人",
          "avatar": "https://example.com/avatars/user123.jpg"
        },
        "stats": {
          "likes": 12500,
          "views": 156000,
          "score": 98.5
        },
        "trend": "up",
        "rank_change": 3
      }
    ],
    "updated_at": "2026-04-01T00:00:00Z"
  }
}
```

**查询参数说明：**
- `type`: 排行榜类型，`hot`（热度榜）、`new`（新作榜）、`quality`（质量榜）
- `period`: 时间范围，`day`（日榜）、`week`（周榜）、`month`（月榜）、`all`（总榜）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 17. 发布增强API

### 17.1 支持的发布平台列表
```http
GET /api/v1/platforms
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "platform_id": "douyin",
        "name": "抖音",
        "icon_url": "https://storage.example.com/icons/douyin.png",
        "supported_content_types": ["video"],
        "max_video_duration": 900,
        "max_file_size": 4294967296,
        "supported_formats": ["mp4", "mov"],
        "requires_auth": true,
        "auth_type": "oauth2",
        "status": "active",
        "features": ["scheduled_publish", "analytics", "comment_management"]
      },
      {
        "platform_id": "xiaohongshu",
        "name": "小红书",
        "icon_url": "https://storage.example.com/icons/xhs.png",
        "supported_content_types": ["video", "image", "text"],
        "max_video_duration": 600,
        "max_file_size": 2147483648,
        "supported_formats": ["mp4", "jpg", "png"],
        "requires_auth": true,
        "auth_type": "oauth2",
        "status": "active",
        "features": ["scheduled_publish", "analytics"]
      },
      {
        "platform_id": "bilibili",
        "name": "哔哩哔哩",
        "icon_url": "https://storage.example.com/icons/bilibili.png",
        "supported_content_types": ["video"],
        "max_video_duration": 14400,
        "max_file_size": 8589934592,
        "supported_formats": ["mp4", "flv"],
        "requires_auth": true,
        "auth_type": "oauth2",
        "status": "active",
        "features": ["scheduled_publish", "analytics", "danmaku"]
      }
    ]
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 17.2 绑定平台账号（OAuth）
```http
POST /api/v1/platforms/{platform_id}/bind
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "redirect_uri": "https://example.com/callback/douyin",
  "state": "random_state_string"
}

响应体：
{
  "code": 200,
  "message": "请前往授权页面完成绑定",
  "data": {
    "auth_url": "https://open.douyin.com/platform/oauth/connect?client_key=xxx&redirect_uri=xxx&state=xxx&scope=xxx",
    "state": "random_state_string",
    "expires_in": 300
  }
}
```

**OAuth回调处理：**
```http
GET /api/v1/platforms/{platform_id}/bind/callback
查询参数：
?code=auth_code_from_platform&state=random_state_string

响应体：
{
  "code": 200,
  "message": "平台账号绑定成功",
  "data": {
    "account_id": "account_1234567890",
    "platform": "douyin",
    "account_name": "抖音用户123",
    "account_avatar": "https://p3.douyinpic.com/...",
    "permissions": ["publish", "read", "analytics"],
    "bound_at": "2026-04-01T12:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_REDIRECT_URI | 回调地址不在白名单中 |
| 400 | INVALID_STATE | state参数不匹配 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | PLATFORM_NOT_FOUND | 平台不存在 |
| 409 | PLATFORM_ALREADY_BOUND | 已绑定该平台账号 |
| 422 | OAUTH_FAILED | 平台授权失败 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 17.3 平台账号状态
```http
GET /api/v1/platforms/{platform_id}/status
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "platform_id": "douyin",
    "platform_name": "抖音",
    "is_bound": true,
    "account": {
      "account_id": "account_1234567890",
      "account_name": "抖音用户123",
      "account_avatar": "https://p3.douyinpic.com/...",
      "permissions": ["publish", "read", "analytics"],
      "token_status": "valid",
      "token_expires_at": "2026-05-01T12:00:00Z"
    },
    "publish_stats": {
      "total_published": 25,
      "last_published_at": "2026-04-01T16:00:00Z",
      "total_views": 50000,
      "total_likes": 3200
    },
    "bound_at": "2026-03-01T10:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | PLATFORM_NOT_FOUND | 平台不存在 |
| 404 | PLATFORM_NOT_BOUND | 未绑定该平台 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 17.4 定时发布
```http
POST /api/v1/publish/schedule
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "content_type": "video",
  "content_id": "video_1234567890",
  "platforms": ["douyin", "bilibili"],
  "scheduled_at": "2026-04-02T18:00:00+08:00",
  "title": "AI奇幻冒险动画版",
  "description": "由AI生成的奇幻冒险动画短片",
  "hashtags": ["#AI创作", "#奇幻冒险"],
  "privacy": "public",
  "platform_specific": {
    "douyin": {
      "cover_time": 5.0,
      "allow_duet": true,
      "allow_stitch": true
    },
    "bilibili": {
      "partition": 27,
      "tag": "动画,AI",
      "allow_reprint": false
    }
  }
}

响应体：
{
  "code": 201,
  "message": "定时发布任务创建成功",
  "data": {
    "schedule_id": "sch_1234567890",
    "content_type": "video",
    "content_id": "video_1234567890",
    "platforms": ["douyin", "bilibili"],
    "scheduled_at": "2026-04-02T18:00:00+08:00",
    "status": "scheduled",
    "estimated_cost": 0.40,
    "created_at": "2026-04-01T17:00:00Z"
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 400 | INVALID_SCHEDULE_TIME | 定时发布时间必须在当前时间之后 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 402 | INSUFFICIENT_BALANCE | 余额不足 |
| 404 | CONTENT_NOT_FOUND | 内容不存在 |
| 422 | PLATFORM_NOT_BOUND | 目标平台账号未绑定 |
| 422 | PLATFORM_TOKEN_EXPIRED | 平台授权已过期，请重新绑定 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 17.5 发布数据分析
```http
GET /api/v1/publish/{publish_id}/analytics
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "publish_id": "publish_1234567890",
    "content_type": "video",
    "title": "AI奇幻冒险动画版",
    "published_at": "2026-04-01T16:00:00Z",
    "platforms": [
      {
        "platform": "douyin",
        "platform_url": "https://www.douyin.com/video/1234567890",
        "metrics": {
          "views": 15600,
          "likes": 1250,
          "comments": 89,
          "shares": 56,
          "favorites": 340,
          "watch_duration_avg": 45.5,
          "completion_rate": 0.68,
          "follower_gain": 12
        },
        "audience": {
          "gender": {"male": 0.45, "female": 0.55},
          "age_groups": {"18-24": 0.35, "25-34": 0.40, "35-44": 0.15, "45+": 0.10},
          "top_cities": ["北京", "上海", "广州", "深圳", "杭州"]
        },
        "trend": [
          {"date": "2026-04-01", "views": 8000, "likes": 600},
          {"date": "2026-04-02", "views": 5000, "likes": 400},
          {"date": "2026-04-03", "views": 2600, "likes": 250}
        ],
        "updated_at": "2026-04-03T00:00:00Z"
      }
    ],
    "total_metrics": {
      "total_views": 25600,
      "total_likes": 2100,
      "total_comments": 156,
      "total_shares": 89
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | PUBLISH_NOT_FOUND | 发布记录不存在 |
| 404 | ANALYTICS_NOT_AVAILABLE | 数据分析尚未就绪 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 18. 视频评审API

### 18.1 获取评审结果
```http
GET /api/v1/videos/{video_id}/review
Authorization: Bearer {access_token}

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "video_id": "video_1234567890",
    "review_status": "reviewed",
    "auto_review": {
      "score": 85,
      "passed": true,
      "checks": [
        {"item": "content_safety", "passed": true, "score": 95, "detail": "未检测到违规内容"},
        {"item": "video_quality", "passed": true, "score": 80, "detail": "画质清晰，帧率稳定"},
        {"item": "audio_quality", "passed": true, "score": 88, "detail": "语音清晰，无杂音"},
        {"item": "subtitle_accuracy", "passed": true, "score": 78, "detail": "字幕与语音基本一致，个别时间轴偏差"},
        {"item": "copyright_check", "passed": true, "score": 100, "detail": "未检测到侵权素材"}
      ],
      "suggestions": [
        "建议优化字幕时间轴，部分段落存在0.5秒偏差",
        "建议增加片尾引导关注画面"
      ],
      "reviewed_at": "2026-04-01T14:30:00Z"
    },
    "manual_review": null
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | VIDEO_NOT_FOUND | 视频不存在 |
| 404 | REVIEW_NOT_FOUND | 评审记录不存在（视频尚未完成生成） |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 18.2 提交人工评审
```http
POST /api/v1/videos/{video_id}/review/submit
Authorization: Bearer {access_token}
Content-Type: application/json

请求体：
{
  "overall_score": 90,
  "passed": true,
  "items": [
    {"item": "content_quality", "score": 85, "comment": "剧情连贯，画风统一"},
    {"item": "audio_quality", "score": 92, "comment": "配音效果好"},
    {"item": "visual_quality", "score": 88, "comment": "动画流畅，色彩搭配佳"},
    {"item": "subtitle", "score": 80, "comment": "个别段落字幕偏快"}
  ],
  "overall_comment": "整体质量优秀，建议微调字幕节奏",
  "action": "approve"
}

响应体：
{
  "code": 200,
  "message": "评审提交成功",
  "data": {
    "review_id": "review_1234567890",
    "video_id": "video_1234567890",
    "reviewer": {
      "user_id": "user_1234567890",
      "username": "user123"
    },
    "overall_score": 90,
    "passed": true,
    "action": "approve",
    "submitted_at": "2026-04-01T15:00:00Z"
  }
}
```

**请求参数说明：**
- `action`: 评审动作，`approve`（通过）、`reject`（拒绝）、`revision`（要求修改）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 参数错误 |
| 400 | INVALID_SCORE | 评分必须在0-100之间 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | VIDEO_NOT_FOUND | 视频不存在 |
| 409 | ALREADY_REVIEWED | 您已提交过评审 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 18.3 评审历史
```http
GET /api/v1/videos/{video_id}/review/history
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "video_id": "video_1234567890",
    "items": [
      {
        "review_id": "review_1234567890",
        "type": "auto",
        "overall_score": 85,
        "passed": true,
        "reviewer": {
          "type": "system",
          "name": "AI自动评审"
        },
        "summary": "自动评审通过，内容安全评分95，视频质量评分80",
        "reviewed_at": "2026-04-01T14:30:00Z"
      },
      {
        "review_id": "review_2345678901",
        "type": "manual",
        "overall_score": 90,
        "passed": true,
        "reviewer": {
          "type": "user",
          "user_id": "user_1234567890",
          "name": "user123"
        },
        "summary": "人工评审通过，整体质量优秀",
        "reviewed_at": "2026-04-01T15:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 2,
      "total_pages": 1
    }
  }
}
```

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 404 | VIDEO_NOT_FOUND | 视频不存在 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 19. 专家建议API

### 19.1 专家建议列表
```http
GET /api/v1/expert-advices
Authorization: Bearer {access_token}
查询参数：
?page=1&page_size=20&genre=fantasy&category=plot

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [
      {
        "advice_id": "adv_1234567890",
        "title": "奇幻小说的世界观构建技巧",
        "category": "plot",
        "genre": "fantasy",
        "content": "构建奇幻世界观时需要注意以下要素：1. 魔法体系的内在逻辑...",
        "tags": ["世界观", "魔法体系", "奇幻"],
        "author": {
          "name": "专家团队",
          "avatar": "https://example.com/avatars/expert.jpg"
        },
        "applicable_to": {
          "genres": ["fantasy", "sci_fi"],
          "novel_length": ["medium", "long"],
          "conflict_levels": ["medium", "high"]
        },
        "rating": 4.8,
        "usage_count": 1560,
        "created_at": "2026-03-01T10:00:00Z",
        "updated_at": "2026-03-15T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 50,
      "total_pages": 3
    }
  }
}
```

**查询参数说明：**
- `genre`: 适用题材，`fantasy`、`romance`、`sci_fi`、`urban`、`historical`
- `category`: 建议类别，`plot`（情节）、`character`（角色）、`worldbuilding`（世界观）、`style`（文风）、`pacing`（节奏）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 查询参数无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 19.2 匹配建议
```http
GET /api/v1/expert-advices/match
Authorization: Bearer {access_token}
查询参数：
?genre=fantasy&length=medium&style=humorous&conflict_level=high&chapters=18

响应体：
{
  "code": 200,
  "message": "success",
  "data": {
    "match_params": {
      "genre": "fantasy",
      "length": "medium",
      "style": "humorous",
      "conflict_level": "high",
      "chapters": 18
    },
    "recommendations": [
      {
        "advice_id": "adv_1234567890",
        "title": "奇幻小说的世界观构建技巧",
        "category": "worldbuilding",
        "relevance_score": 0.95,
        "summary": "针对中篇奇幻小说，建议构建2-3个核心魔法规则，避免体系过于复杂",
        "key_points": [
          "限定魔法体系规模，中篇建议不超过3种核心能力",
          "高冲突设定下，魔法代价是关键张力来源",
          "幽默风格可通过角色对魔法的吐槽实现"
        ],
        "applicable_chapters": "全篇适用",
        "tags": ["世界观", "魔法体系"]
      },
      {
        "advice_id": "adv_2345678901",
        "title": "高冲突情节的幽默表达技巧",
        "category": "style",
        "relevance_score": 0.88,
        "summary": "在紧张情节中穿插幽默元素，可有效调节读者情绪节奏",
        "key_points": [
          "每3-4章安排一个轻松桥段",
          "利用角色性格差异制造自然笑料",
          "战斗场景中的吐槽式旁白是有效手段"
        ],
        "applicable_chapters": "第3、7、11、15章建议安排",
        "tags": ["幽默", "节奏", "高冲突"]
      }
    ],
    "total_matched": 8,
    "showing": 2
  }
}
```

**查询参数说明：**
- `genre`: 小说题材（必填）
- `length`: 篇幅，`short`（短篇，<5万字）、`medium`（中篇，5-20万字）、`long`（长篇，>20万字）
- `style`: 文风，`serious`（严肃）、`humorous`（幽默）、`literary`（文学）、`popular`（通俗）
- `conflict_level`: 冲突强度，`low`、`medium`、`high`
- `chapters`: 章节数（可选，用于更精准的匹配）

**错误码：**

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | MISSING_REQUIRED_PARAMS | 缺少必填参数（genre为必填） |
| 400 | INVALID_PARAMS | 参数值无效 |
| 401 | UNAUTHORIZED | 未认证或token已过期 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

## 20. 错误码汇总

### 20.1 通用错误码

| HTTP状态码 | 错误码 | 描述 |
|-----------|--------|------|
| 400 | INVALID_PARAMS | 请求参数无效 |
| 401 | UNAUTHORIZED | 未认证或认证信息已过期 |
| 401 | INVALID_API_KEY | API Key无效或已过期（OpenClaw接口） |
| 403 | FORBIDDEN | 无权限访问该资源 |
| 404 | NOT_FOUND | 请求的资源不存在 |
| 405 | METHOD_NOT_ALLOWED | 不支持的HTTP方法 |
| 409 | CONFLICT | 资源冲突 |
| 422 | UNPROCESSABLE_ENTITY | 请求格式正确但语义错误 |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超过限制 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 502 | BAD_GATEWAY | 上游服务不可用 |
| 503 | SERVICE_UNAVAILABLE | 服务维护中 |

### 20.2 速率限制说明

```
速率限制响应头：
X-RateLimit-Limit: 1000          // 窗口期内最大请求数
X-RateLimit-Remaining: 999       // 剩余请求数
X-RateLimit-Reset: 1617019200    // 限制重置时间戳

超限响应体：
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retry_after": 60,
    "limit": 1000,
    "window": "1h"
  }
}
```

### 20.3 认证方式汇总

| 接口分组 | 认证方式 | 请求头 |
|---------|---------|-------|
| 用户端API（第2-10章） | Bearer Token | `Authorization: Bearer {access_token}` |
| 管理端API（第11章） | Bearer Token（管理员） | `Authorization: Bearer {admin_access_token}` |
| 套餐订阅API（第12章） | Bearer Token | `Authorization: Bearer {access_token}` |
| OpenClaw专用API（第13章） | API Key | `X-API-Key: {api_key}` |
| 多端认证API（第14章） | 无需认证（登录接口） / Bearer Token（绑定接口） | 视接口而定 |
| 支付回调API（第15.1-15.3） | 平台签名验证 | 各平台专用签名头 |
| 支付增强API（第15.4-15.6） | Bearer Token | `Authorization: Bearer {access_token}` |
| 内容广场API（第16章） | Bearer Token（部分可选） | `Authorization: Bearer {access_token}` |
| 发布增强API（第17章） | Bearer Token | `Authorization: Bearer {access_token}` |
| 视频评审API（第18章） | Bearer Token | `Authorization: Bearer {access_token}` |
| 专家建议API（第19章） | Bearer Token | `Authorization: Bearer {access_token}` |