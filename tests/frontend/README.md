# AI小说生成Agent系统 - 前端测试

本文档描述AI小说生成Agent系统的前端测试策略和执行方法。

## 测试类型

### 1. 契约测试 (Contract Tests)
- **位置**: `tests/frontend/`
- **目的**: 验证静态资源与主控制台脚本的约定
- **测试内容**:
  - HTML文件引用正确的JS和CSS
  - 关键DOM元素ID存在
  - API前缀和路径正确

### 2. 单元测试 (Unit Tests)
- **位置**: `tests/frontend/unit/`
- **目的**: 测试前端JavaScript函数和模块
- **测试内容**:
  - API调用函数
  - 状态渲染函数
  - 工具函数（HTML转义、格式化等）

### 3. 集成测试 (Integration Tests)
- **位置**: `tests/frontend/integration/`
- **目的**: 测试用户交互和组件协作
- **测试内容**:
  - 任务管理交互
  - 按钮点击事件处理
  - API调用与状态更新

### 4. 组件测试 (Component Tests)
- **位置**: `tests/frontend/components/`
- **目的**: 测试UI组件渲染和状态
- **测试内容**:
  - 进度条渲染
  - 任务状态显示
  - 文件列表渲染

## 测试框架

- **测试运行器**: Vitest
- **断言库**: Vitest内置断言
- **模拟**: Vitest模拟函数
- **DOM环境**: JSDOM

## 运行测试

### 安装依赖
```bash
cd tests/frontend
npm install
```

### 运行所有测试
```bash
npm test
```

### 运行特定类型测试
```bash
# 运行单元测试
npm run test:unit

# 运行集成测试
npm run test:integration

# 运行组件测试
npm run test:components

# 运行契约测试
npm run test:contract

# 运行所有测试（包括自定义脚本）
npm run test:all

# 运行测试并生成覆盖率报告
npm run test:coverage
```

### 开发模式（监听文件变化）
```bash
npm run test:watch
```

## 测试文件结构

```
tests/frontend/
├── README.md                    # 本文档
├── package.json                 # 依赖和脚本
├── vitest.config.js            # Vitest配置
├── setup.js                    # 测试设置
├── run_tests.js               # 测试运行脚本
├── static_contract.test.js     # 契约测试
├── unit/                       # 单元测试
│   └── api.test.js            # API函数测试
├── integration/                # 集成测试
│   └── task-management.test.js # 任务管理测试
└── components/                 # 组件测试
    └── progress-renderer.test.js # 进度渲染测试
```

## 编写新测试

### 单元测试示例
```javascript
import { describe, it, expect } from 'vitest';

describe('函数名称', () => {
  it('应该执行预期行为', () => {
    const result = someFunction(input);
    expect(result).toBe(expected);
  });
});
```

### 集成测试示例
```javascript
import { describe, it, expect, vi } from 'vitest';
import { JSDOM } from 'jsdom';

describe('用户交互', () => {
  beforeEach(() => {
    // 设置DOM环境
    const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
    global.document = dom.window.document;
    
    // 模拟fetch
    global.fetch = vi.fn();
  });
  
  it('应该处理按钮点击', () => {
    // 测试代码
  });
});
```

## 测试覆盖率

运行覆盖率报告：
```bash
npm run test:coverage
```

覆盖率报告将生成在 `coverage/` 目录中。

## 持续集成

前端测试已集成到GitHub Actions工作流中，每次推送或拉取请求时自动运行。

## 最佳实践

1. **测试独立性**: 每个测试应该独立运行，不依赖其他测试的状态
2. **模拟外部依赖**: 使用Vitest模拟函数模拟fetch、定时器等
3. **清理资源**: 在afterEach中清理模拟函数和定时器
4. **描述性测试名**: 使用描述性的测试名称说明测试目的
5. **边界条件**: 测试正常情况、边界情况和错误情况

## 故障排除

### 常见问题

1. **JSDOM相关错误**
   - 确保安装了jsdom: `npm install jsdom`
   - 在测试文件中正确设置全局变量

2. **模块导入错误**
   - 确保使用ES模块语法（type: "module"）
   - 检查文件路径是否正确

3. **模拟函数不工作**
   - 确保在测试前调用`vi.clearAllMocks()`
   - 检查模拟函数是否正确设置

### 调试测试
```bash
# 使用--reporter=verbose查看详细输出
npx vitest run --reporter=verbose

# 调试特定测试文件
npx vitest run tests/frontend/unit/api.test.js
```

## 相关文档

- [Vitest文档](https://vitest.dev/)
- [JSDOM文档](https://github.com/jsdom/jsdom)
- [AI小说生成Agent系统测试文档](../docs/requirements/testing_documentation.md)