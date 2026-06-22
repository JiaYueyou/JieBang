# JieBang 团队 Git 日常协作指南

本项目采用 GitHub Flow。所有开发从最新 `main` 创建短期个人分支，通过
Pull Request（PR）合并回 `main`。禁止直接向 `main` 推送代码。

```text
最新 main
  → 创建个人分支
  → 开发与小步提交
  → 同步 origin/main
  → 本地验证
  → 推送个人分支
  → 创建 PR
  → 1 人审核 + CI 通过
  → Squash merge
  → 删除个人分支
```

## 1. 第一次参与项目

### 1.1 安装和配置

安装 Git 后配置自己的真实姓名和邮箱。邮箱建议与 GitHub 账号绑定：

```powershell
git config --global user.name "你的姓名或 GitHub 用户名"
git config --global user.email "你的 GitHub 邮箱"
git config --global init.defaultBranch main
git config --global fetch.prune true
```

查看配置：

```powershell
git config --global --list
```

不要照抄其他成员的姓名和邮箱。提交作者信息错误时，应在推送前修正。

### 1.2 克隆仓库

```powershell
cd E:\Project
git clone https://github.com/JiaYueyou/JieBang.git
cd JieBang
git remote -v
git status --short --branch
```

正常结果应包含：

```text
origin  https://github.com/JiaYueyou/JieBang.git
## main...origin/main
```

### 1.3 初始化本地环境

密钥只写入本地 `.env`，不能提交：

```powershell
Copy-Item fyz-src\backend\.env.example fyz-src\backend\.env
```

安装前端依赖：

```powershell
cd E:\Project\JieBang\fyz-src\frontend
npm.cmd ci --cache .npm-cache

cd E:\Project\JieBang\jtt-src\frontend
npm.cmd ci --cache .npm-cache
```

## 2. 分支命名规则

统一格式：

```text
<类型>/<成员>-<任务>
```

允许的常用类型：

| 类型 | 用途 | 示例 |
| --- | --- | --- |
| `feat` | 新功能 | `feat/jtt-resume-upload` |
| `fix` | 缺陷修复 | `fix/fyz-graph-query` |
| `refactor` | 不改变行为的重构 | `refactor/jtt-api-layer` |
| `docs` | 文档 | `docs/fyz-git-guide` |
| `test` | 测试 | `test/fyz-job-service` |
| `chore` | 工程配置、依赖、CI | `chore/fyz-update-ci` |

约束：

- 使用小写英文和短横线；
- 必须包含负责人标识，例如 `fyz`、`jtt`；
- 一个分支只处理一个明确任务；
- 分支建议在 1–3 天内合并，避免长期偏离 `main`；
- 不使用 `dev`、`new`、`test1`、`我的分支` 等含义模糊的名字。

## 3. 每天开始开发

无论昨天在哪个分支，开始新任务前都先更新 `main`：

```powershell
cd E:\Project\JieBang
git status --short --branch
git switch main
git fetch origin
git pull --ff-only origin main
git status --short --branch
```

`--ff-only` 会在本地 `main` 出现异常提交时拒绝制造合并提交。此时不要强行
执行普通 `git pull`，先检查：

```powershell
git log --oneline --graph --decorate --all -15
git log --oneline origin/main..main
```

确认 `main` 最新且干净后创建任务分支：

```powershell
git switch -c feat/jtt-resume-upload
```

确认当前位置：

```powershell
git branch --show-current
git status --short --branch
```

## 4. 开发过程中的提交

### 4.1 查看改动

```powershell
git status --short
git diff
git diff --stat
```

只暂存与当前任务有关的文件：

```powershell
git add jtt-src\frontend\src\views\resume\Upload.vue
git add jtt-src\frontend\src\api\resume.ts
```

检查暂存区：

```powershell
git diff --cached
git diff --cached --stat
git diff --cached --check
```

`git diff --cached --check` 必须无报错。确认后提交：

```powershell
git commit -m "feat(jtt-frontend): 完成简历上传流程"
```

### 4.2 提交信息

格式：

```text
<type>(<scope>): <简短说明>
```

常用 scope：

```text
backend
fyz-frontend
jtt-frontend
graph
data
agent
docs
ci
```

示例：

```powershell
git commit -m "feat(backend): 新增简历上传接口"
git commit -m "fix(graph): 修复节点路径查询重复结果"
git commit -m "test(backend): 补充岗位服务边界测试"
git commit -m "docs(git): 完善团队协作指南"
git commit -m "chore(ci): 增加前端构建检查"
```

提交应当小而完整：代码、对应测试和必要文档尽量放在同一逻辑提交中，不要把
多个无关功能塞进一个提交。

### 4.3 撤销尚未提交的操作

取消暂存，但保留文件修改：

```powershell
git restore --staged 路径
```

丢弃某个文件的未提交修改：

```powershell
git restore 路径
```

第二条命令会丢失修改，只能在确认不需要这些内容时使用。先运行 `git diff 路径`
检查。

## 5. 同步主分支

开发期间，尤其是准备提 PR 前，应把远端最新 `main` 整理到个人分支：

```powershell
git status --short
git fetch origin
git rebase origin/main
```

执行 rebase 前工作区必须干净。如果仍有未提交改动，先提交，或者临时保存：

```powershell
git stash push -u -m "WIP: 简历上传页面"
git fetch origin
git rebase origin/main
git stash pop
```

### 5.1 解决 rebase 冲突

出现冲突后：

```powershell
git status
```

打开冲突文件，处理以下标记：

```text
<冲突开始：HEAD>
main 中的内容
<冲突分隔线>
个人分支中的内容
<冲突结束：提交>
```

保留正确内容并删除标记，然后：

```powershell
git add 冲突文件
git rebase --continue
```
如果还有冲突，重复上述步骤。确认当前 rebase 不应继续时：

```powershell
git rebase --abort
```

不要在不理解冲突内容时整文件选择 “ours” 或 “theirs”。涉及 API、数据库迁移、
共享类型时，应找对应模块负责人共同确认。

### 5.2 rebase 后推送

个人分支第一次推送：

```powershell
git push -u origin feat/jtt-resume-upload
```

已经推送过的个人分支在 rebase 后提交哈希会变化，只允许使用：

```powershell
git push --force-with-lease
```

`--force-with-lease` 会在远端出现自己未获取的新提交时拒绝覆盖。禁止使用
`git push --force`，更禁止对 `main` 强推。

## 6. 提交 PR 前的完整验证

### 6.1 后端

```powershell
cd E:\Project\JieBang\fyz-src\backend
E:\Computer_tools\Anaconda\dld\envs\jiebang\python.exe -m pytest test -q
```

### 6.2 FYZ 管理/决策端

```powershell
cd E:\Project\JieBang\fyz-src\frontend
npm.cmd ci --cache .npm-cache
npm.cmd run test
npm.cmd run build
```

### 6.3 JTT 求职者端

```powershell
cd E:\Project\JieBang\jtt-src\frontend
npm.cmd ci --cache .npm-cache
npm.cmd run build
```

只需运行与改动相关的工程，但共享 API、类型、配置或根目录工程修改必须运行所有
受影响检查。CI 最终会再次执行三套检查。

### 6.4 仓库安全检查

```powershell
cd E:\Project\JieBang
git status --short --ignored
git diff --cached --check
gitleaks git --log-opts="--all" --redact .
```

确认 Git 未跟踪依赖、构建产物、缓存、真实 `.env` 或个人配置：

```powershell
git ls-files |
  Select-String 'node_modules|(^|/)dist/|__pycache__|\.pyc$|(^|/)\.env$|\.npm-cache|\.idea|\.vscode'
```

`.env.example` 是脱敏模板，可以提交；真实 `.env` 不可以。

## 7. 创建 Pull Request

推送分支：

```powershell
git push -u origin 当前分支名
```

在 GitHub 仓库页面点击 **Compare & pull request**：

1. Base 选择 `main`；
2. Compare 选择个人分支；
3. 标题使用 Conventional Commits，例如
   `feat(jtt-frontend): 完成简历上传流程`；
4. 按 PR 模板填写改动、测试、兼容性和截图；
5. 指定至少一名非作者成员为 Reviewer；
6. 等待四项 CI 全部通过；
7. 处理 Reviewer 评论，并点击 Resolve conversation；
8. 获得至少 1 个 Approve 后才允许合并。

Reviewer 应重点检查：

- 代码是否属于 PR 描述的任务；
- 是否破坏 API、数据库迁移、共享类型或配置；
- 是否包含测试、错误状态和边界情况；
- 是否误提交密钥、缓存、依赖或构建产物；
- 页面改动是否附截图，接口改动是否附请求/响应示例；
- CI 是否全部通过。

## 8. Squash 合并

本项目统一使用 **Squash and merge**。个人分支可以包含多个开发提交，但进入
`main` 后只保留一个清晰提交。

合并前调整 squash 提交标题：

```text
feat(jtt-frontend): 完成简历上传流程
```

不要使用 `Merge branch...`、`update`、`final` 等无意义标题。合并后在 GitHub
删除远端个人分支。

## 9. 合并后的本地清理

```powershell
cd E:\Project\JieBang
git switch main
git fetch origin
git pull --ff-only origin main
git branch -d feat/jtt-resume-upload
git fetch --prune
git status --short --branch
```

如果 Git 提示分支未完全合并，但 GitHub 已经 squash 合并，这是因为 squash
产生了新提交。确认 PR 确实已合并后可以删除：

```powershell
git branch -D feat/jtt-resume-upload
```

不要在未确认 PR 状态时使用 `-D`。

## 10. 修改已经创建的 PR

继续在原个人分支修改和提交：

```powershell
git switch feat/jtt-resume-upload
git add 指定文件
git commit -m "fix(jtt-frontend): 修复上传失败提示"
git push
```

GitHub 会自动更新原 PR，不要为同一任务重复创建 PR。Reviewer 提出修改后，不要
覆盖或删除他人的评论；修复并回复说明即可。

## 11. 常见问题与恢复

### 11.1 在 main 上误改但尚未提交

保留改动并转移到新分支：

```powershell
git switch -c fix/fyz-correct-task-name
git status --short
```

### 11.2 最近一次提交信息错误

仅限尚未推送，或确定只有自己使用的个人分支：

```powershell
git commit --amend -m "fix(backend): 正确的提交说明"
```

若分支已推送，amend 后使用：

```powershell
git push --force-with-lease
```

### 11.3 提交中误包含文件

尚未推送：

```powershell
git rm --cached 路径
git commit --amend --no-edit
```

如果文件应该一直忽略，同时补充 `.gitignore`。已经推送但不含密钥时，可在个人
分支修复后更新 PR。

### 11.4 撤销已经合并到 main 的错误

不要重写 `main` 历史。创建修复分支并使用 revert：

```powershell
git switch main
git pull --ff-only origin main
git switch -c revert/fyz-broken-change
git revert 错误提交哈希
git push -u origin revert/fyz-broken-change
```

然后创建紧急 PR。

### 11.5 密钥被提交

立即执行：

1. 在对应平台撤销并轮换密钥；
2. 通知仓库管理员和全体成员；
3. 暂停继续推送；
4. 不要认为删除文件或新增 `.gitignore` 就已解决；
5. 由管理员评估 Gitleaks 结果并使用 `git-filter-repo` 清理历史；
6. 历史重写后所有成员重新克隆。

密钥事故不能通过普通 revert 解决，因为旧提交仍可访问。

## 12. 明确禁止的操作

日常开发禁止：

```powershell
git push origin main
git push --force origin main
git push --force
git reset --hard
git clean -fd
git checkout -- .
```

这些命令可能绕过审核、覆盖他人提交或永久删除本地工作。确需恢复操作时，应先
备份改动并由仓库管理员确认目标提交和影响范围。

同样禁止：

- 共用一个长期个人分支；
- 在一个 PR 混入多个无关功能；
- 提交真实 `.env`、API Key、Token、密码或私钥；
- 提交 `node_modules`、`dist`、缓存、数据库或个人 IDE 配置；
- CI 失败时通过删除测试、跳过检查或直接推 `main` 绕过。

## 13. 仓库管理员：保护 main

在 GitHub 仓库进入 **Settings → Rules → Rulesets**，为 `main` 建立 Active
规则：

1. Target branches 选择 `main`；
2. Require a pull request before merging；
3. Required approvals 设置为 `1`；
4. Require conversation resolution；
5. Require status checks to pass；
6. Require branches to be up to date；
7. 必需检查选择：
   - `backend-tests`
   - `fyz-frontend`
   - `jtt-frontend`
   - `repository-security`
8. Block force pushes；
9. Restrict deletions；
10. 不配置普通成员 bypass。

在 **Settings → General → Pull Requests**：

- 仅启用 Allow squash merging；
- 启用 Automatically delete head branches；
- 禁用不需要的 merge commit 和 rebase merge。

## 14. 每日速查

```powershell
# 开始任务
git switch main
git fetch origin
git pull --ff-only origin main
git switch -c feat/jtt-resume-upload

# 开发提交
git status --short
git diff
git add 指定文件
git diff --cached
git diff --cached --check
git commit -m "feat(jtt-frontend): 完成简历上传流程"

# 同步并推送
git fetch origin
git rebase origin/main
git push -u origin feat/jtt-resume-upload

# PR squash 合并后
git switch main
git pull --ff-only origin main
git branch -d feat/jtt-resume-upload
git fetch --prune
```
