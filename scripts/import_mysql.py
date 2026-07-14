# -*- coding: utf-8 -*-
"""
将 merged_jobs_iflytek.json 导入 MySQL jiebang_db 数据库

表结构: iflytek_jobs（含原始字段 + parsed 解析 + 标准化字段）
"""

import pymysql
import csv
import os

# ============================================================
# 1. 数据库连接（按需修改）
# ============================================================
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'root123',
    'database': 'jiebang_db',
    'charset': 'utf8mb4'
}

conn = pymysql.connect(**DB_CONFIG)
cursor = conn.cursor()
print("✅ 连接数据库成功")


def _format_time(time_str):
    """标准化时间字符串"""
    if not time_str:
        return None
    time_str = str(time_str).replace('T', ' ').split('+')[0].split('Z')[0].strip()
    return time_str if time_str else None


def _int_or_none(val):
    """转整数，空字符串返回 None"""
    if val is None or val == '' or val == 'None':
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _float_or_none(val):
    """转浮点数，空字符串返回 None"""
    if val is None or val == '' or val == 'None':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

# ============================================================
# 2. 创建表
# ============================================================
create_table_sql = """
CREATE TABLE IF NOT EXISTS iflytek_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- 14个标准字段
    `title` VARCHAR(300) DEFAULT NULL COMMENT '原始职位名称',
    `company` VARCHAR(200) DEFAULT NULL COMMENT '公司名称',
    `city` VARCHAR(200) DEFAULT NULL COMMENT '工作城市',
    `salary` VARCHAR(100) DEFAULT NULL COMMENT '原始薪资文本',
    `experience` VARCHAR(100) DEFAULT NULL COMMENT '原始经验要求文本',
    `education` VARCHAR(100) DEFAULT NULL COMMENT '原始学历要求文本',
    `jd_text` TEXT DEFAULT NULL COMMENT '完整职位描述',
    `responsibilities` TEXT DEFAULT NULL COMMENT '岗位职责',
    `requirements` TEXT DEFAULT NULL COMMENT '任职要求',
    `keywords` VARCHAR(500) DEFAULT NULL COMMENT '关键词标签',
    `posted_at` DATETIME DEFAULT NULL COMMENT '发布时间',
    `url` VARCHAR(500) DEFAULT NULL COMMENT '原始链接',
    `source` VARCHAR(100) DEFAULT NULL COMMENT '来源标识',
    `crawled_at` VARCHAR(50) DEFAULT NULL COMMENT '爬取时间',

    -- 来源标签
    `source_tag` VARCHAR(20) DEFAULT NULL COMMENT '标准化来源标签',

    -- 结构化解析结果
    `parsed_salary_min` INT DEFAULT NULL COMMENT '解析薪资下限',
    `parsed_salary_max` INT DEFAULT NULL COMMENT '解析薪资上限',
    `parsed_experience_min` INT DEFAULT NULL COMMENT '解析经验下限(年)',
    `parsed_experience_max` INT DEFAULT NULL COMMENT '解析经验上限(年)',
    `parsed_education` VARCHAR(30) DEFAULT NULL COMMENT '解析学历标签',

    -- 质量评分
    `quality` FLOAT DEFAULT NULL COMMENT '字段完整率0~1',

    -- Step 2 标准化字段
    `standardized_title` VARCHAR(200) DEFAULT NULL COMMENT '标准化岗位名称',
    `canonical_key` VARCHAR(100) DEFAULT NULL COMMENT '规范键',
    `level` VARCHAR(20) DEFAULT NULL COMMENT '级别(junior/mid/senior)',
    `stack` VARCHAR(30) DEFAULT NULL COMMENT '技术方向',
    `title_confidence` FLOAT DEFAULT NULL COMMENT '标准化置信度0~1',

    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_canonical_key (`canonical_key`),
    INDEX idx_level (`level`),
    INDEX idx_stack (`stack`),
    INDEX idx_source_tag (`source_tag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

cursor.execute("DROP TABLE IF EXISTS iflytek_jobs")
cursor.execute(create_table_sql)
print("✅ 表 iflytek_jobs 创建成功")

# ============================================================
# 3. 读取 CSV 并导入
# ============================================================
csv_path = os.path.join('outputs', 'merged_jobs_iflytek.csv')
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"✅ 读取 CSV: {len(rows)} 条记录, {len(rows[0])} 个字段")

insert_sql = """
INSERT INTO iflytek_jobs (
    title, company, city, salary, experience, education,
    jd_text, responsibilities, requirements, keywords,
    posted_at, url, source, crawled_at,
    source_tag,
    parsed_salary_min, parsed_salary_max,
    parsed_experience_min, parsed_experience_max,
    parsed_education,
    quality,
    standardized_title, canonical_key, level, stack, title_confidence
) VALUES (
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s,
    %s, %s,
    %s, %s,
    %s,
    %s,
    %s, %s, %s, %s, %s
)
"""

imported = 0
errors = 0
batch = []
BATCH_SIZE = 50

for row in rows:
    values = (
        row.get('title') or None,
        row.get('company') or None,
        row.get('city') or None,
        row.get('salary') or None,
        row.get('experience') or None,
        row.get('education') or None,
        row.get('jd_text') or None,
        row.get('responsibilities') or None,
        row.get('requirements') or None,
        row.get('keywords') or None,
        _format_time(row.get('posted_at')),
        row.get('url') or None,
        row.get('source') or None,
        row.get('crawled_at') or None,
        row.get('source_tag') or None,
        _int_or_none(row.get('parsed_salary_min')),
        _int_or_none(row.get('parsed_salary_max')),
        _int_or_none(row.get('parsed_experience_min')),
        _int_or_none(row.get('parsed_experience_max')),
        row.get('parsed_education') or None,
        _float_or_none(row.get('quality')),
        row.get('standardized_title') or None,
        row.get('canonical_key') or None,
        row.get('level') or None,
        row.get('stack') or None,
        _float_or_none(row.get('title_confidence')),
    )

    batch.append(values)

    if len(batch) >= BATCH_SIZE:
        try:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            imported += len(batch)
            print(f"  已导入 {imported}/{len(rows)} 条...")
        except Exception as e:
            print(f"  ❌ 导入失败: {e}")
            conn.rollback()
            errors += len(batch)
        batch = []

# 导入剩余
if batch:
    try:
        cursor.executemany(insert_sql, batch)
        conn.commit()
        imported += len(batch)
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        conn.rollback()
        errors += len(batch)

print(f"\n✅ 导入完成！成功 {imported} 条, 失败 {errors} 条")


# ============================================================
# 4. 验证
# ============================================================
cursor.execute('SELECT COUNT(*) FROM iflytek_jobs')
count = cursor.fetchone()[0]
print(f"\n📊 iflytek_jobs 表总计: {count} 条记录")

print("\n=== 数据预览 ===")
cursor.execute('''
    SELECT title, standardized_title, level, stack, parsed_education, quality
    FROM iflytek_jobs
    ORDER BY quality DESC
    LIMIT 10
''')
print(f"{'原始title':50s} | {'标准化':22s} | {'级别':8s} | {'方向':12s} | {'学历':10s} | {'质量':5s}")
print("-" * 120)
for row in cursor.fetchall():
    print(f"{str(row[0]):50s} | {str(row[1]):22s} | {str(row[2]):8s} | {str(row[3]):12s} | {str(row[4]):10s} | {str(row[5]):5s}")

# 统计
print("\n=== 级别分布 ===")
cursor.execute('SELECT level, COUNT(*) FROM iflytek_jobs GROUP BY level ORDER BY COUNT(*) DESC')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}个")

print("\n=== 技术方向分布 ===")
cursor.execute('SELECT stack, COUNT(*) FROM iflytek_jobs GROUP BY stack ORDER BY COUNT(*) DESC')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}个")

cursor.close()
conn.close()
print("\n🎉 全部完成！")
