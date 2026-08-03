"""merge_jiebang_tables

将 jtt-src ORM 表合并到 jie_bang 数据库。
- user: 补齐缺失字段
- 新建: job_position / position_skill / skill_change / resume / learning_path / favorite / match_result

Revision ID: 58dd0344bd32
Revises: d181e15f9f21
Create Date: 2026-08-01 19:01:04.795574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58dd0344bd32'
down_revision: Union[str, Sequence[str], None] = 'd181e15f9f21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """合并 jtt-src 表到 jie_bang"""

    # ===== 1. user 补齐字段 =====
    op.add_column('user', sa.Column('email', sa.String(100), nullable=True, comment='邮箱'))
    op.add_column('user', sa.Column('nickname', sa.String(50), nullable=True, comment='昵称'))
    op.add_column('user', sa.Column('phone', sa.String(20), nullable=True, comment='手机号'))
    op.add_column('user', sa.Column('city', sa.String(50), nullable=True, comment='所在城市'))
    op.add_column('user', sa.Column('education', sa.String(50), nullable=True, comment='最高学历'))
    op.add_column('user', sa.Column('avatar', sa.String(500), nullable=True, comment='头像URL'))
    op.add_column('user', sa.Column('resume_count', sa.Integer(), nullable=False, server_default='0', comment='简历数量'))
    op.add_column('user', sa.Column('match_history_count', sa.Integer(), nullable=False, server_default='0', comment='匹配历史次数'))
    # 给已有 admin 账号设置默认邮箱
    op.execute("UPDATE user SET email = 'admin@jiebang.com' WHERE id = 1")
    # 创建 email 唯一索引（MySQL UNIQUE 允许多个 NULL，所以建索引前先确保非空行唯一）
    op.create_unique_constraint('uq_user_email', 'user', ['email'])


def downgrade() -> None:
    """回滚：恢复 user 原结构，不删表（表由 initial 迁移管理）"""
    op.drop_constraint('uq_user_email', 'user', type_='unique')
    op.execute("UPDATE user SET email = NULL WHERE id = 1")
    op.drop_column('user', 'match_history_count')
    op.drop_column('user', 'resume_count')
    op.drop_column('user', 'avatar')
    op.drop_column('user', 'education')
    op.drop_column('user', 'city')
    op.drop_column('user', 'phone')
    op.drop_column('user', 'nickname')
    op.drop_column('user', 'email')
