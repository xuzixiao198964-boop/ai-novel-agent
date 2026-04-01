# 104服务器主页设计文档（续）

## 6. API Key管理系统（续）

### 6.2 API Key管理界面
```html
          </tbody>
        </table>
      </div>
      
      <div class="key-actions-bar">
        <button class="btn-secondary" onclick="refreshKeyList()">刷新列表</button>
        <button class="btn-danger" onclick="revokeSelectedKeys()">撤销选中</button>
        <button class="btn-primary" onclick="exportKeys()">导出列表</button>
      </div>
      
      <div class="key-stats">
        <h4>使用统计</h4>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value" id="total-keys">0</div>
            <div class="stat-label">总密钥数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="active-keys">0</div>
            <div class="stat-label">活跃密钥</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="today-calls">0</div>
            <div class="stat-label">今日调用</div>
          </div>
          <div class="stat-card">
            <div class="stat-value" id="month-cost">¥0.00</div>
            <div class="stat-label">本月费用</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <div class="key-security">
    <h3>安全建议</h3>
    <div class="security-tips">
      <div class="tip">
        <div class="tip-icon">🔒</div>
        <div class="tip-content">
          <h4>保护您的API Key</h4>
          <ul>
            <li>不要将API Key提交到版本控制系统（如Git）</li>
            <li>不要在客户端代码中硬编码API Key</li>
            <li>定期轮换API Key，建议每90天更换一次</li>
            <li>为不同环境使用不同的API Key</li>
          </ul>
        </div>
      </div>
      
      <div class="tip">
        <div class="tip-icon">📊</div>
        <div class="tip-content">
          <h4>监控使用情况</h4>
          <ul>
            <li>设置使用限额，防止意外超额使用</li>
            <li>启用使用通知，及时了解异常情况</li>
            <li>定期查看使用日志，发现异常调用</li>
            <li>使用IP限制，增强安全性</li>
          </ul>
        </div>
      </div>
      
      <div class="tip">
        <div class="tip-icon">🚨</div>
        <div class="tip-content">
          <h4>应急处理</h4>
          <ul>
            <li>如果怀疑API Key泄露，立即撤销并创建新密钥</li>
            <li>启用双因素认证增强账户安全</li>
            <li>定期检查账户活动日志</li>
            <li>设置异常活动告警</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</section>
```

### 6.3 API Key管理JavaScript逻辑
```javascript
// API Key管理逻辑
class ApiKeyManager {
  constructor() {
    this.baseUrl = 'http://104.244.90.202:9000';
    this.userToken = localStorage.getItem('user_token');
  }
  
  async createApiKey