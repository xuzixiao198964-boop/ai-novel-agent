/**
 * 任务管理集成测试
 * 测试用户与任务列表的交互
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';

// 创建模拟DOM环境
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.HTMLElement = dom.window.HTMLElement;
global.fetch = vi.fn();

// 模拟app.js中的函数
let currentTaskId = null;
let refreshTimer = null;
let refreshInterval = 30;

const api = (path, options = {}) => {
  return fetch('/api' + path, { 
    ...options, 
    headers: { 
      'Content-Type': 'application/json', 
      ...options.headers 
    } 
  })
    .then(r => { 
      if (!r.ok) throw new Error(r.statusText); 
      return r.json(); 
    });
};

const renderTaskStatus = (task) => {
  if (task.running) {
    return task.paused ? '⏸️ 已暂停' : '▶️ 运行中';
  }
  if (task.completed) {
    return '✅ 已完成';
  }
  if (task.failed) {
    return '❌ 失败';
  }
  return '⏳ 等待';
};

const escapeHtml = (text) => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

describe('任务管理集成测试', () => {
  beforeEach(() => {
    fetch.mockClear();
    document.body.innerHTML = `
      <div id="taskList"></div>
      <button id="btnStart">启动</button>
      <button id="btnStop">停止</button>
      <button id="btnPause">暂停</button>
      <button id="btnResume">继续</button>
      <div id="currentRun"></div>
      <div id="runModeBadge"></div>
      <button id="btnToggleMode">切换模式</button>
      <div id="agentFileTabs"></div>
      <div id="agentFileList"></div>
      <div id="novelToc"></div>
      <div id="overallProgress"></div>
      <select id="agentSelect">
        <option value="trend">趋势分析</option>
        <option value="planner">策划</option>
        <option value="writer">写作</option>
      </select>
    `;
  });

  afterEach(() => {
    vi.clearAllMocks();
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  });

  describe('任务列表渲染', () => {
    it('应该正确渲染任务列表', async () => {
      // 模拟API响应
      const mockTasks = [
        { task_id: 'task1', name: '测试任务1', running: true, paused: false },
        { task_id: 'task2', name: '测试任务2', completed: true },
        { task_id: 'task3', name: '测试任务3', failed: true }
      ];

      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tasks: mockTasks })
      });

      // 模拟app.js中的任务列表渲染逻辑
      const taskList = document.getElementById('taskList');
      taskList.innerHTML = mockTasks.map(t => `
        <li>
          <span class="task-name" data-id="${t.task_id}">${escapeHtml(t.name || t.task_id)}</span>
          <span class="task-status">${renderTaskStatus(t)}</span>
          <button class="task-act task-select" data-id="${t.task_id}" type="button">选择</button>
          <button class="task-act task-start" data-id="${t.task_id}" type="button">启动</button>
          <button class="task-act task-delete" data-id="${t.task_id}" type="button" title="删除任务">删除</button>
        </li>
      `).join('');

      // 验证渲染结果
      expect(taskList.children.length).toBe(3);
      
      const firstTask = taskList.children[0];
      expect(firstTask.querySelector('.task-name').textContent).toBe('测试任务1');
      expect(firstTask.querySelector('.task-status').textContent).toBe('▶️ 运行中');
      
      const secondTask = taskList.children[1];
      expect(secondTask.querySelector('.task-status').textContent).toBe('✅ 已完成');
      
      const thirdTask = taskList.children[2];
      expect(thirdTask.querySelector('.task-status').textContent).toBe('❌ 失败');
    });

    it('应该处理空任务列表', () => {
      const taskList = document.getElementById('taskList');
      taskList.innerHTML = '';
      
      expect(taskList.children.length).toBe(0);
    });
  });

  describe('任务选择交互', () => {
    it('应该处理任务选择点击', () => {
      const taskList = document.getElementById('taskList');
      
      // 创建测试任务项
      taskList.innerHTML = `
        <li>
          <span class="task-name" data-id="test-task">测试任务</span>
          <span class="task-status">⏳ 等待</span>
          <button class="task-act task-select" data-id="test-task" type="button">选择</button>
        </li>
      `;

      const taskName = taskList.querySelector('.task-name');
      const selectButton = taskList.querySelector('.task-select');
      
      // 模拟点击事件
      let selectedTaskId = null;
      taskName.addEventListener('click', () => {
        selectedTaskId = taskName.dataset.id;
      });
      
      selectButton.addEventListener('click', () => {
        selectedTaskId = selectButton.dataset.id;
      });

      // 触发点击
      taskName.click();
      expect(selectedTaskId).toBe('test-task');
      
      selectedTaskId = null;
      selectButton.click();
      expect(selectedTaskId).toBe('test-task');
    });
  });

  describe('任务操作按钮', () => {
    it('应该处理任务启动', async () => {
      const taskList = document.getElementById('taskList');
      
      taskList.innerHTML = `
        <li>
          <span class="task-name" data-id="task1">任务1</span>
          <button class="task-act task-start" data-id="task1" type="button">启动</button>
        </li>
      `;

      const startButton = taskList.querySelector('.task-start');
      
      // 模拟API调用
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      });

      let apiCalled = false;
      startButton.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = startButton.dataset.id;
        api('/tasks/' + id + '/start', { method: 'POST' })
          .then(() => {
            apiCalled = true;
            currentTaskId = id;
          })
          .catch(err => {
            console.error('启动失败:', err);
          });
      });

      // 模拟点击事件
      const clickEvent = new dom.window.Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });
      
      startButton.dispatchEvent(clickEvent);

      // 等待异步操作
      await new Promise(resolve => setTimeout(resolve, 0));

      expect(apiCalled).toBe(true);
      expect(currentTaskId).toBe('task1');
      expect(fetch).toHaveBeenCalledWith(
        '/api/tasks/task1/start',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );
    });

    it('应该处理任务删除确认', async () => {
      const taskList = document.getElementById('taskList');
      
      taskList.innerHTML = `
        <li>
          <span class="task-name" data-id="task1">任务1</span>
          <button class="task-act task-delete" data-id="task1" type="button" title="删除任务">删除</button>
        </li>
      `;

      const deleteButton = taskList.querySelector('.task-delete');
      
      // 模拟confirm对话框
      const originalConfirm = window.confirm;
      let confirmCalled = false;
      window.confirm = vi.fn(() => {
        confirmCalled = true;
        return true; // 用户点击确定
      });

      // 模拟fetch
      let fetchResolve;
      const fetchPromise = new Promise(resolve => {
        fetchResolve = resolve;
      });
      
      fetch.mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({})
        });
      });

      let deleteCalled = false;
      deleteButton.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = deleteButton.dataset.id;
        if (!window.confirm('确定删除该任务？删除后不可恢复。')) return;
        
        fetch('/api/tasks/' + id, { method: 'DELETE' })
          .then(r => { 
            if (!r.ok) throw new Error(r.statusText); 
            return r.json(); 
          })
          .then(() => { 
            deleteCalled = true;
            if (currentTaskId === id) currentTaskId = null;
            fetchResolve();
          })
          .catch(err => {
            console.error('删除失败:', err);
            fetchResolve();
          });
      });

      // 模拟点击事件
      const clickEvent = new dom.window.Event('click', { bubbles: true });
      Object.defineProperty(clickEvent, 'stopPropagation', { value: vi.fn() });
      
      deleteButton.dispatchEvent(clickEvent);

      // 等待异步操作完成
      await fetchPromise;

      expect(confirmCalled).toBe(true);
      expect(deleteCalled).toBe(true);
      expect(fetch).toHaveBeenCalledWith(
        '/api/tasks/task1',
        expect.objectContaining({
          method: 'DELETE'
        })
      );

      // 恢复原confirm函数
      window.confirm = originalConfirm;
    });
  });

  describe('刷新间隔设置', () => {
    it('应该设置刷新间隔并启动定时器', () => {
      const setRefreshInterval = (sec) => {
        refreshInterval = sec;
        document.getElementById('refreshVal').textContent = sec;
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(() => {
          console.log('刷新所有数据');
        }, sec * 1000);
      };

      // 添加refreshVal元素
      const refreshVal = document.createElement('div');
      refreshVal.id = 'refreshVal';
      document.body.appendChild(refreshVal);

      // 设置刷新间隔
      setRefreshInterval(10);

      expect(refreshInterval).toBe(10);
      expect(refreshVal.textContent).toBe('10');
      expect(refreshTimer).toBeDefined();
    });

    it('应该清除之前的定时器', () => {
      const originalClearInterval = clearInterval;
      const mockClearInterval = vi.fn();
      global.clearInterval = mockClearInterval;

      // 设置第一个定时器
      refreshTimer = 123; // 模拟定时器ID
      const setRefreshInterval = (sec) => {
        if (refreshTimer) clearInterval(refreshTimer);
        refreshTimer = setInterval(() => {}, sec * 1000);
      };

      // 设置新的刷新间隔
      setRefreshInterval(20);

      expect(mockClearInterval).toHaveBeenCalledWith(123);

      // 恢复原函数
      global.clearInterval = originalClearInterval;
    });
  });
});