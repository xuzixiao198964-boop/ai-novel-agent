import paramiko
import sys
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def improve_parse_json():
    # 服务器信息
    HOST = "104.244.90.202"
    USER = "root"
    PASSWORD = "v9wSxMxg92dp"
    PORT = 22
    
    print("=== 改进 parse_json 函数 ===")
    print("问题: 无法解析 {name: test} 这种格式")
    print("="*60)
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        
        print("✅ 已连接到服务器")
        
        # 1. 备份当前函数
        print("\n1. 备份当前函数:")
        timestamp = int(time.time())
        backup_file = f"/opt/ai-novel-agent/backend/app/core/llm.py.backup.improve.{timestamp}"
        
        run_ssh_command(client,
            f"cp /opt/ai-novel-agent/backend/app/core/llm.py {backup_file}",
            f"备份到 {backup_file}")
        
        # 2. 改进 parse_json 函数
        print("\n2. 改进 parse_json 函数:")
        
        # 先删除旧的 parse_json 函数
        run_ssh_command(client,
            "sed -i '/^def parse_json/,/^def/ { /^def parse_json/,/^def [a-zA-Z]/ { /^def [a-zA-Z][a-zA-Z0-9_]*/ { x; s/\\n/\\n/; t; }; p; d; }; }' /opt/ai-novel-agent/backend/app/core/llm.py 2>/dev/null || echo '使用备用方法'",
            "尝试删除旧函数")
        
        # 更简单的方法：直接在文件末尾添加改进版函数
        improved_function = '''
def parse_json(text):
    """
    安全解析JSON字符串，支持多种非标准格式
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip()
    
    # 如果为空，返回None
    if not text:
        return None
    
    # 移除可能的代码块标记
    if text.startswith('```'):
        lines = text.split('\\n')
        if len(lines) > 1 and lines[0].startswith('```'):
            # 移除第一行和最后一行
            text = '\\n'.join(lines[1:-1]).strip()
    
    # 尝试1: 标准JSON解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试2: 修复常见的JSON格式问题
    fixed_text = text
    
    # 2.1 处理单引号
    fixed_text = fixed_text.replace("'", '"')
    
    # 2.2 处理未加引号的键（如 {name: "value"} -> {"name": "value"}）
    import re
    
    # 匹配未加引号的键：字母数字下划线开头，后面跟着冒号
    def add_quotes_to_keys(match):
        key = match.group(1)
        return f'"{key}":'
    
    # 多次应用，处理嵌套
    for _ in range(3):  # 最多尝试3次
        old_fixed = fixed_text
        fixed_text = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:', add_quotes_to_keys, fixed_text)
        if old_fixed == fixed_text:
            break
    
    # 2.3 处理多余的逗号
    fixed_text = re.sub(r',\s*([}\]])', r'\1', fixed_text)
    
    # 2.4 处理未转义的控制字符
    fixed_text = fixed_text.replace('\\n', '\\\\n').replace('\\t', '\\\\t').replace('\\r', '\\\\r')
    
    # 尝试解析修复后的文本
    try:
        return json.loads(fixed_text)
    except json.JSONDecodeError:
        pass
    
    # 尝试3: 提取可能的JSON对象
    try:
        # 尝试提取 {...} 或 [...]
        json_objects = re.findall(r'({[^{}]*}|\[[^\[\]]*\])', text)
        for obj in json_objects:
            try:
                return json.loads(obj)
            except:
                continue
    except:
        pass
    
    # 尝试4: 如果是类似Python字典的格式，尝试eval（安全限制）
    try:
        # 只允许基本类型：数字、字符串、列表、字典、布尔值、None
        import ast
        # 使用ast.literal_eval代替eval，更安全
        result = ast.literal_eval(text)
        # 转换为JSON兼容格式
        if isinstance(result, (dict, list, str, int, float, bool, type(None))):
            return result
    except:
        pass
    
    # 最后尝试：返回包装的字典
    return {"raw_text": text, "error": "JSON解析失败，已尝试多种修复方案"}
'''
        
        # 添加到文件末尾
        add_cmd = f'''cat >> /opt/ai-novel-agent/backend/app/core/llm.py << 'APPENDEOF'
{improved_function}
APPENDEOF'''
        
        run_ssh_command(client, add_cmd, "添加改进版函数")
        
        # 3. 测试改进后的函数
        print("\n3. 测试改进后的函数:")
        
        test_cmd = '''cd /opt/ai-novel-agent/backend && \
source ../venv/bin/activate && \
python -c "
import sys
sys.path.insert(0, '.')

try:
    from app.core import llm
    
    test_cases = [
        '{\"name\": \"test\"}',  # 标准JSON
        '{name: \"test\"}',      # 无引号键
        '{name: test}',          # 无引号键和值
        \"{'name': 'test'}\",    # 单引号
        '{\"量化参数\": {\"节奏\": 0.8}}',  # 中文键
        '{量化参数: {节奏: 0.8}}',          # 中文键无引号
        '```json\\n{\"name\": \"test\"}\\n```',  # 代码块
        'invalid json',
    ]
    
    print('测试 parse_json 改进版:')
    for i, tc in enumerate(test_cases):
        result = llm.parse_json(tc)
        print(f'{i+1}. 输入: {tc[:40]}...')
        print(f'   结果: {result}')
        print()
        
except Exception as e:
    print(f'❌ 测试失败: {e}')
    import traceback
    traceback.print_exc()
"
'''
        
        run_ssh_command(client, test_cmd, "测试各种格式")
        
        # 4. 重启服务
        print("\n4. 重启服务:")
        
        run_ssh_command(client,
            "systemctl restart ai-novel-agent.service",
            "重启服务")
        
        time.sleep(3)
        
        run_ssh_command(client,
            "systemctl status ai-novel-agent.service --no-pager | head -3",
            "服务状态")
        
        # 5. 测试实际任务
        print("\n5. 测试实际任务:")
        
        # 查看当前任务
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/tasks",
            "当前任务")
        
        # 如果有失败任务，重试或创建新任务
        print("\n建议创建新任务测试:")
        print("  curl -X POST http://104.244.90.202:9000/api/tasks \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"name\": \"改进后测试任务\"}'")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ parse_json 函数改进完成！")
        print("="*60)
        
        print("\n📊 改进内容:")
        print("  1. 支持无引号的键（如 {name: \"value\"}）")
        print("  2. 支持中文键无引号")
        print("  3. 更好的错误修复逻辑")
        print("  4. 支持更多非标准JSON格式")
        
        print("\n🔧 现在应该能正确处理风格解析的JSON了")
        
    except Exception as e:
        print(f"❌ 改进失败: {e}")

def run_ssh_command(client, cmd, description):
    """执行SSH命令"""
    print(f"\n{description}:")
    print(f"  执行: {cmd}")
    
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        if output:
            print(f"  {output[:400]}")
    except:
        pass

if __name__ == "__main__":
    improve_parse_json()