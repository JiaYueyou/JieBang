# -*- coding: utf-8 -*-
"""
data_source 数据源配置初始化脚本

两种使用方式：
  1. 通过 Alembic 迁移（推荐）：
     cd fyz-src/backend && alembic upgrade head

  2. 独立运行（未配置 Alembic 时）：
     python scripts/init_data_source.py
"""

import json
import sys
from pathlib import Path

# 数据源初始配置
INITIAL_DATA_SOURCES = [
    {
        "name": "科大讯飞官网",
        "source_type": "iflytek",
        "entry_url": "https://iflytek.zhiye.com/social/jobs",
        "description": "科大讯飞股份有限公司官方招聘网站（社会化招聘）",
        "enabled": True,
        "crawl_config": {
            "method": "POST",
            "base_url": "https://iflytek.zhiye.com/api/Jobad/GetJobAdPageList",
            "total_pages": 11,
            "page_size": 20,
            "request_interval": 1.0,
        },
    },
    {
        "name": "智联招聘",
        "source_type": "zhaopin",
        "entry_url": "https://sou.zhaopin.com/",
        "description": "智联招聘搜索'科大讯飞'相关岗位（含第三方外包公司）",
        "enabled": True,
        "crawl_config": {
            "method": "GET",
            "keyword": "科大讯飞",
            "base_url": "https://sou.zhaopin.com/",
            "total_pages": 5,
            "page_size": 20,
            "months_back": 3,
            "request_interval": 2.0,
        },
    },
    {
        "name": "科大讯飞官网(原始存档)",
        "source_type": "iflytek",
        "entry_url": None,
        "description": "科大讯飞官网220条原始数据（学长存档，未清洗）",
        "enabled": False,
        "crawl_config": None,
    },
    {
        "name": "智联招聘(旧版存档)",
        "source_type": "zhaopin",
        "entry_url": None,
        "description": "智联招聘90条旧数据（学长存档）",
        "enabled": False,
        "crawl_config": None,
    },
]


def init_direct(sql_url: str | None = None):
    """
    独立运行：直接连接数据库 + 建表 + 插入初始化数据

    需要安装: pip install sqlalchemy pymysql
    """
    if not sql_url:
        sql_url = input("请输入 MySQL 连接 URL (如 mysql+pymysql://root:pass@localhost/jiebang): ").strip()
        if not sql_url:
            print("已取消")
            return

    from sqlalchemy import create_engine, MetaData, Table, Column, inspect, text

    engine = create_engine(sql_url)
    inspector = inspect(engine)

    # 检查表是否存在
    if "data_source" in inspector.get_table_names():
        print("表 data_source 已存在，跳过建表")
    else:
        print("创建表 data_source...")
        metadata = MetaData()
        Table(
            "data_source",
            metadata,
            Column("id", type_().with_variant(Integer, "mysql"), primary_key=True, autoincrement=True),
            # 简化：直接用原始 SQL 建表
        )
        metadata.create_all(engine)

    # 插入数据
    with engine.connect() as conn:
        for ds in INITIAL_DATA_SOURCES:
            result = conn.execute(
                text("SELECT id FROM data_source WHERE name = :name"),
                {"name": ds["name"]},
            )
            if result.fetchone():
                print(f"  数据源已存在: {ds['name']}")
                continue
            conn.execute(
                text(
                    """INSERT INTO data_source (name, source_type, entry_url, description, enabled, crawl_config)
                       VALUES (:name, :source_type, :entry_url, :description, :enabled, :crawl_config)"""
                ),
                {
                    "name": ds["name"],
                    "source_type": ds["source_type"],
                    "entry_url": ds["entry_url"],
                    "description": ds["description"],
                    "enabled": ds["enabled"],
                    "crawl_config": json.dumps(ds["crawl_config"]) if ds["crawl_config"] else None,
                },
            )
            print(f"  + 已添加数据源: {ds['name']}")
        conn.commit()

    print("\n初始化完成！")


def print_config():
    """打印数据源配置表内容（无需数据库）"""
    print("=" * 60)
    print("data_source 配置表 — 初始数据")
    print("=" * 60)
    print(f"{'名称':20s} {'类型':12s} {'启用':5s} {'入口'}")
    print("-" * 60)
    for ds in INITIAL_DATA_SOURCES:
        enabled = "是" if ds["enabled"] else "否"
        url = ds["entry_url"] or "(存档)"
        print(f"{ds['name']:20s} {ds['source_type']:12s} {enabled:5s} {url}")
    print()
    print("配置详情见: scripts/configs/")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print_config()
    elif len(sys.argv) > 1 and sys.argv[1] == "--init":
        sql_url = sys.argv[2] if len(sys.argv) > 2 else None
        init_direct(sql_url)
    else:
        print("用法:")
        print("  python scripts/init_data_source.py --print     # 打印配置（无需数据库）")
        print("  python scripts/init_data_source.py --init URL  # 初始化数据库")
