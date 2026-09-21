# mobile · 安卓 App

把 `frontend/` 那套网页包成一个安卓 App 自己用。

- **保留的功能**：登录 / 注册、账号设置、词汇记忆（翻卡 · 拼写 · 听写 · AI 助记）、学习统计、管理后台（系统统计 · 用户管理）
- **去掉的功能**：整个 PDF 模块（资料库、上传、分组、预览、下载）
- **离线**：不做，全程实时联网

> `frontend/` 和 `backend/` 一个字都没改。这里是从 `frontend/` **复制出来的一份副本**，之后所有改动都只发生在 `mobile/` 里面。

---

## 目录结构

```
mobile/
├── web/                    # 前端副本（从 frontend/ 复制后改的），真正的界面代码在这
│   ├── src/
│   │   ├── App.vue         # 改成手机壳：底部标签栏 + 默认进词汇页
│   │   ├── api.js          # 接口地址改成绝对地址；删掉 PDF/分组相关接口
│   │   ├── main.js         # 最后引入 mobile.css，保证覆盖样式生效
│   │   ├── mobile.css      # 手机端尺寸、安全区、触控目标等
│   │   └── components/     # 只留 LoginView / VocabView / StatsView / AccountView / AdminView(+admin)
│   └── vite.config.js      # 代理指向线上站点，方便电脑调试
├── android/                # Capacitor 生成的安卓原生工程（可直接用 Android Studio 打开）
├── ci/android-build.yml    # GitHub Actions 云构建工作流（还没启用，见下文）
├── capacitor.config.json   # App 名称、包名、CapacitorHttp 开关
└── package.json
```

---

## 出 APK

### 方式一：GitHub Actions 云构建（不用装 Android Studio）

工作流我放在 `mobile/ci/`，因为要严格守住「不动 `mobile/` 以外的文件」，所以**没有**替你写进 `.github/workflows/`。启用只要一条命令：

```bash
mkdir -p .github/workflows && cp mobile/ci/android-build.yml .github/workflows/
```

提交推送之后，去 GitHub 仓库的 **Actions** 页面，选 `Build Android APK` → `Run workflow`。
跑完在该次运行的 **Artifacts** 里下载 `vocab-memory-debug-apk.zip`，解压得到 `app-debug.apk`，装到手机上即可（手机需允许「安装未知来源应用」）。

### 方式二：本机编译

前提：JDK 17 或 21、Android SDK（本机目前**都没有**，2026-09-21 核查过）。

```bash
cd mobile
npm install
npm --prefix web install
npm --prefix web run build
npx cap sync android
cd android && ./gradlew assembleDebug
# 产物：android/app/build/outputs/apk/debug/app-debug.apk
```

### 方式三：Android Studio 打开

```bash
cd mobile && npx cap open android
```

---

## 电脑上预览界面（不用真机）

```bash
cd mobile/web
npm run dev      # http://localhost:5173
# 或
npm run build && npm run preview   # http://localhost:4173
```

dev / preview 的 `/api` 会被代理到 `http://47.101.42.177:8080`，所以在电脑浏览器里就能调试，不用本机起后端。

---

## 几个关键技术决定

### 1. 为什么用 `CapacitorHttp` 而不改后端 CORS

页面打包进 App 之后，来源是 `https://localhost`，和服务器不同源，正常会撞 CORS。
`capacitor.config.json` 里开了 `plugins.CapacitorHttp.enabled = true`，请求改由**原生层**发出，绕开浏览器同源策略，**后端一个字都不用改**。

### 2. 为什么需要 `network_security_config.xml`

后端跑在 `http://47.101.42.177:8080`（没有 HTTPS），而安卓 9 起默认禁止明文 HTTP。
`android/app/src/main/res/xml/network_security_config.xml` 只对这**一个 IP** 放行明文，其他域名照样禁止。

> 以后服务器配上域名 + HTTPS，这个文件连同上面对它的引用可以整段删掉。

### 3. 接口地址只能走 8080

实测：`8000` 端口外网**不通**（`HTTP 000`），`8080` 上的 nginx 已经把 `/api` 反代到后端了。
所以 App 里的接口地址是 `http://47.101.42.177:8080/api`，写在 `web/src/api.js` 的 `NATIVE_API_BASE`。
想换服务器，改这一行即可，或者打包时用 `VITE_API_BASE` 环境变量覆盖。

### 4. 返回键

安卓物理返回键被接管了：不在「词汇」页就先退回「词汇」，已经在「词汇」页才退出 App。
不接管的话返回键会直接关掉 App，背单词背着背着就退出了。

---

## 以后 `frontend/` 改了怎么办

这份副本是**一次性分叉**：`frontend/` 后续的改动不会自动同步过来。

如果想同步，需要重新复制一遍，然后把这几个文件的手工改动再打一次（建议用 git 对比出差异）：

| 文件 | 改动 |
|---|---|
| `src/App.vue` | 整个重写：底部标签栏、默认进词汇页、接管返回键 |
| `src/api.js` | 接口地址改绝对路径；删掉 groups / files / admin-files / admin-groups |
| `src/main.js` | 末尾引入 `mobile.css` |
| `src/mobile.css` | 新增文件 |
| `src/components/AdminView.vue` | 去掉「文件管理」「分组管理」两个页签 |
| `src/components/admin/StatsPanel.vue` | 只留「用户数」，去掉文件/分组/上传记录 |
| `src/components/admin/UserManager.vue` | 去掉「文件数」「存储」两列 |
| `src/components/AccountView.vue` | 去掉「上传文件数」「占用存储」两行 |
| `src/components/LoginView.vue` | 标题「📄 PDF 工具」→「词汇记忆」 |
| `index.html` | 标题、viewport 加 `viewport-fit=cover` |
| `vite.config.js` | 代理目标改成线上站点 |

另需删除 `PdfList.vue` / `UploadPanel.vue` / `GroupSidebar.vue` / `admin/FileManager.vue` / `admin/GroupManager.vue`。

---

## 已知限制

- **必须联网**，断网打不开。
- **AI 助记**要联网调大模型，依赖后端 `config` 表里的 `ai_api_key` 配置。
- **Debug 版 APK** 是用调试密钥签名的，自己装没问题；要发给别人或上架得配正式签名。
- 管理后台里的「系统统计」只剩用户数——因为该接口只返回 PDF 相关统计，没有词汇数据。
- 手机上如果显示错位，改 `web/src/mobile.css` 最省事；那是所有手机端覆盖样式的集中出口。
