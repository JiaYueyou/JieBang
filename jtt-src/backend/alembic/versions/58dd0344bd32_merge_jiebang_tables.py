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

    # ===== 2. job_position =====
    op.create_table('job_position',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='岗位名称'),
        sa.Column('category', sa.String(20), nullable=False, comment='岗位类型: new=新岗位, existing=既有岗位'),
        sa.Column('aliases', sa.JSON(), nullable=False, comment='岗位别名列表'),
        sa.Column('summary', sa.Text(), nullable=False, comment='岗位概述'),
        sa.Column('responsibilities', sa.JSON(), nullable=False, comment='核心职责列表'),
        sa.Column('industry_scenarios', sa.JSON(), nullable=False, comment='典型行业应用场景'),
        sa.Column('tech_stack', sa.JSON(), nullable=False, comment='技术栈列表'),
        sa.Column('career_level', sa.String(20), nullable=False, comment='职业级别: junior/mid/senior'),
        sa.Column('salary_range', sa.String(50), nullable=True, comment='薪资范围'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== 3. position_skill（避免与 fyz-src skill 全局表冲突）=====
    op.create_table('position_skill',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, comment='技能名称'),
        sa.Column('level', sa.String(20), nullable=False, comment='重要性: required/preferred/advanced'),
        sa.Column('kind', sa.String(20), nullable=False, comment='类型: required=必备, preferred=加分'),
        sa.Column('category', sa.String(50), nullable=False, comment='技术栈分类'),
        sa.ForeignKeyConstraint(['position_id'], ['job_position.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== 4. skill_change =====
    op.create_table('skill_change',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('skill_name', sa.String(100), nullable=False, comment='变化的技能名'),
        sa.Column('change_type', sa.String(20), nullable=False, comment='变化类型: added/removed/modified'),
        sa.Column('description', sa.Text(), nullable=False, comment='变化说明'),
        sa.Column('source', sa.String(200), nullable=False, comment='数据来源'),
        sa.Column('change_date', sa.String(20), nullable=False, comment='变化日期'),
        sa.ForeignKeyConstraint(['position_id'], ['job_position.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== 5. resume =====
    op.create_table('resume',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='所属用户ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='简历别名'),
        sa.Column('target_position', sa.String(100), nullable=True, comment='目标岗位方向'),
        sa.Column('personal_name', sa.String(50), nullable=False, comment='姓名'),
        sa.Column('personal_email', sa.String(100), nullable=False, comment='邮箱'),
        sa.Column('personal_phone', sa.String(20), nullable=False, comment='手机号'),
        sa.Column('personal_location', sa.String(50), nullable=False, comment='所在地'),
        sa.Column('desired_position', sa.String(100), nullable=True, comment='期望职位'),
        sa.Column('desired_city', sa.String(50), nullable=True, comment='期望城市'),
        sa.Column('salary_expectation', sa.String(50), nullable=True, comment='期望薪资'),
        sa.Column('work_mode', sa.String(20), nullable=True, comment='工作模式'),
        sa.Column('self_evaluation', sa.Text(), nullable=False, comment='自我评价'),
        sa.Column('source_file', sa.String(200), nullable=True, comment='原始文件名'),
        sa.Column('source_file_path', sa.String(500), nullable=True, comment='文件存储路径'),
        sa.Column('raw_text', sa.Text(), nullable=True, comment='提取纯文本'),
        sa.Column('education_list', sa.JSON(), nullable=False, comment='教育经历列表'),
        sa.Column('work_experience_list', sa.JSON(), nullable=False, comment='工作经历列表'),
        sa.Column('project_list', sa.JSON(), nullable=False, comment='项目经历列表'),
        sa.Column('skill_list', sa.JSON(), nullable=False, comment='技能列表'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== 6. learning_path =====
    op.create_table('learning_path',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='路径名称'),
        sa.Column('position_id', sa.Integer(), nullable=False, comment='目标岗位ID'),
        sa.Column('position_name', sa.String(100), nullable=False, comment='目标岗位名称'),
        sa.Column('steps', sa.JSON(), nullable=False, comment='学习步骤列表'),
        sa.Column('total_duration', sa.String(50), nullable=False, comment='总学习时长'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['job_position.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # ===== 7. favorite =====
    op.create_table('favorite',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('item_type', sa.String(30), nullable=False, comment='收藏类型'),
        sa.Column('item_id', sa.String(100), nullable=False, comment='资源ID'),
        sa.Column('title', sa.String(200), nullable=False, comment='收藏项标题'),
        sa.Column('summary', sa.String(500), nullable=True, comment='简要描述'),
        sa.Column('metadata', sa.JSON(), nullable=False, comment='完整数据快照'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='用户自定义标签'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='收藏时间'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_favorite_item_type'), 'favorite', ['item_type'], unique=False)

    # ===== 8. match_result =====
    op.create_table('match_result',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('resume_id', sa.Integer(), nullable=False, comment='简历ID'),
        sa.Column('position_id', sa.Integer(), nullable=False, comment='岗位ID'),
        sa.Column('position_name', sa.String(100), nullable=False, comment='岗位名称'),
        sa.Column('resume_name', sa.String(100), nullable=False, comment='简历名称'),
        sa.Column('total_score', sa.Integer(), nullable=False, comment='综合匹配分数 0-100'),
        sa.Column('dimensions', sa.JSON(), nullable=False, comment='各维度评分列表'),
        sa.Column('gap_analysis', sa.JSON(), nullable=False, comment='差距分析结果'),
        sa.Column('suggestions', sa.JSON(), nullable=False, comment='优化建议列表'),
        sa.Column('match_date', sa.DateTime(), nullable=False, comment='匹配时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['position_id'], ['job_position.id'], ),
        sa.ForeignKeyConstraint(['resume_id'], ['resume.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """回滚：移除 jtt-src 表，恢复 user 原结构"""
    op.drop_table('match_result')
    op.drop_index(op.f('ix_favorite_item_type'), table_name='favorite')
    op.drop_table('favorite')
    op.drop_table('learning_path')
    op.drop_table('resume')
    op.drop_table('skill_change')
    op.drop_table('position_skill')
    op.drop_table('job_position')

    # 恢复 user 表
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
