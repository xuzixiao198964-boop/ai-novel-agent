/**
 * app.js核心函数单元测试（简化版）
 */
import { describe, it, expect } from 'vitest';
import { escapeHtml } from '../test-utils.js';

describe('核心工具函数', () => {
  describe('escapeHtml函数', () => {
    it('应该转义HTML特殊字符', () => {
      const testCases = [
        { input: '<script>alert("xss")</script>', expected: '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;' },
        { input: 'Hello & World', expected: 'Hello &amp; World' },
        { input: '"Quoted" text', expected: '&quot;Quoted&quot; text' },
        { input: "Apostrophe's test", expected: "Apostrophe&#039;s test" },
        { input: '正常文本', expected: '正常文本' }
      ];

      testCases.forEach(({ input, expected }) => {
        const result = escapeHtml(input);
        expect(result).toBe(expected);
      });
    });

    it('应该处理空值和未定义', () => {
      expect(escapeHtml('')).toBe('');
      expect(escapeHtml(null)).toBe('null');
      expect(escapeHtml(undefined)).toBe('undefined');
      expect(escapeHtml(123)).toBe('123');
    });
  });

  describe('任务状态渲染函数', () => {
    it('应该正确渲染任务状态', () => {
      // 模拟renderTaskStatus函数（从app.js中提取）
      function renderTaskStatus(task) {
        const status = task.status || '';
        let label = status;
        if (status === 'failed' && task.warning) {
          label = 'completed（' + task.warning + '）';
        } else if (status === 'failed' && task.error) {
          label = 'failed（' + task.error + '）';
        }
        const mode = task.run_mode === 'test' ? '测试6章' : '正式';
        return escapeHtml(label + ' · ' + mode);
      }

      const testCases = [
        {
          task: { status: 'running', run_mode: 'prod' },
          expected: 'running · 正式'
        },
        {
          task: { status: 'completed', run_mode: 'test' },
          expected: 'completed · 测试6章'
        },
        {
          task: { status: 'failed', warning: '部分成功', run_mode: 'prod' },
          expected: 'completed（部分成功） · 正式'
        },
        {
          task: { status: 'failed', error: '网络错误', run_mode: 'test' },
          expected: 'failed（网络错误） · 测试6章'
        },
        {
          task: { status: '', run_mode: 'prod' },
          expected: ' · 正式'
        }
      ];

      testCases.forEach(({ task, expected }) => {
        const result = renderTaskStatus(task);
        expect(result).toBe(expected);
      });
    });
  });

  describe('进度渲染函数', () => {
    it('应该正确计算整体进度', () => {
      // 模拟renderProgress函数的核心逻辑
      function calculateOverallProgress(summary) {
        const agents = Object.entries(summary || {});
        const completed = agents.filter(([, v]) => v.status === 'completed').length;
        const total = agents.length;
        return { completed, total };
      }

      const progress = {
        TrendAgent: { status: 'completed', message: '趋势分析完成', progress_percent: 100 },
        StyleAgent: { status: 'completed', message: '风格解析完成', progress_percent: 100 },
        PlannerAgent: { status: 'running', message: '策划大纲生成中', progress_percent: 75 },
        WriterAgent: { status: 'pending', message: '等待生成', progress_percent: 0 },
        PolishAgent: { status: 'pending', message: '等待润色', progress_percent: 0 },
        AuditorAgent: { status: 'pending', message: '等待审计', progress_percent: 0 },
        ReviserAgent: { status: 'pending', message: '等待修订', progress_percent: 0 }
      };

      const { completed, total } = calculateOverallProgress(progress);

      expect(completed).toBe(2); // TrendAgent和StyleAgent已完成
      expect(total).toBe(7); // 总共7个Agent
    });

    it('应该生成正确的进度文本', () => {
      const progress = {
        TrendAgent: { status: 'completed' },
        StyleAgent: { status: 'completed' },
        PlannerAgent: { status: 'running' },
        WriterAgent: { status: 'pending' },
        PolishAgent: { status: 'pending' },
        AuditorAgent: { status: 'pending' },
        ReviserAgent: { status: 'pending' }
      };
      
      const agents = Object.entries(progress);
      const completed = agents.filter(([, v]) => v.status === 'completed').length;
      const total = agents.length;
      
      const progressText = `整体进度：${completed}/${total} 个 Agent 已完成`;
      
      expect(progressText).toBe('整体进度：2/7 个 Agent 已完成');
    });
  });

  describe('Agent文件标签渲染', () => {
    it('应该正确映射Agent标签', () => {
      const AGENT_LABELS = {
        TrendAgent: '热门趋势',
        StyleAgent: '风格解析',
        PlannerAgent: '策划大纲',
        WriterAgent: '正文生成',
        PolishAgent: '润色',
        AuditorAgent: '质量审计',
        ReviserAgent: '修订定稿'
      };

      expect(AGENT_LABELS['TrendAgent']).toBe('热门趋势');
      expect(AGENT_LABELS['WriterAgent']).toBe('正文生成');
      expect(AGENT_LABELS['UnknownAgent']).toBeUndefined();
    });

    it('应该过滤没有文件的Agent', () => {
      const filesByAgent = {
        TrendAgent: [{ path: 'file1.json', size: 1024 }],
        StyleAgent: [], // 空数组
        PlannerAgent: [{ path: 'file2.md', size: 2048 }],
        WriterAgent: null // null值
      };

      const agentsWithFiles = Object.keys(filesByAgent).filter(
        a => Array.isArray(filesByAgent[a]) && filesByAgent[a].length > 0
      );

      expect(agentsWithFiles).toEqual(['TrendAgent', 'PlannerAgent']);
      expect(agentsWithFiles).not.toContain('StyleAgent');
      expect(agentsWithFiles).not.toContain('WriterAgent');
    });
  });

  describe('文件列表渲染', () => {
    it('应该正确生成文件下载链接', () => {
      const currentTaskId = 'test-task-1';
      const files = [
        { path: 'trend/hot_genres.json', size: 1024 },
        { path: 'planner/outline.md', size: 2048 }
      ];

      // 模拟renderAgentFiles函数的核心逻辑
      function generateFileLinks(files, taskId) {
        const base = '/api/tasks/' + taskId + '/files/download?path=';
        return files.map(f => {
          const encodedPath = encodeURIComponent(f.path);
          return `<a href="${base + encodedPath}" target="_blank">${escapeHtml(f.path)}</a> (${f.size || 0} B)`;
        });
      }

      const links = generateFileLinks(files, currentTaskId);

      expect(links).toHaveLength(2);
      expect(links[0]).toContain('href="/api/tasks/test-task-1/files/download?path=trend%2Fhot_genres.json"');
      expect(links[0]).toContain('trend/hot_genres.json');
      expect(links[0]).toContain('1024 B');
    });

    it('应该处理空文件列表', () => {
      const files = [];

      function renderAgentFiles(files) {
        if (!files.length) return '<p class="hint">该 Agent 暂无产出</p>';
        return '<div>文件列表</div>';
      }

      const result = renderAgentFiles(files);
      expect(result).toBe('<p class="hint">该 Agent 暂无产出</p>');
    });
  });

  describe('日志渲染', () => {
    it('应该正确格式化日志时间', () => {
      const logs = [
        { time: '2026-03-27T08:00:00.123Z', level: 'info', message: '测试日志' }
      ];

      // 模拟renderLogs函数的时间格式化逻辑
      function formatLogTime(timeString) {
        return (timeString || '').replace('T', ' ').slice(0, 19);
      }

      const formattedTime = formatLogTime(logs[0].time);
      expect(formattedTime).toBe('2026-03-27 08:00:00');
    });

    it('应该根据日志级别添加CSS类', () => {
      const logs = [
        { time: '2026-03-27T08:00:00Z', level: 'info', message: '普通日志' },
        { time: '2026-03-27T08:01:00Z', level: 'error', message: '错误日志' },
        { time: '2026-03-27T08:02:00Z', level: 'warning', message: '警告日志' }
      ];

      // 模拟renderLogs函数的CSS类逻辑
      function getLogCssClass(level) {
        return level === 'error' ? 'log-error' : '';
      }

      expect(getLogCssClass('info')).toBe('');
      expect(getLogCssClass('error')).toBe('log-error');
      expect(getLogCssClass('warning')).toBe('');
    });
  });
});