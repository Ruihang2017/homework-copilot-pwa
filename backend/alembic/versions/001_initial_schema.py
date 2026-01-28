"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=True),
        sa.Column('oauth_provider', sa.Enum('GOOGLE', 'GITHUB', name='oauthprovider'), nullable=True),
        sa.Column('oauth_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create child_profiles table
    op.create_table(
        'child_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nickname', sa.String(100), nullable=True),
        sa.Column('grade', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_global_state table
    op.create_table(
        'user_global_state',
        sa.Column('child_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('grade_alignment', sa.String(50), nullable=False),
        sa.Column('curriculum', sa.String(50), nullable=False, server_default='NSW'),
        sa.Column('language', sa.String(20), nullable=False, server_default='zh_en'),
        sa.Column('default_explanation_style', sa.String(50), nullable=False, server_default='balanced'),
        sa.Column('no_direct_answer', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['child_profile_id'], ['child_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('child_profile_id')
    )

    # Create child_topic_state table
    op.create_table(
        'child_topic_state',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(50), nullable=False),
        sa.Column('topic_key', sa.String(255), nullable=False),
        sa.Column('mastery', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('preferred_abstraction', sa.Enum('MORE_CONCRETE', 'BALANCED', 'MORE_ABSTRACT', name='abstractionlevel'), nullable=False),
        sa.Column('preferred_hint_depth', sa.Enum('LIGHT_HINTS', 'MODERATE', 'STEP_BY_STEP', name='hintdepth'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['child_profile_id'], ['child_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('child_profile_id', 'topic_key', name='uq_child_topic')
    )
    op.create_index('ix_child_topic_state_topic_key', 'child_topic_state', ['topic_key'])

    # Create questions table
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_key', sa.String(255), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('response_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['child_profile_id'], ['child_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_questions_topic_key', 'questions', ['topic_key'])

    # Create feedback_events table
    op.create_table(
        'feedback_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('topic_key', sa.String(255), nullable=False),
        sa.Column('event_type', sa.Enum('TOO_SIMPLE', 'JUST_RIGHT', 'TOO_ADVANCED', 'UNDERSTOOD', 'STILL_CONFUSED', name='feedbackeventtype'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['child_profile_id'], ['child_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_feedback_events_topic_key', 'feedback_events', ['topic_key'])


def downgrade() -> None:
    op.drop_table('feedback_events')
    op.drop_table('questions')
    op.drop_table('child_topic_state')
    op.drop_table('user_global_state')
    op.drop_table('child_profiles')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS feedbackeventtype')
    op.execute('DROP TYPE IF EXISTS hintdepth')
    op.execute('DROP TYPE IF EXISTS abstractionlevel')
    op.execute('DROP TYPE IF EXISTS oauthprovider')
