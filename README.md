# MD読み書き君

Python 3.12 / PyQt6 製の Markdown エディタです。  
リアルタイムプレビュー・マルチタブ・シンタックスハイライトを備えた、ローカル完結型のデスクトップアプリです。

---

アプリのスナップショット
![alt](https://github.com/AtsushiCafeK/md_yomikakikun/blob/main/shapshot.png?raw=true)


## 機能一覧

### エディタ
- Markdown シンタックスハイライト（見出し・太字・斜体・コード・リンク・画像・YAML front matter）
- Enter キーでリスト行の自動継続（箇条書き・番号付き・タスクリスト）
- 番号付きリストの自動インクリメント
- 空のリスト行で Enter を押すとリストを抜ける
- Tab キーで 4 スペースインデント / Shift+Tab でアンインデント

### リアルタイムプレビュー
- GitHub 風 CSS によるスタイリング
- MathJax によるインライン / ブロック数式レンダリング（`$...$` / `$$...$$`）
- Mermaid によるダイアグラム描画（` ```mermaid ` フェンス）
- Pygments によるコードブロックのシンタックスハイライト
- YAML front matter のパースと非表示
- テキスト入力時はページリロードなしで本文のみ差し替え（ちらつきなし）
- テーマ切替・ダークモード時も背景色を即時反映（白フラッシュなし）
- **表示 → 目次** で目次パネルのON/OFF切り替え可能

### マルチタブ
- 複数ファイルをタブで同時編集
- 未保存タブには「●」マークを表示
- タブを閉じる際に未保存確認ダイアログ
- アプリ終了時に全タブの未保存確認

### 書式設定ツールバー
| ボタン | 機能 | ショートカット |
|---|---|---|
| 本文 / H1〜H6 | 見出しレベル変更 | — |
| **B** | 太字 `**text**` | Ctrl+B |
| *I* | 斜体 `*text*` | Ctrl+I |
| S̶ | 打ち消し線 `~~text~~` | — |
| `` ` `` | インラインコード | — |
| ` ``` ` | コードブロック挿入 | — |
| 🔗 リンク | `[text](url)` 挿入 | Ctrl+K |
| 🖼 画像 | ファイル選択して `![alt](path)` 挿入 | Ctrl+Shift+I |
| • リスト | 箇条書き `- ` 挿入 | — |
| 1. リスト | 番号付きリスト `1. ` 挿入 | — |
| ☑ タスク | タスクリスト `- [ ] ` 挿入 | — |
| > 引用 | 引用 `> ` 挿入 | — |
| ― HR | 水平線 `---` 挿入 | — |
| ⊞ 表 | 3列のテーブルひな形を挿入 | — |

### ファイル操作
- ファイルを開く（Ctrl+O）
- 新規作成（Ctrl+N）
- 上書き保存（Ctrl+S）
- 名前を付けて保存（Ctrl+Shift+S）
- 全タブ保存
- 最近のファイル（最大 20 件）
- **ドラッグ＆ドロップでファイルを開く**（`.md` / `.markdown` / `.txt`）  
  エディタ・プレビュー・ウィンドウのいずれにドロップしても開けます
- 画像ファイルをエディタへドロップすると `![alt](相対パス)` を自動挿入

### エクスポート
- HTML として書き出し（Ctrl+Shift+H）  
  CSS・MathJax・Mermaid をすべて埋め込んだ単一 HTML ファイルを生成
- PDF として書き出し（Ctrl+Shift+X）  
  プレビューの描画内容をそのまま PDF 出力

### 全文検索
- Ctrl+F でプロジェクトフォルダ内の `.md` / `.txt` ファイルを横断検索
- 正規表現・大文字小文字区別オプション
- 検索結果からファイルを該当行で直接開く

### サイドバー（ファイルブラウザ）
- ツリー表示でフォルダを閲覧
- ダブルクリックでファイルをタブで開く
- Ctrl+Shift+E でサイドバーの表示 / 非表示を切り替え

### 自動保存
- 入力が止まってから 2 秒後に自動保存（設定で ON/OFF 可）
- 未保存（新規）ファイルには自動保存は働きません

### 目次
- **表示 → 目次** でプレビュー内の目次パネルをON/OFF切り替え（チェックマーク付き）
- H1〜H3 の見出しから自動生成
- ON/OFFの状態は設定ファイルに保存され、次回起動時に引き継がれる

### スクロール同期
- **表示 → スクロール同期** でON/OFFを切り替え（チェックマーク付き）
- ONにするとエディタのスクロール位置に合わせてプレビューが自動追従
- ON/OFFの状態は設定ファイルに保存され、次回起動時に引き継がれる

### ダークモード
- OS テーマを自動検出（light / dark / system）
- メニューから手動切り替え可
- エディタ・プレビュー・UI すべてに適用

---

## キーボードショートカット一覧

| 操作 | ショートカット |
|---|---|
| 新規 | Ctrl+N |
| 開く | Ctrl+O |
| 保存 | Ctrl+S |
| 名前を付けて保存 | Ctrl+Shift+S |
| HTML 書き出し | Ctrl+Shift+H |
| PDF 書き出し | Ctrl+Shift+X |
| 太字 | Ctrl+B |
| 斜体 | Ctrl+I |
| リンク挿入 | Ctrl+K |
| 画像挿入 | Ctrl+Shift+I |
| 検索 | Ctrl+F |
| プレビュー表示切替 | Ctrl+Shift+P |
| サイドバー表示切替 | Ctrl+Shift+E |
| 設定 | Ctrl+, |
| 終了 | Ctrl+Q |

---

## 設定ファイル

設定は以下の JSON ファイルに保存されます（レジストリは使用しません）。

```
%USERPROFILE%\.md_yomikakikun\settings.json
```

主な設定項目：

| キー | 既定値 | 説明 |
|---|---|---|
| `theme` | `"system"` | `"light"` / `"dark"` / `"system"` |
| `font_family` | `"Consolas"` | エディタフォント |
| `font_size` | `14` | エディタフォントサイズ |
| `auto_save` | `true` | 自動保存の ON/OFF |
| `auto_save_interval` | `2000` | 自動保存までの待機時間（ミリ秒）|
| `sync_scroll` | `false` | スクロール同期の ON/OFF |
| `toc_visible` | `true` | 目次パネルの ON/OFF |
| `recent_files` | `[]` | 最近のファイル一覧（最大 20 件）|

設定の変更は **ツール → 設定** から行えます。  
「最近のファイル履歴を消去」「設定を初期化」も設定画面から実行できます。

---

## 動作環境

- Windows 10 / 11（64 ビット）
- Python 3.12.10 + Poetry（開発時）
- または配布用 exe（`dist/md_yomikakikun.exe`）

### 主な依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| PyQt6 | GUI フレームワーク |
| PyQt6-WebEngine | Chromium ベースのプレビュー表示 |
| markdown + pymdownx | Markdown → HTML 変換・拡張構文 |
| Pygments | コードハイライト |
| PyYAML | YAML front matter パース |

---

## 開発環境のセットアップ

```bash
# リポジトリをクローン後
cd md_yomikakikun

# 依存ライブラリのインストール
poetry install

# アプリの起動
poetry run python main.py
```

## exe のビルド

```bat
build.bat
```

`dist\md_yomikakikun.exe` に単一ファイルの exe が生成されます（約 200MB）。  
初回起動時は一時フォルダへの展開があるため数秒かかります。

## beta版exeダウンロード
[https://github.com/AtsushiCafeK/md_yomikakikun/releases/tag/beta 
](https://github.com/AtsushiCafeK/md_yomikakikun/releases/tag/beta)