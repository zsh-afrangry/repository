"""导出 MySQL 表结构到 `backend/sql/`，让表结构随 git 提交。

对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§3.2 表结构管理」。

**为什么需要这个脚本**（用户 2026-10-06 决定）

项目刻意不用 Alembic，靠 `Base.metadata.create_all()` 建表。但 `create_all()`
**只创建缺失的表，不会 ALTER 已有表**——所以一旦改了模型（例如新增
`completed_at` 列、把 `tone` 从四值收敛为两值），别的机器上不会自动生效，
只能靠人记得手动执行 SQL。把结构导出进版本控制后：

1. 换机器时可据此重建/核对，不再依赖"记得执行某条 SQL"；
2. 可随时比对"代码模型 vs 真实库"是否漂移；
3. 审阅改动时能在 diff 里看到结构变化。

**产物**
    backend/sql/knowledgemap.sql    全库结构（--no-data，不含任何业务数据）

**用法**
    python backend/scripts/export_schema.py            # 导出
    python backend/scripts/export_schema.py --check    # 只比对，不写文件（CI/验收用）

只读**业务数据**（`--no-data`），但会**覆盖** `backend/sql/*.sql` 这一个文件。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SQL_DIR = BACKEND_DIR / "sql"
TARGET = SQL_DIR / "knowledgemap.sql"

# mysqldump 可执行文件。允许用 KM_MYSQLDUMP 覆盖（例如 Linux 上就是 `mysqldump`）。
DEFAULT_MYSQLDUMP = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

OK_MARK = "[OK]"
FAIL_MARK = "[!!]"

# 这些行每次导出都会变，但**不代表结构变化**，留着会让 diff 充满噪声：
#   - AUTO_INCREMENT=N 是"当前计数器"，随插入数据而变；
#   - 导出时间戳与主机信息同理。
# 把它们抹平，这样 git diff 只在**真正的结构变化**时才有内容。
_NOISE_PATTERNS = (
    (re.compile(r"^/\*!40101 SET .*?\*/;$", re.MULTILINE), ""),
    (re.compile(r"^/\*!40014 SET .*?\*/;$", re.MULTILINE), ""),
    (re.compile(r"^/\*!40103 SET .*?\*/;$", re.MULTILINE), ""),
    (re.compile(r"^/\*!50003 SET .*?\*/;$", re.MULTILINE), ""),
    (re.compile(r" AUTO_INCREMENT=\d+"), ""),
    (re.compile(r"^-- Dump completed.*$", re.MULTILINE), ""),
    (re.compile(r"^-- Host:.*$", re.MULTILINE), ""),
)


def load_db_settings() -> dict:
    """从 `backend/.env` 读连接配置，与 `app/database.py` 保持同一套键名。

    刻意不在这里 import `app.database`：那个模块会 `load_dotenv` 并建 engine，
    而导出脚本只需要连接参数，不该依赖运行中的应用代码。
    """
    env_path = BACKEND_DIR / ".env"
    settings: dict[str, str] = {}
    if env_path.exists():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            settings[key.strip()] = value.strip().strip('"').strip("'")

    return {
        "user": settings.get("MySQL_USER", "root"),
        "password": settings.get("MySQL_PASSWORD", "root"),
        "host": settings.get("MySQL_HOST", "127.0.0.1"),
        "port": settings.get("MySQL_PORT", "3306"),
        "database": settings.get("MySQL_DATABASE", "knowledgemap"),
    }


def dump_schema(settings: dict) -> str:
    """跑 mysqldump --no-data，返回**原始** SQL 文本（未清洗）。

    刻意不做 `_sanitize`：清洗与加文件头是 `render_schema` 的职责，
    这样 `--check` 与正常导出共用同一条渲染路径，不会出现两边不一致。
    """
    binary = os.getenv("KM_MYSQLDUMP", DEFAULT_MYSQLDUMP)
    if not Path(binary).exists() and not binary.endswith(("mysqldump", "mysqldump.exe")):
        raise RuntimeError(f"找不到 mysqldump: {binary}（可用 KM_MYSQLDUMP 指定）")

    args = [
        binary,
        f"--host={settings['host']}",
        f"--port={settings['port']}",
        f"--user={settings['user']}",
        f"--password={settings['password']}",
        "--no-data",              # 只要结构，不要业务数据
        "--skip-comments",        # 去掉 mysqldump 自带的说明块
        "--no-tablespaces",       # 避免需要 PROCESS 权限
        "--default-character-set=utf8mb4",
        "--set-gtid-purged=OFF",  # 避免带上 GTID 状态
        settings["database"],
    ]
    try:
        result = subprocess.run(args, capture_output=True, check=True, text=True,
                                encoding="utf-8", errors="replace", timeout=60)
    except subprocess.CalledProcessError as error:
        # 注意：不要把 stderr 原样抛出——它可能含密码提示。
        raise RuntimeError(f"mysqldump 失败（退出码 {error.returncode}）") from error
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"无法执行 mysqldump: {error}") from error

    return result.stdout


def _sanitize(sql: str, source_label: str) -> str:
    """抹平与结构无关的噪声，并加上文件头。

    `source_label` 由调用方传入（例如 `127.0.0.1:3306/knowledgemap`），
    而不是在函数里读全局——否则导出内容的生成就依赖了模块级可变状态。
    """
    for pattern, replacement in _NOISE_PATTERNS:
        sql = pattern.sub(replacement, sql)

    # 压缩连续空行，避免 diff 里大段空白
    sql = re.sub(r"\n{3,}", "\n\n", sql).strip()

    header = f"""-- KnowledgeMap 表结构（自动生成，请勿手工编辑）
--
-- 生成方式：python backend/scripts/export_schema.py
-- 来源库：  {source_label}
--
-- ⚠️ 本文件由脚本覆盖，手工修改会在下次导出时丢失。
-- ⚠️ 含 DROP TABLE IF EXISTS，**不要**直接对生产库执行；它用于重建空库或核对结构漂移。
--
-- 表结构的权威来源是 `backend/app/models/` 下的 SQLAlchemy 模型
-- （项目刻意不使用 Alembic，决定见 docs/3 §13）。本文件是它的导出快照。
--
-- 已抹平 AUTO_INCREMENT 计数等噪声，使 git diff 只反映真实结构变化。

"""
    return header + sql + "\n"


def render_schema(settings: dict) -> str:
    """导出并渲染成最终写入文件的文本。`--check` 与正常导出共用这一条路径。"""
    source_label = f"{settings['host']}:{settings['port']}/{settings['database']}"
    return _sanitize(dump_schema(settings), source_label)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="只与现有文件比对，不写入。有差异时退出码 1")
    args = parser.parse_args()

    settings = load_db_settings()
    source_label = f"{settings['host']}:{settings['port']}/{settings['database']}"

    print(f"mysqldump: {os.getenv('KM_MYSQLDUMP', DEFAULT_MYSQLDUMP)}")
    print(f"来源库:    {source_label}")
    print(f"目标文件:  {TARGET}")
    print()

    rendered = render_schema(settings)

    if args.check:
        if not TARGET.exists():
            print(f"{FAIL_MARK} 目标文件不存在，先跑一次不带 --check 的导出")
            return 1
        current = TARGET.read_text(encoding="utf-8")
        if current == rendered:
            print(f"{OK_MARK} 结构一致，无漂移")
            return 0
        print(f"{FAIL_MARK} 结构有漂移（真实库与 {TARGET.name} 不一致）")
        print("     跑 `python backend/scripts/export_schema.py` 更新后再提交")
        return 1

    SQL_DIR.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(rendered, encoding="utf-8", newline="\n")
    lines = rendered.count("\n") + 1
    print(f"{OK_MARK} 已写入 {TARGET}（{lines} 行）")
    tables = re.findall(r"^CREATE TABLE `(\w+)`", rendered, re.MULTILINE)
    print(f"     含 {len(tables)} 张表: {', '.join(tables)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
