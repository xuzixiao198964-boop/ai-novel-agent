# API Key管理JavaScript实现

## 完整的API Key管理逻辑

```javascript
// api-key-manager.js
class ApiKeyManager {
  constructor() {
    this.baseUrl = 'http://104.244.90.202:9000';
    this.userToken = localStorage.getItem('user_token');
    this.init();
  }
  
  init() {
    // 加载API Keys列表
    this.loadApiKeys();
    
    // 绑定事件
    this.bindEvents();
    
    // 加载统计数据
    this.loadStats();
  }
  
  bindEvents() {
    // 创建API Key表单提交
    document.getElementById('create-key-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.createApiKey();
    });
    
    // 刷新按钮
    document.getElementById('refresh-keys').addEventListener('click', () => {
      this.loadApiKeys();
    });
    
    // 撤销选中按钮
    document.getElementById('revoke-selected').addEventListener('click', () => {
      this.revokeSelectedKeys();
    });
    
    // 导出按钮
    document.getElementById('export-keys').addEventListener('click', () => {
      this.exportKeys();
    });
  }
  
  async createApiKey() {
    const formData = {
      name: document.getElementById('key-name').value,
      permissions: Array.from(document.querySelectorAll('input[name="permissions"]:checked'))
        .map(cb => cb.value),
      ip_restriction: document.getElementById('ip-restriction').value || null,
      quotas: {
        daily: document.getElementById('daily-limit').value || null,
        monthly: document.getElementById('monthly-limit').value || null,
        cost: document.getElementById('cost-limit').value || null
      },
      expires_in: parseInt(document.getElementById('expiry-days').value)
    };
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        throw new Error(`创建失败: ${response.statusText}`);
      }
      
      const result = await response.json();
      this.showApiKey(result);
      
      // 刷新列表
      this.loadApiKeys();
      this.loadStats();
      
    } catch (error) {
      this.showError(`创建API Key失败: ${error.message}`);
    }
  }
  
  showApiKey(keyData) {
    // 显示创建的API Key
    document.getElementById('api-key-value').textContent = keyData.key;
    document.getElementById('key-id').textContent = keyData.id;
    document.getElementById('key-created').textContent = new Date(keyData.created_at).toLocaleString();
    document.getElementById('key-expires').textContent = keyData.expires_at 
      ? new Date(keyData.expires_at).toLocaleString()
      : '永不过期';
    
    // 生成使用示例
    const exampleCode = `curl -X GET "${this.baseUrl}/api/v1/user/balance" \\
  -H "Authorization: Bearer ${keyData.key}"`;
    document.getElementById('key-example-code').textContent = exampleCode;
    
    // 显示密钥区域
    document.getElementById('key-display-area').style.display = 'block';
    document.getElementById('key-creation').style.display = 'none';
    
    // 滚动到显示区域
    document.getElementById('key-display-area').scrollIntoView({ behavior: 'smooth' });
  }
  
  async loadApiKeys() {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys`, {
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`加载失败: ${response.statusText}`);
      }
      
      const keys = await response.json();
      this.renderApiKeys(keys);
      
    } catch (error) {
      this.showError(`加载API Keys失败: ${error.message}`);
    }
  }
  
  renderApiKeys(keys) {
    const tbody = document.getElementById('api-keys-list');
    tbody.innerHTML = '';
    
    if (keys.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state">
            <div class="empty-icon">🔑</div>
            <div class="empty-text">暂无API Keys，请创建一个</div>
          </td>
        </tr>
      `;
      return;
    }
    
    keys.forEach(key => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>
          <div class="key-name-cell">
            <input type="checkbox" class="key-select" value="${key.id}">
            <span class="key-name">${key.name}</span>
          </div>
        </td>
        <td><code class="key-id">${key.id}</code></td>
        <td>${new Date(key.created_at).toLocaleDateString()}</td>
        <td>${key.expires_at ? new Date(key.expires_at).toLocaleDateString() : '永不过期'}</td>
        <td>
          <div class="usage-cell">
            <span class="usage-count">${key.usage_count || 0}次</span>
            <span class="usage-cost">¥${(key.total_cost || 0).toFixed(2)}</span>
          </div>
        </td>
        <td>
          <span class="status-badge ${key.status}">${this.getStatusText(key.status)}</span>
        </td>
        <td>
          <div class="key-actions-cell">
            <button class="btn-icon" onclick="apiKeyManager.viewKey('${key.id}')" title="查看详情">
              👁️
            </button>
            <button class="btn-icon" onclick="apiKeyManager.regenerateKey('${key.id}')" title="重新生成">
              🔄
            </button>
            <button class="btn-icon btn-danger" onclick="apiKeyManager.revokeKey('${key.id}')" title="撤销">
              🗑️
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(row);
    });
  }
  
  getStatusText(status) {
    const statusMap = {
      'active': '活跃',
      'expired': '已过期',
      'revoked': '已撤销',
      'limited': '受限制'
    };
    return statusMap[status] || status;
  }
  
  async loadStats() {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/stats`, {
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`加载统计失败: ${response.statusText}`);
      }
      
      const stats = await response.json();
      this.renderStats(stats);
      
    } catch (error) {
      console.error('加载统计失败:', error);
    }
  }
  
  renderStats(stats) {
    document.getElementById('total-keys').textContent = stats.total_keys || 0;
    document.getElementById('active-keys').textContent = stats.active_keys || 0;
    document.getElementById('today-calls').textContent = stats.today_calls || 0;
    document.getElementById('month-cost').textContent = `¥${(stats.month_cost || 0).toFixed(2)}`;
  }
  
  async viewKey(keyId) {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/${keyId}`, {
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`查看失败: ${response.statusText}`);
      }
      
      const keyData = await response.json();
      this.showKeyDetail(keyData);
      
    } catch (error) {
      this.showError(`查看API Key失败: ${error.message}`);
    }
  }
  
  showKeyDetail(keyData) {
    // 创建模态框显示详细信息
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>API Key详情</h3>
          <button class="modal-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="modal-body">
          <div class="key-detail">
            <div class="detail-field">
              <label>名称</label>
              <div>${keyData.name}</div>
            </div>
            <div class="detail-field">
              <label>密钥ID</label>
              <div><code>${keyData.id}</code></div>
            </div>
            <div class="detail-field">
              <label>创建时间</label>
              <div>${new Date(keyData.created_at).toLocaleString()}</div>
            </div>
            <div class="detail-field">
              <label>过期时间</label>
              <div>${keyData.expires_at ? new Date(keyData.expires_at).toLocaleString() : '永不过期'}</div>
            </div>
            <div class="detail-field">
              <label>权限</label>
              <div class="permissions-list">
                ${keyData.permissions.map(p => `<span class="permission-tag">${p}</span>`).join('')}
              </div>
            </div>
            <div class="detail-field">
              <label>IP限制</label>
              <div>${keyData.ip_restriction || '无限制'}</div>
            </div>
            <div class="detail-field">
              <label>使用统计</label>
              <div class="usage-stats">
                <div>总调用: ${keyData.usage_count || 0}次</div>
                <div>总费用: ¥${(keyData.total_cost || 0).toFixed(2)}</div>
                <div>最后使用: ${keyData.last_used ? new Date(keyData.last_used).toLocaleString() : '从未使用'}</div>
              </div>
            </div>
            <div class="detail-field">
              <label>使用限额</label>
              <div class="quota-stats">
                <div>每日: ${keyData.quotas?.daily || '无限制'}</div>
                <div>每月: ${keyData.quotas?.monthly || '无限制'}</div>
                <div>费用: ${keyData.quotas?.cost ? `¥${keyData.quotas.cost}` : '无限制'}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" onclick="apiKeyManager.regenerateKey('${keyData.id}')">重新生成</button>
          <button class="btn-danger" onclick="apiKeyManager.revokeKey('${keyData.id}')">撤销密钥</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
  }
  
  async regenerateKey(keyId) {
    if (!confirm('确定要重新生成此API Key吗？旧的密钥将立即失效。')) {
      return;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/${keyId}/regenerate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`重新生成失败: ${response.statusText}`);
      }
      
      const newKey = await response.json();
      this.showApiKey(newKey);
      this.loadApiKeys();
      
    } catch (error) {
      this.showError(`重新生成API Key失败: ${error.message}`);
    }
  }
  
  async revokeKey(keyId) {
    if (!confirm('确定要撤销此API Key吗？撤销后将无法恢复。')) {
      return;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/${keyId}/revoke`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`撤销失败: ${response.statusText}`);
      }
      
      this.showSuccess('API Key已成功撤销');
      this.loadApiKeys();
      this.loadStats();
      
    } catch (error) {
      this.showError(`撤销API Key失败: ${error.message}`);
    }
  }
  
  async revokeSelectedKeys() {
    const selected = Array.from(document.querySelectorAll('.key-select:checked'))
      .map(cb => cb.value);
    
    if (selected.length === 0) {
      this.showError('请先选择要撤销的API Keys');
      return;
    }
    
    if (!confirm(`确定要撤销选中的 ${selected.length} 个API Keys吗？`)) {
      return;
    }
    
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/batch-revoke`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ key_ids: selected })
      });
      
      if (!response.ok) {
        throw new Error(`批量撤销失败: ${response.statusText}`);
      }
      
      this.showSuccess(`成功撤销 ${selected.length} 个API Keys`);
      this.loadApiKeys();
      this.loadStats();
      
    } catch (error) {
      this.showError(`批量撤销失败: ${error.message}`);
    }
  }
  
  async exportKeys() {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/apikeys/export`, {
        headers: {
          'Authorization': `Bearer ${this.userToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`导出失败: ${response.statusText}`);
      }
      
      const data = await response.json();
      this.downloadJson(data, `api-keys-${new Date().toISOString().split('T')[0]}.json`);
      
    } catch (error) {
      this.showError(`导出API Keys失败: ${error.message}`);
    }
  }
  
  downloadJson(data, filename) {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  
  copyApiKey() {
    const keyElement = document.getElementById('api-key-value');
    const keyText = keyElement.textContent;
    
    navigator.clipboard.writeText(keyText).then(() => {
      this.showSuccess('API Key已复制到剪贴板');
    }).catch(err => {
      this.showError('复制失败，请手动复制');
    });
  }
  
  downloadKeyFile() {
    const keyData = {
      api_key: document.getElementById('api-key-value').textContent,
      key_id: document.getElementById('key-id').textContent,
      created_at: document.getElementById('key-created').textContent,
      expires_at: document.getElementById('key-expires').textContent,
      base_url: this.baseUrl
    };
    
    const content = `# AI Novel Media Agent API Key
# 请妥善保存此文件，不要分享给他人

API_KEY=${keyData.api_key}
KEY_ID=${keyData.key_id}
BASE_URL=${keyData.base_url}
CREATED_AT=${keyData.created_at}
EXPIRES_AT=${keyData.expires_at}

# 使用示例
# curl -X GET "\${BASE_URL}/api/v1/user/balance" \\
#   -H "Authorization: Bearer \${API_KEY}"

# Python示例
# import requests
# headers = {"Authorization": f"Bearer {API_KEY}"}
# response = requests.get(f"{BASE_URL}/api/v1/user/balance", headers=headers)`;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `api-key-${keyData.key_id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  
  showSuccess(message) {
    this.showNotification(message, 'success');
  }
  
  showError(message) {
    this.showNotification(message, 'error');
  }
  
  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
      <div class="notification-content">${message}</div>
      <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // 3秒后自动消失
    setTimeout(() => {
      if (notification.parentElement) {
        notification.remove();
      }
    }, 3000);
  }
}

// 初始化API Key管理器
const apiKeyManager = new ApiKeyManager();

// 全局函数供HTML调用
function copyApiKey() {
  apiKeyManager.copyApiKey();
}

function downloadKeyFile() {
  apiKeyManager.downloadKeyFile();
}

function closeKeyDisplay() {
  document.getElementById('key-display-area').style.display = 'none';
  document.getElementById('key-creation').style.display = 'block';
  document.getElementById('create-key-form').reset();
}

function printKey() {
  const printContent = document.getElementById('key-display-area').innerHTML;
  const originalContent = document.body.innerHTML;
  
  document.body.innerHTML = `
    <div class="print-container">
      <h1>API Key凭证</h1>
      <div class="print-warning">
        <strong>重要：