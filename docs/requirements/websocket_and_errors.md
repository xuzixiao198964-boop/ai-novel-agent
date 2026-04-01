# WebSocket接口和错误处理

## 8. WebSocket实时通信API

### 8.1 WebSocket连接
```
连接URL: ws://104.244.90.202:9000/ws
认证方式: 在连接URL中添加token参数
示例: ws://104.244.90.202:9000/ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

连接建立后，客户端可以发送订阅消息来接收特定类型的通知。
```

### 8.2 客户端到服务器的消息格式
```json
{
  "type": "subscribe",  // 消息类型
  "data": {
    "channels": ["task_updates", "notifications", "balance_updates"],
    "task_ids": ["novel_xxxxxxxx", "video_yyyyyyyy"],
    "user_id": "user_xxxxxxxx"
  }
}

消息类型:
- subscribe: 订阅通知频道
- unsubscribe: 取消订阅
- ping: 心跳保持连接
- custom: 自定义消息
```

### 8.3 服务器到客户端的消息格式

#### 8.3.1 任务进度更新
```json
{
  "type": "task_progress",
  "timestamp": "2026-04-01T12:05:00Z",
  "data": {
    "task_id": "novel_xxxxxxxx",
    "task_type": "novel_generation",
    "status": "running",
    "progress": {
      "current_step": 3,
      "total_steps": 7,
      "percent": 42,
      "message": "正在生成故事大纲...",
      "current_agent": "PlannerAgent"
    },
    "estimated_remaining": 1200,
    "cost_so_far": 2.50
  }
}
```

#### 8.3.2 任务完成通知
```json
{
  "type": "task_completed",
  "timestamp": "2026-04-01T12:30:00Z",
  "data": {
    "task_id": "novel_xxxxxxxx",
    "task_type": "novel_generation",
    "result": {
      "novel_id": "novel_xxxxxxxx",
      "title": "AI创作的奇幻冒险",
      "total_words": 55678,
      "total_cost": 6.85,
      "quality_score": 8.5,
      "download_url": "http://104.244.90.202:9000/api/v1/novels/novel_xxxxxxxx/download/full"
    },
    "completion_time": "2026-04-01T12:30:00Z"
  }
}
```

#### 8.3.3 任务失败通知
```json
{
  "type": "task_failed",
  "timestamp": "2026-04-01T12:15:00Z",
  "data": {
    "task_id": "novel_xxxxxxxx",
    "task_type": "novel_generation",
    "error": {
      "code": "API_RATE_LIMIT",
      "message": "DeepSeek API调用频率超限",
      "details": "请等待1分钟后重试",
      "retryable": true,
      "retry_after": 60  // 秒
    },
    "partial_refund": 3.45,
    "failed_at": "2026-04-01T12:15:00Z"
  }
}
```

#### 8.3.4 余额变动通知
```json
{
  "type": "balance_updated",
  "timestamp": "2026-04-01T12:05:00Z",
  "data": {
    "user_id": "user_xxxxxxxx",
    "transaction_type": "consumption",
    "amount": -6.90,
    "new_balance": 93.10,
    "description": "中篇小说生成",
    "transaction_id": "tx_xxxxxxxx",
    "related_task": "novel_xxxxxxxx"
  }
}
```

#### 8.3.5 系统通知
```json
{
  "type": "notification",
  "timestamp": "2026-04-01T12:00:00Z",
  "data": {
    "id": "notif_xxxxxxxx",
    "level": "info",  // info/warning/error/success
    "title": "系统维护通知",
    "message": "系统将于今晚24:00-02:00进行维护",
    "action": {
      "type": "url",
      "label": "查看详情",
      "url": "http://104.244.90.202:9000/announcements/maintenance"
    },
    "expires_at": "2026-04-02T02:00:00Z"
  }
}
```

#### 8.3.6 发布状态更新
```json
{
  "type": "publish_status",
  "timestamp": "2026-04-01T18:01:00Z",
  "data": {
    "publish_id": "publish_xxxxxxxx",
    "platform": "douyin",
    "status": "published",
    "published_url": "https://www.douyin.com/video/123456789",
    "published_at": "2026-04-01T18:00:30Z",
    "views": 150,
    "likes": 25,
    "comments": 8
  }
}
```

### 8.4 WebSocket客户端示例
```javascript
class AINovelMediaWebSocket {
  constructor(token, options = {}) {
    this.token = token;
    this.baseUrl = options.baseUrl || 'ws://104.244.90.202:9000';
    this.ws = null;
    this.subscriptions = new Set();
    this.messageHandlers = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    
    this.init();
  }
  
  init() {
    this.connect();
    this.setupEventHandlers();
  }
  
  connect() {
    const wsUrl = `${this.baseUrl}/ws?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket连接已建立');
      this.reconnectAttempts = 0;
      
      // 重新订阅之前的频道
      if (this.subscriptions.size > 0) {
        this.subscribe(Array.from(this.subscriptions));
      }
    };
    
    this.ws.onclose = (event) => {
      console.log('WebSocket连接关闭', event.code, event.reason);
      
      // 尝试重新连接
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        console.log(`将在${delay}ms后尝试重新连接...`);
        
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, delay);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('消息解析错误:', error);
      }
    };
  }
  
  setupEventHandlers() {
    // 注册默认的消息处理器
    this.on('task_progress', (data) => {
      console.log(`任务进度: ${data.task_id} - ${data.progress.percent}%`);
    });
    
    this.on('task_completed', (data) => {
      console.log(`任务完成: ${data.task_id}`);
      console.log(`结果:`, data.result);
    });
    
    this.on('task_failed', (data) => {
      console.error(`任务失败: ${data.task_id}`);
      console.error(`错误:`, data.error);
    });
    
    this.on('balance_updated', (data) => {
      console.log(`余额变动: ${data.transaction_type} ${data.amount}`);
      console.log(`新余额: ${data.new_balance}`);
    });
    
    this.on('notification', (data) => {
      console.log(`系统通知 [${data.level}]: ${data.title}`);
      console.log(data.message);
    });
  }
  
  subscribe(channels, taskIds = []) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法订阅');
      return;
    }
    
    const message = {
      type: 'subscribe',
      data: {
        channels: Array.isArray(channels) ? channels : [channels],
        task_ids: taskIds
      }
    };
    
    this.ws.send(JSON.stringify(message));
    
    // 记录订阅
    channels.forEach(channel => {
      this.subscriptions.add(channel);
    });
  }
  
  unsubscribe(channels) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }
    
    const message = {
      type: 'unsubscribe',
      data: {
        channels: Array.isArray(channels) ? channels : [channels]
      }
    };
    
    this.ws.send(JSON.stringify(message));
    
    // 移除订阅记录
    channels.forEach(channel => {
      this.subscriptions.delete(channel);
    });
  }
  
  subscribeToTask(taskId) {
    this.subscribe(['task_updates'], [taskId]);
  }
  
  on(messageType, handler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }
    this.messageHandlers.get(messageType).push(handler);
  }
  
  off(messageType, handler) {
    if (this.messageHandlers.has(messageType)) {
      const handlers = this.messageHandlers.get(messageType);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }
  
  handleMessage(message) {
    const { type, data } = message;
    
    if (this.messageHandlers.has(type)) {
      this.messageHandlers.get(type).forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`消息处理器错误 (${type}):`, error);
        }
      });
    }
    
    // 触发全局事件
    if (typeof this.onMessage === 'function') {
      this.onMessage(message);
    }
  }
  
  sendCustomMessage(data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    
    const message = {
      type: 'custom',
      data: data,
      timestamp: new Date().toISOString()
    };
    
    this.ws.send(JSON.stringify(message));
    return true;
  }
  
  ping() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    
    const message = {
      type: 'ping',
      timestamp: new Date().toISOString()
    };
    
    this.ws.send(JSON.stringify(message));
    return true;
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close(1000, '客户端主动断开');
      this.ws = null;
    }
    this.subscriptions.clear();
  }
}

// 使用示例
const wsClient = new AINovelMediaWebSocket('your_token_here');

// 订阅特定任务
wsClient.subscribeToTask('novel_xxxxxxxx');

// 自定义消息处理器
wsClient.on('task_progress', (data) => {
  // 更新UI进度条
  updateProgressBar(data.task_id, data.progress.percent);
  
  // 显示进度消息
  showProgressMessage(data.task_id, data.progress.message);
});

// 余额变动处理
wsClient.on('balance_updated', (data) => {
  updateBalanceDisplay(data.new_balance);
  
  if (data.new_balance < 10) {
    showLowBalanceWarning();
  }
});
```

## 9. 错误处理

### 9.1 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "INVALID_API_KEY",
    "message": "API密钥无效或已过期",
    "details": "请检查API密钥是否正确，或重新生成新的API密钥",
    "field": "Authorization",  // 可选，指示哪个字段有问题
    "timestamp": "2026-04-01T12:00:00Z",
    "request_id": "req_xxxxxxxx"
  }
}
```

### 9.2 常见错误代码

#### 9.2.1 认证错误 (4xx)
```json
{
  "code": "UNAUTHORIZED",
  "message": "未授权访问",
  "details": "请提供有效的认证令牌"
}

{
  "code": "INVALID_TOKEN",
  "message": "令牌无效",
  "details": "认证令牌已过期或格式错误"
}

{
  "code": "INSUFFICIENT_PERMISSIONS",
  "message": "权限不足",
  "details": "您的API密钥没有执行此操作的权限"
}

{
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "请求频率超限",
  "details": "请稍后再试，或升级套餐提高限制",
  "retry_after": 60  // 秒
}
```

#### 9.2.2 资源错误 (4xx)
```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "资源不存在",
  "details": "请求的小说/视频/任务不存在"
}

{
  "code": "INSUFFICIENT_BALANCE",
  "message": "余额不足",
  "details": "当前余额不足，请先充值",
  "required_amount": 10.50,
  "current_balance": 5.00
}

{
  "code": "QUOTA_EXCEEDED",
  "message": "配额超限",
  "details": "今日API调用次数已达上限",
  "quota_type": "daily",
  "quota_limit": 1000,
  "quota_used": 1000,
  "reset_time": "2026-04-02T00:00:00Z"
}
```

#### 9.2.3 业务逻辑错误 (4xx)
```json
{
  "code": "INVALID_PARAMETERS",
  "message": "参数无效",
  "details": "章节数量必须在1-200之间",
  "field": "chapters",
  "expected": "1-200",
  "actual": 250
}

{
  "code": "TASK_ALREADY_COMPLETED",
  "message": "任务已完成",
  "details": "无法取消已完成的任务"
}

{
  "code": "CONTENT_TOO_LONG",
  "message": "内容过长",
  "details": "单次生成内容不能超过100万字",
  "max_length": 1000000,
  "requested_length": 1200000
}
```

#### 9.2.4 服务器错误 (5xx)
```json
{
  "code": "INTERNAL_SERVER_ERROR",
  "message": "服务器内部错误",
  "details": "请稍后重试，或联系技术支持",
  "request_id": "req_xxxxxxxx"
}

{
  "code": "SERVICE_UNAVAILABLE",
  "message": "服务暂时不可用",
  "details": "系统维护中，预计30分钟后恢复",
  "estimated_recovery": "2026-04-01T12:30:00Z"
}

{
  "code": "EXTERNAL_API_ERROR",
  "message": "外部API错误",
  "details": "DeepSeek API服务暂时不可用",
  "external_service": "DeepSeek",
  "external_error": "Rate limit exceeded"
}
```

### 9.3 错误处理最佳实践

#### 客户端错误处理示例
```javascript
async function callApi(endpoint, options = {}) {
  try {
    const response = await fetch(endpoint, {
      ...options,
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // 处理API错误
      throw new ApiError(data.error);
    }
    
    return data;
    
  } catch (error) {
    if (error instanceof ApiError) {
      // 处理已知的API错误
      handleApiError(error);
    } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
      // 网络错误
      showNetworkError();
    } else {
      // 未知错误
      console.error('未知错误:', error);
      showGenericError();
    }
    
    throw error;
  }
}

class ApiError extends Error {
  constructor(errorData) {
    super(errorData.message);
    this.name = 'ApiError';
    this.code = errorData.code;
    this.details = errorData.details;
    this.field = errorData.field;
    this.timestamp = errorData.timestamp;
    this.requestId = errorData.request_id;
  }
  
  isRetryable() {
    // 判断错误是否可重试
    const retryableCodes = [
      'RATE_LIMIT_EXCEEDED',
      'SERVICE_UNAVAILABLE',
      'EXTERNAL_API_ERROR',
      'NETWORK_ERROR'
    ];
    
    return retryableCodes.includes(this.code);
  }
  
  getRetryAfter() {
    // 获取重试等待时间
    if (this.code === 'RATE_LIMIT_EXCEEDED') {
      return this.details?.retry_after || 60;
    }
    return 5; // 默认5秒后重试
  }
}

function handleApiError(error) {
  console.error(`API错误 [${error.code}]: ${error.message}`);
  
  switch (error.code) {
    case 'INSUFFICIENT_BALANCE':
      showRechargePrompt(error.details.