#!/bin/bash
# 远程调试脚本 - 需要在服务器上运行

echo "=== AI小说生成Agent系统调试 ==="
echo "时间: $(date)"
echo ""

# 1. 检查服务状态
echo "1. 检查systemd服务状态:"
systemctl status ai-novel-agent --no-pager

echo ""
echo "2. 检查服务日志 (最近50行):"
journalctl -u ai-novel-agent --no-pager -n 50

echo ""
echo "3. 检查进程:"
ps aux | grep -E "(uvicorn|python.*ai-novel)" | grep -v grep

echo ""
echo "4. 检查/data目录权限:"
ls -la /opt/ai-novel-agent/backend/data/

echo ""
echo "5. 检查数据库:"
if [ -f "/opt/ai-novel-agent/backend/data/novel_platform.db" ]; then
    echo "数据库文件存在"
    sqlite3 /opt/ai-novel-agent/backend/data/novel_platform.db "SELECT task_id, name, status, error FROM tasks ORDER BY created_at DESC LIMIT 5;"
else
    echo "数据库文件不存在"
fi

echo ""
echo "6. 检查Python环境:"
cd /opt/ai-novel-agent && python3 -c "import sys; print('Python版本:', sys.version)"
cd /opt/ai-novel-agent && python3 -c "try: import app.agents; print('Agents模块导入成功'); except Exception as e: print(f'Agents导入失败: {e}')"

echo ""
echo "7. 检查关键依赖:"
cd /opt/ai-novel-agent && python3 -c "
import importlib
deps = ['yaml', 'httpx', 'sqlite3', 'asyncio', 'aiofiles', 'fastapi', 'uvicorn']
for dep in deps:
    try:
        importlib.import_module(dep if dep != 'yaml' else 'yaml')
        print(f'{dep}: OK')
    except ImportError as e:
        print(f'{dep}: MISSING - {e}')
"

echo ""
echo "8. 尝试手动运行Agent测试:"
cd /opt/ai-novel-agent && python3 -c "
import asyncio
import sys
sys.path.insert(0, '/opt/ai-novel-agent/backend')

try:
    from app.agents.trend import TrendAgent
    print('TrendAgent导入成功')
    
    # 尝试创建实例
    agent = TrendAgent(task_id='test', chapter_count=6)
    print('TrendAgent实例创建成功')
    
except Exception as e:
    print(f'Agent测试失败: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== 调试完成 ==="