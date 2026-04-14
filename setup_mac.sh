#!/bin/bash
# work-projects MacBookセットアップスクリプト
# 使い方: bash <(curl -s https://raw.githubusercontent.com/gp6sk1029-design/work-projects/main/setup_mac.sh)

echo "=== work-projects MacBookセットアップ開始 ==="
cd ~
if [ -d "work-projects" ]; then
  echo "既存フォルダをバックアップ中..."
  mv work-projects "work-projects-backup-$(date '+%Y%m%d-%H%M%S')"
  echo "✅ バックアップ完了"
fi
echo "GitHubからclone中..."
git clone https://github.com/gp6sk1029-design/work-projects
if [ $? -eq 0 ]; then
  echo ""
  echo "=== ✅ セットアップ完了！ ==="
  cd ~/work-projects && git log --oneline -3
  echo "次のステップ: Claude Codeで ~/work-projects を開くだけ"
else
  echo "❌ cloneに失敗しました"
fi
