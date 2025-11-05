Windows/PowerShell 実行メモ

- 一部の Windows/PowerShell 環境では `python` コマンドが正しく動作せず、`Python ` のみ表示されて終了することがあります。
- その場合は Python ランチャー経由で実行してください。

例: 日次パイプラインの実行

```powershell
$env:PYTHONPATH = 'src'
py -3 scripts/run_daily.py --date 2025-10-11
```

例: レポート生成

```powershell
$env:PYTHONPATH = 'src'
py -3 scripts/render_report.py 2025-10-11 2025-10-12
```

