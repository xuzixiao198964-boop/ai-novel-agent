# PowerShell脚本部署修复到服务器

$Server = "10.66.66.3"
$User = "root"
$Password = $env:DEPLOY_SSH_PASSWORD
if (-not $Password) { Write-Error "请先设置环境变量 DEPLOY_SSH_PASSWORD"; exit 1 }
$RemoteDir = "/opt/ai-novel-agent"
$LocalDir = "E:\work\ai-novel-agent"

Write-Host "部署修复到服务器 $Server..." -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan

# 1. 创建SSH会话
Write-Host "1. 创建SSH会话..." -ForegroundColor Yellow

$Session = $null
try {
    # 使用Plink（PuTTY的命令行工具）
    $PlinkPath = "C:\Program Files\PuTTY\plink.exe"
    if (-not (Test-Path $PlinkPath)) {
        Write-Host "错误: 未找到plink.exe，请安装PuTTY" -ForegroundColor Red
        exit 1
    }
    
    # 测试连接
    Write-Host "测试SSH连接..." -ForegroundColor Yellow
    $TestResult = & $PlinkPath -ssh "$User@$Server" -pw $Password -batch "echo '连接测试成功'"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "SSH连接测试失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "SSH连接测试成功" -ForegroundColor Green
    
} catch {
    Write-Host "SSH连接错误: $_" -ForegroundColor Red
    exit 1
}

# 2. 备份服务器文件
Write-Host "2. 备份服务器文件..." -ForegroundColor Yellow

$BackupCommand = @"
cd $RemoteDir
BACKUP_DIR="backup-\$(date +%Y%m%d_%H%M%S)"
mkdir -p \$BACKUP_DIR
cp -r backend/app/agents \$BACKUP_DIR/
cp backend/app/core/pipeline.py \$BACKUP_DIR/
cp backend/app/core/pipeline_fixed.py \$BACKUP_DIR/
echo "备份完成到: \$BACKUP_DIR"
ls -la \$BACKUP_DIR/
"@

Write-Host "执行备份命令..." -ForegroundColor Gray
& $PlinkPath -ssh "$User@$Server" -pw $Password -batch $BackupCommand

# 3. 部署修复文件
Write-Host "3. 部署修复文件..." -ForegroundColor Yellow

# 使用PSCP（PuTTY的SCP工具）
$PscpPath = "C:\Program Files\PuTTY\pscp.exe"
if (-not (Test-Path $PscpPath)) {
    Write-Host "错误: 未找到pscp.exe，请安装PuTTY" -ForegroundColor Red
    exit 1
}

$FilesToDeploy = @(
    "backend\app\agents\trend.py",
    "backend\app\agents\style.py", 
    "backend\app\agents\planner.py",
    "backend\app\agents\reviser.py",
    "backend\app\agents\scorer.py",
    "backend\app\agents\__init__.py"
)

foreach ($File in $FilesToDeploy) {
    $LocalFile = Join-Path $LocalDir $File
    $RemoteFile = "$RemoteDir/$File".Replace("\", "/")
    
    if (Test-Path $LocalFile) {
        Write-Host "部署 $File..." -ForegroundColor Gray
        & $PscpPath -pw $Password "$LocalFile" "$User@$Server:$RemoteFile"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ 部署成功" -ForegroundColor Green
        } else {
            Write-Host "  ✗ 部署失败" -ForegroundColor Red
        }
    } else {
        Write-Host "文件不存在: $LocalFile" -ForegroundColor Red
    }
}

# 4. 测试修复
Write-Host "4. 测试修复..." -ForegroundColor Yellow

$TestCommand = @"
cd $RemoteDir
cat > test_agents_fix.py << 'EOF'
import sys
sys.path.insert(0, 'backend/app')

try:
    from agents.trend import TrendAgent
    from agents.style import StyleAgent
    from agents.planner import PlannerAgent
    from agents.reviser import ReviserAgent
    from agents.scorer import ScorerAgent
    
    print("测试Agent初始化修复...")
    
    test_task_id = "test_task_123"
    
    agents = [
        ("TrendAgent", TrendAgent(test_task_id)),
        ("StyleAgent", StyleAgent(test_task_id)),
        ("PlannerAgent", PlannerAgent(test_task_id)),
        ("ReviserAgent", ReviserAgent(test_task_id)),
        ("ScorerAgent", ScorerAgent(test_task_id)),
    ]
    
    success = True
    for name, agent in agents:
        if hasattr(agent, 'task_id') and agent.task_id == test_task_id:
            print(f"{name}: ✓ 初始化成功")
        else:
            print(f"{name}: ✗ 初始化失败")
            success = False
    
    if success:
        print("所有Agent初始化测试通过!")
    else:
        print("部分Agent初始化失败")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
EOF

python3 test_agents_fix.py
"@

Write-Host "执行测试命令..." -ForegroundColor Gray
& $PlinkPath -ssh "$User@$Server" -pw $Password -batch $TestCommand

# 5. 重启服务
Write-Host "5. 重启服务..." -ForegroundColor Yellow

$RestartCommand = @"
systemctl restart ai-novel-agent
sleep 3
echo "服务状态:"
systemctl status ai-novel-agent --no-pager | head -10
"@

Write-Host "重启服务..." -ForegroundColor Gray
& $PlinkPath -ssh "$User@$Server" -pw $Password -batch $RestartCommand

# 6. 测试API
Write-Host "6. 测试API..." -ForegroundColor Yellow

$ApiTestCommand = @"
cd $RemoteDir
cat > test_api_simple.py << 'EOF'
import requests
import json

server = "http://localhost:9000"

print("简单API测试...")

# 健康检查
try:
    resp = requests.get(f"{server}/api/health", timeout=5)
    print(f"健康检查: {resp.status_code}")
    if resp.status_code == 200:
        print("  ✓ 服务健康")
    else:
        print(f"  ✗ 服务异常: {resp.text}")
except Exception as e:
    print(f"健康检查失败: {e}")

# 创建任务
try:
    resp = requests.post(
        f"{server}/api/tasks",
        json={"name": "修复测试任务"},
        timeout=10
    )
    print(f"创建任务: {resp.status_code}")
    if resp.status_code == 200:
        task_data = resp.json()
        task_id = task_data.get("task_id")
        print(f"  ✓ 创建成功, 任务ID: {task_id}")
        
        # 启动任务
        start_resp = requests.post(
            f"{server}/api/tasks/{task_id}/start",
            timeout=10
        )
        print(f"启动任务: {start_resp.status_code}")
        if start_resp.status_code == 200:
            print(f"  ✓ 启动成功: {start_resp.text}")
        else:
            print(f"  ✗ 启动失败: {start_resp.text}")
    else:
        print(f"  ✗ 创建失败: {resp.text}")
        
except Exception as e:
    print(f"API测试异常: {e}")
EOF

python3 test_api_simple.py
"@

Write-Host "执行API测试..." -ForegroundColor Gray
& $PlinkPath -ssh "$User@$Server" -pw $Password -batch $ApiTestCommand

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "部署完成!" -ForegroundColor Green
Write-Host ""
Write-Host "请在前端测试'创建并启动'按钮，检查任务是否正常创建和运行。" -ForegroundColor Yellow
Write-Host "如果仍有问题，请检查服务日志: journalctl -u ai-novel-agent --no-pager -n 50" -ForegroundColor Yellow