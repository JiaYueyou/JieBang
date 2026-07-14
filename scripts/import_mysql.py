# -*- coding: utf-8 -*-
"""
将清洗后的岗位数据导入 MySQL jiebang_db 数据库
"""

import pymysql
import csv

# ============================================================
# 1. 数据库连接
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

# ============================================================
# 2. 创建清洗数据表
# ============================================================
create_table_sql = """
CREATE TABLE IF NOT EXISTS job_posting_cleaned (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `岗位名称` VARCHAR(200) DEFAULT NULL,
    `公司` VARCHAR(200) DEFAULT NULL,
    `工作城市` VARCHAR(200) DEFAULT NULL,
    `薪资` VARCHAR(100) DEFAULT NULL,
    `经验要求_原始` VARCHAR(100) DEFAULT NULL,
    `经验要求_标准化` VARCHAR(100) DEFAULT NULL,
    `经验要求_年` INT DEFAULT 0,
    `学历要求_原始` VARCHAR(100) DEFAULT NULL,
    `学历要求_标准化` VARCHAR(100) DEFAULT NULL,
    `发布时间` DATETIME DEFAULT NULL,
    `数据来源` VARCHAR(100) DEFAULT NULL,
    `原始关键词` VARCHAR(500) DEFAULT NULL,
    `岗位级别` VARCHAR(50) DEFAULT NULL,
    `技术职能` VARCHAR(200) DEFAULT NULL,
    `AI方向细分` VARCHAR(200) DEFAULT NULL,
    `编程语言` VARCHAR(200) DEFAULT NULL,
    `后端框架` VARCHAR(200) DEFAULT NULL,
    `数据库` VARCHAR(200) DEFAULT NULL,
    `中间件_消息队列` VARCHAR(200) DEFAULT NULL,
    `DevOps_云工具` VARCHAR(200) DEFAULT NULL,
    `大数据技术栈` VARCHAR(200) DEFAULT NULL,
    `AI_ML框架` VARCHAR(200) DEFAULT NULL,
    `AI细分方向` VARCHAR(200) DEFAULT NULL,
    `大模型相关` VARCHAR(200) DEFAULT NULL,
    `协议_标准` VARCHAR(200) DEFAULT NULL,
    `硬件_平台` VARCHAR(200) DEFAULT NULL,
    `工程能力` VARCHAR(300) DEFAULT NULL,
    `数据处理能力` VARCHAR(300) DEFAULT NULL,
    `行业领域` VARCHAR(300) DEFAULT NULL,
    `专业要求` VARCHAR(300) DEFAULT NULL,
    `软技能` VARCHAR(500) DEFAULT NULL,
    `管理能力` VARCHAR(300) DEFAULT NULL,
    `语言能力` VARCHAR(200) DEFAULT NULL,
    `证书认证` VARCHAR(200) DEFAULT NULL,
    `能力要求_标准化` TEXT DEFAULT NULL,
    `岗位要求_标准化摘要` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

cursor.execute("DROP TABLE IF EXISTS job_posting_cleaned")
cursor.execute(create_table_sql)
print("✅ 表 job_posting_cleaned 创建成功")

# ============================================================
# 3. 读取CSV并导入
# ============================================================
csv_file = '岗位数据_清洗完成.csv'
with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"✅ 读取CSV: {len(rows)} 条记录, {len(rows[0])} 个字段")

# 字段映射：CSV列名 -> 数据库列名
field_map = {
    '岗位名称': '岗位名称',
    '公司': '公司',
    '工作城市': '工作城市',
    '薪资': '薪资',
    '经验要求(原始)': '经验要求_原始',
    '经验要求(标准化)': '经验要求_标准化',
    '经验要求(年)': '经验要求_年',
    '学历要求(原始)': '学历要求_原始',
    '学历要求(标准化)': '学历要求_标准化',
    '发布时间': '发布时间',
    '数据来源': '数据来源',
    '原始关键词': '原始关键词',
    '岗位级别': '岗位级别',
    '技术职能': '技术职能',
    'AI方向细分': 'AI方向细分',
    '编程语言': '编程语言',
    '后端框架': '后端框架',
    '数据库': '数据库',
    '中间件/消息队列': '中间件_消息队列',
    'DevOps/云工具': 'DevOps_云工具',
    '大数据技术栈': '大数据技术栈',
    'AI/ML框架': 'AI_ML框架',
    'AI细分方向': 'AI细分方向',
    '大模型相关': '大模型相关',
    '协议/标准': '协议_标准',
    '硬件/平台': '硬件_平台',
    '工程能力': '工程能力',
    '数据处理能力': '数据处理能力',
    '行业领域': '行业领域',
    '专业要求': '专业要求',
    '软技能': '软技能',
    '管理能力': '管理能力',
    '语言能力': '语言能力',
    '证书认证': '证书认证',
    '能力要求(标准化)': '能力要求_标准化',
    '岗位要求(标准化摘要)': '岗位要求_标准化摘要',
}

db_fields = list(field_map.values())
placeholders = ', '.join(['%s'] * len(db_fields))
columns = ', '.join([f'`{f}`' for f in db_fields])

insert_sql = f'INSERT INTO job_posting_cleaned ({columns}) VALUES ({placeholders})'

imported = 0
errors = 0
batch = []
BATCH_SIZE = 50

for row in rows:
    values = []
    for csv_field, db_field in field_map.items():
        val = row.get(csv_field, '')
        # 经验要求(年) 转整数
        if db_field == '经验要求_年':
            try:
                val = int(val) if val else 0
            except:
                val = 0
        # 发布时间转datetime
        elif db_field == '发布时间' and val:
            # 处理 ISO 格式 "2026-06-12T13:41:56"
            val = val.replace('T', ' ').split('+')[0].split('Z')[0].strip()
        else:
            val = val if val else None
        values.append(val)

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
cursor.execute('SELECT COUNT(*) FROM job_posting_cleaned')
count = cursor.fetchone()[0]
print(f"📊 job_posting_cleaned 表总计: {count} 条记录")

# 显示前3条预览
cursor.execute('SELECT 岗位名称, 岗位级别, 学历要求_标准化, 经验要求_标准化 FROM job_posting_cleaned LIMIT 5')
print("\n=== 数据预览 ===")
for row in cursor.fetchall():
    print(f"  {row[0]:40s} | {str(row[1]):6s} | {str(row[2]):10s} | {str(row[3]):10s}")

print("\n=== 能力要求(标准化) 样例 ===")
cursor.execute('SELECT 岗位名称, 能力要求_标准化 FROM job_posting_cleaned WHERE 能力要求_标准化 IS NOT NULL LIMIT 3')
for row in cursor.fetchall():
    print(f"\n  📌 {row[0]}")
    print(f"     {row[1][:200]}")

cursor.close()
conn.close()
print("\n🎉 全部完成！")
