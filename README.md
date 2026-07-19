# SQLite Viewer

一个面向 Windows 的只读 SQLite 桌面查看器。

## 开发环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -v
python -m sqlite_viewer.app
```

打包 Windows 可执行程序：

```powershell
pyinstaller sqlite-viewer.spec
```

应用仅允许读取 SQLite 文件；写入 SQL 在应用层和 SQLite 连接层均会被拒绝。

查询结果最多保留 1,000 行；表数据按每页 100 行加载。当前表页或查询结果可导出为 UTF-8 CSV，导出操作不会修改源数据库。
