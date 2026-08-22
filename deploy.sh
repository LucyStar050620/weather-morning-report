#!/usr/bin/env bash
# 一键部署脚本（在 weather-morning-report 目录内运行）
# 用法: bash deploy.sh
set -e

REPO="weather-morning-report"

echo "==> 1) 准备 GitHub CLI"
if ! command -v gh >/dev/null 2>&1; then
  echo "    未检测到 gh，正在通过 winget 安装..."
  winget install --id GitHub.cli -e --source winget \
    --accept-package-agreements --accept-source-agreements
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "    请在浏览器中完成 GitHub 登录:"
  gh auth login
fi

echo "==> 2) 创建仓库并推送"
if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "    仓库已存在，直接推送。"
  git push -u origin main || git push -u origin master
else
  gh repo create "$REPO" --public --source=. --remote=origin --push
fi

echo "==> 3) 配置 Secrets"
read -s -p "    请输入 Server酱 SendKey: " SENDKEY
echo
gh secret set SERVERCHAN_SENDKEY -b "$SENDKEY"
read -p "    是否修改默认城市(留空则用 郑州): " CITY_INPUT
if [ -n "$CITY_INPUT" ]; then
  gh secret set CITY -b "$CITY_INPUT"
fi

echo ""
echo "✅ 部署完成！GitHub Actions 会在每天北京时间早 6 点自动推送天气到你的微信。"
echo "   可到仓库 Actions 页面手动 Run workflow 立即测试一次。"
