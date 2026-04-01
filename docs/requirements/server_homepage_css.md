# 104服务器主页CSS样式

## 完整的样式设计

```css
/* 主页整体样式 */
:root {
  --primary-color: #4f46e5;
  --primary-dark: #3730a3;
  --secondary-color: #10b981;
  --danger-color: #ef4444;
  --warning-color: #f59e0b;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --border-color: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.5;
  color: var(--text-primary);
  background-color: var(--bg-primary);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

/* 导航栏样式 */
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background-color: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  padding: 1rem 0;
  box-shadow: var(--shadow-sm);
}

.navbar .container {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--primary-color);
}

.nav-brand img {
  height: 2rem;
  width: auto;
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-menu a {
  text-decoration: none;
  color: var(--text-secondary);
  font-weight: 500;
  transition: color 0.2s;
}

.nav-menu a:hover {
  color: var(--primary-color);
}

.btn-primary, .btn-secondary, .btn-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-md);
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-primary {
  background-color: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background-color: var(--primary-dark);
}

.btn-secondary {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background-color: var(--border-color);
}

.btn-danger {
  background-color: var(--danger-color);
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
}

.btn-large {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

/* Hero区域样式 */
.hero {
  padding: 4rem 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.hero .container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  align-items: center;
}

.hero h1 {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1.2;
  margin-bottom: 1rem;
}

.hero .subtitle {
  font-size: 1.25rem;
  opacity: 0.9;
  margin-bottom: 2rem;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 3rem;
}

.hero-stats {
  display: flex;
  gap: 2rem;
}

.stat {
  text-align: center;
}

.stat .number {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}

.stat .label {
  font-size: 0.875rem;
  opacity: 0.8;
}

.hero-image img {
  width: 100%;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

/* 功能展示区样式 */
.features {
  padding: 4rem 0;
}

.features h2 {
  text-align: center;
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.features .subtitle {
  text-align: center;
  color: var(--text-secondary);
  font-size: 1.125rem;
  margin-bottom: 3rem;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.feature-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.feature-card p {
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 价格计算器样式 */
.pricing-calculator {
  padding: 4rem 0;
  background-color: var(--bg-secondary);
}

.calculator-container {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: var(--shadow-md);
}

.service-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 2rem;
}

.service-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.service-option.active {
  border-color: var(--primary-color);
  background-color: rgba(79, 70, 229, 0.05);
}

.service-option:hover:not(.active) {
  border-color: var(--text-secondary);
}

.service-icon {
  font-size: 1.25rem;
}

.price-info ul {
  list-style: none;
  padding-left: 0;
}

.price-info li {
  padding: 0.25rem 0;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.calculator-form {
  display: none;
}

.calculator-form.active {
  display: block;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.form-group input[type="range"] {
  width: 100%;
  margin: 0.5rem 0;
}

.form-group select,
.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
}

.price-result {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 1.5rem;
  margin-top: 2rem;
}

.price-breakdown {
  margin-bottom: 1.5rem;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color);
}

.breakdown-total {
  display: flex;
  justify-content: space-between;
  padding: 1rem 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.calculator-actions {
  display: flex;
  gap: 1rem;
}

.cart-summary {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid var(--border-color);
}

.cart-total {
  display: flex;
  justify-content: space-between;
  font-size: 1.5rem;
  font-weight: 600;
  padding: 1rem 0;
  border-top: 1px solid var(--border-color);
  margin-top: 1rem;
}

.cart-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

/* API文档区域样式 */
.api-docs {
  padding: 4rem 0;
}

.api-quick-links {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}

.api-link {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}

.api-link:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.api-link-icon {
  font-size: 2rem;
}

.api-link-content h4 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.api-link-content p {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.code-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.code-tab {
  padding: 0.5rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  cursor: pointer;
  font-size: 0.875rem;
}

.code-tab.active {
  background: var(--bg-primary);
  border-bottom-color: var(--bg-primary);
}

.code-block {
  display: none;
  background: #1e1e1e;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.code-block.active {
  display: block;
}

.code-block pre {
  margin: 0;
  padding: 1.5rem;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #d4d4d4;
}

.api-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

/* OpenClaw集成样式 */
.openclaw-integration {
  padding: 4rem 0;
  background-color: var(--bg-secondary);
}

.integration-features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.install-steps {
  margin: 2rem 0;
}

.step {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  font-weight: 600;
  flex-shrink: 0;
}

.step-content h4 {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.integration-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.plugin-code-example {
  margin-top: 3rem;
}

.plugin-download {
  margin-top: 2rem;
  padding: 2rem;
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  text-align: center;
}

.download-options {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-top: 1rem;
}

.download-options .icon {
  height: 1.25rem;
  width: auto;
  margin-right: 0.5rem;
}

/* API Key管理样式 */
.api-key-management {
  padding: 4rem 0;
}

.key-management-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.key-creation, .key-list {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
}

.key-form .form-group {
  margin-bottom: 1.5rem;
}

.permission-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.5rem;
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.quota-inputs {
  display: grid;
  gap: 0.75rem;
}

.quota-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quota-item input {
  width: 100px;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.key-display {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 2rem;
}

.key-warning {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: var(--radius-md);
  margin-bottom: 1.5rem;
}

.warning-icon {
  font-size: 1.5rem;
}

.key-field {
  margin-bottom: 1rem;
}

.key-field label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.key-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.key-value code {
  flex: 1;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  font-family: monospace;
  font-size: 0.875rem;
  overflow-x: auto;
}

.copy-btn {
  padding: 0.5rem 1rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 0.875rem;
}

.copy-btn:hover {
  background: var(--border-color);
}

.key-example {
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  padding: 1rem;
  overflow-x: auto;
}

.key-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.key-table-container {
  overflow-x: auto;
  margin: 1rem 0;
}

.key-table {
  width: 100%;
  border-collapse: collapse;
}

.key-table th {
  text-align: left;
  padding: 0.75rem 1rem;
  background: var(--bg-secondary);
  border-bottom: 2px solid var(--border-color);
  font-weight: 600;
  font-size: 0.875rem;
}

.key-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
}

.key-name-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.key-id {
  font-family: monospace;
  font-size: 0.75rem;
  background: var(--bg-secondary);
  padding: 0.25rem