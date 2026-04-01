/**
 * 前端测试工具函数
 */

// 模拟DOM环境
export function setupDOM() {
  // 创建全局document对象
  global.document = {
    getElementById: (id) => {
      const elements = {
        'refreshVal': { textContent: '' },
        'currentRun': { textContent: '' },
        'btnStop': { disabled: false },
        'btnStart': { disabled: false },
        'btnPause': { disabled: false },
        'btnResume': { disabled: false },
        'chkAutoRun': { checked: false },
        'runModeBadge': { textContent: '' },
        'btnToggleMode': { textContent: '' },
        'taskList': { innerHTML: '' },
        'agentFileTabs': { innerHTML: '' },
        'agentFileList': { innerHTML: '' },
        'novelToc': { innerHTML: '' },
        'overallProgress': { textContent: '' },
        'agentCards': { innerHTML: '' },
        'agentDetail': { innerHTML: '' },
        'logContainer': { innerHTML: '' },
        'agentSelect': { value: '' }
      };
      return elements[id] || { textContent: '', innerHTML: '', disabled: false, checked: false, value: '' };
    },
    querySelectorAll: () => [],
    createElement: () => ({ 
      addEventListener: () => {},
      setAttribute: () => {},
      appendChild: () => {},
      textContent: ''
    })
  };

  // 模拟全局fetch
  global.fetch = () => {};
  
  // 模拟全局alert
  global.alert = () => {};
  
  // 模拟全局confirm
  global.confirm = () => true;
  
  // 模拟全局setInterval和clearInterval
  global.setInterval = () => 'timer-id';
  global.clearInterval = () => {};
}

// 清理DOM环境
export function cleanupDOM() {
  delete global.document;
  delete global.fetch;
  delete global.alert;
  delete global.confirm;
  delete global.setInterval;
  delete global.clearInterval;
}

// 模拟API响应
export function mockApiResponse(data, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data)
  });
}

// 模拟API错误
export function mockApiError(status = 500, message = 'Internal Server Error') {
  return Promise.resolve({
    ok: false,
    status,
    statusText: message,
    json: () => Promise.reject(new Error(message))
  });
}

// HTML转义函数（简化版，不依赖document）
export function escapeHtml(text) {
  if (text == null) return String(text);
  
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 创建测试任务数据
export function createTestTask(id = 'test-task-1', status = 'running', name = '测试任务') {
  return {
    task_id: id,
    name: name,
    status: status,
    run_mode: 'prod',
    created_at: '2026-03-27T08:00:00Z',
    updated_at: '2026-03-27T08:30:00Z'
  };
}

// 创建测试进度数据
export function createTestProgress() {
  return {
    TrendAgent: { status: 'completed', message: '趋势分析完成', progress_percent: 100 },
    StyleAgent: { status: 'completed', message: '风格解析完成', progress_percent: 100 },
    PlannerAgent: { status: 'running', message: '策划大纲生成中', progress_percent: 75 },
    WriterAgent: { status: 'pending', message: '等待生成', progress_percent: 0 },
    PolishAgent: { status: 'pending', message: '等待润色', progress_percent: 0 },
    AuditorAgent: { status: 'pending', message: '等待审计', progress_percent: 0 },
    ReviserAgent: { status: 'pending', message: '等待修订', progress_percent: 0 }
  };
}

// 创建测试文件数据
export function createTestFiles() {
  return {
    by_agent: {
      TrendAgent: [
        { path: 'trend/hot_genres.json', size: 1024 },
        { path: 'trend/analysis_report.md', size: 2048 }
      ],
      PlannerAgent: [
        { path: 'planner/story_outline.md', size: 4096 },
        { path: 'planner/chapter_summaries.json', size: 3072 }
      ]
    }
  };
}

// 创建测试日志数据
export function createTestLogs() {
  return {
    logs: [
      { time: '2026-03-27T08:00:00Z', level: 'info', message: '任务开始执行' },
      { time: '2026-03-27T08:05:00Z', level: 'info', message: 'TrendAgent开始分析' },
      { time: '2026-03-27T08:10:00Z', level: 'info', message: 'TrendAgent分析完成' },
      { time: '2026-03-27T08:15:00Z', level: 'warning', message: '网络延迟较高' }
    ]
  };
}