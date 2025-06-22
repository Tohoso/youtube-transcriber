# GitHub へのデプロイ手順

## 1. GitHubでリポジトリを作成

1. [GitHub](https://github.com) にログイン
2. 右上の「+」ボタンから「New repository」を選択
3. 以下の情報を入力：
   - Repository name: `youtube-transcriber`
   - Description: `YouTube channel transcript extraction CLI application`
   - Public を選択
   - "Initialize this repository with:" のチェックは全て外す
4. 「Create repository」をクリック

## 2. リモートリポジトリを追加してプッシュ

GitHubでリポジトリを作成後、以下のコマンドを実行：

```bash
# リモートリポジトリを追加（YOUR_USERNAME を自分のGitHubユーザー名に置き換え）
git remote add origin https://github.com/YOUR_USERNAME/youtube-transcriber.git

# または SSH を使用する場合
git remote add origin git@github.com:YOUR_USERNAME/youtube-transcriber.git

# mainブランチにプッシュ
git push -u origin main
```

## 3. 確認

ブラウザでリポジトリページを更新し、コードがアップロードされていることを確認。

## オプション: GitHub Actions の設定

`.github/workflows/test.yml` を作成して自動テストを設定：

```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev]
    - name: Run tests
      run: |
        pytest tests/
```