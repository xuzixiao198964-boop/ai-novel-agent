#!/usr/bin/env node

/**
 * 前端测试运行脚本
 * 运行所有前端测试并生成报告
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const execAsync = promisify(exec);

async function runTests() {
  console.log('🚀 开始运行前端测试...\n');

  try {
    // 1. 运行单元测试
    console.log('📋 运行单元测试...');
    const unitResult = await execAsync('npx vitest run tests/frontend/unit --reporter=verbose');
    console.log(unitResult.stdout);
    if (unitResult.stderr) console.error(unitResult.stderr);

    // 2. 运行集成测试
    console.log('\n📋 运行集成测试...');
    const integrationResult = await execAsync('npx vitest run tests/frontend/integration --reporter=verbose');
    console.log(integrationResult.stdout);
    if (integrationResult.stderr) console.error(integrationResult.stderr);

    // 3. 运行组件测试
    console.log('\n📋 运行组件测试...');
    const componentResult = await execAsync('npx vitest run tests/frontend/components --reporter=verbose');
    console.log(componentResult.stdout);
    if (componentResult.stderr) console.error(integrationResult.stderr);

    // 4. 运行契约测试
    console.log('\n📋 运行契约测试...');
    const contractResult = await execAsync('npx vitest run tests/frontend --reporter=verbose');
    console.log(contractResult.stdout);
    if (contractResult.stderr) console.error(contractResult.stderr);

    // 5. 生成测试报告
    console.log('\n📊 生成测试报告...');
    const reportResult = await execAsync('npx vitest run --reporter=json --reporter=junit');
    console.log('测试报告已生成');

    // 6. 汇总测试结果
    await generateTestSummary();

    console.log('\n✅ 前端测试完成！');

  } catch (error) {
    console.error('\n❌ 测试运行失败:', error.message);
    if (error.stdout) console.error('标准输出:', error.stdout);
    if (error.stderr) console.error('错误输出:', error.stderr);
    process.exit(1);
  }
}

async function generateTestSummary() {
  const summary = {
    timestamp: new Date().toISOString(),
    testTypes: {
      unit: { tests: 0, passed: 0, failed: 0 },
      integration: { tests: 0, passed: 0, failed: 0 },
      component: { tests: 0, passed: 0, failed: 0 },
      contract: { tests: 0, passed: 0, failed: 0 }
    },
    overall: {
      totalTests: 0,
      totalPassed: 0,
      totalFailed: 0,
      successRate: 0
    }
  };

  // 这里可以解析测试结果文件来生成详细报告
  // 目前先输出基本统计

  const reportDir = join(__dirname, '..', '..', 'test-reports');
  if (!existsSync(reportDir)) {
    mkdirSync(reportDir, { recursive: true });
  }

  const summaryFile = join(reportDir, 'frontend-test-summary.json');
  writeFileSync(summaryFile, JSON.stringify(summary, null, 2), 'utf8');
  
  console.log(`测试报告已保存到: ${summaryFile}`);
}

// 运行测试
runTests().catch(console.error);