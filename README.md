# SQLite Viewer

SQLite Viewer 是一个面向 Windows 的 SQLite 桌面查看器，专门用于**安全、只读地浏览** SQLite 数据库。它适合查看 .db、.sqlite、.sqlite3 等 SQLite 文件中的表、视图、索引和数据，而不会修改源数据库。

## 主要功能

- 以只读模式打开 SQLite 数据库，避免误改原始数据。
- 浏览表、视图和索引，以及字段结构和建表 SQL。
- 分页查看表数据：每页最多显示 100 行。
- 在 SQL 页面执行受限的只读查询：支持 SELECT、EXPLAIN 与少量安全的 PRAGMA 查询。
- 自动拒绝 INSERT、UPDATE、DELETE、DROP、事务、多语句等可能修改数据库的 SQL。
- 查询结果最多显示 1,000 行，避免一次加载过多数据。
- 将当前表页或查询结果导出为 UTF-8 CSV 文件。
- 支持同时打开多个数据库，每个数据库在独立标签页中浏览。
- 支持文件选择、拖放打开和最近打开文件记录。

## 只读安全边界

应用同时在两个层面限制写入：

1. SQLite 连接使用只读 URI 模式打开数据库。
2. SQL 输入会进行白名单校验，只允许安全的只读语句。

因此，导出 CSV、浏览结构和执行查询均不会修改源数据库。对于损坏、截断、缺失或非 SQLite 的文件，应用会显示打开失败信息。

## 普通用户使用说明

### 运行应用

打开发布目录中的 SQLite Viewer.exe，然后通过以下任一方式选择数据库：

- 点击“打开数据库”并选择 SQLite 文件；
- 将数据库文件拖放到应用窗口；
- 从最近打开的文件列表中再次打开。

### 浏览与查询

- 在左侧对象树中选择表、视图或索引。
- 使用 **Data** 页面浏览表数据；可使用上一页、下一页进行翻页。
- 使用 **Structure** 页面查看字段、索引和建表 SQL。
- 使用 **SQL** 页面运行只读查询，例如：

    SELECT * FROM users LIMIT 20;

### 导出 CSV

在数据页面或查询结果页面选择导出功能，指定保存位置即可生成 UTF-8 编码的 CSV 文件。导出仅写入新 CSV 文件，不会修改所打开的数据库。

## 分发给其他人

当前 Windows 发布物采用单目录形式。请将整个 dist\SQLite Viewer\ 文件夹压缩为 ZIP 后发送，而**不要只发送** SQLite Viewer.exe。

目录中的 _internal\ 文件夹包含程序运行所需的 Python、Qt 和其他依赖文件，必须与 EXE 保持相对位置不变。对方解压后双击 SQLite Viewer.exe 即可使用，无需安装 Python。

建议运行环境为 Windows 10 或 Windows 11（x64）。未签名程序首次运行时，Windows 可能显示安全提示；在企业设备上，如被应用白名单策略拦截，需要由设备管理员处理。

## 开发者指南

### 环境要求

- Windows 10/11 x64
- Python 3.12 或更新版本
- PowerShell（示例命令使用 PowerShell）

### 安装依赖

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -e ".[dev]"

也可以使用依赖清单安装运行所需依赖：

    python -m pip install -r requirements.txt

### 启动开发版本

    python -m sqlite_viewer.app

### 运行测试

    python -m pytest --basetemp .pytest-tmp -v

--basetemp .pytest-tmp 用于避免部分 Windows 环境下系统临时目录权限导致的 pytest 问题。

### 构建 Windows 发布包

先确保已安装开发依赖（其中包含 PyInstaller），然后运行：

    python -m PyInstaller --noconfirm sqlite-viewer.spec

构建结果位于：

    dist\SQLite Viewer\SQLite Viewer.exe

这是单目录包；发布时请分发整个 dist\SQLite Viewer\ 目录。

## 项目结构

    src/sqlite_viewer/
    ├── app.py                 # 应用入口
    ├── models/                # 领域模型与错误类型
    ├── services/              # 只读连接、结构读取、查询与导出服务
    ├── workers/               # 后台数据库任务
    └── presentation/          # PySide6 窗口、标签页与视图
    tests/                     # 自动化测试
    sqlite-viewer.spec         # PyInstaller 打包配置

## 设计限制

- 本项目不是 SQLite 编辑器，无法新增、修改或删除数据。
- SQL 编辑器不支持写入语句、事务控制、附加数据库和多语句脚本。
- 单次查询最多返回 1,000 行；表浏览按每页 100 行加载。
- 应用只面向 SQLite 数据库，不支持 MySQL、PostgreSQL 或 SQL Server。
