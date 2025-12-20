# Kindle Capture - 詳細リファレンス

このドキュメントでは、Kindle Captureツールの技術的な詳細、全コマンドラインオプション、設定ファイルの詳細、内部実装について説明します。

## コマンドライン引数

### capture.py - スクリーンショット取得

#### 必須オプション

**`--asin <ASIN>`**
- 書籍のASIN（Amazon Standard Identification Number）
- 例: `B0DSKPTJM5`
- Amazon商品URLの`/dp/`の後に続く英数字

#### オプション

**`--layout <single|double>`**
- レイアウトモード（デフォルト: `single`）
- `single`: シングルページ表示
- `double`: 見開き（ダブルページ）表示
- 見開きモードは1回のキャプチャで2ページを取得

**`--start <位置>`**
- キャプチャ開始位置（Kindleの位置番号）
- 省略時は書籍の最初から開始
- 例: `--start 1000`

**`--end <位置>`**
- キャプチャ終了位置（Kindleの位置番号）
- 省略時は書籍の最後まで
- 例: `--end 5000`

**`--output <ディレクトリ>`**
- スクリーンショットの出力先ディレクトリ
- デフォルト: `./kindle-captures/{ASIN}/`
- 指定ディレクトリが存在しない場合は自動作成

**`--headless`**
- ヘッドレスモードで実行（UIなし）
- デフォルト: `false`（ブラウザウィンドウを表示）
- サーバー環境や自動化での使用に適している

**`--chrome-profile <パス>`**
- 使用するChromeプロファイルのパス
- デフォルト: `~/Library/Application Support/Google/Chrome`（macOS）
- Kindleにログイン済みのプロファイルを指定

**`--config <ファイル>`**
- 設定ファイルのパス
- デフォルト: `./config.yaml`
- カスタム設定ファイルを使用する場合に指定

#### 使用例

```bash
# 基本的な使い方
python src/capture.py --asin B0DSKPTJM5

# 見開きレイアウト
python src/capture.py --asin B0DSKPTJM5 --layout double

# 範囲指定
python src/capture.py --asin B0DSKPTJM5 --start 1000 --end 5000

# カスタム出力先
python src/capture.py --asin B0DSKPTJM5 --output ./my-captures/

# ヘッドレスモード
python src/capture.py --asin B0DSKPTJM5 --headless
```

### create_pdf.py - PDF生成

#### 必須オプション

**`--input <ディレクトリ>`**
- スクリーンショットが保存されているディレクトリ
- capture.pyで生成したディレクトリを指定
- 例: `./kindle-captures/B0DSKPTJM5/`

#### オプション

**`--output <ファイル名>`**
- 出力PDFファイル名
- デフォルト: `{ASIN}.pdf` または `{ディレクトリ名}.pdf`
- 例: `--output my_book.pdf`

**`--quality <1-100>`**
- JPEG品質（1-100の整数）
- デフォルト: `85`
- 高い値ほど高品質だがファイルサイズが大きくなる
- 推奨値:
  - 高品質: `95`
  - 標準: `85`
  - 軽量: `70-80`
  - 超軽量: `60-70`

**`--resize <0.1-1.0>`**
- リサイズ比率（0.1-1.0の小数）
- デフォルト: `1.0`（リサイズなし）
- 例:
  - `0.7`: 元の70%のサイズ（モバイル用）
  - `0.5`: 元の50%のサイズ（超軽量）

**`--config <ファイル>`**
- 設定ファイルのパス
- デフォルト: `./config.yaml`

#### 使用例

```bash
# 基本的な使い方
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/

# 出力ファイル名指定
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --output my_book.pdf

# 高品質PDF
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --quality 95

# モバイル最適化（70%サイズ、品質80）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.7 --quality 80

# 超軽量PDF
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.5 --quality 60
```

## config.yaml 設定項目

設定ファイル（`config.yaml`）で、ブラウザ動作、キャプチャ設定、PDF設定をカスタマイズできます。

### browser セクション

```yaml
browser:
  chrome_profile: "/tmp/kindle-test-profile"
  headless: false
  timeout: 30000
```

**`chrome_profile`**
- Chromeプロファイルのパス
- Kindleにログイン済みのプロファイルを指定
- デフォルト: `~/Library/Application Support/Google/Chrome` (macOS)

**`headless`**
- ヘッドレスモードの有効/無効
- `true`: UIなしで実行
- `false`: ブラウザウィンドウを表示（デフォルト）

**`timeout`**
- ページ読み込みタイムアウト（ミリ秒）
- デフォルト: `30000`（30秒）
- ネットワークが遅い場合は増やす

### capture セクション

```yaml
capture:
  default_layout: "single"
  wait_strategy: "hybrid"
  wait_timeout: 3.0
  screenshot_format: "png"
  output_dir: "./kindle-captures"
```

**`default_layout`**
- デフォルトのレイアウトモード
- `single`: シングルページ
- `double`: 見開き

**`wait_strategy`**
- ページ読み込み検知戦略
- `location_change`: Location表示の変化を監視
- `fixed`: 固定時間待機
- `hybrid`: ハイブリッド（Location変化→固定待機へフォールバック）
- 推奨: `hybrid`

**`wait_timeout`**
- ページ読み込み待機時間（秒）
- デフォルト: `3.0`
- ネットワークが遅い場合は `5.0` 以上に設定

**`screenshot_format`**
- スクリーンショットのフォーマット
- `png`: PNG形式（ロスレス、デフォルト）
- `jpeg`: JPEG形式（非推奨）

**`output_dir`**
- デフォルトの出力ディレクトリ
- デフォルト: `./kindle-captures`

### pdf セクション

```yaml
pdf:
  default_quality: 85
  default_resize: 1.0
```

**`default_quality`**
- デフォルトのJPEG品質（1-100）
- デフォルト: `85`

**`default_resize`**
- デフォルトのリサイズ比率（0.1-1.0）
- デフォルト: `1.0`（リサイズなし）

## KindleRenderer API

Kindle Web Readerは内部的に`KindleRenderer`というJavaScript APIを提供しています。このツールはこのAPIを利用してページナビゲーションを実現しています。

### 使用しているAPI

#### `KindleRenderer.getMinimumPosition()`
- 書籍の最小位置（開始位置）を取得
- 戻り値: 整数（位置番号）

#### `KindleRenderer.getMaximumPosition()`
- 書籍の最大位置（終了位置）を取得
- 戻り値: 整数（位置番号）

#### `KindleRenderer.gotoPosition(position)`
- 指定位置へ移動
- パラメータ: `position`（整数）

#### `KindleRenderer.hasNextScreen()`
- 次ページの有無を確認
- 戻り値: `true` / `false`

#### `KindleRenderer.nextScreen()`
- 次ページへ移動
- 戻り値: なし

#### `KindleRenderer.getPosition()`
- 現在の位置を取得
- 戻り値: 整数（位置番号）

### JavaScript実行例

```javascript
// ブラウザコンソールでの実行例
await page.evaluate(() => {
    return {
        min: KindleRenderer.getMinimumPosition(),
        max: KindleRenderer.getMaximumPosition(),
        current: KindleRenderer.getPosition(),
        hasNext: KindleRenderer.hasNextScreen()
    };
});
```

## ページ読み込み検知戦略

Kindle Web Readerではページ遷移後の読み込み完了を確実に検知する必要があります。このツールでは3つの戦略を提供しています。

### 1. location_change 戦略

Location表示（"Location X of Y"）の変化を監視して読み込み完了を検知します。

**メリット**:
- 正確な検知
- 無駄な待機時間が少ない

**デメリット**:
- Location表示がない場合に対応できない

### 2. fixed 戦略

固定時間（デフォルト: 1.5秒）待機します。

**メリット**:
- シンプルで確実
- Location表示の有無に依存しない

**デメリット**:
- 無駄な待機時間が発生する可能性

### 3. hybrid 戦略（推奨）

Location表示の変化を監視し、タイムアウト時は固定待機にフォールバックします。

**動作フロー**:
1. Location表示の変化を監視（最大3秒）
2. 変化を検知したら即座に次へ
3. タイムアウト時は固定1.5秒待機にフォールバック
4. 追加の安定化待機（300ms）

**設定**:
```yaml
capture:
  wait_strategy: "hybrid"
  wait_timeout: 3.0  # Location変化の監視時間（秒）
```

## 出力ファイル形式

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

### スクリーンショットファイル

- **ファイル名**: `page_XXXX.png`（4桁のゼロパディング）
- **フォーマット**: PNG（ロスレス）
- **解像度**: 2560x1440（デフォルトのブラウザ解像度）

### metadata.json

各キャプチャセッションの詳細情報を記録します。

**構造**:
```json
{
  "asin": "B0DSKPTJM5",
  "layout": "single",
  "total_pages": 245,
  "position_range": {
    "min": 0,
    "max": 12345
  },
  "pages": [
    {
      "page_number": 1,
      "filename": "page_0001.png",
      "position": 0,
      "timestamp": "2024-01-15T10:30:45.123456"
    },
    {
      "page_number": 2,
      "filename": "page_0002.png",
      "position": 50,
      "timestamp": "2024-01-15T10:30:48.234567"
    }
  ]
}
```

**フィールド説明**:
- `asin`: 書籍のASIN
- `layout`: レイアウトモード（single/double）
- `total_pages`: キャプチャしたページ数
- `position_range.min`: 書籍の最小位置
- `position_range.max`: 書籍の最大位置
- `pages`: 各ページの詳細情報配列
  - `page_number`: ページ番号（1始まり）
  - `filename`: スクリーンショットファイル名
  - `position`: Kindleの位置番号
  - `timestamp`: キャプチャ日時（ISO 8601形式）

## 技術的制限事項

### 対応書籍形式

- **対応**: リフロー型Kindle書籍（テキストベース）
- **非対応**: 固定レイアウト型書籍（コミック、雑誌など）

### 対応プラットフォーム

- **macOS**: 完全対応
- **Windows**: 未テスト（Chromeプロファイルパスの調整が必要）
- **Linux**: 未テスト（Chromeプロファイルパスの調整が必要）

### ブラウザ要件

- **必須**: Google Chrome
- **非対応**: Firefox、Safari、Edge

### セッション管理

- Kindle Web Readerのログインセッションが必要
- 50ページごとにセッション有効性を再確認
- セッション切れ時は手動でログインし直す必要がある

### パフォーマンス

- **キャプチャ速度**: 約3-5秒/ページ（ネットワーク速度に依存）
- **メモリ使用量**: 書籍サイズに比例（大量ページの場合は注意）

## トラブルシューティング詳細

### セッション切れの原因

1. 長時間のキャプチャ（数時間以上）
2. Amazonアカウントのセキュリティ設定
3. IPアドレスの変更（VPN使用時など）

**対処**:
- 定期的にKindle Web Readerにログインし直す
- セッションタイムアウトを考慮して、大量ページは分割キャプチャ

### Chrome起動エラー

**症状**: `Failed to launch browser: Executable doesn't exist`

**原因**: Chromeがインストールされていない、またはパスが間違っている

**対処**:
- Google Chromeをインストール
- `--chrome-profile`オプションで正しいパスを指定

### ページ読み込みが遅い

**原因**:
- ネットワーク速度が遅い
- Kindle Web Readerサーバーの負荷が高い
- 大きな画像を含むページ

**対処**:
1. `config.yaml`の`wait_timeout`を増やす
2. `wait_strategy`を`fixed`に変更
3. より安定したネットワーク環境で実行

## 内部実装

### 使用技術スタック

- **Python**: 3.10+
- **Playwright**: ブラウザ自動化
- **img2pdf**: ロスレスPDF生成
- **Pillow**: 画像処理（リサイズ、JPEG変換）
- **PyYAML**: 設定ファイル管理
- **tqdm**: 進捗表示

### 処理フロー

#### capture.py

1. 設定ファイル読み込み
2. Playwrightブラウザコンテキスト作成
3. Kindle Web Readerへナビゲート
4. セッション有効性確認
5. レイアウトモード設定
6. 位置範囲取得（min/max）
7. ページループ：
   - スクリーンショット取得
   - metadata記録
   - 次ページへ移動
   - 進捗表示更新
8. metadata.json保存
9. ブラウザ終了

#### create_pdf.py

1. 入力ディレクトリの検証
2. PNG画像ファイル検出
3. リサイズ処理（必要な場合）：
   - Pillowで画像読み込み
   - 指定比率でリサイズ
   - JPEG一時ファイル作成
4. img2pdfでPDF生成
5. 一時ファイル削除
6. 完了報告

### ファイル構成

```
src/
├── capture.py          # メインキャプチャスクリプト（340行）
├── create_pdf.py       # PDF生成スクリプト（234行）
└── kindle_utils.py     # ユーティリティ関数（458行）
```

**kindle_utils.py 主要関数**:
- `create_browser_context()`: Playwrightブラウザコンテキスト作成
- `check_session_valid()`: セッション有効性確認
- `set_layout_mode()`: レイアウトモード設定
- `goto_position()`: 指定位置へ移動
- `next_page()`: 次ページへ移動
- `has_next_page()`: 次ページ有無確認
- `get_current_location()`: 現在位置取得
- `get_position_range()`: 位置範囲取得
- `wait_for_page_load()`: ページ読み込み待機
- `dismiss_modal_dialogs()`: モーダルダイアログ閉じ

## 関連ドキュメント

- [SKILL.md](SKILL.md) - 基本的な使い方とクイックスタート
- [EXAMPLES.md](EXAMPLES.md) - 実践的な使用例とシナリオ
