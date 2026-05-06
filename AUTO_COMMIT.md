# 自动提交到 GitHub 仓库

本文档用于说明如何把 `D:\gaokaollm-v2` 中的本地改动自动提交并推送到对应 GitHub 仓库。

当前仓库远程地址：

```powershell
https://github.com/PZQ-ship-it/gaokaollm-v2.git
```

## 前置条件

1. 本地仓库已经初始化，并设置好远程：

```powershell
git remote -v
```

应能看到：

```powershell
origin  https://github.com/PZQ-ship-it/gaokaollm-v2.git (fetch)
origin  https://github.com/PZQ-ship-it/gaokaollm-v2.git (push)
```

2. GitHub 远程仓库已经创建为 public。

3. 当前机器已经具备 GitHub 推送权限。可以先手动测试一次：

```powershell
git push -u origin main
```

如果需要登录，按 Git 弹出的 GitHub 登录窗口或 token 提示完成授权。

## 手动提交流程

每次修改后，可以在仓库目录运行：

```powershell
git status
git add .
git commit -m "Update project files"
git push
```

如果没有文件变更，`git commit` 会提示没有可提交内容。

## 自动提交脚本

可以新建一个本地脚本，例如：

```powershell
D:\gaokaollm-v2\scripts\auto_commit.ps1
```

脚本内容：

```powershell
$RepoPath = "D:\gaokaollm-v2"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$CommitMessage = "Auto commit: $Timestamp"

Set-Location $RepoPath

git status --short

$Changes = git status --porcelain
if ([string]::IsNullOrWhiteSpace($Changes)) {
    Write-Host "No changes to commit."
    exit 0
}

git add .
git commit -m $CommitMessage
git push origin main
```

运行方式：

```powershell
powershell -ExecutionPolicy Bypass -File D:\gaokaollm-v2\scripts\auto_commit.ps1
```

## 定时自动提交

如果希望 Windows 定时执行，可以使用“任务计划程序”：

1. 打开“任务计划程序”。
2. 创建基本任务，例如 `gaokaollm-v2 auto commit`。
3. 触发器选择每天、每小时，或按需要设置。
4. 操作选择“启动程序”。
5. 程序填写：

```powershell
powershell.exe
```

6. 参数填写：

```powershell
-ExecutionPolicy Bypass -File D:\gaokaollm-v2\scripts\auto_commit.ps1
```

## 注意事项

- 自动提交适合保存阶段性进度，但不建议提交临时大文件、密钥、缓存文件或数据集。
- 后续如果出现 `.env`、模型文件、日志、缓存目录，应先加入 `.gitignore`。
- 自动提交前最好保持 commit message 可读。如果需要更清晰的历史记录，关键节点仍建议手动提交。
- 如果多人协作，自动 `git push` 前可能需要先执行 `git pull --rebase`，避免远程分支已有新提交导致推送失败。
