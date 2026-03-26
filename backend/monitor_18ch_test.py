#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控18章测试任务
实时监控创作过程，发现问题立即修复
"""

import os
import sys
import time
import json
import requests
import threading
import subprocess
from pathlib import Path
from datetime import datetime

class TestMonitor:
    def __init__(self, base_url="http://127.0.0.1:9000"):
        self.base_url = base_url
        self.task_id = None
        self.errors = []
        self.fixes_applied = []
        
    def start_server(self):
        """启动后端服务"""
        print("启动后端服务...")
        # 这里我们假设服务已经在运行
        # 实际部署中可能需要启动 uvicorn
        return True
    
    def create_test_task(self):
        """创建测试任务"""
        print("创建测试任务...")
        try:
            response = requests.post(
                f"{self.base_url}/api/tasks",
                json={"name": "18章智能审核测试"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.task_id = data.get("task_id")
                print(f"任务创建成功: {self.task_id}")
                return True
            else:
                print(f"创建任务失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"连接服务器失败: {e}")
            return False
    
    def set_test_mode(self):
        """设置为测试模式，目标18章"""
        print("设置为测试模式，目标18章...")
        try:
            response = requests.post(
                f"{self.base_url}/api/run-mode",
                json={"run_mode": "test", "test_chapters": 18},
                timeout=10
            )
            if response.status_code == 200:
                print("测试模式设置成功")
                return True
            else:
                print(f"设置测试模式失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"设置测试模式失败: {e}")
            return False
    
    def start_pipeline(self):
        """启动流水线"""
        print("启动创作流水线...")
        try:
            response = requests.post(
                f"{self.base_url}/api/tasks/{self.task_id}/start",
                timeout=10
            )
            if response.status_code == 200:
                print("流水线启动成功")
                return True
            else:
                print(f"启动流水线失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"启动流水线失败: {e}")
            return False
    
    def get_task_status(self):
        """获取任务状态"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tasks/{self.task_id}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def get_agent_status(self, agent_name):
        """获取Agent状态"""
        try:
            response = requests.get(
                f"{self.base_url}/api/tasks/{self.task_id}/agents/{agent_name}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def monitor_progress(self):
        """监控进度"""
        print("\n开始监控创作进度...")
        print("=" * 60)
        
        last_progress = {}
        start_time = time.time()
        
        while True:
            try:
                status = self.get_task_status()
                if not status:
                    time.sleep(5)
                    continue
                
                # 显示基本信息
                current_time = datetime.now().strftime("%H:%M:%S")
                task_status = status.get("status", "unknown")
                elapsed = int(time.time() - start_time)
                
                print(f"\n[{current_time}] 运行时间: {elapsed}s | 任务状态: {task_status}")
                
                # 检查各个Agent状态
                agents = ["TrendAgent", "StyleAgent", "PlannerAgent", "WriterAgent", 
                         "PolishAgent", "AuditorAgent", "ReviserAgent", "ScorerAgent"]
                
                for agent in agents:
                    agent_status = self.get_agent_status(agent)
                    if agent_status:
                        progress = agent_status.get("progress_percent", 0)
                        message = agent_status.get("message", "")
                        agent_state = agent_status.get("status", "")
                        
                        if agent in last_progress and last_progress[agent] != progress:
                            print(f"  {agent}: {progress}% - {message}")
                        last_progress[agent] = progress
                
                # 检查是否完成或失败
                if task_status in ["completed", "failed"]:
                    print(f"\n任务{task_status}!")
                    if task_status == "completed":
                        print("✅ 18章测试任务成功完成!")
                    else:
                        print("❌ 任务失败，需要检查问题")
                    break
                
                # 检查是否有错误
                self.check_for_errors(status)
                
                time.sleep(10)  # 每10秒检查一次
                
            except KeyboardInterrupt:
                print("\n监控被用户中断")
                break
            except Exception as e:
                print(f"监控出错: {e}")
                time.sleep(10)
    
    def check_for_errors(self, status):
        """检查错误并尝试修复"""
        # 这里可以添加自动错误检测和修复逻辑
        pass
    
    def apply_fix(self, fix_name, description):
        """记录修复"""
        self.fixes_applied.append({
            "time": datetime.now().isoformat(),
            "fix": fix_name,
            "description": description
        })
        print(f"🔧 应用修复: {fix_name} - {description}")
    
    def generate_report(self):
        """生成监控报告"""
        print("\n" + "=" * 60)
        print("监控报告")
        print("=" * 60)
        
        if self.errors:
            print(f"发现错误: {len(self.errors)}个")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.fixes_applied:
            print(f"应用修复: {len(self.fixes_applied)}个")
            for fix in self.fixes_applied:
                print(f"  - {fix['fix']}: {fix['description']}")
        
        # 检查最终结果
        status = self.get_task_status()
        if status and status.get("status") == "completed":
            print("\n✅ 测试成功完成!")
            print(f"任务ID: {self.task_id}")
            
            # 检查生成的章节
            task_dir = Path("data") / "tasks" / self.task_id
            if task_dir.exists():
                chapters_dir = task_dir / "output" / "final"
                if chapters_dir.exists():
                    chapters = list(chapters_dir.glob("ch_*.md"))
                    print(f"生成章节数: {len(chapters)}")
                    
                    # 检查审核日志
                    audit_log = task_dir / "output" / "audit" / "audit_log.md"
                    if audit_log.exists():
                        print("审核日志已生成")
        else:
            print("\n❌ 测试未完成")
    
    def run(self):
        """运行完整监控流程"""
        print("=" * 60)
        print("18章智能审核测试监控")
        print("=" * 60)
        
        steps = [
            ("启动服务", self.start_server),
            ("创建任务", self.create_test_task),
            ("设置测试模式", self.set_test_mode),
            ("启动流水线", self.start_pipeline),
            ("监控进度", self.monitor_progress),
        ]
        
        for step_name, step_func in steps:
            print(f"\n步骤: {step_name}")
            if not step_func():
                print(f"❌ {step_name}失败")
                return False
        
        self.generate_report()
        return True

def check_server_running():
    """检查服务器是否在运行"""
    try:
        response = requests.get("http://127.0.0.1:9000/api/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_server_in_background():
    """在后台启动服务器"""
    print("启动后端服务器...")
    # 使用subprocess启动uvicorn
    cmd = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--reload"]
    process = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    print("等待服务器启动...")
    for _ in range(30):  # 最多等待30秒
        if check_server_running():
            print("服务器启动成功")
            return process
        time.sleep(1)
    
    print("服务器启动超时")
    process.terminate()
    return None

if __name__ == "__main__":
    # 检查服务器是否在运行
    if not check_server_running():
        print("服务器未运行，尝试启动...")
        server_process = start_server_in_background()
        if not server_process:
            print("无法启动服务器，请手动启动:")
            print("cd E:\\work\\ai-novel-agent\\backend")
            print("uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload")
            sys.exit(1)
    
    # 运行监控
    monitor = TestMonitor()
    success = monitor.run()
    
    sys.exit(0 if success else 1)