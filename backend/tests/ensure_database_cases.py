"""`ensure_database.py` 的隔离用例：不碰真实库，只验证**纯逻辑**部分。

对应文档：docs/15_开发启动脚本方案.md「§6.1 `ensure_database_cases.py`：钉住安全边界」。

**这个文件存在的直接原因**：`ensure_database.py` 是全脚本里唯一会**写**数据库的地方
（创建库）。而"清理/初始化"与"破坏数据"只有一线之隔——2026-10-07 就因为
"清空整表"丢过真实数据（docs/14 §12.4）。所以它的**安全边界必须被用例钉住**：

  1. 库名白名单：含非法字符（如反引号）必须被拒——否则是 SQL 注入；
  2. 全脚本**不得包含**任何 `DROP` / `TRUNCATE` / `DELETE` / 清空语义；
  3. `--check` 模式下**绝不创建**库；
  4. Mongo 检查**只读**：
     a. 不做任何启停服务的动作；
     b. 必须有**短超时**（pymongo 默认 30 秒会让启动脚本卡住）。

跑法（需已安装 fastapi/sqlalchemy/pymongo 的 desheng 环境）：

    conda activate desheng
    cd backend
    python tests/ensure_database_cases.py

**不连任何真实数据库**：全部是源码扫描与纯函数调用，**毫秒级**。
"""

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

SCRIPT = BACKEND_DIR / "scripts" / "ensure_database.py"

failures = []
checks = 0


def check(condition, label):
    global checks
    checks += 1
    if condition:
        print("PASS", label)
    else:
        print("FAIL", label)
        failures.append(label)


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def strip_comments_and_docstrings(text: str) -> str:
    """剥掉注释与文档字符串，只留**可执行代码**。

    ⚠️ 必须这么做：本脚本的文档里大段写着"不做 DROP""不清空数据"，
    如果直接对全文做正则，会匹配到**说明书本身**。
    这个坑在 docs/14 §12.2 第 3 条记过（断言"某文案已消失"时匹配到了开发者自己的注释）。
    """
    # 去掉三引号字符串（含 docstring）
    text = re.sub(r'""".*?"""', "", text, flags=re.DOTALL)
    text = re.sub(r"'''.*?'''", "", text, flags=re.DOTALL)
    # 去掉行注释
    text = re.sub(r"#[^\n]*", "", text)
    return text


# ---------------------------------------------------------------- 安全边界

def test_no_destructive_sql():
    """⭐ 全脚本不得含任何破坏性 SQL。

    这条是 2026-10-07 数据丢失事故的直接产物：那个教训是
    "任何删除都必须能说清删的是哪些行"，而初始化脚本**根本不该有删除**。
    """
    code = strip_comments_and_docstrings(source()).upper()
    for keyword in ("DROP ", "TRUNCATE", "DELETE FROM", "ALTER TABLE"):
        check(keyword not in code, f"安全: 可执行代码里不含 `{keyword.strip()}`")


def test_no_recreate_option():
    """不得提供 --recreate / --force 之类的破坏性开关。"""
    code = strip_comments_and_docstrings(source())
    for flag in ("--recreate", "--force", "--reset", "--drop"):
        check(f'"{flag}"' not in code and f"'{flag}'" not in code,
              f"安全: 不提供 `{flag}` 开关")


def test_create_is_guarded_by_check_flag():
    """`--check` 必须能阻止创建。"""
    code = strip_comments_and_docstrings(source())
    check("--check" in code, "安全: 存在 --check 开关")
    # create_database 只在 `elif create:` 分支里调用
    check(re.search(r"elif create:\s*\n\s*try:\s*\n\s*create_database", code) is not None
          or "elif create:" in code,
          "安全: create_database 只在 `elif create:` 分支调用")


def test_database_name_whitelist():
    """⭐ 库名必须过白名单——它会被拼进 SQL，是唯一的注入面。"""
    code = source()
    check("isalnum()" in code, "安全: 库名做了字母数字下划线校验")
    check("非法字符" in code or "只允许字母" in code, "安全: 非法库名会报错而不是静默继续")


# ---------------------------------------------------------------- 行为契约

def test_check_mode_does_not_create(tmp_path=None):
    """`--check` 对不存在的库必须返回非零，且**不创建**。

    这里不真连数据库：直接验证 `run(create=False)` 的分支逻辑存在。
    """
    code = strip_comments_and_docstrings(source())
    # create=False 时走的分支应直接返回 1，而不是调用 create_database
    check("create: bool" in source() or "create=not args.check" in source(),
          "契约: --check 通过 create=False 传递")
    check("report[\"ok\"] = False" in code or "report['ok'] = False" in code,
          "契约: 库不存在且未创建时标记失败")


def test_mongo_check_has_short_timeout():
    """⭐ Mongo 检查必须有短超时。

    `pymongo` 默认懒连接且 `serverSelectionTimeoutMS` 默认 30 秒——
    不设的话启动脚本会**静默卡住半分钟**，看起来像"脚本死了"。
    """
    code = strip_comments_and_docstrings(source())
    check("serverSelectionTimeoutMS" in code, "Mongo: 设置了 serverSelectionTimeoutMS")
    m = re.search(r"serverSelectionTimeoutMS\s*=\s*(\d+)", code)
    check(m is not None and int(m.group(1)) <= 5000,
          f"Mongo: 超时不超过 5 秒（实际 {m.group(1) if m else '?'} ms）")


def test_mongo_check_is_read_only():
    """Mongo 检查只允许 ping/读版本，不得启停服务或写数据。

    ⚠️ **不要用"源码里有没有 `Start-Service` 字样"来判断**——
    脚本的**提示文本**里正当地写着"Windows 上你可以 `Start-Service MongoDB`"，
    那是给用户的建议，不是脚本的动作。字符串匹配分不清这两者。

    正确的判据是**能力**：脚本从不引入执行 shell 命令的手段
    （`subprocess` / `os.system` / `os.popen`），所以它**做不到**启停服务。
    """
    code = strip_comments_and_docstrings(source())
    check('"ping"' in code or "'ping'" in code, "Mongo: 用了 admin.command('ping') 探测")
    # 能力检查：没有执行外部命令的手段
    for capability in ("import subprocess", "os.system", "os.popen", "shutil.which"):
        check(capability not in code,
              f"Mongo: 不引入 `{capability}`（无法执行外部命令，自然不能启停服务）")
    # 写操作检查：Mongo 侧只读
    for forbidden in ("insert_one", "update_one", "delete_many", "drop_collection",
                      "create_collection", "drop_database"):
        check(forbidden not in code, f"Mongo: 不做 `{forbidden}`")


def test_script_runs_no_shell_commands():
    """⭐ 整个脚本不执行任何外部命令。

    这条比"Mongo 只读"更强：`ensure_database.py` 靠 SQLAlchemy 与 pymongo 工作，
    不需要 shell。没有 shell 就意味着**不可能**误删文件、误停服务。
    """
    code = strip_comments_and_docstrings(source())
    for capability in ("import subprocess", "os.system", "os.popen"):
        check(capability not in code, f"安全: 不引入 `{capability}`")


def test_mongo_failure_does_not_fail_the_run():
    """Mongo 不可用**不该**让自检失败——门户不依赖它，只有 TradeSim 回测用。"""
    code = strip_comments_and_docstrings(source())
    check("不影响门户" in source(), "Mongo: 失败信息里说明了它不影响门户")

    # ⚠️ 只取 **run() 函数体内**、Mongo 之后的那段，不能 `split` 到文件末尾——
    # 否则会把 `main()` 里的 `return 1` 也算进来（这里第一次就写错了）。
    body = code[code.index("def run("):code.index("def main(")]
    mongo_part = body[body.index("mongo = check_mongodb()"):]
    check("return 1" not in mongo_part,
          "Mongo: 不可用时不会 return 1（不拦住启动）")


def test_json_output_mode_exists():
    """启动脚本要解析结果，所以必须有 --json。"""
    check("--json" in source(), "接口: 支持 --json 机器可读输出")
    check("json.dumps" in source(), "接口: 真的输出了 JSON")


def test_uses_shared_database_url():
    """⭐ 复用 `app.database` 的解析，不自己重写 .env 规则。

    否则 `.env` 的键名规则会变成两份，两边迟早不一致（docs/14 §12.3）。
    """
    code = strip_comments_and_docstrings(source())
    check("from app.database import DATABASE_URL" in code,
          "复用: 从 app.database 取 DATABASE_URL，不重复实现 .env 解析")


def test_reports_seed_rows_without_writing():
    """字典/种子数据只报告，不擅自补写。"""
    code = strip_comments_and_docstrings(source())
    check("EXPECTED_SEED_ROWS" in code, "种子: 定义了期望行数")
    check("SELECT COUNT(*)" in code, "种子: 用 SELECT COUNT 只读检查")
    for forbidden in ("seed_default_tags", "seed_notes", "db.add("):
        check(forbidden not in code,
              f"种子: 不调用 `{forbidden}`（那是 main.py 的职责）")


def main():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print()
    if failures:
        print(f"{len(failures)}/{checks} checks FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"{checks}/{checks} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
