"""Neo4j 连接诊断 — 运行此脚本查看连接问题"""

import sys
sys.path.insert(0, ".")

from app.core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from app.core.neo4j import health_detail, get_driver, health_check

print("=" * 60)
print("Neo4j 连接诊断")
print("=" * 60)
print(f"  URI:      {NEO4J_URI}")
print(f"  User:     {NEO4J_USER}")
print(f"  Password: {'*' * len(NEO4J_PASSWORD) if NEO4J_PASSWORD else '(empty)'}")
print()

# 测试 1: 驱动创建
print("[1] 尝试创建驱动...")
try:
    driver = get_driver()
    print(f"    驱动创建成功: {driver}")
except Exception as e:
    print(f"    FAILED: {e}")
    sys.exit(1)

# 测试 2: 连接验证
print("[2] 尝试连接...")
result = health_detail()
print(f"    {result}")
print()

# 测试 3: 简单查询
if health_check():
    print("[3] 查询测试通过 ✓")
    from app.core.neo4j import run_read
    try:
        r = run_read("MATCH (n) RETURN count(n) AS total")
        print(f"    数据库节点总数: {r[0]['total']}")
    except Exception as e:
        print(f"    查询失败: {e}")
else:
    print("[3] 连接失败，跳过查询测试")

print()
print("=" * 60)
print("诊断建议:")
if not health_check():
    print("  1. 确认 Neo4j 正在运行: neo4j.bat status")
    print("  2. 确认密码正确 — 检查 .env 中 NEO4J_PASSWORD")
    print("  3. 试试在浏览器访问: http://localhost:7474")
    print("  4. 首次安装 Neo4j 需要先通过浏览器登录并修改密码")
print("=" * 60)
