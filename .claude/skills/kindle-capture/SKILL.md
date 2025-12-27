---
name: kindle-capture
description: Kindle Web ReaderからスクリーンショットをキャプチャしてPDF生成。書籍名やASIN指定でKindle本を自動PDF化。Kindleライブラリから書籍検索、PlaywrightでKindleページ自動取得、PNG画像からPDF変換、レイアウト設定（single/double）、範囲指定、品質調整、リサイズに対応。「githubの本」など曖昧な書籍名でも検索可能。書籍スクリーンショット取得と文書PDF化を効率化。
---

# Kindle Capture Skill

Kindle Web Readerから書籍のスクリーンショットを自動取得し、PDFを生成します。

## 概要

このSkillは、Amazon Kindle Web Reader（read.amazon.co.jp）からPlaywrightを使用して書籍ページを自動的にキャプチャし、高品質なPDFファイルを生成します。KindleRenderer JavaScript APIを利用した効率的なページナビゲーションと、img2pdfによるロスレスPDF変換を実現しています。

## 前提条件

- **Google Chrome**: インストール済みで、Kindle Web Reader（https://read.amazon.co.jp）にログイン済みであること
- **ブラウザ自動化拡張機能**（オプション）: 書籍名での自動検索を行う場合に必要
  - 拡張機能未接続の場合は、ASINを手動で指定する必要があります
- **Python**: 3.10以降
- **依存パッケージ**: requirements.txtに記載のライブラリ

## セットアップ

```bash
cd /Users/tsunoda/Development/kindle-app

# 仮想環境を作成（初回のみ）
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# 注意: このツールはシステムのGoogle Chromeを使用します
# Playwrightのブラウザインストールは不要です
```

## 基本的な使い方

### ステップ1: スクリーンショット取得

```bash
source venv/bin/activate
python src/capture.py --asin <ASIN>
```

書籍のASINコードを指定して、全ページのスクリーンショットを取得します。
デフォルトはログイン済みの既存プロファイルを使用します。Chrome起動中でプロファイルロックが発生した場合は、自動的に `~/Library/Application Support/Google/Chrome-Kindle` にフォールバックします（初回ログインが必要）。

### ステップ2: PDF生成

```bash
source venv/bin/activate
python src/create_pdf.py --input ./kindle-captures/<ASIN>/
```

キャプチャしたスクリーンショットからPDFを生成します。

## コマンドオプション

### capture.py - スクリーンショット取得

**必須オプション**:
- `--asin <ASIN>`: 書籍のASINコード（Amazon商品識別子）

**主要オプション**:
- `--chrome-profile <パス>`: Chromeプロファイルパス（デフォルト: `~/Library/Application Support/Google/Chrome`）
  - Chrome起動中でプロファイルロックが発生した場合は `~/Library/Application Support/Google/Chrome-Kindle` に自動フォールバック
- `--layout <single|double>`: レイアウトモード（デフォルト: double）
  - `single`: シングルページ表示
  - `double`: 見開き（ダブルページ）表示
- `--start <位置>`: キャプチャ開始位置（Kindleの位置番号）
- `--end <位置>`: キャプチャ終了位置（Kindleの位置番号）
- `--output <ディレクトリ>`: 出力先ディレクトリ（デフォルト: ./kindle-captures/{ASIN}/）
- `--headless`: ヘッドレスモードで実行（デフォルト: false）
- `--max-pages <数値>`: 取得ページ数の上限（デフォルト: 無制限）
- `--viewport-width <数値>`: ブラウザのviewport幅（デフォルト: 3840）
- `--viewport-height <数値>`: ブラウザのviewport高さ（デフォルト: 2160）

### create_pdf.py - PDF生成

**必須オプション**:
- `--input <ディレクトリ>`: スクリーンショットが保存されているディレクトリ

**主要オプション**:
- `--output <ファイル名>`: 出力PDFファイル名（デフォルト: {ASIN}.pdf）
- `--quality <1-100>`: JPEG品質（デフォルト: 85）
- `--resize <0.1-1.0>`: リサイズ比率（デフォルト: 1.0 = リサイズなし）

## よくある使用パターン

### パターン1: 完全キャプチャ＆PDF生成

書籍全体をキャプチャしてPDF化する基本的なワークフローです。

```bash
source venv/bin/activate

# 1. スクリーンショット取得
python src/capture.py --asin B0DSKPTJM5

# 2. PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン2: 部分キャプチャ（範囲指定）

特定の範囲のみをキャプチャする場合に使用します。

```bash
source venv/bin/activate

# 位置1000から5000までをキャプチャ
python src/capture.py --asin B0DSKPTJM5 --start 1000 --end 5000

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン3: 見開きレイアウトでキャプチャ

見開き表示でキャプチャする場合に使用します。

```bash
source venv/bin/activate

# 見開きモードでキャプチャ
python src/capture.py --asin B0DSKPTJM5 --layout double

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン4: モバイル最適化PDF

モバイルデバイス用にファイルサイズを最適化する場合に使用します。

```bash
source venv/bin/activate

# 通常キャプチャ
python src/capture.py --asin B0DSKPTJM5

# リサイズ＆圧縮してPDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.7 --quality 80
```

## ブラウザ自動化によるASIN検索

このスキルはブラウザ自動化ツールを使用してKindleライブラリから書籍を検索できます。使用するエージェントに応じて適切なツールを使用してください。

### 抽象的なフロー（全エージェント共通）

1. Kindleライブラリ（https://read.amazon.co.jp/kindle-library）にアクセス
2. ログイン状態を確認（未ログインならユーザーに依頼）
3. 検索バーにキーワードを入力
4. 検索結果から書籍を選択
5. URLからASINを抽出（例: `https://read.amazon.co.jp/?asin=B0DSKPTJM5`）
6. `source venv/bin/activate && python src/capture.py --asin <ASIN>` を実行
7. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/` を実行
8. 完了報告

### Claude Code

ブラウザ自動化ツール: `mcp__claude-in-chrome__*`

| 操作 | ツール |
|------|--------|
| タブ確認/作成 | `tabs_context_mcp`, `tabs_create_mcp` |
| ナビゲート | `navigate` |
| 要素検索 | `find` |
| フォーム入力 | `form_input` |
| クリック/操作 | `computer` |
| ページ読み取り | `read_page` |

**前提条件**: Claude in Chrome エクステンション（https://claude.ai/chrome）

**実装例**:
1. `mcp__claude-in-chrome__tabs_context_mcp` でブラウザ接続を確認
2. `mcp__claude-in-chrome__navigate` でKindleライブラリにアクセス
3. `mcp__claude-in-chrome__find` で検索バーを特定
4. `mcp__claude-in-chrome__form_input` でキーワードを入力
5. `mcp__claude-in-chrome__computer` で検索を実行
6. `mcp__claude-in-chrome__read_page` で検索結果を取得

### Codex CLI

ブラウザ自動化ツール: `mcp__chrome-devtools__*`

| 操作 | ツール |
|------|--------|
| 新規ページ | `new_page` |
| ナビゲート | `navigate_page` |
| スナップショット | `take_snapshot` |
| フォーム入力 | `fill` |
| キー入力 | `press_key` |
| クリック | `click` |
| スクリプト実行 | `evaluate_script` |

**実装例**:
1. `mcp__chrome-devtools__new_page` でKindleライブラリにアクセス
2. ログイン画面が表示されていれば、ユーザーにログインを依頼
3. `mcp__chrome-devtools__take_snapshot` で検索バーを特定
4. `mcp__chrome-devtools__fill` でキーワードを入力
5. `mcp__chrome-devtools__press_key`（Enter）で検索実行
6. `mcp__chrome-devtools__take_snapshot` で検索結果を取得

### 他のエージェント

上記に該当しないエージェントを使用している場合：

1. エージェントのブラウザ自動化ツールを確認
2. 「抽象的なフロー」に従って同等の操作を実行
3. ブラウザ自動化が利用できない場合は、ユーザーに手動でASINを確認してもらう

**手動確認の案内**:
1. ユーザーにKindleライブラリ（https://read.amazon.co.jp/kindle-library）へのアクセスを依頼
2. 検索バーでキーワード検索を実行してもらう
3. 該当書籍のURLまたはASINを教えてもらう
4. 提供されたASINでキャプチャを実行

### ASINの確認方法

- **Kindle Web Reader URL**: `https://read.amazon.co.jp/?asin=B0DSKPTJM5` → ASIN: `B0DSKPTJM5`
- **Amazon商品URL**: `https://www.amazon.co.jp/dp/B0DSKPTJM5/` → ASIN: `B0DSKPTJM5`（`/dp/`の後の英数字）

## ユーザーリクエストの解釈と対応

**「githubの本をPDF化して」（書籍名が曖昧な場合）**:
1. ブラウザ自動化ツールでKindleライブラリを検索
2. 複数の候補がある場合はリスト表示してユーザーに確認
3. 選択された書籍のASINでキャプチャを実行

**「この本の100ページ目から200ページ目までPDF化」**:
1. ページ番号とKindleの位置番号の違いを説明（必要に応じて）
2. `--start` と `--end` オプションで範囲指定

**「見開きでキャプチャして」**:
1. `--layout double` オプションを使用

**「モバイル用に軽量化してPDF化」**:
1. `--resize 0.7 --quality 80` オプションを使用

## トラブルシューティング

### ブラウザ自動化が利用できない

**症状**: ブラウザ自動化ツールが接続されていない

**対処法**:
1. 手動でKindleライブラリから書籍のASINを確認
2. `source venv/bin/activate && python src/capture.py --asin <ASIN>` で直接実行

### セッション切れエラー

**症状**: `Session invalid. Please log in to Kindle in Chrome and retry.`

**原因**: Kindle Web Readerのログインセッションが切れている

**対処法**:
1. Google Chromeを開く
2. https://read.amazon.co.jp にアクセス
3. Amazonアカウントでログイン
4. スクリプトを再実行

### Chromeプロファイルがロックされているエラー

**症状**: `Failed to launch browser` または `Chrome profile is locked`

**原因**: 既にChromeが起動中で、デフォルトのプロファイルが使用されている

**対処法**（推奨）:
一時的なプロファイルを使用してプロファイル競合を回避します。この方法を使えば、通常のChromeを起動したままでもキャプチャできます。
```bash
source venv/bin/activate
python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile
```

**補足**: 自動フォールバック後は初回ログインが必要です。

**代替対処法**:
1. 起動中のGoogle Chromeをすべて終了
2. スクリプトを再実行

### ページ読み込みタイムアウト

**症状**: キャプチャが途中で進まなくなる、または遅い

**原因**: ネットワーク速度が遅い、またはページ読み込み検知のタイムアウトが短すぎる

**対処法**:
1. ネットワーク接続を確認
2. `config.yaml` の `wait_timeout` を増やす（例: `3.0` → `5.0`）
3. スクリプトを再実行

```yaml
# config.yaml
capture:
  wait_timeout: 5.0  # 3.0から5.0に変更
```

### スクリーンショットが見つからないエラー

**症状**: `No screenshots found in {directory}`

**原因**: capture.pyを実行せずにcreate_pdf.pyを実行した、またはディレクトリパスが間違っている

**対処法**:
1. 先に `source venv/bin/activate && python src/capture.py --asin <ASIN>` を実行（フォールバック時は初回ログイン）
2. 正しい入力ディレクトリパスを指定（`--input ./kindle-captures/<ASIN>/`）

## 出力ファイル

### ディレクトリ構造

```
kindle-captures/
└── {ASIN}/
    ├── page_0001.png
    ├── page_0002.png
    ├── page_0003.png
    ├── ...
    └── metadata.json
```

### metadata.json

各キャプチャセッションの詳細情報を記録します：
- ASIN
- レイアウト設定（single/double）
- キャプチャページ数
- 位置範囲（最小・最大）
- 各ページの位置情報とタイムスタンプ

### 生成されるPDF

- **デフォルト**: カレントディレクトリに `{ASIN}.pdf`
- **カスタム**: `--output` オプションで指定したファイル名

## 注意事項

このツールは**私的利用のみ**を目的としています。以下の点を遵守してください：

- 日本の著作権法を遵守してください
- Amazon Kindleの利用規約に従ってください
- 商業利用や第三者への再配布は禁止されています
- 生成したPDFは個人的な利用のみに使用してください

## 技術情報

### 使用ライブラリ

- **Playwright**: ブラウザ自動化（Chrome制御）
- **img2pdf**: PNG→PDF変換（ロスレス圧縮）
- **Pillow**: 画像処理（リサイズ、JPEG変換）
- **PyYAML**: 設定ファイル管理
- **tqdm**: 進捗表示

### KindleRenderer API

Kindle Web ReaderのJavaScript APIを利用：
- `getMinimumPosition()` / `getMaximumPosition()`: 書籍の位置範囲取得
- `gotoPosition(position)`: 指定位置へ移動
- `hasNextScreen()`: 次ページの有無確認
- `nextScreen()`: 次ページへ移動

## 詳細情報

- **詳細なオプション説明**: [REFERENCE.md](REFERENCE.md) を参照
- **より多くの使用例**: [EXAMPLES.md](EXAMPLES.md) を参照
