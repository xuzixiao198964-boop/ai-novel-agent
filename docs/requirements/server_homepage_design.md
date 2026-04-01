# 104服务器主页设计文档

## 文档信息
- **服务器地址**: 104.244.90.202:9000
- **项目名称**: AI Novel Media Agent 商业化平台
- **设计目标**: 宣传页面 + API文档 + OpenClaw对接说明 + API Key管理
- **创建日期**: 2026-04-01

## 1. 主页整体设计

### 1.1 页面结构
```
首页布局：
┌─────────────────────────────────────────────┐
│             导航栏 (固定顶部)                 │
├─────────────────────────────────────────────┤
│   Hero区域 (项目介绍+CTA按钮)                │
├─────────────────────────────────────────────┤
│   功能展示区 (3列布局)                       │
│   ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│   │ AI小说  │ │ AI视频  │ │ 多平台  │      │
│   │ 生成    │ │ 生成    │ │ 发布    │      │
│   └─────────┘ └─────────┘ └─────────┘      │
├─────────────────────────────────────────────┤
│   技术特性区 (图标+描述)                     │
├─────────────────────────────────────────────┤
│   价格计算器 (交互式)                        │
├─────────────────────────────────────────────┤
│   API文档入口                               │
├─────────────────────────────────────────────┤
│   OpenClaw集成指南                          │
├─────────────────────────────────────────────┤
│   API Key管理入口                           │
├─────────────────────────────────────────────┤
│   用户案例展示                              │
├─────────────────────────────────────────────┤
│   页脚 (联系信息+版权)                       │
└─────────────────────────────────────────────┘
```

### 1.2 导航栏设计
```html
<nav class="navbar">
  <div class="nav-brand">
    <img src="/logo.png" alt="AI创作平台">
    <span>AI Novel Media Agent</span>
  </div>
  
  <div class="nav-menu">
    <a href="#features">功能特性</a>
    <a href="#pricing">价格计算</a>
    <a href="#api">API文档</a>
    <a href="#openclaw">OpenClaw集成</a>
    <a href="/dashboard" class="btn-primary">控制面板</a>
    <a href="/login" class="btn-secondary">登录/注册</a>
  </div>
</nav>
```

### 1.3 Hero区域设计
```html
<section class="hero">
  <div class="hero-content">
    <h1>AI驱动的智能内容创作平台</h1>
    <p class="subtitle">
      一键生成小说，自动转为视频，多平台智能发布<br>
      支持OpenClaw深度集成，提供完整API接口
    </p>
    
    <div class="hero-actions">
      <a href="#pricing" class="btn-primary btn-large">立即体验</a>
      <a href="#api" class="btn-secondary btn-large">查看API文档</a>
    </div>
    
    <div class="hero-stats">
      <div class="stat">
        <span class="number">10,000+</span>
        <span class="label">部小说已生成</span>
      </div>
      <div class="stat">
        <span class="number">50,000+</span>
        <span class="label">个视频已制作</span>
      </div>
      <div class="stat">
        <span class="number">100,000+</span>
        <span class="label">次平台发布</span>
      </div>
    </div>
  </div>
  
  <div class="hero-image">
    <img src="/hero-demo.gif" alt="平台演示">
  </div>
</section>
```

## 2. 功能展示区

### 2.1 AI小说生成功能
```html
<section id="features" class="features">
  <h2>强大的AI小说生成能力</h2>
  
  <div class="feature-grid">
    <div class="feature-card">
      <div class="feature-icon">📚</div>
      <h3>7个智能Agent</h3>
      <p>TrendAgent趋势分析 → StyleAgent风格解析 → PlannerAgent策划生成 → WriterAgent正文创作 → PolishAgent润色优化 → AuditorAgent质量审核 → ReviserAgent修订完善</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">⚡</div>
      <h3>冲突感强化</h3>
      <p>微小说必须包含三级以上冲突，短篇小说多线冲突结构，中篇小说复杂冲突网络，确保每部作品都引人入胜</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">🎯</div>
      <h3>专家建议集成</h3>
      <p>集成网络大咖写作建议，每部小说策划基于专家建议且独一无二，避免重复模式</p>
    </div>
  </div>
</section>
```

### 2.2 AI视频生成功能
```html
<section class="features">
  <h2>智能视频生成与优化</h2>
  
  <div class="feature-grid">
    <div class="feature-card">
      <div class="feature-icon">🎬</div>
      <h3>5种生成模式</h3>
      <p>仅配音模式（经济快速）、仅字幕模式（阅读友好）、动画模式（生动有趣）、混合模式（完整体验）、资讯转视频模式（自动化）</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">✨</div>
      <h3>视频记忆点设计</h3>
      <p>黄金5秒开头设计，强制内容评审，确保每个视频都引人入胜，提高完播率</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">🔊</div>
      <h3>多TTS服务支持</h3>
      <p>腾讯云TTS（高质量）、Edge TTS（本地备选）、OpenAI TTS（备选方案），智能选择最优服务</p>
    </div>
  </div>
</section>
```

### 2.3 多平台发布功能
```html
<section class="features">
  <h2>一站式多平台发布</h2>
  
  <div class="feature-grid">
    <div class="feature-card">
      <div class="feature-icon">📱</div>
      <h3>小说平台发布</h3>
      <p>番茄小说、起点中文网、晋江文学城、自有平台，支持自动章节更新和作品管理</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">🎥</div>
      <h3>视频平台发布</h3>
      <p>抖音、小红书、B站、微信视频号、快手，智能发布时间选择，平台特定优化</p>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">📊</div>
      <h3>数据监控分析</h3>
      <p>实时发布状态监控，详细数据统计，效果分析报告，优化建议生成</p>
    </div>
  </div>
</section>
```

## 3. 价格计算器

### 3.1 交互式价格计算器
```html
<section id="pricing" class="pricing-calculator">
  <h2>透明按量计费，实时价格计算</h2>
  <p class="subtitle">充值金额，按实际使用量扣费，价格透明无隐藏费用</p>
  
  <div class="calculator-container">
    <div class="calculator-sidebar">
      <h3>服务选择</h3>
      
      <div class="service-selector">
        <div class="service-option active" data-service="novel">
          <span class="service-icon">📖</span>
          <span class="service-name">小说生成</span>
        </div>
        
        <div class="service-option" data-service="video">
          <span class="service-icon">🎬</span>
          <span class="service-name">视频生成</span>
        </div>
        
        <div class="service-option" data-service="publish">
          <span class="service-icon">🚀</span>
          <span class="service-name">平台发布</span>
        </div>
      </div>
      
      <div class="price-info">
        <h4>价格说明</h4>
        <ul>
          <li>用户价格 = 实际API成本 × 加成系数（1.1-1.2）</li>
          <li>余额实时显示，用完可随时充值</li>
          <li>无包月套餐，完全按量计费</li>
          <li>支持支付宝、微信支付</li>
        </ul>
      </div>
    </div>
    
    <div class="calculator-main">
      <!-- 小说生成计算器 -->
      <div id="novel-calculator" class="calculator-form active">
        <h3>小说生成价格计算</h3>
        
        <div class="form-group">
          <label>小说类型</label>
          <select id="novel-type">
            <option value="micro">微型小说（1-3章）</option>
            <option value="short">短篇小说（6-18章）</option>
            <option value="medium">中篇小说（18-54章）</option>
            <option value="long">长篇小说（54-162章）</option>
            <option value="super">超长篇小说（162+章）</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>章节数量</label>
          <input type="range" id="chapter-count" min="1" max="200" value="6">
          <span id="chapter-display">6章</span>
        </div>
        
        <div class="form-group">
          <label>每章字数</label>
          <input type="range" id="words-per-chapter" min="1000" max="5000" value="3000" step="500">
          <span id="words-display">3000字</span>
        </div>
        
        <div class="price-result">
          <div class="price-breakdown">
            <div class="breakdown-item">
              <span>API成本估算</span>
              <span id="api-cost">¥3.00</span>
            </div>
            <div class="breakdown-item">
              <span>平台服务费（15%）</span>
              <span id="service-fee">¥0.45</span>
            </div>
            <div class="breakdown-total">
              <span>总计价格</span>
              <span id="total-price">¥3.45</span>
            </div>
          </div>
          
          <div class="calculator-actions">
            <button class="btn-primary" onclick="addToCart('novel')">加入计算</button>
            <button class="btn-secondary" onclick="resetCalculator()">重置</button>
          </div>
        </div>
      </div>
      
      <!-- 视频生成计算器 -->
      <div id="video-calculator" class="calculator-form">
        <!-- 类似结构，省略详细代码 -->
      </div>
      
      <!-- 购物车汇总 -->
      <div class="cart-summary">
        <h3>费用汇总</h3>
        <div id="cart-items">
          <!-- 动态生成购物车项目 -->
        </div>
        <div class="cart-total">
          <span>总计费用</span>
          <span id="cart-total">¥0.00</span>
        </div>
        <div class="cart-actions">
          <button class="btn-primary" onclick="checkout()">立即充值并开始使用</button>
          <button class="btn-secondary" onclick="clearCart()">清空计算</button>
        </div>
      </div>
    </div>
  </div>
</section>
```

### 3.2 价格计算JavaScript逻辑
```javascript
// 价格计算逻辑
const PRICES = {
  novel: {
    micro: { base: 0.50, perChapter: 0.10, perWord: 0.0001 },
    short: { base: 2.00, perChapter: 0.15, perWord: 0.0001 },
    medium: { base: 8.00, perChapter: 0.20, perWord: 0.0001 },
    long: { base: 20.00, perChapter: 0.25, perWord: 0.0001 },
    super: { base: 50.00, perChapter: 0.30, perWord: 0.0001 }
  },
  video: {
    voiceOnly: 0.50,    // 每分钟
    subtitleOnly: 0.80,
    animation: 2.00,
    mixed: 3.00
  },
  publish: {
    novelPlatform: 0.10, // 每次发布
    videoPlatform: 0.20
  }
};

const SERVICE_FEE_RATE = 0.15; // 15%服务费

function calculateNovelPrice() {
  const type = document.getElementById('novel-type').value;
  const chapters = parseInt(document.getElementById('chapter-count').value);
  const wordsPerChapter = parseInt(document.getElementById('words-per-chapter').value);
  
  const priceConfig = PRICES.novel[type];
  const totalWords = chapters * wordsPerChapter;
  
  // 计算API成本
  let apiCost = priceConfig.base + 
                (priceConfig.perChapter * chapters) + 
                (priceConfig.perWord * totalWords);
  
  // 计算服务费
  const serviceFee = apiCost * SERVICE_FEE_RATE;
  const totalPrice = apiCost + serviceFee;
  
  // 更新显示
  document.getElementById('api-cost').textContent = `¥${apiCost.toFixed(2)}`;
  document.getElementById('service-fee').textContent = `¥${serviceFee.toFixed(2)}`;
  document.getElementById('total-price').textContent = `¥${totalPrice.toFixed(2)}`;
  
  return {
    type: 'novel',
    subtype: type,
    chapters: chapters,
    wordsPerChapter: wordsPerChapter,
    apiCost: apiCost,
    serviceFee: serviceFee,
    totalPrice: totalPrice
  };
}

// 实时更新显示
document.getElementById('chapter-count').addEventListener('input', function() {
  document.getElementById('chapter-display').textContent = `${this.value}章`;
  calculateNovelPrice();
});

document.getElementById('words-per-chapter').addEventListener('input', function() {
  document.getElementById('words-display').textContent = `${this.value}字`;
  calculateNovelPrice();
});

document.getElementById('novel-type').addEventListener('change', calculateNovelPrice);
```

## 4. API文档区域

### 4.1 API文档入口
```html
<section id="api" class="api-docs">
  <h2>完整的API接口文档</h2>
  <p class="subtitle">提供RESTful API和WebSocket接口，支持多种编程语言调用</p>
  
  <div class="api-quick-links">
    <a href="/api/docs#authentication" class="api-link">
      <div class="api-link-icon">🔐</div>
      <div class="api-link-content">
        <h4>认证授权</h4>
        <p>用户注册、登录、令牌管理</p>
      </div>
    </a>
    
    <a href="/api/docs#novel" class="api-link">
      <div class="api-link-icon">📖</div>
      <div class="api-link-content">
        <h4>小说生成API</h4>
        <p>7个Agent完整工作流</p>
      </div>
    </a>
    
    <a href="/api/docs#video" class="api-link">
      <div class="api-link-icon">🎬</div>
      <div class="api-link-content">
        <h4>视频生成API</h4>
        <p>5种生成模式，多TTS支持</p>
      </div>
    </a>
    
    <a href="/api/docs#publish" class="api-link">
      <div class="api-link-icon">🚀</div>
      <div class="api-link-content">
        <h4>发布管理API</h4>
        <p>多平台自动发布，状态监控</p>
      </div>
    </a>
    
    <a href="/api/docs#billing" class="api-link">
      <div class="api-link-icon">💰</div>
      <div class="api-link-content">
        <h4>计费系统API</h4>
        <p>余额查询，消费记录，充值接口</p>
      </div>
    </a>
    
    <a href="/api/docs#websocket" class="api-link">
      <div class="api-link-icon">🔌</div>
      <div class="api-link-content">
        <h4>WebSocket API</h4>
        <p>实时进度推送，任务状态通知</p>
      </div>
    </a>
  </div>
  
  <div class="api-example">
    <h3>快速开始示例</h3>
    
    <div class="code-tabs">
      <button class="code-tab active" data-language="python">Python</button>
      <button class="code-tab" data-language="javascript">JavaScript</button>
      <button class="code-tab" data-language="curl">cURL</button>
    </div>
    
    <div class="code-content">
      <div id="python-code" class="code-block active">
        <pre><code class="language-python">import requests

# 初始化客户端
class AINovelMediaClient:
    def __init__(self, api_key, base_url="http://104.244.90.202:9000"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def create_novel(self, title, genre, chapters):
        """创建小说生成任务"""
        payload = {
            "title": title,
            "genre": genre,
            "chapters": chapters,
            "conflict_level": "high"  # 高冲突感
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/novels",
            json=payload
        )
        return response.json()
    
    def get_task_progress(self, task_id):
        """获取任务进度"""
        response = self.session.get(
            f"{self.base_url}/api/v1/tasks/{task_id}/progress"
        )
        return response.json()
    
    def get_balance(self):
        """查询用户余额"""
        response = self.session.get(
            f"{self.base_url}/api/v1/user/balance"
        )
        return response.json()

# 使用示例
client = AINovelMediaClient(api_key="your_api_key_here")

# 创建小说任务
task = client.create_novel(
    title="AI创作的奇幻冒险",
    genre="fantasy",
    chapters=18
)
print(f"任务ID: {task['id']}")

# 查询余额
balance = client.get_balance()
print(f"当前余额: ¥{balance['amount']}")</code></pre>
      </div>
      
      <div id="javascript-code" class="code-block">
        <pre><code class="language-javascript">// JavaScript客户端示例
class AINovelMediaClient {
  constructor(apiKey, baseUrl = 'http://104.244.90.202:9000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async createNovel(title, genre, chapters) {
    const response = await fetch(`${this.baseUrl}/api/v1/novels`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        title,
        genre,
        chapters,
        conflict_level: 'high'
      })
    });
    return await response.json();
  }

  async getTaskProgress(taskId) {
    const response = await fetch(`${this.baseUrl}/api/v1/tasks/${taskId}/progress`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    return await response.json();
  }

  async getBalance() {
    const response = await fetch(`${this.baseUrl}/api/v1/user/balance`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });
    return await response.json();
  }
}

// 使用示例
const client = new AINovelMediaClient('your_api_key_here');

// 创建小说任务
client.createNovel('AI创作的奇幻冒险', 'fantasy', 18)
  .then(task => {
    console.log('任务ID:', task.id);
    
    // WebSocket连接监听进度
    const ws = new WebSocket(`ws://104.244.90.202:9000/ws?task_id=${task.id}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress') {
        console.log(`进度: ${data.progress}% - ${data.message}`);
      }
      if (data.type === 'completed') {
        console.log('任务完成:', data.result);
      }
    };
  })
  .catch(error => console.error('错误:', error));</code></pre>
      </div>
      
      <div id="curl-code" class="code-block">
        <pre><code class="language-bash"># cURL命令示例

# 1. 创建小说生成任务
curl -X POST "http://104.244.90.202:9000/api/v1/novels" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI创作的奇幻冒险",
    "genre": "fantasy",
    "chapters": 18,
    "conflict_level": "high",
    "expert_advice": true
  }'

# 2. 查询任务进度
curl -X GET "http://104.244.90.202:9000/api/v1/tasks/TASK_ID/progress" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 3. 查询用户余额
curl -X GET "http://104.244.90.202:9000/api/v1/user/balance" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 4. 创建视频生成任务
curl -X POST "http://104.244.90.202:9000/api/v1/videos" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "novel",
    "source_id": "NOVEL_ID",
    "generation_mode": "animation",
    "duration": 300,
    "memory_points": true
  }'

# 5. 发布内容到平台
curl -X POST "http://104.244.90.202:9000/api/v1/publish" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "video",
    "content_id": "VIDEO_ID",
    "platforms": ["douyin", "xiaohongshu"],
    "publish_time": "immediate",
    "privacy": "public"
  }'</code></pre>
      </div>
    </div>
    
    <div class="api-actions">
      <a href="/api/docs" class="btn-primary">查看完整API文档</a>
      <a href="/api/playground" class="btn-secondary">API在线测试</a>
    </div>
  </div>
</section>
```

## 5. OpenClaw集成指南

### 5.1 OpenClaw集成入口
```html
<section id="openclaw" class="openclaw-integration">
  <h2>OpenClaw深度集成</h2>
  <p class="subtitle">作为OpenClaw的智能创作插件，提供命令行和自动化支持</p>
  
  <div class="integration-features">
    <div class="feature-card">
      <div class="feature-icon">🤖</div>
      <h3>命令行操作</h3>
      <p>支持OpenClaw命令行直接调用，集成到自动化工作流中</p>
      <pre><code class="language-bash">openclaw ai-novel create \
  --title "奇幻冒险" \
  --genre fantasy \
  --chapters 18 \
  --conflict high</code></pre>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">⚙️</div>
      <h3>配置管理</h3>
      <p>通过OpenClaw配置文件管理API密钥、默认参数和任务模板</p>
      <pre><code class="language-yaml"># ~/.openclaw/config.yaml
ai_novel_media:
  api_key: "your_api_key_here"
  default_genre: "fantasy"
  default_chapters: 18
  auto_publish: true
  platforms: ["douyin", "xiaohongshu"]</code></pre>
    </div>
    
    <div class="feature-card">
      <div class="feature-icon">📊</div>
      <h3>进度监控</h3>
      <p>在OpenClaw界面实时查看任务进度，接收完成通知</p>
      <pre><code class="language-bash"># 查看所有任务状态
openclaw ai-novel list

# 查看特定任务进度
openclaw ai-novel progress TASK_ID

# 实时监控任务
openclaw ai-novel watch TASK_ID</code></pre>
    </div>
  </div>
  
  <div class="integration-install">
    <h3>安装与配置</h3>
    
    <div class="install-steps">
      <div class="step">
        <div class="step-number">1</div>
        <div class="step-content">
          <h4>安装OpenClaw插件</h4>
          <pre><code class="language-bash"># 安装AI Novel Media Agent插件
openclaw plugin install ai-novel-media

# 或者从GitHub安装
openclaw plugin install https://github.com/your-repo/ai-novel-media-openclaw</code></pre>
        </div>
      </div>
      
      <div class="step">
        <div class="step-number">2</div>
        <div class="step-content">
          <h4>配置API密钥</h4>
          <pre><code class="language-bash"># 设置API密钥
openclaw config set ai_novel_media.api_key YOUR_API_KEY

# 验证连接
openclaw ai-novel test</code></pre>
        </div>
      </div>
      
      <div class="step">
        <div class="step-number">3</div>
        <div class="step-content">
          <h4>开始使用</h4>
          <pre><code class="language-bash"># 创建第一个小说任务
openclaw ai-novel create \
  --title "我的第一部AI小说" \
  --genre urban \
  --chapters 6 \
  --output-dir ./my-novel

# 将小说转为视频
openclaw ai-novel to-video NOVEL_ID \
  --mode animation \
  --duration 180

# 自动发布到平台
openclaw ai-novel publish VIDEO_ID \
  --platforms douyin,xiaohongshu \
  --schedule "tomorrow 10:00"</code></pre>
        </div>
      </div>
    </div>
    
    <div class="integration-actions">
      <a href="/openclaw/docs" class="btn-primary">查看完整集成文档</a>
      <a href="/openclaw/examples" class="btn-secondary">查看使用示例</a>
    </div>
  </div>
</section>
```

### 5.2 OpenClaw插件代码示例
```html
<div class="plugin-code-example">
  <h3>OpenClaw插件核心代码</h3>
  
  <div class="code-tabs">
    <button class="code-tab active" data-file="plugin.py">plugin.py</button>
    <button class="code-tab" data-file="commands.py">commands.py</button>
    <button class="code-tab" data-file="config.py">config.py</button>
  </div>
  
  <div class="code-content">
    <div id="plugin.py" class="code-block active">
      <pre><code class="language-python"># ai_novel_media_plugin.py
from openclaw.plugin import Plugin
from openclaw.command import command, argument, option
import requests
import json
from typing import Optional

class AINovelMediaPlugin(Plugin):
    """AI Novel Media Agent OpenClaw插件"""
    
    def __init__(self):
        super().__init__()
        self.name = "ai-novel-media"
        self.version = "1.0.0"
        self.description = "AI小说视频生成平台插件"
        
        # API配置
        self.base_url = "http://104.244.90.202:9000"
        self.api_key = None
        
    def setup(self, config):
        """插件初始化"""
        self.api_key = config.get("ai_novel_media.api_key")
        if not self.api_key:
            raise ValueError("请先配置API密钥: openclaw config set ai_novel_media.api_key YOUR_KEY")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    @command("ai-novel create")
    @argument("title", help="小说标题")
    @option("--genre", "-g", default="fantasy", help="小说题材")
    @option("--chapters", "-c", type=int, default=18, help="章节数量")
    @option("--conflict", default="high", help="冲突等级: low/medium/high")
    @option("--expert-advice", is_flag=True, help="启用专家建议")
    def create_novel(self, title: str, genre: str, chapters: int, 
                    conflict: str, expert_advice: bool):
        """创建小说生成任务"""
        payload = {
            "title": title,
            "genre": genre,
            "chapters": chapters,
            "conflict_level": conflict,
            "expert_advice": expert_advice
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/novels",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            task_id = result.get("id")
            estimated_cost = result.get("estimated_cost")
            
            self.logger.info(f"✅ 任务创建成功")
            self.logger.info(f"   任务ID: {task_id}")
            self.logger.info(f"   预估费用: ¥{estimated_cost}")
            self.logger.info(f"   查看进度: openclaw ai-novel progress {task_id}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ 请求失败: {e}")
            return None
    
    @command("ai-novel progress")
    @argument("task_id", help="任务ID")
    def get_progress(self, task_id: str):
        """获取任务进度"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/tasks/{task_id}/progress"
            )
            response.raise_for_status()
            progress = response.json()
            
            status = progress.get("status")
            current = progress.get("current_step")
            total = progress.get("total_steps")
            percent = progress.get("percent", 0)
            message = progress.get("message", "")
            
            # 进度条显示
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            self.logger.info(f"📊 任务进度: {task_id}")
            self.logger.info(f"   状态: {status}")
            self.logger.info(f"   进度: [{bar}] {percent}%")
            self.logger.info(f"   当前步骤: {current}/{total}")
            self.logger.info(f"   消息: {message}")
            
            return progress
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ 获取进度失败: {e}")
            return None
    
    @command("ai-novel balance")
    def get_balance(self):
        """查询用户余额"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/user/balance"
            )
            response.raise_for_status()
            balance = response.json()
            
            amount = balance.get("amount", 0)
            currency = balance.get("currency", "CNY")
            last_recharge = balance.get("last_recharge")
            
            self.logger.info(f"💰 账户余额")
            self.logger.info(f"   余额: {currency} {amount:.2f}")
            if last_recharge:
                self.logger.info(f"   最后充值: {last_recharge}")
            
            return balance
            
        except requests.exceptions.RequestException as