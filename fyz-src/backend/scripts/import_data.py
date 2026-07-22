"""导入 mysql_snapshot.sql 到 MySQL（绕过版本检查）"""
import asyncio
import aiomysql


async def import_snapshot():
    with open("scripts/mysql_snapshot.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    # 按分号分割（跳过字符串内部的）
    statements = []
    current = ""
    in_string = False
    string_char = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        if in_string:
            current += ch
            if ch == "\\" and i + 1 < len(sql):
                i += 1
                current += sql[i]
            elif ch == string_char:
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                current += ch
            elif ch == ";":
                stmt = current.strip()
                if stmt and not stmt.startswith("--"):
                    statements.append(stmt + ";")
                current = ""
            else:
                current += ch
        i += 1

    print(f"共解析 {len(statements)} 条语句")

    conn = await aiomysql.connect(
        host="localhost", port=3306,
        user="root", password="root",
        db="jie_bang", autocommit=False,
    )

    async with conn.cursor() as cur:
        await cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for stmt in statements:
            if stmt.upper().strip().startswith("DELETE"):
                table = stmt.split()[-1].strip(";").strip("`")
                await cur.execute(stmt)
                print(f"  清空 {table}")
            elif stmt.upper().strip().startswith("INSERT"):
                table = stmt.split("INTO")[1].strip().split("(")[0].strip().strip("`")
                await cur.execute(stmt)
                print(f"  导入 {table} -> {cur.rowcount} 行")
        await cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        await conn.commit()

    # 验证
    tables_to_check = [
        ("raw_job_record", "原始岗位"),
        ("skill", "技能"),
        ("job_skill_fact", "岗位-技能关联"),
        ("standard_job", "标准化岗位"),
        ("source_document", "来源文档"),
    ]
    async with conn.cursor() as cur:
        for tbl, label in tables_to_check:
            await cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
            r = await cur.fetchone()
            print(f"  ✅ {label} ({tbl}): {r[0]} 条")

    conn.close()
    print("\n🎉 数据导入完成！")


asyncio.run(import_snapshot())
