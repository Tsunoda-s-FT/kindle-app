# Kindle Web Reader Screenshot Automation

Kindle Webリーダーから自動的にスクリーンショットを取得し、PDFを生成するツールです。

## 特徴

- 全ページを自動キャプチャ（KindleRenderer API使用）
- シングル/見開きレイアウト対応
- PDF生成（リサイズ・品質調整可能）
- 進捗表示とメタデータ記録
- Claude Code Skillとして統合可能

## 前提条件

- **macOS** (macOS 14以降で動作確認)
- **Python 3.10以降**
- **Google Chrome** (ログイン済みKindleアカウント)
- Kindleライブラリに書籍が登録されていること

## クイックスタート

### 1. インストール

```bash
# リポジトリをクローン（または移動）
cd /Users/tsunoda/Development/kindle-app

# 依存パッケージインストール
pip install -r requirements.txt

# 注意: このツールはシステムのGoogle Chromeを使用します
# Playwrightのブラウザインストールは不要です
```

### 2. Kindleにログイン

1. Chromeを開く
2. https://read.amazon.co.jp にアクセス
3. Amazonアカウントでログイン
4. Chromeを終了

### 3. スクリーンショット取得

```bash
python src/capture.py --asin B0DSKPTJM5
```

### 4. PDF生成

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

完了！ カレントディレクトリに`B0DSKPTJM5.pdf`が生成されます。

## 詳細な使い方

### スクリーンショット取得

#### 基本

```bash
python src/capture.py --asin <ASIN>
```

#### オプション

| オプション | 説明 | デフォルト |
|----------|------|-----------|
| `--asin` | 書籍ASIN（必須） | - |
| `--layout` | single/double | single |
| `--output` | 出力ディレクトリ | ./kindle-captures/{ASIN}/ |
| `--start` | 開始位置 | 最初 |
| `--end` | 終了位置 | 最後 |
| `--headless` | ヘッドレスモード | False |
| `--chrome-profile` | Chromeプロファイルパス | ~/Library/Application Support/Google/Chrome |

#### 例

```bash
# 見開きレイアウトでキャプチャ
python src/capture.py --asin B0DSKPTJM5 --layout double

# 部分キャプチャ（位置500から10000まで）
python src/capture.py --asin B0DSKPTJM5 --start 500 --end 10000

# カスタム出力先
python src/capture.py --asin B0DSKPTJM5 --output ~/Documents/my-book/
```

### PDF生成

#### 基本

```bash
python src/create_pdf.py --input <ディレクトリ>
```

#### オプション

| オプション | 説明 | デフォルト |
|----------|------|-----------|
| `--input` | スクリーンショットディレクトリ（必須） | - |
| `--output` | 出力PDFファイル名 | {ディレクトリ名}.pdf |
| `--quality` | JPEG品質（1-100） | 85 |
| `--resize` | リサイズ比率（0.1-1.0） | 1.0 |

#### 例

```bash
# 基本
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/

# ファイル名指定
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --output my_book.pdf

# モバイル用に最適化（70%にリサイズ、品質80）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.7 --quality 80
```

## 設定ファイル

`config.yaml`で各種設定をカスタマイズできます。

```yaml
browser:
  chrome_profile: "~/Library/Application Support/Google/Chrome"
  headless: false
  timeout: 30000

capture:
  default_layout: "single"
  wait_strategy: "hybrid"  # location_change, fixed, hybrid
  wait_timeout: 3.0
  screenshot_format: "png"
  output_dir: "./kindle-captures"

pdf:
  default_quality: 85
  default_resize: 1.0
```

## ディレクトリ構造

```
kindle-app/
├── .claude/
│   ├── settings.local.json
│   └── skills/
│       └── kindle-capture/
│           ├── SKILL.md           # Claude Code Skill定義
│           ├── REFERENCE.md       # 詳細リファレンス
│           └── EXAMPLES.md        # 使用例と会話例
├── src/
│   ├── __init__.py
│   ├── capture.py           # スクリーンショット取得
│   ├── create_pdf.py         # PDF生成
│   └── kindle_utils.py       # 共通ユーティリティ
├── examples/
│   └── usage_examples.md     # コマンドライン使用例
├── requirements.txt          # 依存パッケージ
├── config.yaml               # 設定ファイル
├── README.md                 # このファイル
└── kindle-captures/          # デフォルト出力先
    └── {ASIN}/
        ├── page_0001.png
        ├── page_0002.png
        └── metadata.json
```

## 出力ファイル

### スクリーンショット

```
kindle-captures/
└── B0DSKPTJM5/
    ├── page_0001.png         # ページ1
    ├── page_0002.png         # ページ2
    ├── page_0003.png         # ページ3
    ├── ...
    └── metadata.json         # メタデータ
```

### metadata.json

各キャプチャの詳細情報を記録:

```json
{
  "asin": "B0DSKPTJM5",
  "layout": "single",
  "total_pages": 243,
  "position_range": [496, 141946],
  "capture_range": [496, 141946],
  "captured_at": "2025-12-21T15:30:00",
  "pages": [
    {
      "page": 1,
      "location": {"current": 1, "total": 241, "percent": 0},
      "timestamp": "2025-12-21T15:30:05"
    }
  ]
}
```

## トラブルシューティング

### セッション切れ

**症状**: "Session invalid. Please log in to Kindle"

**対処**:
1. Chromeで https://read.amazon.co.jp にログイン
2. 再実行

### Chromeプロファイルロック

**症状**: "Failed to launch browser"

**対処**:
1. 起動中のChromeをすべて終了
2. 再実行

### ページ読み込みが遅い

**症状**: キャプチャが進まない

**対処**:
- `config.yaml`の`wait_timeout`を増やす（3.0 → 5.0）
- ネットワーク接続を確認

### 書籍が見つからない

**症状**: ページが正しく表示されない

**対処**:
- ASINが正しいか確認
- Kindleライブラリに書籍があるか確認
- ブラウザで手動アクセスして確認

## Claude Code Skillとして使用

このツールはClaude Code Skillとして統合されています。

詳細は [SKILL.md](SKILL.md) を参照してください。

### 基本的な使い方

```
ユーザー: 「このKindle本をPDF化して」（ASINを提供）
Claude: capture.pyとcreate_pdf.pyを実行
```

## 技術情報

### 使用ライブラリ

- **Playwright 1.40+**: ブラウザ自動化
- **img2pdf 0.5+**: PNG→PDF変換（ロスレス）
- **Pillow 10.0+**: 画像処理
- **PyYAML 6.0+**: 設定ファイル
- **tqdm 4.66+**: 進捗表示

### KindleRenderer API

Kindle Web Readerの内部JavaScript APIを使用:

- `KindleRenderer.getMinimumPosition()` - 最初のページ位置
- `KindleRenderer.getMaximumPosition()` - 最後のページ位置
- `KindleRenderer.gotoPosition(position)` - 位置指定移動
- `KindleRenderer.nextScreen()` - 次ページ
- `KindleRenderer.hasNextScreen()` - 次ページの有無確認

### ページ読み込み検知

**ハイブリッド戦略**（デフォルト）:

1. Location表示の変化を監視（最大3秒）
2. タイムアウト時は固定1.5秒待機
3. 追加の安定化待機300ms

**他の戦略**:

- `location_change`: Location表示変化のみ監視
- `fixed`: 固定1.5秒待機のみ

`config.yaml`で変更可能。

## 制限事項

- **リフロー型書籍のみ対応**（固定レイアウト・コミックは未対応）
- **macOSのみ動作確認**（Windows/Linuxは未検証）
- **Chrome必須**（他のブラウザは非対応）
- **ログイン状態必須**（自動ログインは未実装）

## ロードマップ

将来的な機能拡張:

- [ ] 書籍検索機能（search_books.py）
- [ ] 中断からの自動復帰
- [ ] 複数書籍の一括処理
- [ ] OCRによるテキスト抽出
- [ ] GUIラッパー
- [ ] 固定レイアウト書籍対応

## 法的注意事項

**重要**: このツールは私的利用のみを目的としています。

- 著作権法を遵守してください
- Kindleの利用規約に従ってください
- 商業利用や再配布は禁止されています
- 生成されたPDFの取り扱いには十分注意してください

著作権法に違反する使用については、一切の責任を負いません。

## ライセンス

MIT License

## 作者

Created for private use with Kindle Web Reader.

## 参考

- [Kindle Web Reader](https://read.amazon.co.jp/)
- [Playwright](https://playwright.dev/)
- [img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf)
