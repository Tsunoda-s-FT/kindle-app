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
- **Claude in Chrome エクステンション**: 書籍名での自動検索を行う場合に必要（https://claude.ai/chrome からインストール）
  - エクステンション未接続の場合は、ASINを手動で指定する必要があります
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

# Playwrightブラウザをインストール
playwright install chromium
```

## 基本的な使い方

### ステップ1: スクリーンショット取得

```bash
source venv/bin/activate
python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile
```

書籍のASINコードを指定して、全ページのスクリーンショットを取得します。
`--chrome-profile /tmp/kindle-test-profile` オプションで一時プロファイルを使用し、既存のChromeセッションとの競合を回避します。

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
- `--chrome-profile <パス>`: Chromeプロファイルパス（推奨: `/tmp/kindle-test-profile`）
  - 一時プロファイルを使用して既存のChromeセッションとの競合を回避
- `--layout <single|double>`: レイアウトモード（デフォルト: single）
  - `single`: シングルページ表示
  - `double`: 見開き（ダブルページ）表示
- `--start <位置>`: キャプチャ開始位置（Kindleの位置番号）
- `--end <位置>`: キャプチャ終了位置（Kindleの位置番号）
- `--output <ディレクトリ>`: 出力先ディレクトリ（デフォルト: ./kindle-captures/{ASIN}/）
- `--headless`: ヘッドレスモードで実行（デフォルト: false）

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
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile

# 2. PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン2: 部分キャプチャ（範囲指定）

特定の範囲のみをキャプチャする場合に使用します。

```bash
source venv/bin/activate

# 位置1000から5000までをキャプチャ
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --start 1000 --end 5000

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン3: 見開きレイアウトでキャプチャ

見開き表示でキャプチャする場合に使用します。

```bash
source venv/bin/activate

# 見開きモードでキャプチャ
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --layout double

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

### パターン4: モバイル最適化PDF

モバイルデバイス用にファイルサイズを最適化する場合に使用します。

```bash
source venv/bin/activate

# 通常キャプチャ
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile

# リサイズ＆圧縮してPDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.7 --quality 80
```

## Claude Codeからの使い方

このSkillは、ユーザーの自然言語リクエストに基づいて自動的に起動されます。

### ユーザーリクエストの解釈と対応

**「githubの本をPDF化して」（書籍名が曖昧な場合）**:
1. `mcp__claude-in-chrome__tabs_context_mcp` でブラウザエクステンション接続を確認
2. 接続されている場合：
   - Kindleライブラリ（https://read.amazon.co.jp/kindle-library）にアクセス
   - 検索機能で「github」を検索
   - 該当する書籍をユーザーに確認（複数ある場合はリスト表示）
   - 書籍URLからASINを抽出（例: `/dp/B0DSKPTJM5/`）
3. 未接続の場合：
   - ユーザーに手動での確認を依頼
   - KindleライブラリでのASIN確認方法を案内
4. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile` を実行
5. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/` を実行
6. 完了報告

**「Kindle本をPDF化して」（ASINが不明な場合）**:
1. `mcp__claude-in-chrome__tabs_context_mcp` でブラウザエクステンション接続を確認
2. 接続されている場合はKindleライブラリにアクセスして書籍を検索
3. 未接続の場合はユーザーにASINの確認を依頼
4. URLからASINを抽出、またはユーザーにASINを確認
5. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile` を実行
6. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/` を実行
7. 完了報告（「PDFファイルを {ファイル名} として生成しました」）

**「この本の100ページ目から200ページ目までPDF化」**:
1. ページ番号とKindleの位置番号の違いを説明（必要に応じて）
2. 範囲を確認（`--start` と `--end` の値を確認）
3. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile --start <開始位置> --end <終了位置>` を実行
4. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/` を実行
5. 完了報告

**「見開きでキャプチャして」**:
1. ASINを確認
2. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile --layout double` を実行
3. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/` を実行
4. 完了報告

**「モバイル用に軽量化してPDF化」**:
1. ASINを確認
2. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile` を実行
3. `source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/<ASIN>/ --resize 0.7 --quality 80` を実行
4. 完了報告

### 書籍名からASINを特定する方法

ユーザーが書籍名（「githubの本」など曖昧な表現含む）で依頼した場合、以下の方法でASINを特定します。

#### 方法1: Kindleライブラリから自動検索（推奨）

**前提条件**: Claude in Chrome エクステンションがインストール・接続されている必要があります

Claude Codeのブラウザ自動化ツールを使用して、Kindleライブラリから書籍を検索します：

1. **エクステンション接続確認**:
   - `mcp__claude-in-chrome__tabs_context_mcp` でブラウザ接続を確認
   - 未接続の場合は方法2または方法3を使用

2. **Kindleライブラリにアクセス**:
   - URL: https://read.amazon.co.jp/kindle-library
   - `mcp__claude-in-chrome__navigate` でアクセス

3. **書籍を検索**:
   - `mcp__claude-in-chrome__find` でライブラリ内の検索バーを特定
   - `mcp__claude-in-chrome__form_input` でキーワード（例: "github"）を入力
   - `mcp__claude-in-chrome__computer` で検索を実行

4. **検索結果を取得**:
   - `mcp__claude-in-chrome__read_page` で検索結果のページを読み取り
   - 書籍のタイトル、著者名、ASINを抽出

5. **候補をユーザーに確認**:
   - 複数の候補がある場合、書籍タイトルと著者名をリスト表示
   - `AskUserQuestion` ツールでユーザーに選択してもらう

6. **ASINを抽出**:
   - 書籍のURLまたはHTML属性からASINを抽出
   - URL例: `https://read.amazon.co.jp/?asin=B0DSKPTJM5`
   - ASIN: `B0DSKPTJM5`

#### 方法2: ユーザーに手動で確認を依頼（エクステンション未接続時）

Claude in Chrome エクステンションが接続されていない場合の代替手段：

1. ユーザーにKindleライブラリ（https://read.amazon.co.jp/kindle-library）へのアクセスを依頼
2. 検索バーでキーワード検索を実行してもらう
3. 該当書籍のURLまたはASINを教えてもらう
4. 提供されたASINでキャプチャを実行

#### 方法3: ASINを直接指定

ASINを知っている場合は直接確認します：

- Amazon商品URLから確認: `https://www.amazon.co.jp/dp/B0DSKPTJM5/`
- ASIN: `B0DSKPTJM5`（`/dp/`の後の英数字）

#### 実装例

**エクステンション接続時の自動検索**:
```
ユーザー: 「githubの本をPDF化して」

Claude:
[mcp__claude-in-chrome__tabs_context_mcp で接続確認]
[Kindleライブラリにアクセスして「github」で検索]
[検索結果を取得]

以下の書籍が見つかりました：
- 「いちばんやさしいGit&GitHubの教本 第3版」（著者: 横田紋奈, 宇賀神みずき） - ASIN: B0DSKPTJM5
- 「GitHubの教科書」（著者: 山田太郎） - ASIN: B0XYZ12345

どちらの書籍をPDF化しますか？

ユーザー: 「いちばんやさしいGit&GitHubの教本 第3版」

Claude: 承知しました。ASIN: B0DSKPTJM5 の書籍をキャプチャします...
[source venv/bin/activate && python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile を実行]
[スクリーンショット取得完了]
[source venv/bin/activate && python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ を実行]

PDFファイルを B0DSKPTJM5.pdf として生成しました。
```

**エクステンション未接続時の代替手順**:
```
ユーザー: 「githubの本をPDF化して」

Claude:
[mcp__claude-in-chrome__tabs_context_mcp で接続確認 → 未接続]

Claude in Chrome エクステンションが接続されていないため、自動検索ができません。
以下の方法で書籍を特定できます：

1. Kindleライブラリ（https://read.amazon.co.jp/kindle-library）にアクセス
2. 「github」で検索
3. 該当書籍のURLまたはASINを教えてください

ユーザー: 「ASIN: B0DSKPTJM5」

Claude: 承知しました。ASIN: B0DSKPTJM5 の書籍をキャプチャします...
[source venv/bin/activate && python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile を実行]
```

## トラブルシューティング

### ブラウザエクステンション未接続エラー

**症状**: `Browser extension is not connected.`

**原因**: Claude in Chrome エクステンションがインストールされていない、または接続されていない

**対処法**:
1. https://claude.ai/chrome からClaude in Chrome エクステンションをインストール
2. Chromeを再起動
3. エクステンションが有効になっていることを確認
4. スクリプトを再実行

**代替手段**（エクステンションを使用しない場合）:
1. 手動でKindleライブラリから書籍のASINを確認
2. `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile` で直接実行

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

**重要**: すべてのcapture.pyコマンドで `--chrome-profile /tmp/kindle-test-profile` オプションを使用することを推奨します。

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
1. 先に `source venv/bin/activate && python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile` を実行
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
