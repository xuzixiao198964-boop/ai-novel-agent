/**
 * UI组件单元测试
 */
import { describe, it, expect, vi } from 'vitest';

describe('UI组件函数', () => {
  describe('进度条组件', () => {
    it('应该根据进度百分比计算CSS宽度', () => {
      // 模拟进度条宽度计算函数
      function calculateProgressWidth(percent) {
        if (percent < 0) return '0%';
        if (percent > 100) return '100%';
        return `${percent}%`;
      }

      const testCases = [
        { percent: 0, expected: '0%' },
        { percent: 50, expected: '50%' },
        { percent: 100, expected: '100%' },
        { percent: 75.5, expected: '75.5%' },
        { percent: -10, expected: '0%' },
        { percent: 150, expected: '100%' }
      ];

      testCases.forEach(({ percent, expected }) => {
        const width = calculateProgressWidth(percent);
        expect(width).toBe(expected);
      });
    });

    it('应该根据状态返回对应的CSS类', () => {
      // 模拟状态CSS类函数
      function getStatusClass(status) {
        const statusClasses = {
          'pending': 'status-pending',
          'running': 'status-running',
          'completed': 'status-completed',
          'failed': 'status-failed',
          'paused': 'status-paused'
        };
        return statusClasses[status] || 'status-unknown';
      }

      expect(getStatusClass('pending')).toBe('status-pending');
      expect(getStatusClass('running')).toBe('status-running');
      expect(getStatusClass('completed')).toBe('status-completed');
      expect(getStatusClass('failed')).toBe('status-failed');
      expect(getStatusClass('paused')).toBe('status-paused');
      expect(getStatusClass('unknown')).toBe('status-unknown');
    });
  });

  describe('任务列表组件', () => {
    it('应该正确排序任务列表', () => {
      const tasks = [
        { task_id: 'task-1', created_at: '2026-03-27T10:00:00Z', status: 'completed' },
        { task_id: 'task-2', created_at: '2026-03-27T11:00:00Z', status: 'running' },
        { task_id: 'task-3', created_at: '2026-03-27T09:00:00Z', status: 'pending' }
      ];

      // 模拟任务排序函数
      function sortTasks(tasks, sortBy = 'created_at', order = 'desc') {
        return [...tasks].sort((a, b) => {
          const aValue = a[sortBy];
          const bValue = b[sortBy];
          
          if (order === 'desc') {
            return bValue.localeCompare(aValue);
          } else {
            return aValue.localeCompare(bValue);
          }
        });
      }

      // 按创建时间降序排序
      const sortedDesc = sortTasks(tasks, 'created_at', 'desc');
      expect(sortedDesc[0].task_id).toBe('task-2'); // 最新
      expect(sortedDesc[1].task_id).toBe('task-1');
      expect(sortedDesc[2].task_id).toBe('task-3'); // 最旧

      // 按创建时间升序排序
      const sortedAsc = sortTasks(tasks, 'created_at', 'asc');
      expect(sortedAsc[0].task_id).toBe('task-3'); // 最旧
      expect(sortedAsc[1].task_id).toBe('task-1');
      expect(sortedAsc[2].task_id).toBe('task-2'); // 最新
    });

    it('应该过滤任务列表', () => {
      const tasks = [
        { task_id: 'task-1', status: 'completed', name: '测试任务1' },
        { task_id: 'task-2', status: 'running', name: '运行中任务' },
        { task_id: 'task-3', status: 'failed', name: '失败任务' },
        { task_id: 'task-4', status: 'completed', name: '测试任务2' }
      ];

      // 模拟任务过滤函数
      function filterTasks(tasks, filterCriteria) {
        return tasks.filter(task => {
          if (filterCriteria.status && task.status !== filterCriteria.status) {
            return false;
          }
          if (filterCriteria.searchText) {
            const searchLower = filterCriteria.searchText.toLowerCase();
            const taskName = (task.name || '').toLowerCase();
            const taskId = task.task_id.toLowerCase();
            return taskName.includes(searchLower) || taskId.includes(searchLower);
          }
          return true;
        });
      }

      // 按状态过滤
      const completedTasks = filterTasks(tasks, { status: 'completed' });
      expect(completedTasks).toHaveLength(2);
      expect(completedTasks.every(t => t.status === 'completed')).toBe(true);

      // 按搜索文本过滤
      const searchedTasks = filterTasks(tasks, { searchText: '测试' });
      expect(searchedTasks).toHaveLength(2);
      expect(searchedTasks.map(t => t.task_id)).toEqual(['task-1', 'task-4']);

      // 组合过滤
      const combinedFilter = filterTasks(tasks, { 
        status: 'completed', 
        searchText: '任务1' 
      });
      expect(combinedFilter).toHaveLength(1);
      expect(combinedFilter[0].task_id).toBe('task-1');
    });
  });

  describe('分页组件', () => {
    it('应该正确计算分页信息', () => {
      // 模拟分页计算函数
      function calculatePagination(totalItems, itemsPerPage, currentPage) {
        const totalPages = Math.ceil(totalItems / itemsPerPage);
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
        
        return {
          totalPages,
          currentPage,
          startIndex,
          endIndex,
          hasPrevious: currentPage > 1,
          hasNext: currentPage < totalPages,
          pageNumbers: Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
            let pageNum;
            if (totalPages <= 5) {
              pageNum = i + 1;
            } else if (currentPage <= 3) {
              pageNum = i + 1;
            } else if (currentPage >= totalPages - 2) {
              pageNum = totalPages - 4 + i;
            } else {
              pageNum = currentPage - 2 + i;
            }
            return pageNum;
          })
        };
      }

      // 测试用例1：少量项目
      const pagination1 = calculatePagination(15, 10, 1);
      expect(pagination1.totalPages).toBe(2);
      expect(pagination1.startIndex).toBe(0);
      expect(pagination1.endIndex).toBe(10);
      expect(pagination1.hasPrevious).toBe(false);
      expect(pagination1.hasNext).toBe(true);
      expect(pagination1.pageNumbers).toEqual([1, 2]);

      // 测试用例2：多页情况，当前页在中间
      const pagination2 = calculatePagination(100, 10, 5);
      expect(pagination2.totalPages).toBe(10);
      expect(pagination2.startIndex).toBe(40);
      expect(pagination2.endIndex).toBe(50);
      expect(pagination2.hasPrevious).toBe(true);
      expect(pagination2.hasNext).toBe(true);
      expect(pagination2.pageNumbers).toEqual([3, 4, 5, 6, 7]);

      // 测试用例3：最后一页
      const pagination3 = calculatePagination(100, 10, 10);
      expect(pagination3.totalPages).toBe(10);
      expect(pagination3.startIndex).toBe(90);
      expect(pagination3.endIndex).toBe(100);
      expect(pagination3.hasPrevious).toBe(true);
      expect(pagination3.hasNext).toBe(false);
      expect(pagination3.pageNumbers).toEqual([6, 7, 8, 9, 10]);
    });
  });

  describe('表单验证组件', () => {
    it('应该验证任务名称', () => {
      // 模拟任务名称验证函数
      function validateTaskName(name) {
        const errors = [];
        
        if (!name || name.trim() === '') {
          errors.push('任务名称不能为空');
        }
        
        if (name.length > 100) {
          errors.push('任务名称不能超过100个字符');
        }
        
        if (/[<>"&]/.test(name)) {
          errors.push('任务名称包含非法字符');
        }
        
        return {
          isValid: errors.length === 0,
          errors
        };
      }

      const testCases = [
        { name: '正常任务名称', expectedValid: true, expectedErrors: [] },
        { name: '', expectedValid: false, expectedErrors: ['任务名称不能为空'] },
        { name: '   ', expectedValid: false, expectedErrors: ['任务名称不能为空'] },
        { name: 'a'.repeat(101), expectedValid: false, expectedErrors: ['任务名称不能超过100个字符'] },
        { name: '测试<script>alert("xss")</script>', expectedValid: false, expectedErrors: ['任务名称包含非法字符'] },
        { name: '包含&符号', expectedValid: false, expectedErrors: ['任务名称包含非法字符'] }
      ];

      testCases.forEach(({ name, expectedValid, expectedErrors }) => {
        const result = validateTaskName(name);
        expect(result.isValid).toBe(expectedValid);
        expect(result.errors).toEqual(expectedErrors);
      });
    });

    it('应该验证章节数量', () => {
      // 模拟章节数量验证函数
      function validateChapterCount(count, mode = 'prod') {
        const errors = [];
        
        if (typeof count !== 'number' || isNaN(count)) {
          errors.push('章节数量必须是数字');
          return { isValid: false, errors };
        }
        
        if (!Number.isInteger(count)) {
          errors.push('章节数量必须是整数');
        }
        
        if (count <= 0) {
          errors.push('章节数量必须大于0');
        }
        
        if (mode === 'test' && count !== 6) {
          errors.push('测试模式只能生成6章');
        }
        
        if (mode === 'prod' && count > 100) {
          errors.push('正式模式最多生成100章');
        }
        
        return {
          isValid: errors.length === 0,
          errors
        };
      }

      // 测试正式模式
      expect(validateChapterCount(18, 'prod')).toEqual({ isValid: true, errors: [] });
      expect(validateChapterCount(0, 'prod')).toEqual({ 
        isValid: false, 
        errors: ['章节数量必须大于0'] 
      });
      expect(validateChapterCount(101, 'prod')).toEqual({ 
        isValid: false, 
        errors: ['正式模式最多生成100章'] 
      });

      // 测试测试模式
      expect(validateChapterCount(6, 'test')).toEqual({ isValid: true, errors: [] });
      expect(validateChapterCount(18, 'test')).toEqual({ 
        isValid: false, 
        errors: ['测试模式只能生成6章'] 
      });

      // 测试无效输入
      expect(validateChapterCount('不是数字', 'prod')).toEqual({ 
        isValid: false, 
        errors: ['章节数量必须是数字'] 
      });
      expect(validateChapterCount(18.5, 'prod')).toEqual({ 
        isValid: false, 
        errors: ['章节数量必须是整数'] 
      });
    });
  });

  describe('时间格式化组件', () => {
    it('应该格式化时间显示', () => {
      // 模拟时间格式化函数
      function formatTime(timeString, format = 'relative') {
        if (!timeString) return '未知时间';
        
        const date = new Date(timeString);
        if (isNaN(date.getTime())) return '无效时间';
        
        const now = new Date();
        const diffMs = now - date;
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (format === 'relative') {
          if (diffMinutes < 1) return '刚刚';
          if (diffMinutes < 60) return `${diffMinutes}分钟前`;
          if (diffHours < 24) return `${diffHours}小时前`;
          if (diffDays < 7) return `${diffDays}天前`;
          
          // 超过一周显示具体日期
          return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
          });
        } else if (format === 'full') {
          return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          });
        } else if (format === 'time-only') {
          return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          });
        }
        
        return date.toISOString().slice(0, 19).replace('T', ' ');
      }

      // 测试相对时间格式
      const now = new Date();
      const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000).toISOString();
      const twoHoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString();
      const threeDaysAgo = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString();
      
      expect(formatTime(fiveMinutesAgo, 'relative')).toBe('5分钟前');
      expect(formatTime(twoHoursAgo, 'relative')).toBe('2小时前');
      expect(formatTime(threeDaysAgo, 'relative')).toBe('3天前');

      // 测试无效时间
      expect(formatTime('')).toBe('未知时间');
      expect(formatTime('invalid-date')).toBe('无效时间');

      // 测试完整格式
      const testDate = '2026-03-27T08:30:00Z';
      const fullFormat = formatTime(testDate, 'full');
      // 注意：不同环境的日期格式可能不同，我们检查它包含日期和时间即可
      expect(fullFormat).toMatch(/\d{4}/); // 包含年份
      expect(fullFormat).toMatch(/\d{2}/); // 包含月份或日期
      expect(fullFormat).toMatch(/:/); // 包含时间分隔符
    });

    it('应该计算执行时间', () => {
      // 模拟执行时间计算函数
      function calculateExecutionTime(startTime, endTime) {
        if (!startTime) return '未开始';
        
        const start = new Date(startTime);
        if (isNaN(start.getTime())) return '无效开始时间';
        
        let end;
        if (endTime) {
          end = new Date(endTime);
          if (isNaN(end.getTime())) return '无效结束时间';
        } else {
          end = new Date();
        }
        
        const diffMs = end - start;
        if (diffMs < 0) return '时间错误';
        
        const seconds = Math.floor(diffMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (days > 0) {
          return `${days}天${hours % 24}小时`;
        } else if (hours > 0) {
          return `${hours}小时${minutes % 60}分钟`;
        } else if (minutes > 0) {
          return `${minutes}分钟${seconds % 60}秒`;
        } else {
          return `${seconds}秒`;
        }
      }

      // 测试用例
      const startTime = '2026-03-27T08:00:00Z';
      
      expect(calculateExecutionTime('')).toBe('未开始');
      expect(calculateExecutionTime('invalid')).toBe('无效开始时间');
      
      // 测试不同时间间隔
      const endTime1 = '2026-03-27T08:00:30Z'; // 30秒后
      expect(calculateExecutionTime(startTime, endTime1)).toBe('30秒');
      
      const endTime2 = '2026-03-27T08:05:30Z'; // 5分30秒后
      expect(calculateExecutionTime(startTime, endTime2)).toBe('5分钟30秒');
      
      const endTime3 = '2026-03-27T10:30:45Z'; // 2小时30分45秒后
      expect(calculateExecutionTime(startTime, endTime3)).toBe('2小时30分钟');
      
      const endTime4 = '2026-03-28T10:30:00Z'; // 1天2小时30分后
      expect(calculateExecutionTime(startTime, endTime4)).toBe('1天2小时');
    });
  });
});