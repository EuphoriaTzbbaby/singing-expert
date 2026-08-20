# 管理端实现计划

## Context

PDF 工具的多用户隔离已上线（`User.is_admin` + `PdfFile.user_id` + `Group.user_id`），但缺少管理端界面：管理员目前只能在 MySQL 里手改 `is_admin`、看不到所有用户、无法重置密码/删用户、没有系统统计。本次新增一个"顶部按钮切换"的管理端（不引入 vue-router），含 4 个 tab：用户管理 / 文件管理 / 分组管理 / 系统统计。非管理员隐藏入口，看到也调不到接口（`require_admin` 403 兜底）。

## 后端改动

### 1. `backend/auth.py` — 新增 `require_admin` 依赖

基于现有 `get_current_user`，叠加 `is_admin` 校验：

```python
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
```

> 关键：**不要给 `get_current_user` 加缓存** —— 管理员被取消后下一次请求必须立刻生效。

### 2. `backend/schemas.py` — 新增 6 个 schema

- `UserAdminOut`（id/username/is_admin/created_at/file_count/storage_bytes）
- `PdfFileAdminOut`（含 owner_username/group_name，复用进 StatsOut.recent_uploads）
- `GroupAdminOut`（含 owner_username/file_count）
- `StatsOut`（user_count/file_count/total_storage_bytes/group_count/public_file_count/recent_uploads）
- `ResetPasswordIn`（new_password min_length=6）
- `SetAdminIn`（is_admin: bool）

> 所有带 `created_at` 的 schema 复用 `_serialize_cst` + `_ensure_tz` 模式（参考 `backend/schemas.py:10`）。

### 3. `backend/main.py` — 新增 7 个路由（统一 `/api/admin/` 前缀）

| 方法 | 路径 | 安全约束 |
|---|---|---|
| GET | `/api/admin/stats` | — |
| GET | `/api/admin/users` | — |
| PATCH | `/api/admin/users/{id}/admin` | 不能改自己的 is_admin（400） |
| DELETE | `/api/admin/users/{id}` | 不能删自己；删前循环 OSS 删除该用户文件，返回 `failed_oss_keys` |
| POST | `/api/admin/users/{id}/reset-password` | 不能重置自己（用户改密走另一套流程） |
| GET | `/api/admin/files` | 支持 user_id/group_id/keyword 过滤 |
| GET | `/api/admin/groups` | — |

文件/分组**删除**直接复用 `DELETE /api/files/{id}` 和 `DELETE /api/groups/{id}`（现有 `_check_owner_or_admin` 已允许管理员操作任意记录），不新增端点。

`admin_delete_user` 的实现要点（`PdfFile.user_id` 虽然 `ondelete=CASCADE`，但 OSS 对象不会被自动删，必须 Python 侧先循环 `delete_from_oss` 再 `db.delete(user)`）：

```python
pdfs = db.query(PdfFile).filter(PdfFile.user_id == user_id).all()
failed = []
for p in pdfs:
    try: delete_from_oss(p.oss_key)
    except Exception: failed.append(p.oss_key)
db.delete(user)   # CASCADE 带走 PdfFile/Group 行
db.commit()
return {"ok": True, "id": user_id, "failed_oss_keys": failed}
```

## 前端改动

### 4. `frontend/src/api.js` — 追加 7 个 admin API 函数

```js
export function adminListUsers() { return api.get('/admin/users') }
export function adminSetAdmin(id, { is_admin }) { return api.patch(`/admin/users/${id}/admin`, { is_admin }) }
export function adminDeleteUser(id) { return api.delete(`/admin/users/${id}`).then(r => r.data) }
export function adminResetPassword(id, { new_password }) { return api.post(`/admin/users/${id}/reset-password`, { new_password }).then(r => r.data) }
export function adminListFiles(userId, groupId, keyword) { /* query params */ }
export function adminListGroups() { return api.get('/admin/groups') }
export function adminStats() { return api.get('/admin/stats') }
```

### 5. `frontend/src/App.vue` — 3 处改动

- `currentUser` 从字符串改为对象：`currentUser.value = user`（onMounted）、`onLoggedIn(user)` 接收对象
- 模板第 11 行 `{{ currentUser }}` → `{{ currentUser.username }}`
- 新增 `view` ref（`'user' | 'admin'`）；header 加按钮（`v-if="currentUser.is_admin && view === 'user'"`）→ 切到 admin；admin 视图下显示"← 返回用户端"按钮；返回时 `nextTick(refresh)` 触发 GroupSidebar+PdfList 重新 load（因为管理员可能在管理端改了数据）

### 6. `frontend/src/components/LoginView.vue`

登录成功后多调一次 `getMe()` 拿完整对象再 emit：

```js
const data = isRegister.value ? await register(u, p) : await login(u, p)
const me = await getMe()
emit('logged-in', me)   // 之前传 data.username
```

### 7. 新建 5 个前端组件

| 路径 | 作用 |
|---|---|
| `frontend/src/components/AdminView.vue` | 4 tab 容器（stats/users/files/groups） |
| `frontend/src/components/admin/StatsPanel.vue` | 5 个数字卡片 + 最近 10 条上传表 |
| `frontend/src/components/admin/UserManager.vue` | 用户表 + 3 个写操作（改管理员/重置密码/删用户） |
| `frontend/src/components/admin/FileManager.vue` | 文件表 + 查看/下载/删除（复用 `deletePdf`/`getViewUrl`/`getDownloadUrl`） |
| `frontend/src/components/admin/GroupManager.vue` | 分组表 + 删除（复用 `deleteGroup`） |

每个表组件：`load()` 初始化、操作按钮 `disabled="u.id === me.id"`（前端禁用自操作，后端 400 兜底）；删除前 `window.confirm`；失败 `window.alert(err.response.data.detail)`。

`UserManager` 的"重置密码"用 `window.prompt` 收集新密码（≥6 位），**不设固定默认密码**，避免"重置即知道所有人密码"。

## 实施顺序

1. 后端骨架：`auth.require_admin` → `schemas.py` 6 schema → `main.py` 仅 `/api/admin/stats`（最简单）→ 部署验证
2. 后端 3 个只读列表路由（users/files/groups）
3. 后端 3 个写路由（set_admin/reset_password/delete_user）
4. 前端 `App.vue` + `LoginView.vue` + `api.js` 改造（先确认入口按钮 + AdminView 空壳能切换）
5. 4 个 tab 组件，从简到难：StatsPanel → GroupManager → FileManager → UserManager
6. 联调：普通用户登录看不到入口、管理员登录 4 tab 全可用、自操作前后端双重拦截
7. commit + push 触发自动部署

## 验证清单

- [ ] 普通用户登录：header 无"管理端"按钮
- [ ] 普通用户直接 `curl /api/admin/stats` → 403
- [ ] 管理员登录：4 个 tab 切换正常
- [ ] UserManager：自己行 3 个按钮 disabled；改别人 is_admin 后下一次 `/api/auth/me` 立即生效
- [ ] UserManager：删用户后该用户的 OSS 对象也被清理（failed_oss_keys 为空）
- [ ] FileManager：删除任意文件触发 OSS + MySQL 双删
- [ ] GroupManager：删除任意分组（含他人私有 + 公共）成功
- [ ] StatsPanel：5 个数字 + 最近 10 条上传显示正确
- [ ] 从管理端返回用户端：GroupSidebar + PdfList 自动重新加载

## 关键复用位置

- `backend/auth.py:35` `get_current_user`（token 解析 + User 查询）
- `backend/auth.py:18` `hash_password`（重置密码用）
- `backend/main.py:210` `_pdf_visible_filter`（参考其管理员分支）
- `backend/main.py:299` `_check_owner_or_admin`（管理员删任意文件/分组走这里）
- `backend/storage.py` `delete_from_oss`（删用户时循环调）
- `backend/schemas.py:10` `_serialize_cst` + `_ensure_tz`（时区序列化模板）
- `frontend/src/api.js:34` 响应拦截器（401 自动登出）
- `frontend/src/api.js` `getViewUrl`/`getDownloadUrl`/`deletePdf`/`deleteGroup`（FileManager/GroupManager 复用）
