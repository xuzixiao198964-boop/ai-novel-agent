# 后端API接口设计

## API基础信息
- **基础URL**: `http://104.244.90.202:9000`
- **API版本**: `v1`
- **认证方式**: Bearer Token (JWT)
- **响应格式**: JSON

## 1. 认证授权API

### 1.1 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "user123",
  "email": "user@example.com",
  "password": "secure_password",
  "phone": "13800138000"  // 可选
}

响应:
{
  "success": true,
  "message": "注册成功",
  "data": {
    "user_id": "user_xxxxxxxx",
    "username": "user123",
    "email": "user@example.com",
    "created_at": "2026-04-01T12:00:00Z",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh_token_here"
  }
}
```

### 1.2 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user123",  // 或 email
  "password": "secure_password"
}

或使用第三方登录:
{
  "provider": "wechat",  // wechat/douyin/qq
  "code": "oauth_code_here"
}

响应:
{
  "success": true,
  "message": "登录成功",
  "data": {
    "user_id": "user_xxxxxxxx",
    "username": "user123",
    "email": "user@example.com",
    "balance": 100.00,
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "refresh_token_here",
    "expires_in": 3600
  }
}
```

### 1.3 刷新令牌
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token_here"
}

响应:
{
  "success": true,
  "message": "令牌刷新成功",
  "data": {
    "token": "new_token_here",
    "refresh_token": "new_refresh_token_here",
    "expires_in": 3600
  }
}
```

### 1.4 退出登录
```http
POST /api/v1/auth/logout
Authorization: Bearer {token}

响应:
{
  "success": true,
  "message": "退出成功"
}
```

## 2. 用户账户API

### 2.1 获取用户信息
```http
GET /api/v1/user/profile
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "user_id": "user_xxxxxxxx",
    "username": "user123",
    "email": "user@example.com",
    "phone": "13800138000",
    "avatar": "https://example.com/avatar.jpg",
    "created_at": "2026-04-01T12:00:00Z",
    "last_login": "2026-04-01T14:30:00Z",
    "settings": {
      "language": "zh-CN",
      "timezone": "Asia/Shanghai",
      "notification_email": true,
      "notification_push": true
    }
  }
}
```

### 2.2 更新用户信息
```http
PUT /api/v1/user/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "new_username",  // 可选
  "email": "new_email@example.com",  // 可选
  "phone": "13900139000",  // 可选
  "avatar": "https://example.com/new_avatar.jpg",  // 可选
  "settings": {  // 可选
    "language": "en-US",
    "timezone": "America/New_York"
  }
}

响应:
{
  "success": true,
  "message": "用户信息更新成功",
  "data": {
    "user_id": "user_xxxxxxxx",
    "username": "new_username",
    "email": "new_email@example.com",
    "updated_at": "2026-04-01T15:00:00Z"
  }
}
```

### 2.3 修改密码
```http
POST /api/v1/user/change-password
Authorization: Bearer {token}
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}

响应:
{
  "success": true,
  "message": "密码修改成功"
}
```

### 2.4 重置密码
```http
POST /api/v1/user/reset-password
Content-Type: application/json

{
  "email": "user@example.com",
  "verification_code": "123456"  // 邮箱验证码
}

响应:
{
  "success": true,
  "message": "密码重置邮件已发送"
}
```

## 3. 余额与支付API

### 3.1 获取余额
```http
GET /api/v1/user/balance
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "balance": 100.50,
    "currency": "CNY",
    "last_recharge": "2026-04-01T10:00:00Z",
    "last_recharge_amount": 100.00,
    "total_consumed": 50.00,
    "balance_warning": false,
    "warning_threshold": 10.00
  }
}
```

### 3.2 充值
```http
POST /api/v1/payment/recharge
Authorization: Bearer {token}
Content-Type: application/json

{
  "amount": 100.00,
  "payment_method": "alipay",  // alipay/wechat/douyin
  "return_url": "https://example.com/return"
}

响应:
{
  "success": true,
  "data": {
    "order_id": "order_xxxxxxxx",
    "payment_url": "https://alipay.com/pay?order=xxx",
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
    "expires_at": "2026-04-01T12:10:00Z"
  }
}
```

### 3.3 支付回调
```http
POST /api/v1/payment/callback/{payment_method}
Content-Type: application/json

{
  "order_id": "order_xxxxxxxx",
  "transaction_id": "transaction_xxxxxxxx",
  "amount": 100.00,
  "status": "success",  // success/failed
  "timestamp": "2026-04-01T12:05:00Z",
  "signature": "signature_here"
}

响应:
{
  "success": true,
  "message": "回调处理成功"
}
```

### 3.4 获取消费记录
```http
GET /api/v1/user/transactions
Authorization: Bearer {token}
Query Parameters:
  - type: recharge/consumption (可选)
  - start_date: 2026-04-01 (可选)
  - end_date: 2026-04-30 (可选)
  - page: 1 (可选，默认1)
  - limit: 20 (可选，默认20)

响应:
{
  "success": true,
  "data": {
    "transactions": [
      {
        "id": "tx_xxxxxxxx",
        "type": "recharge",
        "amount": 100.00,
        "description": "支付宝充值",
        "status": "completed",
        "created_at": "2026-04-01T10:00:00Z",
        "balance_after": 150.00
      },
      {
        "id": "tx_yyyyyyyy",
        "type": "consumption",
        "amount": -6.90,
        "description": "中篇小说生成",
        "status": "completed",
        "created_at": "2026-04-01T11:00:00Z",
        "balance_after": 143.10,
        "details": {
          "service": "novel_generation",
          "novel_id": "novel_xxxxxxxx",
          "chapters": 18,
          "actual_cost": 6.00,
          "service_fee": 0.90
        }
      }
    ],
    "pagination": {
      "total": 45,
      "page": 1,
      "limit": 20,
      "total_pages": 3
    }
  }
}
```

## 4. API Key管理API

### 4.1 创建API Key
```http
POST /api/v1/apikeys
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "生产环境密钥",
  "permissions": [
    "novel_read",
    "novel_write",
    "video_read",
    "video_write"
  ],
  "ip_restriction": "192.168.1.0/24",  // 可选
  "quotas": {  // 可选
    "daily": 1000,
    "monthly": 10000,
    "cost": 1000.00
  },
  "expires_in": 30  // 天数，0表示永不过期
}

响应:
{
  "success": true,
  "data": {
    "id": "key_xxxxxxxx",
    "name": "生产环境密钥",
    "key": "ak_example_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "permissions": ["novel_read", "novel_write", "video_read", "video_write"],
    "ip_restriction": "192.168.1.0/24",
    "quotas": {
      "daily": 1000,
      "monthly": 10000,
      "cost": 1000.00
    },
    "created_at": "2026-04-01T12:00:00Z",
    "expires_at": "2026-05-01T12:00:00Z",
    "usage_count": 0,
    "total_cost": 0.00,
    "last_used": null
  }
}
```

### 4.2 获取API Key列表
```http
GET /api/v1/apikeys
Authorization: Bearer {token}
Query Parameters:
  - status: active/expired/revoked (可选)
  - page: 1 (可选)
  - limit: 20 (可选)

响应:
{
  "success": true,
  "data": {
    "keys": [
      {
        "id": "key_xxxxxxxx",
        "name": "生产环境密钥",
        "permissions": ["novel_read", "novel_write"],
        "status": "active",
        "created_at": "2026-04-01T12:00:00Z",
        "expires_at": "2026-05-01T12:00:00Z",
        "usage_count": 123,
        "total_cost": 45.67,
        "last_used": "2026-04-01T14:30:00Z"
      }
    ],
    "pagination": {
      "total": 5,
      "page": 1,
      "limit": 20,
      "total_pages": 1
    }
  }
}
```

### 4.3 获取API Key详情
```http
GET /api/v1/apikeys/{key_id}
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "key_xxxxxxxx",
    "name": "生产环境密钥",
    "permissions": ["novel_read", "novel_write", "video_read", "video_write"],
    "ip_restriction": "192.168.1.0/24",
    "quotas": {
      "daily": 1000,
      "monthly": 10000,
      "cost": 1000.00,
      "daily_used": 45,
      "monthly_used": 123,
      "cost_used": 45.67
    },
    "created_at": "2026-04-01T12:00:00Z",
    "expires_at": "2026-05-01T12:00:00Z",
    "usage_count": 123,
    "total_cost": 45.67,
    "last_used": "2026-04-01T14:30:00Z",
    "usage_history": [
      {
        "timestamp": "2026-04-01T14:30:00Z",
        "endpoint": "/api/v1/novels",
        "cost": 0.45,
        "ip": "192.168.1.100"
      }
    ]
  }
}
```

### 4.4 重新生成API Key
```http
POST /api/v1/apikeys/{key_id}/regenerate
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "key_xxxxxxxx",
    "name": "生产环境密钥",
    "key": "ak_example_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
    "created_at": "2026-04-01T15:00:00Z",
    "expires_at": "2026-05-01T15:00:00Z",
    "old_key_revoked": true
  }
}
```

### 4.5 撤销API Key
```http
POST /api/v1/apikeys/{key_id}/revoke
Authorization: Bearer {token}

响应:
{
  "success": true,
  "message": "API Key已撤销"
}
```

### 4.6 批量撤销API Keys
```http
POST /api/v1/apikeys/batch-revoke
Authorization: Bearer {token}
Content-Type: application/json

{
  "key_ids": ["key_xxxxxxxx", "key_yyyyyyyy"]
}

响应:
{
  "success": true,
  "message": "成功撤销2个API Keys",
  "data": {
    "revoked_count": 2,
    "failed_count": 0
  }
}
```

### 4.7 获取API Key统计
```http
GET /api/v1/apikeys/stats
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "total_keys": 5,
    "active_keys": 3,
    "expired_keys": 1,
    "revoked_keys": 1,
    "today_calls": 123,
    "week_calls": 856,
    "month_calls": 3456,
    "today_cost": 12.34,
    "week_cost": 67.89,
    "month_cost": 234.56
  }
}
```

## 5. 小说生成API

### 5.1 创建小说生成任务
```http
POST /api/v1/novels
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "AI创作的奇幻冒险",
  "genre": "fantasy",
  "chapters": 18,
  "conflict_level": "high",  // low/medium/high
  "expert_advice": true,
  "target_audience": "adult",  // child/teen/adult
  "writing_style": "modern",  // classical/modern/casual
  "custom_prompt": "请加入龙和魔法的元素",  // 可选
  "estimated_words": 54000  // 可选，自动计算
}

响应:
{
  "success": true,
  "data": {
    "id": "novel_xxxxxxxx",
    "title": "AI创作的奇幻冒险",
    "genre": "fantasy",
    "chapters": 18,
    "status": "pending",
    "estimated_cost": 6.90,
    "estimated_time": 1800,  // 秒
    "created_at": "2026-04-01T12:00:00Z",
    "progress": {
      "current_step": 0,
      "total_steps": 7,
      "percent": 0,
      "message": "任务已创建，等待处理"
    }
  }
}
```

### 5.2 获取小说任务进度
```http
GET /api/v1/novels/{novel_id}/progress
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "novel_xxxxxxxx",
    "status": "running",
    "progress": {
      "current_step": 3,
      "total_steps": 7,
      "percent": 42,
      "message": "正在生成故事大纲...",
      "current_agent": "PlannerAgent",
      "estimated_remaining": 1200  // 秒
    },
    "cost_so_far": 2.50,
    "created_at": "2026-04-01T12:00:00Z",
    "updated_at": "2026-04-01T12:05:00Z"
  }
}
```

### 5.3 获取小说详情
```http
GET /api/v1/novels/{novel_id}
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "novel_xxxxxxxx",
    "title": "AI创作的奇幻冒险",
    "genre": "fantasy",
    "chapters": 18,
    "status": "completed",
    "total_words": 55678,
    "total_cost": 6.85,
    "quality_score": 8.5,
    "conflict_score": 9.2,
    "created_at": "2026-04-01T12:00:00Z",
    "completed_at": "2026-04-01T12:30:00Z",
