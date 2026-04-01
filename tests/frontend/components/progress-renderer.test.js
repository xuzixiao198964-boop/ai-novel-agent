/**
 * 进度渲染组件测试
 * 测试进度条和状态显示组件
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JSDOM } from 'jsdom';

// 创建模拟DOM环境
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;

describe('进度渲染组件', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="overallProgress"></div>
      <div id="agentProgress"></div>
      <div id="novelToc"></div>
    `;
  });

  describe('总体进度渲染', () => {
    const renderOverallProgress = (progressData) => {
      const container = document.getElementById('overallProgress');
      if (!progressData || !progressData.overall) {
        container.innerHTML = '<p class="hint">暂无进度数据</p>';
        return;
      }

      const overall = progressData.overall;
      const percent = Math.round(overall.progress * 100);
      
      container.innerHTML = `
        <div class="progress-container">
          <div class="progress-header">
            <span class="progress-title">总体进度</span>
            <span class="progress-percent">${percent}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${percent}%"></div>
          </div>
          <div class="progress-details">
            <span class="progress-stage">阶段: ${overall.current_stage || '未知'}</span>
            <span class="progress-chapter">章节: ${overall.current_chapter || 0}/${overall.total_chapters || 0}</span>
            <span class="progress-time">预计剩余: ${overall.estimated_remaining || '未知'}</span>
          </div>
        </div>
      `;
    };

    it('应该渲染进度条和百分比', () => {
      const progressData = {
        overall: {
          progress: 0.65,
          current_stage: '写作',
          current_chapter: 13,
          total_chapters: 20,
          estimated_remaining: '2小时'
        }
      };

      renderOverallProgress(progressData);

      const container = document.getElementById('overallProgress');
      expect(container.innerHTML).toContain('总体进度');
      expect(container.innerHTML).toContain('65%');
      expect(container.innerHTML).toContain('阶段: 写作');
      expect(container.innerHTML).toContain('章节: 13/20');
      expect(container.innerHTML).toContain('预计剩余: 2小时');
      
      // 验证进度条宽度
      expect(container.innerHTML).toContain('width: 65%');
    });

    it('应该处理无进度数据的情况', () => {
      renderOverallProgress(null);

      const container = document.getElementById('overallProgress');
      expect(container.innerHTML).toContain('暂无进度数据');
    });

    it('应该处理部分进度数据', () => {
      const progressData = {
        overall: {
          progress: 0.3
          // 缺少其他字段
        }
      };

      renderOverallProgress(progressData);

      const container = document.getElementById('overallProgress');
      expect(container.innerHTML).toContain('30%');
      expect(container.innerHTML).toContain('阶段: 未知');
      expect(container.innerHTML).toContain('章节: 0/0');
    });
  });

  describe('Agent进度渲染', () => {
    const renderAgentProgress = (progressData) => {
      const container = document.getElementById('agentProgress');
      if (!progressData || !progressData.agents) {
        container.innerHTML = '<p class="hint">暂无Agent进度</p>';
        return;
      }

      const agents = progressData.agents;
      container.innerHTML = `
        <div class="agent-progress-container">
          <h3>Agent进度</h3>
          <div class="agent-list">
            ${Object.entries(agents).map(([agentName, agentData]) => `
              <div class="agent-item" data-agent="${agentName}">
                <div class="agent-header">
                  <span class="agent-name">${agentName}</span>
                  <span class="agent-status ${agentData.status}">${getStatusText(agentData.status)}</span>
                </div>
                ${agentData.progress !== undefined ? `
                  <div class="agent-progress-bar">
                    <div class="agent-progress-fill" style="width: ${Math.round(agentData.progress * 100)}%"></div>
                  </div>
                  <div class="agent-details">
                    <span class="agent-stage">${agentData.current_stage || '进行中'}</span>
                    ${agentData.estimated_remaining ? `<span class="agent-time">剩余: ${agentData.estimated_remaining}</span>` : ''}
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    };

    const getStatusText = (status) => {
      const statusMap = {
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'waiting': '等待中',
        'paused': '已暂停'
      };
      return statusMap[status] || status;
    };

    it('应该渲染多个Agent的进度', () => {
      const progressData = {
        agents: {
          'trend': {
            status: 'completed',
            progress: 1.0,
            current_stage: '数据分析完成'
          },
          'planner': {
            status: 'running',
            progress: 0.75,
            current_stage: '章节策划',
            estimated_remaining: '30分钟'
          },
          'writer': {
            status: 'waiting',
            progress: 0
          }
        }
      };

      renderAgentProgress(progressData);

      const container = document.getElementById('agentProgress');
      
      // 验证标题
      expect(container.innerHTML).toContain('Agent进度');
      
      // 验证Agent数量
      expect(container.innerHTML).toContain('data-agent="trend"');
      expect(container.innerHTML).toContain('data-agent="planner"');
      expect(container.innerHTML).toContain('data-agent="writer"');
      
      // 验证状态文本
      expect(container.innerHTML).toContain('已完成');
      expect(container.innerHTML).toContain('运行中');
      expect(container.innerHTML).toContain('等待中');
      
      // 验证进度条
      expect(container.innerHTML).toContain('width: 100%'); // trend
      expect(container.innerHTML).toContain('width: 75%');  // planner
      
      // 验证详细信息
      expect(container.innerHTML).toContain('数据分析完成');
      expect(container.innerHTML).toContain('章节策划');
      expect(container.innerHTML).toContain('剩余: 30分钟');
    });

    it('应该处理无Agent数据的情况', () => {
      renderAgentProgress(null);

      const container = document.getElementById('agentProgress');
      expect(container.innerHTML).toContain('暂无Agent进度');
    });
  });

  describe('小说目录渲染', () => {
    const renderNovelToc = (novelData) => {
      const container = document.getElementById('novelToc');
      if (!novelData || !novelData.chapters) {
        container.innerHTML = '<p class="hint">成书未生成或任务未选</p>';
        return;
      }

      const chapters = novelData.chapters;
      container.innerHTML = `
        <div class="novel-toc-container">
          <h3>小说目录</h3>
          <div class="chapter-list">
            ${chapters.map((chapter, index) => `
              <div class="chapter-item ${chapter.status || ''}" data-chapter="${index + 1}">
                <div class="chapter-header">
                  <span class="chapter-number">第${index + 1}章</span>
                  <span class="chapter-title">${escapeHtml(chapter.title || '未命名')}</span>
                  <span class="chapter-status">${getChapterStatusText(chapter.status)}</span>
                </div>
                ${chapter.summary ? `<div class="chapter-summary">${escapeHtml(chapter.summary)}</div>` : ''}
                ${chapter.word_count ? `<div class="chapter-meta">字数: ${chapter.word_count}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    };

    const escapeHtml = (text) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };

    const getChapterStatusText = (status) => {
      const statusMap = {
        'draft': '草稿',
        'written': '已写作',
        'polished': '已润色',
        'audited': '已审核',
        'final': '最终版'
      };
      return statusMap[status] || '未知';
    };

    it('应该渲染小说目录', () => {
      const novelData = {
        chapters: [
          {
            title: '开端',
            summary: '故事开始，主角登场',
            status: 'final',
            word_count: 3250
          },
          {
            title: '发展',
            summary: '情节推进，冲突升级',
            status: 'polished',
            word_count: 3420
          },
          {
            title: '高潮',
            summary: '关键转折，冲突解决',
            status: 'written',
            word_count: 3850
          },
          {
            title: '结局',
            status: 'draft'
          }
        ]
      };

      renderNovelToc(novelData);

      const container = document.getElementById('novelToc');
      
      // 验证标题
      expect(container.innerHTML).toContain('小说目录');
      
      // 验证章节数量
      expect(container.innerHTML).toContain('第1章');
      expect(container.innerHTML).toContain('第2章');
      expect(container.innerHTML).toContain('第3章');
      expect(container.innerHTML).toContain('第4章');
      
      // 验证章节标题
      expect(container.innerHTML).toContain('开端');
      expect(container.innerHTML).toContain('发展');
      expect(container.innerHTML).toContain('高潮');
      expect(container.innerHTML).toContain('结局');
      
      // 验证状态
      expect(container.innerHTML).toContain('最终版');
      expect(container.innerHTML).toContain('已润色');
      expect(container.innerHTML).toContain('已写作');
      expect(container.innerHTML).toContain('草稿');
      
      // 验证摘要
      expect(container.innerHTML).toContain('故事开始，主角登场');
      expect(container.innerHTML).toContain('情节推进，冲突升级');
      
      // 验证字数
      expect(container.innerHTML).toContain('字数: 3250');
      expect(container.innerHTML).toContain('字数: 3420');
      expect(container.innerHTML).toContain('字数: 3850');
    });

    it('应该处理无章节数据的情况', () => {
      renderNovelToc(null);

      const container = document.getElementById('novelToc');
      expect(container.innerHTML).toContain('成书未生成或任务未选');
    });

    it('应该处理空章节列表', () => {
      const novelData = {
        chapters: []
      };

      renderNovelToc(novelData);

      const container = document.getElementById('novelToc');
      expect(container.innerHTML).toContain('小说目录');
      expect(container.innerHTML).not.toContain('第1章');
    });

    it('应该转义HTML特殊字符', () => {
      const novelData = {
        chapters: [
          {
            title: '<script>alert("xss")</script>',
            summary: 'Test & Test'
          }
        ]
      };

      renderNovelToc(novelData);

      const container = document.getElementById('novelToc');
      expect(container.innerHTML).toContain('&lt;script&gt;alert("xss")&lt;/script&gt;');
      expect(container.innerHTML).toContain('Test &amp; Test');
      expect(container.innerHTML).not.toContain('<script>');
    });
  });

  describe('文件列表渲染', () => {
    const renderAgentFiles = (files) => {
      if (!files || files.length === 0) {
        return '<p class="hint">该Agent暂无文件</p>';
      }

      return `
        <div class="file-list">
          ${files.map(file => `
            <div class="file-item" data-path="${escapeHtml(file.path)}">
              <div class="file-header">
                <span class="file-name">${escapeHtml(file.name)}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <span class="file-time">${formatTime(file.modified)}</span>
              </div>
              <div class="file-actions">
                <button class="btn-preview" data-path="${escapeHtml(file.path)}">预览</button>
                <button class="btn-download" data-path="${escapeHtml(file.path)}">下载</button>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    };

    const escapeHtml = (text) => {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    };

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const formatTime = (timestamp) => {
      if (!timestamp) return '未知时间';
      const date = new Date(timestamp);
      return date.toLocaleString('zh-CN');
    };

    it('应该渲染文件列表', () => {
      const files = [
        {
          name: 'chapter_1.md',
          path: '/tasks/task1/writer/chapter_1.md',
          size: 2048,
          modified: '2026-03-27T10:30:00Z'
        },
        {
          name: 'outline.json',
          path: '/tasks/task1/planner/outline.json',
          size: 5120,
          modified: '2026-03-27T09:15:00Z'
        },
        {
          name: 'trend_analysis.csv',
          path: '/tasks/task1/trend/trend_analysis.csv',
          size: 10240,
          modified: '2026-03-27T08:45:00Z'
        }
      ];

      const html = renderAgentFiles(files);

      // 验证文件数量
      expect(html).toContain('file-item');
      expect((html.match(/file-item/g) || []).length).toBe(3);
      
      // 验证文件名
      expect(html).toContain('chapter_1.md');
      expect(html).toContain('outline.json');
      expect(html).toContain('trend_analysis.csv');
      
      // 验证文件大小格式化
      expect(html).toContain('2 KB');
      expect(html).toContain('5 KB');
      expect(html).toContain('10 KB');
      
      // 验证按钮
      expect(html).toContain('btn-preview');
      expect(html).toContain('btn-download');
      expect(html).toContain('data-path="/tasks/task1/writer/chapter_1.md"');
    });

    it('应该处理空文件列表', () => {
      const html = renderAgentFiles([]);
      expect(html).toContain('该Agent暂无文件');
    });

    it('应该处理null或undefined文件列表', () => {
      const html1 = renderAgentFiles(null);
      const html2 = renderAgentFiles(undefined);
      
      expect(html1).toContain('该Agent暂无文件');
      expect(html2).toContain('该Agent暂无文件');
    });

    it('应该转义文件名中的特殊字符', () => {
      const files = [
        {
          name: 'test<script>.md',
          path: '/tasks/task1/test<script>.md',
          size: 1024,
          modified: '2026-03-27T10:30:00Z'
        }
      ];

      const html = renderAgentFiles(files);
      
      expect(html).toContain('test&lt;script&gt;.md');
      expect(html).toContain('data-path="/tasks/task1/test&lt;script&gt;.md"');
      expect(html).not.toContain('<script>');
    });

    it('应该格式化文件大小', () => {
      const testCases = [
        { bytes: 0, expected: '0 B' },
        { bytes: 500, expected: '500 B' },
        { bytes: 1024, expected: '1 KB' },
        { bytes: 1536, expected: '1.5 KB' },
        { bytes: 1048576, expected: '1 MB' },
        { bytes: 1572864, expected: '1.5 MB' },
        { bytes: 1073741824, expected: '1 GB' }
      ];

      testCases.forEach(({ bytes, expected }) => {
        expect(formatFileSize(bytes)).toBe(expected);
      });
    });
  });
});