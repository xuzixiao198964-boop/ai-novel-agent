/**
 * Vitest全局测试设置文件
 */
import { vi, beforeEach, afterEach, afterAll } from 'vitest';

// 设置全局测试超时
vi.setConfig({ testTimeout: 10000 });

// 全局beforeEach和afterEach钩子
beforeEach(() => {
  // 可以在这里设置测试前的全局状态
});

afterEach(() => {
  // 清理测试后的全局状态
  vi.clearAllMocks();
});

// 全局afterAll钩子
afterAll(() => {
  // 所有测试完成后的清理工作
});