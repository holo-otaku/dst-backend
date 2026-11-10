"""把 MySQL 的資料搬到空的 PostgreSQL。

用法（在 backend/ 底下）:
    MYSQL_URI=mysql+pymysql://user:pw@host:3306/dst \\
    PG_URI=postgresql+psycopg://user:pw@host:5432/dst \\
    uv run python -m scripts.mysql_to_postgres

步驟：檢查兩邊欄位一致 → 依 model 建表 → 依外鍵順序分批複製 → 重設 id 序列
→ 寫入 alembic 版本 → 比對每張表筆數。目標庫必須是空的，任何不一致都會中止。

MySQL 沒有建外鍵約束，PG 有，所以指向不存在資料的孤兒列要處理：
series.created_by 改指 admin（使用者被刪掉但系列要留著），其他孤兒列略過。兩者都會印出來。
"""
import os
import sys

from sqlalchemy import create_engine, inspect, text

from models import model  # noqa: F401
from models.series import Series
from models.shared import db

BATCH_SIZE = 5000


def check_columns(mysql):
    """model 和 MySQL 的欄位不一致時，複製會漏資料或失敗，先擋下來。"""
    inspector = inspect(mysql)
    errors = []
    for table in db.metadata.sorted_tables:
        actual = {column["name"] for column in inspector.get_columns(table.name)}
        expected = set(table.columns.keys())
        if actual != expected:
            errors.append(f"{table.name}: 只在 MySQL {sorted(actual - expected)}，只在 model {sorted(expected - actual)}")
    return errors


def copy_table(table, mysql, pg, admin_id):
    """回傳略過的孤兒列數。"""
    # 依外鍵順序複製，父表已在 PG 裡，用它的 id 判斷孤兒
    valid_ids = {}
    with pg.connect() as conn:
        for fk in table.foreign_keys:
            valid_ids[fk] = set(conn.execute(text(
                f"SELECT {fk.column.name} FROM {fk.column.table.name}")).scalars())

    skipped = 0
    # 用 model 的 Table 讀寫，tinyint → boolean、JSON 等型別由 SQLAlchemy 轉換
    with mysql.connect() as source, pg.begin() as target:
        result = source.execution_options(stream_results=True).execute(table.select())
        while rows := result.mappings().fetchmany(BATCH_SIZE):
            batch = []
            for row in map(dict, rows):
                for fk, ids in valid_ids.items():
                    column = fk.parent.name
                    if row[column] is None or row[column] in ids:
                        continue
                    if fk.parent is Series.__table__.c.created_by:
                        print(f"  series {row['id']}: created_by {row[column]} 不存在，改為 admin ({admin_id})")
                        row[column] = admin_id
                    else:
                        print(f"  略過 {table.name} {row}: {column}={row[column]} 不存在")
                        skipped += 1
                        break
                else:
                    batch.append(row)
            if batch:
                target.execute(table.insert(), batch)
    return skipped


def reset_sequence(table, pg):
    # 直接寫入 id 不會推進序列，不重設的話新資料會撞主鍵
    if "id" not in table.columns or not table.c.id.autoincrement:
        return
    with pg.begin() as conn:
        conn.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'),"
            f" COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"
        ))


def count(engine, table_name):
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()


def main():
    mysql = create_engine(os.environ["MYSQL_URI"])
    pg = create_engine(os.environ["PG_URI"])

    if inspect(pg).get_table_names():
        sys.exit("目標 PostgreSQL 不是空的，中止")
    errors = check_columns(mysql)
    if errors:
        sys.exit("欄位不一致，中止：\n" + "\n".join(errors))

    with mysql.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        admin_id = conn.execute(text("SELECT id FROM users WHERE username = 'admin'")).scalar()
    if admin_id is None:
        sys.exit("MySQL 裡找不到 admin 使用者，中止")

    db.metadata.create_all(pg)
    skipped = {}
    for table in db.metadata.sorted_tables:
        print(f"複製 {table.name} ...", flush=True)
        skipped[table.name] = copy_table(table, mysql, pg, admin_id)
        reset_sequence(table, pg)

    with pg.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": version})

    mismatched = []
    for table in db.metadata.sorted_tables:
        source, target = count(mysql, table.name), count(pg, table.name)
        print(f"{table.name}: MySQL {source} / PostgreSQL {target} / 略過 {skipped[table.name]}")
        if source - skipped[table.name] != target:
            mismatched.append(table.name)
    if mismatched:
        sys.exit(f"筆數不一致：{mismatched}")
    print(f"完成，alembic 版本 {version}")


if __name__ == "__main__":
    main()
