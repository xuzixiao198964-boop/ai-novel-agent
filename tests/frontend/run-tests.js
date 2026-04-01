#!/usr/bin/env node

/**
 * 前端测试运行脚本
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const execAsync = promisify(exec);

async function runTests() {
  console.log('🚀 开始运行前端测试...\n');
  
  try {
    // 运行静态契约测试
    console.log('📋 运行静态契约测试...');
    const { stdout: contractStdout } = await execAsync('npx vitest run static_contract.test.js', {
      cwd: __dirname,
      encoding: 'utf8'
    });
    console.log(contractStdout);
    
    // 运行单元测试
    console.log('🧪 运行单元测试...');
    const { stdout: unitStdout } = await execAsync('npx vitest run unit', {
      cwd: __dirname,
      encoding: 'utf8'
    });
    console.log(unitStdout);
    
    // 运行集成测试
    console.log('🔗 运行集成测试...');
    const { stdout: integrationStdout } = await execAsync('npx vitest run integration', {
      cwd: __dirname,
      encoding: 'utf8'
    });
    console.log(integrationStdout);
    
    // 运行所有测试并生成覆盖率报告
    console.log('📊 生成测试覆盖率报告...');
    const { stdout: coverageStdout } = await execAsync('npx vitest run --coverage', {
      cwd: __dirname,
      encoding: 'utf8'
    });
    console.log(coverageStdout);
    
    console.log('✅ 所有前端测试完成！');
    
  } catch (error) {
    console.error('❌ 测试运行失败:', error.message);
    if (error.stdout) {
      console.error('标准输出:', error.stdout);
    }
    if (error.stderr) {
      console.error('错误输出:', error.stderr);
    }
    process.exit(1);
  }
}

// 如果直接运行此脚本
if (import.meta.url === `file://${process.argv[1]}`) {
  runTests();
}

export { runTests };