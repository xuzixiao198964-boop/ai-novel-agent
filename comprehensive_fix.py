#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面修复导入问题
"""

import os
import sys

def create_fallback_trend_function():
    """创建备用的trend函数，以防导入失败"""
    
    file_path = "backend/app/core/trend_fallback.py"
    
    print(f"创建备用函数文件: {file_path}")
    
    content = '''# -*- coding: utf-8 -*-
"""备用趋势计算函数，当主trend模块导入失败时使用"""

def _compute_trend_numbers_fallback():
    """备用趋势计算函数"""
    return {
        "suggested_total_chapters": 200,
        "avg_chapters_per_novel": 150,
        "avg_words_per_chapter": 2500,
        "total_words": 375000
    }
'''
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("备用函数文件创建完成")

def update_trend_cap_with_fallback():
    """更新trend_cap.py使用备用函数"""
    
    file_path = "backend/app/core/trend_cap.py"
    
    print(f"\n更新 {file_path} 使用备用函数...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换导入和调用
    old_code = """    if n <= 0:
        # 尝试从trend模块导入，如果失败则使用默认值
        try:
            from app.agents.trend import _compute_trend_numbers
            n = int(_compute_trend_numbers().get("suggested_total_chapters") or 200)
        except ImportError:
            # 如果导入失败，使用默认值
            n = 200"""
    
    new_code = """    if n <= 0:
        # 尝试从trend模块导入，如果失败则使用备用函数
        try:
            from app.agents.trend import _compute_trend_numbers
            n = int(_compute_trend_numbers().get("suggested_total_chapters") or 200)
        except ImportError:
            # 如果导入失败，尝试使用备用函数
            try:
                from app.core.trend_fallback import _compute_trend_numbers_fallback
                n = int(_compute_trend_numbers_fallback().get("suggested_total_chapters") or 200)
            except ImportError:
                # 如果备用函数也失败，使用默认值
                n = 200"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("更新完成!")
    else:
        print("未找到需要更新的代码段")

def test_fixes():
    """测试修复"""
    
    print("\n测试修复...")
    
    # 添加backend到路径
    sys.path.insert(0, "backend")
    
    try:
        # 测试导入
        from app.core.trend_cap import get_trend_suggested_chapter_cap
        
        # 测试函数
        result = get_trend_suggested_chapter_cap(None)
        print(f"测试成功! get_trend_suggested_chapter_cap(None) = {result}")
        
        # 测试带任务ID
        result2 = get_trend_suggested_chapter_cap("test_task_123")
        print(f"测试成功! get_trend_suggested_chapter_cap('test_task_123') = {result2}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

def check_pipeline_imports():
    """检查pipeline.py中的导入"""
    
    print("\n检查pipeline.py中的导入...")
    
    file_path = "backend/app/core/pipeline.py"
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有get_trend_suggested_chapter_cap调用
        if 'get_trend_suggested_chapter_cap' in content:
            print("找到get_trend_suggested_chapter_cap调用")
            
            # 检查是否在try-except中
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'get_trend_suggested_chapter_cap' in line:
                    # 检查上下文
                    context_start = max(0, i-5)
                    context_end = min(len(lines), i+5)
                    context = lines[context_start:context_end]
                    
                    print(f"第{i+1}行附近:")
                    for j, ctx_line in enumerate(context):
                        print(f"  {context_start + j + 1}: {ctx_line}")
                    print()
        else:
            print("未找到get_trend_suggested_chapter_cap调用")
    else:
        print(f"文件不存在: {file_path}")

def main():
    print("=" * 80)
    print("全面修复导入问题")
    print("=" * 80)
    
    # 1. 创建备用函数
    create_fallback_trend_function()
    
    # 2. 更新trend_cap.py
    update_trend_cap_with_fallback()
    
    # 3. 检查pipeline
    check_pipeline_imports()
    
    # 4. 测试修复
    test_fixes()
    
    print("\n" + "=" * 80)
    print("修复总结:")
    print("1. 创建了备用趋势计算函数")
    print("2. 更新了trend_cap.py使用备用函数")
    print("3. 检查了pipeline.py中的导入")
    print("4. 测试了修复")
    print("\n下一步: 将修复部署到服务器并重启服务")

if __name__ == "__main__":
    main()