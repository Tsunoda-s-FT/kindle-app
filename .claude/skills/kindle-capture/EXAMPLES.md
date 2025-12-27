# Kindle Capture - 使用例

このドキュメントでは、Kindle Captureツールの実践的な使用例、AIアシスタントでの会話例、複雑なシナリオへの対応方法を紹介します。

## AIアシスタントでの会話例

### 例0: 書籍名からASINを検索してPDF化（最も一般的なケース）

**ユーザー**: githubの本をPDF化して

**AIアシスタント**: Kindleライブラリで「github」を検索します。

（ブラウザ自動化ツールでhttps://read.amazon.co.jp/kindle-libraryにアクセス、検索実行）

以下の書籍が見つかりました：

1. **GitHub実践入門** - 大塚弘記 著
   - ASIN: B0DSKPTJM5
   - 最終閲覧: 2024年1月10日

2. **GitHubの教科書** - 山田太郎 著
   - ASIN: B0XYZ12345
   - 最終閲覧: 2023年12月15日

どちらの書籍をPDF化しますか？番号または書籍名で教えてください。

**ユーザー**: 1番で

**AIアシスタント**: 承知しました。「GitHub実践入門」（ASIN: B0DSKPTJM5）をキャプチャします。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile
```

（キャプチャ実行中...）

キャプチャが完了しました（312ページ）。次にPDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

PDFファイル `B0DSKPTJM5.pdf` を生成しました。カレントディレクトリに保存されています。

---

### 例1: 基本的な全ページキャプチャ（ASINが既知の場合）

**ユーザー**: Kindleの本をPDF化してください

**AIアシスタント**: 書籍のASINコードを教えてください。ASINはAmazonの商品URLの`/dp/`の後に続く英数字です（例: `B0DSKPTJM5`）。

**ユーザー**: B0DSKPTJM5です

**AIアシスタント**: 承知しました。書籍（ASIN: B0DSKPTJM5）のキャプチャを開始します。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile
```

（キャプチャ実行中...）

キャプチャが完了しました（245ページ）。次にPDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

PDFファイル `B0DSKPTJM5.pdf` を生成しました。カレントディレクトリに保存されています。

---

### 例2: 範囲指定でのキャプチャ

**ユーザー**: この本の位置1000から5000までをPDF化して

**AIアシスタント**: 承知しました。ASINコードを教えてください。

**ユーザー**: B0DSKPTJM5

**AIアシスタント**: 位置1000から5000までの範囲をキャプチャします。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --start 1000 --end 5000
```

（キャプチャ実行中...）

範囲キャプチャが完了しました（82ページ）。PDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

PDFファイル `B0DSKPTJM5.pdf` を生成しました。

---

### 例3: 見開きレイアウトでキャプチャ

**ユーザー**: 見開きでこの本をキャプチャしてください。ASIN: B0DSKPTJM5

**AIアシスタント**: 見開きレイアウトでキャプチャします。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --layout double
```

（キャプチャ実行中...）

見開きキャプチャが完了しました（123ページ）。PDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

PDFファイル `B0DSKPTJM5.pdf` を生成しました。

---

### 例4: モバイル用に軽量化してPDF生成

**ユーザー**: スマホで読みやすいように軽量化してPDF化してください

**AIアシスタント**: モバイル最適化（70%サイズ、品質80）でPDFを生成します。ASINを教えてください。

**ユーザー**: B0DSKPTJM5

**AIアシスタント**: まずスクリーンショットをキャプチャします。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile
```

（キャプチャ実行中...）

キャプチャが完了しました。モバイル最適化してPDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --resize 0.7 --quality 80
```

モバイル最適化PDFファイル `B0DSKPTJM5.pdf` を生成しました。元のサイズの約40%になっています。

---

### 例5: カスタムファイル名でPDF生成

**ユーザー**: この本を「プログラミング入門.pdf」という名前でPDF化して

**AIアシスタント**: 承知しました。ASINを教えてください。

**ユーザー**: B0DSKPTJM5

**AIアシスタント**: キャプチャを開始します。

```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile
```

（キャプチャ実行中...）

キャプチャが完了しました。指定されたファイル名でPDFを生成します。

```bash
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ --output "プログラミング入門.pdf"
```

PDFファイル `プログラミング入門.pdf` を生成しました。

---

## 複雑なシナリオ

### シナリオ1: 複数書籍の一括処理

複数の書籍を連続してPDF化する場合、シェルスクリプトで自動化できます。

**books.txt**（ASINリスト）:
```
B0DSKPTJM5
B0ABC12345
B0XYZ67890
```

**batch_capture.sh**:
```bash
#!/bin/bash

# ASINリストを読み込んで順次処理
while IFS= read -r asin; do
    echo "Processing ASIN: $asin"

    # スクリーンショット取得
    python src/capture.py --asin "$asin" --chrome-profile /tmp/kindle-test-profile

    # PDF生成
    python src/create_pdf.py --input "./kindle-captures/$asin/"

    echo "Completed: $asin"
    echo "---"
done < books.txt

echo "All books processed!"
```

**実行**:
```bash
chmod +x batch_capture.sh
./batch_capture.sh
```

---

### シナリオ2: 中断からの復帰

キャプチャが途中で中断した場合、既にキャプチャ済みのページをスキップして再開する方法。

**問題**: 200ページ中120ページまでキャプチャしたところでエラーが発生

**対処**:

1. metadata.jsonで最後にキャプチャした位置を確認:
```bash
cat ./kindle-captures/B0DSKPTJM5/metadata.json | grep -A 3 '"page_number": 120'
```

出力例:
```json
{
  "page_number": 120,
  "position": 6543,
  ...
}
```

2. その位置から再開:
```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --start 6543
```

3. 2つのディレクトリの画像を結合（必要に応じて）:
```bash
# 一時ディレクトリにコピー
cp ./kindle-captures/B0DSKPTJM5/*.png ./temp-merge/
cp ./kindle-captures/B0DSKPTJM5-resumed/*.png ./temp-merge/

# ファイル名を連番にリネーム
cd temp-merge
ls *.png | sort | awk 'BEGIN{i=1}{printf "mv %s page_%04d.png\n", $0, i++}' | sh

# PDFを生成
python src/create_pdf.py --input ./temp-merge/
```

---

### シナリオ3: ネットワーク遅延への対応

ネットワークが不安定な環境でキャプチャする場合。

**config.yaml を調整**:
```yaml
browser:
  timeout: 60000  # 30秒→60秒に延長

capture:
  wait_strategy: "fixed"  # hybrid→fixedに変更
  wait_timeout: 5.0       # 3.0秒→5.0秒に延長
```

**実行**:
```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --config ./config-slow-network.yaml
```

---

### シナリオ4: 高品質アーカイブ用PDF

将来のアーカイブ用に最高品質でPDFを保存する場合。

```bash
# 1. 通常キャプチャ
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile

# 2. 最高品質でPDF生成（品質95、リサイズなし）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ \
    --output "B0DSKPTJM5_archive.pdf" \
    --quality 95 \
    --resize 1.0
```

---

### シナリオ5: 複数デバイス用に異なるPDFを生成

同じスクリーンショットから、デバイスごとに最適化したPDFを生成する場合。

```bash
# 1. 一度だけスクリーンショット取得
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile

# 2. PC用（高品質）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ \
    --output "B0DSKPTJM5_pc.pdf" \
    --quality 90 \
    --resize 1.0

# 3. タブレット用（標準）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ \
    --output "B0DSKPTJM5_tablet.pdf" \
    --quality 85 \
    --resize 0.8

# 4. スマートフォン用（軽量）
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/ \
    --output "B0DSKPTJM5_mobile.pdf" \
    --quality 75 \
    --resize 0.6
```

---

## エラーシナリオとトラブルシューティング

### エラー1: セッション切れ

**症状**:
```
Error: Session invalid. Please log in to Kindle in Chrome and retry.
```

**原因**: Kindleのログインセッションが切れている

**対処手順**:

1. Google Chromeを開く
2. https://read.amazon.co.jp にアクセス
3. Amazonアカウントでログイン
4. 任意の書籍を開いてKindle Readerが動作することを確認
5. Chromeを閉じる
6. スクリプトを再実行

**予防策**:
- 大量ページのキャプチャ前に、事前にログインし直す
- 50ページごとにセッションチェックが入るため、長時間のキャプチャは避ける

---

### エラー2: Chrome プロファイルロック

**症状**:
```
Error: Failed to launch browser: Chrome profile is locked
```

**原因**: Chromeが既に起動中でプロファイルが使用されている

**対処手順**:

1. 起動中のChromeをすべて終了（macOS: `Cmd+Q`）
2. プロセスが残っていないか確認:
```bash
ps aux | grep Chrome
```
3. プロセスが残っている場合は強制終了:
```bash
pkill -9 "Google Chrome"
```
4. スクリプトを再実行

**予防策**:
- `--chrome-profile /tmp/kindle-test-profile` オプションを使用（推奨）
- ヘッドレスモード（`--headless`）を使用

---

### エラー3: ページ読み込みタイムアウト

**症状**:
- キャプチャが途中で止まる
- 進捗バーが動かない

**原因**:
- ネットワーク速度が遅い
- Kindle Web Readerサーバーの負荷が高い

**対処手順**:

1. ネットワーク接続を確認
2. `config.yaml`の`wait_timeout`を増やす:
```yaml
capture:
  wait_timeout: 5.0  # 3.0から5.0に変更
```
3. スクリプトを再実行

**高度な対処**:

固定待機戦略に変更:
```yaml
capture:
  wait_strategy: "fixed"  # hybridからfixedに変更
  wait_timeout: 5.0
```

---

### エラー4: スクリーンショットが見つからない

**症状**:
```
Error: No screenshots found in ./kindle-captures/B0DSKPTJM5/
```

**原因**:
- capture.pyを実行していない
- ディレクトリパスが間違っている

**対処手順**:

1. キャプチャディレクトリを確認:
```bash
ls -la ./kindle-captures/B0DSKPTJM5/
```

2. ディレクトリが存在しない場合、capture.pyを実行:
```bash
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile
```

3. ディレクトリは存在するがPNGがない場合、capture.pyが正常終了したか確認

---

### エラー5: メモリ不足

**症状**:
- 大量ページ（500ページ以上）のキャプチャ中にスクリプトがクラッシュ
- `MemoryError` が発生

**原因**: 大量の画像データをメモリに保持している

**対処手順**:

1. 範囲を分割してキャプチャ:
```bash
# 前半（0-5000）
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --start 0 --end 5000 --output ./kindle-captures/B0DSKPTJM5-part1/

# 後半（5001-10000）
python src/capture.py --asin B0DSKPTJM5 --chrome-profile /tmp/kindle-test-profile --start 5001 --end 10000 --output ./kindle-captures/B0DSKPTJM5-part2/

# PDFを個別に生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5-part1/ --output part1.pdf
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5-part2/ --output part2.pdf
```

2. 後でPDFを結合（macOS: Preview、Windows: Adobe Acrobat）

---

## よくある質問（FAQ）

### Q1: ページ番号と位置番号の違いは？

**A**: Kindleでは「ページ番号」ではなく「位置番号」を使用します。位置番号は書籍内の絶対的な位置を示す番号で、デバイスやフォントサイズに依存しません。

### Q2: 途中でキャプチャを止めることはできますか？

**A**: はい、`Ctrl+C`でいつでも中断できます。既にキャプチャされたスクリーンショットは保持されます。

### Q3: 同じ書籍を再キャプチャすると上書きされますか？

**A**: はい、デフォルトでは同じASINの場合、既存のディレクトリに上書きされます。保持したい場合は`--output`オプションで別のディレクトリを指定してください。

### Q4: ヘッドレスモードでも正常に動作しますか？

**A**: はい、`--headless`オプションで正常に動作します。ただし、デバッグ時はUIを表示した方が問題を把握しやすいです。

### Q5: PDFのファイルサイズを小さくするには？

**A**: `--resize`と`--quality`オプションを調整してください。例えば`--resize 0.7 --quality 80`で大幅に削減できます。

---

## 関連ドキュメント

- [SKILL.md](SKILL.md) - 基本的な使い方とクイックスタート
- [REFERENCE.md](REFERENCE.md) - 詳細な技術リファレンスとAPI仕様
