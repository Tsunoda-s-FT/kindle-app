# Repository Guidelines

## Project Structure & Module Organization
- `src/`: 実装コード。`capture.py`がWebスクリーンショット取得、`capture_app.py`がmacOSアプリのスクリーンショット取得、`create_pdf.py`がPDF生成、`kindle_utils.py`が共通処理。
- `examples/`: CLIの使用例（`examples/usage_examples.md`）。
- `kindle-captures/`: デフォルトの出力先（`{ASIN}/page_0001.png`, `metadata.json`）。
- `config.yaml`: 実行時設定（待機戦略、品質、出力先など）。
- `requirements.txt`: 依存関係。

## Build, Test, and Development Commands
- `pip install -r requirements.txt`: 依存関係をインストール。
- `python src/capture.py --asin <ASIN>`: Kindle Web Readerから全ページをキャプチャ。
- `python src/capture_app.py --book <TITLE>`: Kindle macOSアプリからスクリーンショット取得。
- `python src/create_pdf.py --input ./kindle-captures/<ASIN>/`: 取得した画像をPDF化。
- 併用推奨: `python src/capture.py --asin <ASIN> --chrome-profile /tmp/kindle-test-profile`  
  Chromeのプロファイルロック回避のため、テスト用プロファイルを使う。

## Coding Style & Naming Conventions
- Pythonは4スペースのインデント、PEP 8に準拠。
- 関数・変数は`snake_case`、モジュールは小文字ファイル名。
- 設定値は`config.yaml`に集約し、ハードコードを避ける。

## Testing Guidelines
- 専用テストは現時点で未整備。変更時は手動でE2E検証を行う。
- 推奨手順: `capture.py`→`create_pdf.py`の順で実行し、`metadata.json`とPDF出力を確認。

## Commit & Pull Request Guidelines
- 直近の履歴では`docs:`のようなプレフィックス付きが使われている。必要に応じて`docs:`, `feat:`, `fix:`を使い、短い要約にする。
- PRは目的・変更点・動作確認手順（例: `python src/capture.py --asin ...`）を記載。
- 画像やPDF出力に影響する変更は、出力サンプルか差分説明を添える。

## Security & Configuration Tips
- KindleログインはChrome側で事前に行う。セッション切れ時は再ログインが必要。
- `config.yaml`の`capture.wait_timeout`はネットワークが遅い環境で調整する。
