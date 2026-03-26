#!/bin/bash
# 在服务器上设置 DeepSeek API 测试环境

echo "设置 DeepSeek API 测试环境"
echo "=========================="

# 备份当前配置
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 创建新的 .env 配置
cat > .env << 'EOF'
# DeepSeek API 配置
MOCK_LLM=0
LLM_PROVIDER=openai_compatible
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=你的DeepSeek_API_Key_在这里
LLM_MODEL=deepseek-chat

# 限速配置
AGENT_INTERVAL_SECONDS=1.0
STEP_INTERVAL_SECONDS=0.2

# 小说规模配置
TOTAL_CHAPTERS=0
MAX_CHAPTERS_TO_WRITE=0
WORDS_PER_CHAPTER=10000

# 审核重试配置（已修复）
AUDIT_REWRITE_MAX=6
CHAPTER_SCORE_REWRITE_MAX=6
EOF

echo ".env 配置已更新"
echo ""
echo "请执行以下步骤："
echo "1. 编辑 .env 文件，将 '你的DeepSeek_API_Key_在这里' 替换为真实的 API Key"
echo "2. 重启服务器：pkill -f uvicorn && uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload"
echo "3. 运行测试：python test_deepseek_18ch.py"
echo ""
echo "当前配置摘要："
echo "- Mock 模式: 关闭 (使用真实 API)"
echo "- API: DeepSeek"
echo "- 审核重试: 6次"
echo "- 测试章节: 18章"