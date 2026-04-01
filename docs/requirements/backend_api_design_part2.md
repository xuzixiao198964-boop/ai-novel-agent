# 后端API接口设计（续）

## 5. 小说生成API（续）

### 5.3 获取小说详情（续）
```json
    "metadata": {
      "author": "AI创作助手",
      "synopsis": "一个关于勇气与友谊的奇幻冒险故事...",
      "main_characters": [
        {
          "name": "艾伦",
          "role": "主角",
          "description": "年轻的冒险家，拥有神秘的血统"
        }
      ],
      "themes": ["勇气", "友谊", "成长"],
      "conflict_points": [
        {
          "chapter": 3,
          "type": "身份冲突",
          "intensity": "high",
          "description": "主角发现自己的真实身份"
        }
      ],
      "expert_advice_used": [
        "三幕剧结构",
        "英雄之旅模型",
        "悬念设置技巧"
      ]
    },
    "chapters": [
      {
        "chapter_number": 1,
        "title": "命运的召唤",
        "word_count": 3124,
        "content": "第一章正文内容...",
        "summary": "主角收到神秘信件，开始冒险",
        "conflict_level": "medium",
        "quality_score": 8.2
      }
    ],
    "files": {
      "full_text": "http://104.244.90.202:9000/api/v1/novels/novel_xxxxxxxx/download/full",
      "epub": "http://104.244.90.202:9000/api/v1/novels/novel_xxxxxxxx/download/epub",
      "pdf": "http://104.244.90.202:9000/api/v1/novels/novel_xxxxxxxx/download/pdf"
    }
  }
}
```

### 5.4 下载小说文件
```http
GET /api/v1/novels/{novel_id}/download/{format}
Authorization: Bearer {token}
Query Parameters:
  - format: full/epub/pdf/txt

响应:
直接返回文件流，Content-Type根据格式变化
```

### 5.5 获取小说列表
```http
GET /api/v1/novels
Authorization: Bearer {token}
Query Parameters:
  - status: pending/running/completed/failed (可选)
  - genre: fantasy/romance/sci-fi等 (可选)
  - start_date: 2026-04-01 (可选)
  - end_date: 2026-04-30 (可选)
  - page: 1 (可选)
  - limit: 20 (可选)

响应:
{
  "success": true,
  "data": {
    "novels": [
      {
        "id": "novel_xxxxxxxx",
        "title": "AI创作的奇幻冒险",
        "genre": "fantasy",
        "chapters": 18,
        "status": "completed",
        "total_words": 55678,
        "total_cost": 6.85,
        "quality_score": 8.5,
        "created_at": "2026-04-01T12:00:00Z",
        "completed_at": "2026-04-01T12:30:00Z"
      }
    ],
    "pagination": {
      "total": 15,
      "page": 1,
      "limit": 20,
      "total_pages": 1
    }
  }
}
```

### 5.6 取消小说生成任务
```http
POST /api/v1/novels/{novel_id}/cancel
Authorization: Bearer {token}

响应:
{
  "success": true,
  "message": "任务已取消",
  "data": {
    "id": "novel_xxxxxxxx",
    "status": "cancelled",
    "refund_amount": 3.45,  // 部分退款
    "cancelled_at": "2026-04-01T12:15:00Z"
  }
}
```

### 5.7 重新审核小说
```http
POST /api/v1/novels/{novel_id}/reaudit
Authorization: Bearer {token}
Content-Type: application/json

{
  "audit_focus": ["logic", "language", "consistency"],  // 可选
  "strictness": "high"  // low/medium/high
}

响应:
{
  "success": true,
  "data": {
    "audit_id": "audit_xxxxxxxx",
    "novel_id": "novel_xxxxxxxx",
    "status": "pending",
    "estimated_cost": 0.50,
    "created_at": "2026-04-01T13:00:00Z"
  }
}
```

## 6. 视频生成API

### 6.1 创建视频生成任务
```http
POST /api/v1/videos
Authorization: Bearer {token}
Content-Type: application/json

{
  "source_type": "novel",  // novel/external/news
  "source_id": "novel_xxxxxxxx",  // 小说ID或外部内容URL
  "generation_mode": "animation",  // voice_only/subtitle_only/animation/mixed
  "duration": 180,  // 秒，可选
  "memory_points": true,
  "tts_provider": "tencent",  // tencent/edge/openai，可选
  "voice_type": "female_1",  // 可选
  "background_music": "epic",  // 可选：epic/romantic/calm/none
  "subtitle_style": "modern",  // 可选：classic/modern/minimal
  "output_format": "mp4",  // mp4/gif/webm
  "resolution": "1080p"  // 720p/1080p/2k/4k
}

响应:
{
  "success": true,
  "data": {
    "id": "video_xxxxxxxx",
    "source_type": "novel",
    "source_id": "novel_xxxxxxxx",
    "generation_mode": "animation",
    "status": "pending",
    "estimated_cost": 17.25,
    "estimated_time": 900,  // 秒
    "created_at": "2026-04-01T13:00:00Z",
    "progress": {
      "current_step": 0,
      "total_steps": 5,
      "percent": 0,
      "message": "任务已创建，等待处理"
    }
  }
}
```

### 6.2 获取视频任务进度
```http
GET /api/v1/videos/{video_id}/progress
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "video_xxxxxxxx",
    "status": "running",
    "progress": {
      "current_step": 2,
      "total_steps": 5,
      "percent": 40,
      "message": "正在生成语音...",
      "current_process": "tts_generation",
      "estimated_remaining": 540  // 秒
    },
    "cost_so_far": 6.90,
    "created_at": "2026-04-01T13:00:00Z",
    "updated_at": "2026-04-01T13:05:00Z"
  }
}
```

### 6.3 获取视频详情
```http
GET /api/v1/videos/{video_id}
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "video_xxxxxxxx",
    "source_type": "novel",
    "source_id": "novel_xxxxxxxx",
    "generation_mode": "animation",
    "status": "completed",
    "duration": 182,
    "resolution": "1920x1080",
    "file_size": 45678901,  // 字节
    "total_cost": 17.20,
    "quality_score": 8.8,
    "memory_points_score": 9.2,
    "created_at": "2026-04-01T13:00:00Z",
    "completed_at": "2026-04-01T13:15:00Z",
    "metadata": {
      "title": "AI创作的奇幻冒险 - 动画版",
      "description": "基于小说生成的动画视频...",
      "tags": ["奇幻", "冒险", "动画"],
      "memory_points": [
        {
          "timestamp": "00:05",
          "type": "visual_impact",
          "description": "震撼的开场画面",
          "effectiveness": "high"
        }
      ],
      "voice_characteristics": {
        "provider": "tencent",
        "voice_type": "female_1",
        "speed": 1.0,
        "pitch": 0.8
      },
      "visual_elements": {
        "animation_style": "2d_cartoon",
        "color_palette": "vibrant",
        "transition_effects": "smooth"
      }
    },
    "files": {
      "video": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/download/video",
      "thumbnail": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/download/thumbnail",
      "subtitles": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/download/subtitles",
      "audio": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/download/audio"
    },
    "preview_url": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/preview"
  }
}
```

### 6.4 下载视频文件
```http
GET /api/v1/videos/{video_id}/download/{type}
Authorization: Bearer {token}
Query Parameters:
  - type: video/thumbnail/subtitles/audio
  - quality: low/medium/high (仅视频)

响应:
直接返回文件流
```

### 6.5 获取视频预览
```http
GET /api/v1/videos/{video_id}/preview
Authorization: Bearer {token}

响应:
返回HTML页面，内嵌视频播放器
```

### 6.6 获取视频列表
```http
GET /api/v1/videos
Authorization: Bearer {token}
Query Parameters:
  - status: pending/running/completed/failed (可选)
  - generation_mode: voice_only/subtitle_only/animation/mixed (可选)
  - source_type: novel/external/news (可选)
  - start_date: 2026-04-01 (可选)
  - end_date: 2026-04-30 (可选)
  - page: 1 (可选)
  - limit: 20 (可选)

响应:
{
  "success": true,
  "data": {
    "videos": [
      {
        "id": "video_xxxxxxxx",
        "title": "AI创作的奇幻冒险 - 动画版",
        "source_type": "novel",
        "generation_mode": "animation",
        "status": "completed",
        "duration": 182,
        "file_size": 45678901,
        "total_cost": 17.20,
        "quality_score": 8.8,
        "created_at": "2026-04-01T13:00:00Z",
        "thumbnail_url": "http://104.244.90.202:9000/api/v1/videos/video_xxxxxxxx/download/thumbnail"
      }
    ],
    "pagination": {
      "total": 8,
      "page": 1,
      "limit": 20,
      "total_pages": 1
    }
  }
}
```

### 6.7 取消视频生成任务
```http
POST /api/v1/videos/{video_id}/cancel
Authorization: Bearer {token}

响应:
{
  "success": true,
  "message": "视频生成任务已取消",
  "data": {
    "id": "video_xxxxxxxx",
    "status": "cancelled",
    "refund_amount": 8.60,
    "cancelled_at": "2026-04-01T13:10:00Z"
  }
}
```

### 6.8 重新生成视频
```http
POST /api/v1/videos/{video_id}/regenerate
Authorization: Bearer {token}
Content-Type: application/json

{
  "generation_mode": "mixed",  // 可选，修改生成模式
  "memory_points": false,  // 可选
  "tts_provider": "openai",  // 可选
  "reason": "质量不满意"  // 可选
}

响应:
{
  "success": true,
  "data": {
    "new_video_id": "video_yyyyyyyy",
    "original_video_id": "video_xxxxxxxx",
    "estimated_cost": 18.50,
    "estimated_time": 960,
    "created_at": "2026-04-01T14:00:00Z"
  }
}
```

## 7. 发布管理API

### 7.1 绑定平台账号
```http
POST /api/v1/publish/platforms/{platform}/bind
Authorization: Bearer {token}
Content-Type: application/json

{
  "auth_type": "oauth",  // oauth/api_key
  "credentials": {
    "access_token": "oauth_access_token",  // OAuth方式
    "refresh_token": "oauth_refresh_token"
  }
  // 或
  "credentials": {
    "api_key": "platform_api_key",  // API Key方式
    "api_secret": "platform_api_secret"
  }
}

响应:
{
  "success": true,
  "data": {
    "platform": "douyin",
    "account_id": "douyin_user_123",
    "account_name": "我的抖音账号",
    "avatar": "https://example.com/avatar.jpg",
    "bind_status": "active",
    "bind_at": "2026-04-01T14:00:00Z",
    "permissions": ["publish", "read", "delete"]
  }
}
```

### 7.2 获取已绑定平台
```http
GET /api/v1/publish/platforms
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "platforms": [
      {
        "platform": "douyin",
        "account_id": "douyin_user_123",
        "account_name": "我的抖音账号",
        "avatar": "https://example.com/avatar.jpg",
        "bind_status": "active",
        "bind_at": "2026-04-01T14:00:00Z",
        "last_sync": "2026-04-01T15:00:00Z"
      },
      {
        "platform": "xiaohongshu",
        "account_id": "xhs_user_456",
        "account_name": "我的小红书",
        "bind_status": "expired",
        "bind_at": "2026-03-01T10:00:00Z",
        "expires_at": "2026-04-01T10:00:00Z"
      }
    ]
  }
}
```

### 7.3 解绑平台账号
```http
POST /api/v1/publish/platforms/{platform}/unbind
Authorization: Bearer {token}

响应:
{
  "success": true,
  "message": "平台账号已解绑"
}
```

### 7.4 创建发布任务
```http
POST /api/v1/publish
Authorization: Bearer {token}
Content-Type: application/json

{
  "content_type": "video",  // novel/video
  "content_id": "video_xxxxxxxx",
  "platforms": ["douyin", "xiaohongshu"],
  "publish_time": "2026-04-01T18:00:00Z",  // 或 "immediate"
  "privacy": "public",  // public/followers/private
  "customization": {
    "title": "自定义标题",  // 可选
    "description": "自定义描述",  // 可选
    "tags": ["奇幻", "冒险", "AI创作"],  // 可选
    "cover_image": "http://example.com/cover.jpg"  // 可选
  },
  "notification": {
    "email": true,
    "push": true
  }
}

响应:
{
  "success": true,
  "data": {
    "id": "publish_xxxxxxxx",
    "content_type": "video",
    "content_id": "video_xxxxxxxx",
    "platforms": ["douyin", "xiaohongshu"],
    "status": "scheduled",
    "publish_time": "2026-04-01T18:00:00Z",
    "estimated_completion": "2026-04-01T18:05:00Z",
    "created_at": "2026-04-01T15:00:00Z",
    "tasks": [
      {
        "platform": "douyin",
        "task_id": "task_douyin_123",
        "status": "pending",
        "estimated_cost": 0.10
      },
      {
        "platform": "xiaohongshu",
        "task_id": "task_xhs_456",
        "status": "pending",
        "estimated_cost": 0.10
      }
    ]
  }
}
```

### 7.5 获取发布任务进度
```http
GET /api/v1/publish/{publish_id}/progress
Authorization: Bearer {token}

响应:
{
  "success": true,
  "data": {
    "id": "publish_xxxxxxxx",
    "status": "running",
    "progress": {
      "completed": 1,
      "total": 2,
      "percent": 50,
      "message": "抖音发布完成，小红书发布中..."
    },
    "tasks": [
      {
        "platform": "douyin",
        "task_id": "task_douyin_123",
        "status": "completed",
        "published_url": "