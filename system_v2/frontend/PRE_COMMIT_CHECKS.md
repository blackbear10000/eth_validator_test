# 提交前检查清单

为了避免在构建时出现 TypeScript 和 ESLint 错误，建议在提交代码前执行以下检查：

## 1. 运行 TypeScript 类型检查

```bash
npm run type-check
```

或者直接运行：

```bash
npx tsc --noEmit
```

这会检查所有 TypeScript 类型错误，包括：
- 未使用的变量和导入
- 类型不匹配
- 未定义的变量

## 2. 运行 ESLint 检查

```bash
npm run lint
```

这会检查代码风格和潜在问题，包括：
- 未使用的变量
- React Hooks 规则
- 代码风格问题

## 3. 本地构建测试

在提交前，建议在本地运行构建命令，确保 Docker 构建也能成功：

```bash
npm run build
```

这会执行：
- TypeScript 类型检查 (`tsc`)
- Vite 构建 (`vite build`)

## 4. 常见问题预防

### 未使用的导入和变量

**问题**：导入或声明了变量但未使用

**预防**：
- 使用 IDE 的自动清理功能（如 VS Code 的 "Organize Imports"）
- 定期运行 `npm run lint` 检查
- 使用下划线前缀标记故意未使用的变量：`const _unused = ...`

### 未定义的变量

**问题**：使用了未声明的变量或函数

**预防**：
- 使用 TypeScript 严格模式
- 在重构时，确保移除所有相关代码（包括状态、函数、导入等）
- 使用 IDE 的"查找引用"功能，确保所有引用都已更新

### API 响应处理

**问题**：`apiClient` 的响应拦截器已经返回 `response.data`，但代码中又访问了 `.data`

**预防**：
- 统一 API 响应处理方式
- 在 `api/client.ts` 中查看响应拦截器的实现
- 使用类型断言和可选链：`response as any` 或 `response?.data || response`

## 5. Git Hooks（可选）

可以设置 Git pre-commit hook 自动运行检查：

```bash
# 在 .git/hooks/pre-commit 中添加：
#!/bin/sh
cd system_v2/frontend
npm run type-check && npm run lint
```

## 6. CI/CD 集成

在 CI/CD 流程中，确保构建步骤包含：

```yaml
- name: Type Check
  run: cd system_v2/frontend && npm run type-check

- name: Lint
  run: cd system_v2/frontend && npm run lint

- name: Build
  run: cd system_v2/frontend && npm run build
```

## 快速检查命令

一键运行所有检查：

```bash
cd system_v2/frontend && npm run type-check && npm run lint && npm run build
```

