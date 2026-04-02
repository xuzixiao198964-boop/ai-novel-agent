# AI Novel Media Agent 增强版 - 测试文档

## 文档信息
- **文档编号**: TEST-ENHANCED-001
- **文档标题**: AI小说视频生成系统增强版测试策略
- **项目名称**: AI Novel Media Agent 增强版
- **创建日期**: 2026-04-02
- **创建人**: AI Novel Agent Assistant
- **状态**: 📝 测试策略版
- **版本**: 2.0

## 1. 测试概述

### 1.1 测试目标
确保增强版系统在功能、性能、安全、用户体验等方面达到设计要求，满足新增需求。

### 1.2 测试范围
```
测试范围包括：
1. 新增功能测试
   - 产品官方网站 (80端口)
   - 后台管理系统
   - 用户界面改造
   - 移动端App

2. 核心功能测试
   - 7个Agent小说生成流水线
   - 视频生成功能
   - 用户选择流程
   - 任务管理系统

3. 集成测试
   - 系统间接口集成
   - 第三方服务集成
   - 数据一致性测试

4. 性能测试
   - 系统性能基准测试
   - 压力测试和负载测试
   - 并发用户测试

5. 安全测试
   - 认证授权测试
   - 数据安全测试
   - 漏洞扫描测试

6. 用户体验测试
   - 界面可用性测试
   - 跨平台兼容性测试
   - 移动端体验测试
```

### 1.3 测试环境
```
测试环境配置：
1. 开发测试环境
   - 用途: 功能开发和单元测试
   - 配置: 本地开发环境
   - 数据: 测试数据生成器

2. 集成测试环境
   - 用途: 系统集成测试
   - 配置: 类生产环境
   - 数据: 模拟生产数据

3. 性能测试环境
   - 用途: 性能压力测试
   - 配置: 独立性能测试环境
   - 数据: 大规模测试数据

4. 用户验收环境
   - 用途: 用户验收测试
   - 配置: 生产环境镜像
   - 数据: 真实用户数据
```

## 2. 单元测试策略

### 2.1 后端单元测试

#### 2.1.1 Python后端测试
```python
# 测试文件结构
tests/
├── unit/
│   ├── test_user_service.py
│   ├── test_task_service.py
│   ├── test_content_service.py
│   ├── test_video_service.py
│   └── test_admin_service.py
├── integration/
│   ├── test_api_integration.py
│   └── test_database_integration.py
└── e2e/
    ├── test_workflow_e2e.py
    └── test_performance_e2e.py
```

#### 2.1.2 测试用例设计
```python
# 用户选择逻辑测试用例
class TestUserSelection(unittest.TestCase):
    def test_initialization_selection(self):
        """测试用户初始化选择"""
        selection = UserSelection(
            generation_type="novel",
            novel_options={
                "length": "medium",
                "genre": "male",
                "subgenre": "fantasy"
            }
        )
        self.assertEqual(selection.generation_type, "novel")
        self.assertEqual(selection.novel_options["length"], "medium")
    
    def test_conflict_resolution(self):
        """测试选项冲突处理"""
        selection = UserSelection(
            generation_type="both",
            novel_options={"length": "random"},
            video_options={"source": "random"}
        )
        result = selection.resolve_conflicts()
        self.assertIn(result["novel_length"], ["micro", "short", "medium", "long"])
        self.assertIn(result["video_source"], ["novel", "news", "external"])
    
    def test_time_estimation(self):
        """测试时间预估算法"""
        selection = UserSelection(
            generation_type="video",
            video_options={"source": "novel", "length": "medium"}
        )
        estimate = selection.estimate_time()
        self.assertGreater(estimate.total_time, 0)
        self.assertLess(estimate.total_time, 86400)  # 不超过24小时
```

#### 2.1.3 队列系统测试
```python
# 任务队列测试用例
class TestTaskQueue(unittest.TestCase):
    def setUp(self):
        self.queue = TaskQueue()
        self.queue.clear()
    
    def test_queue_priority(self):
        """测试队列优先级"""
        # 添加不同优先级的任务
        self.queue.enqueue(task_id="task1", priority="normal")
        self.queue.enqueue(task_id="task2", priority="high")
        self.queue.enqueue(task_id="task3", priority="vip")
        
        # 验证VIP任务优先
        next_task = self.queue.dequeue()
        self.assertEqual(next_task.task_id, "task3")
    
    def test_queue_position(self):
        """测试排队位置计算"""
        for i in range(10):
            self.queue.enqueue(task_id=f"task{i}", priority="normal")
        
        position = self.queue.get_position("task5")
        self.assertEqual(position, 5)
    
    def test_wait_time_estimation(self):
        """测试等待时间预估"""
        # 模拟历史任务数据
        historical_data = [
            {"task_type": "novel", "length": "short", "actual_time": 1800},
            {"task_type": "novel", "length": "medium", "actual_time": 7200},
            {"task_type": "video", "source": "novel", "actual_time": 3600}
        ]
        
        estimator = WaitTimeEstimator(historical_data)
        estimate = estimator.estimate(
            task_type="novel",
            length="medium",
            current_load=0.5
        )
        
        self.assertGreater(estimate, 0)
        self.assertLess(estimate, 14400)  # 不超过4小时
```

### 2.2 前端单元测试

#### 2.2.1 React组件测试
```javascript
// 官方网站组件测试
describe('OfficialWebsite Components', () => {
  test('HomePage renders correctly', () => {
    const { getByText } = render(<HomePage />);
    expect(getByText('AI Novel Media Agent')).toBeInTheDocument();
    expect(getByText('一站式AI内容创作平台')).toBeInTheDocument();
  });
  
  test('DownloadCenter shows platform options', () => {
    const { getByText } = render(<DownloadCenter />);
    expect(getByText('iOS App下载')).toBeInTheDocument();
    expect(getByText('Android App下载')).toBeInTheDocument();
    expect(getByText('微信小程序')).toBeInTheDocument();
  });
  
  test('APIDocumentation shows API endpoints', () => {
    const { getByText } = render(<APIDocumentation />);
    expect(getByText('RESTful API')).toBeInTheDocument();
    expect(getByText('WebSocket API')).toBeInTheDocument();
    expect(getByText('API Key申请')).toBeInTheDocument();
  });
});

// 用户选择组件测试
describe('UserSelection Components', () => {
  test('GenerationTypeSelection shows options', () => {
    const { getByLabelText } = render(<GenerationTypeSelection />);
    expect(getByLabelText('只生成小说')).toBeInTheDocument();
    expect(getByLabelText('生成视频')).toBeInTheDocument();
    expect(getByLabelText('小说和视频都生成')).toBeInTheDocument();
  });
  
  test('NovelOptions shows length options', () => {
    const { getByLabelText } = render(<NovelOptions />);
    expect(getByLabelText('微型小说 (1-10章)')).toBeInTheDocument();
    expect(getByLabelText('短篇小说 (10-50章)')).toBeInTheDocument();
    expect(getByLabelText('中篇小说 (50-200章)')).toBeInTheDocument();
    expect(getByLabelText('长篇小说 (200-500章)')).toBeInTheDocument();
  });
  
  test('GenreSelection shows categories', () => {
    const { getByText } = render(<GenreSelection />);
    expect(getByText('儿童故事')).toBeInTheDocument();
    expect(getByText('男频小说')).toBeInTheDocument();
    expect(getByText('女频小说')).toBeInTheDocument();
  });
});
```

#### 2.2.2 Vue管理组件测试
```javascript
// 后台管理组件测试
describe('AdminManagement Components', () => {
  test('UserManagement shows user list', async () => {
    const mockUsers = [
      { id: 1, username: 'user1', email: 'user1@example.com', role: 'user' },
      { id: 2, username: 'user2', email: 'user2@example.com', role: 'vip' }
    ];
    
    axios.get.mockResolvedValue({ data: mockUsers });
    
    const { findByText } = render(<UserManagement />);
    expect(await findByText('user1')).toBeInTheDocument();
    expect(await findByText('user2')).toBeInTheDocument();
  });
  
  test('WorkManagement shows work statistics', async () => {
    const mockStats = {
      total_works: 1234,
      today_works: 56,
      pending_review: 12,
      approved_works: 1200
    };
    
    axios.get.mockResolvedValue({ data: mockStats });
    
    const { findByText } = render(<WorkManagement />);
    expect(await findByText('总作品数: 1234')).toBeInTheDocument();
    expect(await findByText('今日新增: 56')).toBeInTheDocument();
  });
  
  test('TaskMonitor shows real-time progress', () => {
    const mockTasks = [
      { id: 'task1', progress: 65, current_agent: 'WriterAgent' },
      { id: 'task2', progress: 30, current_agent: 'PlannerAgent' }
    ];
    
    const { getByText } = render(<TaskMonitor tasks={mockTasks} />);
    expect(getByText('task1 - 65%')).toBeInTheDocument();
    expect(getByText('WriterAgent')).toBeInTheDocument();
  });
});
```

## 3. 集成测试策略

### 3.1 API集成测试

#### 3.1.1 RESTful API测试
```python
# API集成测试用例
class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_user = self.create_test_user()
        self.auth_token = self.login_test_user()
    
    def test_user_initialization_api(self):
        """测试用户初始化API"""
        response = self.client.post(
            "/api/v1/user/initialize",
            json={
                "generation_type": "novel",
                "novel_options": {
                    "length": "medium",
                    "genre": "male",
                    "subgenre": "fantasy"
                }
            },
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertIn("estimated_time", data)
        self.assertIn("estimated_cost", data)
    
    def test_task_queue_api(self):
        """测试任务队列API"""
        response = self.client.get(
            "/api/v1/tasks/queue",
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("queue_position", data)
        self.assertIn("estimated_wait_time", data)
        self.assertIn("tasks_ahead", data)
    
    def test_progress_monitoring_api(self):
        """测试进度监控API"""
        # 先创建一个测试任务
        task_response = self.client.post(
            "/api/v1/tasks",
            json={"name": "测试任务", "type": "novel"},
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        task_id = task_response.json()["task_id"]
        
        # 查询任务进度
        progress_response = self.client.get(
            f"/api/v1/tasks/{task_id}/progress",
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        
        self.assertEqual(progress_response.status_code, 200)
        data = progress_response.json()
        self.assertIn("overall_progress", data)
        self.assertIn("current_agent", data)
        self.assertIn("agent_progress", data)
```

#### 3.1.2 WebSocket集成测试
```python
# WebSocket集成测试
class TestWebSocketIntegration(unittest.TestCase):
    def test_websocket_connection(self):
        """测试WebSocket连接"""
        with websockets.connect(f"ws://localhost:9000/ws?token={self.auth_token}") as websocket:
            # 测试连接建立
            self.assertTrue(websocket.open)
            
            # 订阅任务更新
            subscribe_message = {
                "event": "task.subscribe",
                "data": {"task_id": "test_task_123"}
            }
            await websocket.send(json.dumps(subscribe_message))
            
            # 接收服务器响应
            response = await websocket.recv()
            response_data = json.loads(response)
            self.assertEqual(response_data["event"], "task.subscribed")
    
    def test_real_time_updates(self):
        """测试实时更新"""
        with websockets.connect(f"ws://localhost:9000/ws?token={self.auth_token}") as websocket:
            # 模拟任务进度更新
            task_id = self.create_test_task()
            
            # 等待进度更新事件
            for _ in range(10):  # 最多等待10个事件
                response = await websocket.recv(timeout=5)
                response_data = json.loads(response)
                
                if response_data["event"] == "task.progress":
                    self.assertEqual(response_data["data"]["task_id"], task_id)
                    self.assertIn("progress", response_data["data"])
                    break
    
    def test_queue_updates(self):
        """测试队列更新"""
        with websockets.connect(f"ws://localhost:9000/ws?token={self.auth_token}") as websocket:
            # 模拟队列变化
            self.add_multiple_tasks_to_queue(5)
            
            # 等待队列更新事件
            response = await websocket.recv(timeout=5)
            response_data = json.loads(response)
            
            if response_data["event"] == "queue.update":
                self.assertIn("queue_position", response_data["data"])
                self.assertIn("estimated_wait_time", response_data["data"])
```

### 3.2 数据库集成测试

#### 3.2.1 数据一致性测试
```python
# 数据库一致性测试
class TestDatabaseConsistency(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseTestClient()
        self.clean_test_data()
    
    def test_user_preferences_consistency(self):
        """测试用户偏好数据一致性"""
        # 创建测试用户
        user_id = self.db.create_user("test_user", "test@example.com")
        
        # 设置用户偏好
        preferences = {
            "default_genre": "male",
            "default_length": "medium",
            "ui_theme": "dark",
            "notification_enabled": True
        }
        
        self.db.set_user_preferences(user_id, preferences)
        
        # 验证数据一致性
        stored_preferences = self.db.get_user_preferences(user_id)
        self.assertEqual(stored_preferences["default_genre"], "male")
        self.assertEqual(stored_preferences["default_length"], "medium")
        self.assertEqual(stored_preferences["ui_theme"], "dark")
        self.assertTrue(stored_preferences["notification_enabled"])
    
    def test_task_progress_tracking(self):
        """测试任务进度跟踪一致性"""
        task_id = self.db.create_task(
            user_id="test_user_123",
            task_type="novel",
            task_name="测试小说任务"
        )
        
        # 模拟进度更新
        progress_updates = [
            {"agent": "TrendAgent", "progress": 100, "status": "completed"},
            {"agent": "StyleAgent", "progress": 100, "status": "completed"},
            {"agent": "PlannerAgent", "progress": 75, "status": "running"}
        ]
        
        for update in progress_updates:
            self.db.update_task_progress(task_id, update)
        
        # 验证进度一致性
        task_progress = self.db.get_task_progress(task_id)
        self.assertEqual(len(task_progress), 3)
        
        overall_progress = self.db.calculate_overall_progress(task_id)
        self.assertGreaterEqual(overall_progress, 0)
        self.assertLessEqual(overall_progress, 100)
    
    def test_queue_consistency(self):
        """测试队列数据一致性"""
        # 添加多个任务到队列
        task_ids = []
        for i in range(5):
            task_id = f"test_task_{i}"
            self.db.enqueue_task(task_id, priority="normal")
            task_ids.append(task_id)
        
        # 验证队列顺序
        queue = self.db.get_task_queue()
        self.assertEqual(len(queue), 5)
        
        # 验证出队顺序
        for expected_task_id in task_ids:
            dequeued_task = self.db.dequeue_task()
            self.assertEqual(dequeued_task["task_id"], expected_task_id)
```

## 4. 端到端测试策略

### 4.1 完整工作流测试

#### 4.1.1 小说生成工作流
```python
# 小说生成端到端测试
class TestNovelGenerationE2E(unittest.TestCase):
    def test_complete_novel_workflow(self):
        """测试完整小说生成工作流"""
        # 1. 用户注册和登录
        user_id = self.register_test_user()
        auth_token = self.login_user(user_id)
        
        # 2. 用户初始化选择
        selection_result = self.user_initialization(
            auth_token,
            generation_type="novel",
            novel_options={
