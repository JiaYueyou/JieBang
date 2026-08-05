"""创建 data_source 数据源配置表。

Revision ID: 20260721_0009
Revises: 20260715_0008
Create Date: 2026-07-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260721_0009"
down_revision: Union[str, Sequence[str], None] = "20260715_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_source",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="数据源名称"),
        sa.Column("source_type", sa.String(50), nullable=False, comment="类型"),
        sa.Column("entry_url", sa.String(500), nullable=True, comment="入口地址"),
        sa.Column("description", sa.String(500), nullable=True, comment="描述"),
        sa.Column("schedule_expression", sa.String(100), nullable=True, comment="cron 表达式"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE"), comment="启停状态"),
        sa.Column("crawl_config", sa.JSON(), nullable=True, comment="抓取配置 JSON"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True, comment="最后运行时间"),
        sa.Column("next_run_at", sa.DateTime(), nullable=True, comment="下次运行时间"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="连续失败次数"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_data_source_name"),
    )

    # 插入初始数据源
    op.execute(
        sa.text("""
            INSERT INTO data_source (name, source_type, entry_url, description, enabled) VALUES
            ('科大讯飞官网', 'iflytek', 'https://iflytek.zhiye.com/social/jobs', '科大讯飞股份有限公司官方招聘网站', TRUE),
            ('智联招聘', 'zhaopin', 'https://sou.zhaopin.com/', '智联招聘搜索"科大讯飞"相关岗位', TRUE)
        """)
    )


def downgrade() -> None:
    op.drop_table("data_source")
