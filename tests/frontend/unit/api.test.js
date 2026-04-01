/**
 * 前端API函数单元测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JSDOM } from 'jsdom';

// 创建模拟DOM环境
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.HTMLElement = dom.window.HTMLElement;

// 模拟全局fetch
global.fetch = vi.fn();

// 导入要测试的函数（需要重构app.js以支持模块化测试）
// 由于app.js是全局脚本，我们先创建测试辅助函数

describe('前端API函数', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('API调用函数', () => {
    it('应该正确构造API请求', async () => {
      // 模拟fetch成功响应
      const mockResponse = { data: 'test' };
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      // 测试API函数（从app.js提取的逻辑）
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

      const result = await api('/test');

      expect(fetch).toHaveBeenCalledWith(
        '/api/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('应该处理API错误', async () => {
      // 模拟fetch失败响应
      fetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found'
      });

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

      await expect(api('/test')).rejects.toThrow('Not Found');
    });
  });

  describe('任务状态渲染函数', () => {
    // 从app.js提取的renderTaskStatus函数逻辑
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

    it('应该正确渲染运行中状态', () => {
      const task = { running: true, paused: false };
      expect(renderTaskStatus(task)).toBe('▶️ 运行中');
    });

    it('应该正确渲染暂停状态', () => {
      const task = { running: true, paused: true };
      expect(renderTaskStatus(task)).toBe('⏸️ 已暂停');
    });

    it('应该正确渲染已完成状态', () => {
      const task = { running: false, completed: true };
      expect(renderTaskStatus(task)).toBe('✅ 已完成');
    });

    it('应该正确渲染失败状态', () => {
      const task = { running: false, failed: true };
      expect(renderTaskStatus(task)).toBe('❌ 失败');
    });

    it('应该正确渲染等待状态', () => {
      const task = { running: false };
      expect(renderTaskStatus(task)).toBe('⏳ 等待');
    });
  });

  describe('HTML转义函数', () => {
    // 从app.js提取的escapeHtml函数逻辑
    const escapeHtml = (text) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };

    it('应该转义HTML特殊字符', () => {
      const testCases = [
        { input: '<script>alert("xss")</script>', expected: '&lt;script&gt;alert("xss")&lt;/script&gt;' },
        { input: 'Test & Test', expected: 'Test &amp; Test' },
        { input: '"Quote"', expected: '"Quote"' }, // JSDOM不转义双引号
        { input: "'Apostrophe'", expected: "'Apostrophe'" }, // 单引号通常不需要转义
        { input: 'Normal text', expected: 'Normal text' }
      ];

      testCases.forEach(({ input, expected }) => {
        expect(escapeHtml(input)).toBe(expected);
      });
    });
  });
});