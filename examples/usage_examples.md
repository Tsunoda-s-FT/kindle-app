# Kindle Capture - 使用例

このドキュメントでは、Kindle Captureツールの実践的な使用例を紹介します。

## 基本的な使用例

### 例1: シンプルな全ページキャプチャ

最もシンプルな使い方です。書籍全体をキャプチャしてPDFを生成します。

```bash
# ステップ1: スクリーンショット取得
python src/capture.py --asin B0DSKPTJM5

# ステップ2: PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

**出力**:
- `kindle-captures/B0DSKPTJM5/` にスクリーンショット
- カレントディレクトリに `B0DSKPTJM5.pdf`

---

### 例2: 見開きレイアウトでキャプチャ

見開き（2カラム）レイアウトでキャプチャします。

```bash
# 見開きでキャプチャ
python src/capture.py --asin B0DSKPTJM5 --layout double

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

**用途**:
- 雑誌や大判書籍
- 見開きで読みたい場合

---

### 例3: カスタムファイル名でPDF生成

わかりやすいファイル名でPDFを保存します。

```bash
# キャプチャ
python src/capture.py --asin B0DSKPTJM5

# わかりやすい名前でPDF生成
python src/create_pdf.py \
  --input ./kindle-captures/B0DSKPTJM5/ \
  --output "Git_GitHub入門.pdf"
```

**出力**:
- `Git_GitHub入門.pdf`

---

## 部分キャプチャ

### 例4: 特定の章だけキャプチャ

本の一部だけをキャプチャします。

```bash
# Location 5000から10000までキャプチャ
python src/capture.py \
  --asin B0DSKPTJM5 \
  --start 5000 \
  --end 10000

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

**用途**:
- 特定の章だけPDF化したい
- テスト用に少量キャプチャしたい
- 容量を節約したい

---

### 例5: テスト用少量キャプチャ

動作確認のため、最初の数ページだけキャプチャします。

```bash
# 最初から位置1000までキャプチャ（約10ページ程度）
python src/capture.py --asin B0DSKPTJM5 --end 1000

# PDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

**用途**:
- 設定が正しいか確認
- レイアウトの見た目を確認
- 処理時間の目安を把握

---

## PDF最適化

### 例6: モバイル用に最適化

スマートフォンやタブレットで読むために、ファイルサイズを小さくします。

```bash
# 通常通りキャプチャ
python src/capture.py --asin B0DSKPTJM5

# 70%にリサイズ、品質80で圧縮
python src/create_pdf.py \
  --input ./kindle-captures/B0DSKPTJM5/ \
  --resize 0.7 \
  --quality 80 \
  --output "Git_GitHub入門_mobile.pdf"
```

**効果**:
- ファイルサイズが約50%削減
- モバイル端末での読み込みが高速化
- 画質はほぼ変わらない

---

### 例7: 高品質PDF（オリジナルサイズ）

画質を最優先にします。

```bash
# キャプチャ
python src/capture.py --asin B0DSKPTJM5

# リサイズなし、高品質で生成
python src/create_pdf.py \
  --input ./kindle-captures/B0DSKPTJM5/ \
  --resize 1.0 \
  --output "Git_GitHub入門_high_quality.pdf"
```

**用途**:
- 図表が多い技術書
- 画質重視の書籍
- アーカイブ用

---

### 例8: 超圧縮PDF

とにかくファイルサイズを小さくしたい場合。

```bash
# キャプチャ
python src/capture.py --asin B0DSKPTJM5

# 50%にリサイズ、品質70
python src/create_pdf.py \
  --input ./kindle-captures/B0DSKPTJM5/ \
  --resize 0.5 \
  --quality 70 \
  --output "Git_GitHub入門_compressed.pdf"
```

**注意**:
- 画質が劣化する可能性あり
- 小さい文字が読みにくくなる場合あり

---

## カスタム出力先

### 例9: カスタムディレクトリに保存

スクリーンショットとPDFを任意の場所に保存します。

```bash
# カスタムディレクトリにキャプチャ
python src/capture.py \
  --asin B0DSKPTJM5 \
  --output ~/Documents/Books/Git入門/

# そのディレクトリからPDF生成
python src/create_pdf.py \
  --input ~/Documents/Books/Git入門/ \
  --output ~/Documents/Books/Git入門.pdf
```

**用途**:
- プロジェクトごとに整理
- 外部ストレージに保存
- バックアップ

---

## 複数の書籍を連続処理

### 例10: 複数の書籍を順次キャプチャ

```bash
#!/bin/bash
# capture_multiple.sh

BOOKS=(
  "B0DSKPTJM5"  # Git入門
  "B08XYZ1234"  # React入門
  "B09ABC5678"  # Python入門
)

for ASIN in "${BOOKS[@]}"; do
  echo "Capturing: $ASIN"
  python src/capture.py --asin "$ASIN"
  python src/create_pdf.py --input "./kindle-captures/$ASIN/"
  echo "Completed: $ASIN"
  echo "---"
done
```

使い方:
```bash
chmod +x capture_multiple.sh
./capture_multiple.sh
```

---

## トラブル時の対処例

### 例11: ネットワークが遅い環境での設定

config.yamlを編集:

```yaml
capture:
  wait_strategy: "fixed"  # 固定待機に変更
  wait_timeout: 5.0  # 5秒に延長
```

そして実行:
```bash
python src/capture.py --asin B0DSKPTJM5
```

---

### 例12: 途中で失敗した場合の再開

```bash
# 失敗した位置を確認
# metadata.jsonの最後のページを確認

# 例: 5000で失敗した場合、5000から再開
python src/capture.py \
  --asin B0DSKPTJM5 \
  --start 5000

# 完了後、すべてのスクリーンショットからPDF生成
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

---

## Claude Codeからの使用例

### 例13: Claude Codeで自然言語から実行

**ユーザー**: 「Git&GitHubの本（ASIN: B0DSKPTJM5）をPDF化して」

**Claude Codeの実行内容**:
1. ASINを確認
2. `python src/capture.py --asin B0DSKPTJM5`を実行
3. 完了を待つ
4. `python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/`を実行
5. PDFのパスを報告

---

### 例14: レイアウト指定

**ユーザー**: 「見開きレイアウトでこの本をキャプチャして」

**Claude Codeの実行内容**:
```bash
python src/capture.py --asin B0DSKPTJM5 --layout double
python src/create_pdf.py --input ./kindle-captures/B0DSKPTJM5/
```

---

### 例15: モバイル最適化

**ユーザー**: 「スマホで読みやすいように軽いPDFにして」

**Claude Codeの実行内容**:
```bash
python src/capture.py --asin B0DSKPTJM5
python src/create_pdf.py \
  --input ./kindle-captures/B0DSKPTJM5/ \
  --resize 0.7 \
  --quality 80
```

---

## よくある組み合わせ

### パターンA: 技術書（高品質）

```bash
python src/capture.py --asin <ASIN> --layout single
python src/create_pdf.py --input ./kindle-captures/<ASIN>/ --resize 1.0
```

### パターンB: 小説（標準品質）

```bash
python src/capture.py --asin <ASIN>
python src/create_pdf.py --input ./kindle-captures/<ASIN>/
```

### パターンC: 雑誌（見開き・高品質）

```bash
python src/capture.py --asin <ASIN> --layout double
python src/create_pdf.py --input ./kindle-captures/<ASIN>/ --resize 1.0
```

### パターンD: 参考資料（部分・モバイル）

```bash
python src/capture.py --asin <ASIN> --start 5000 --end 10000
python src/create_pdf.py \
  --input ./kindle-captures/<ASIN>/ \
  --resize 0.7 \
  --quality 80
```

---

## ベストプラクティス

1. **最初はテストキャプチャ**
   ```bash
   python src/capture.py --asin <ASIN> --end 1000
   ```
   動作確認してから全ページキャプチャ

2. **メタデータを確認**
   ```bash
   cat ./kindle-captures/<ASIN>/metadata.json
   ```
   キャプチャ情報を確認

3. **段階的な品質調整**
   - まず標準設定でPDF生成
   - ファイルサイズが大きければリサイズ
   - 画質が悪ければ品質を上げる

4. **定期的なバックアップ**
   ```bash
   cp -r ./kindle-captures ~/Backup/
   ```

---

## まとめ

Kindle Captureツールは柔軟なオプションで様々なニーズに対応できます。

**基本**: capture.py → create_pdf.py
**最適化**: --resize と --quality で調整
**部分**: --start と --end で範囲指定

詳細は [README.md](../README.md) と [SKILL.md](../SKILL.md) を参照してください。
