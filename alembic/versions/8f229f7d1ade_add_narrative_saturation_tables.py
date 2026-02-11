"""add_narrative_saturation_tables

Revision ID: 8f229f7d1ade
Revises: c8745fb60119
Create Date: 2026-02-09 23:20:40.317603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f229f7d1ade'
down_revision: Union[str, None] = 'c8745fb60119'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create news_articles table first
    op.create_table('news_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('url', sa.String(2048), nullable=True),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('raw_id', sa.UUID(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('author', sa.String(256), nullable=True),
        sa.Column('language', sa.String(8), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['source_id'], ['ingestion.source_registry.id'], ),
        sa.ForeignKeyConstraint(['raw_id'], ['ingestion.raw_ingestion.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create narrative_clusters table
    op.create_table('narrative_clusters',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('representative_title', sa.Text(), nullable=False),
        sa.Column('source_distribution', sa.JSON(), nullable=False),
        sa.Column('average_tone', sa.Float(), nullable=False, default=0.0),
        sa.Column('coverage_intensity', sa.Float(), nullable=False),
        sa.Column('time_span_hours', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create narrative_cluster_articles table
    op.create_table('narrative_cluster_articles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.String(100), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['cluster_id'], ['narrative_clusters.id'], ),
        sa.ForeignKeyConstraint(['article_id'], ['news_articles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create narrative_saturation table
    op.create_table('narrative_saturation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.String(100), nullable=False),
        sa.Column('saturation_score', sa.Float(), nullable=False),
        sa.Column('lifecycle_stage', sa.String(20), nullable=False),
        sa.Column('coverage_volume', sa.Integer(), nullable=False),
        sa.Column('source_concentration', sa.Float(), nullable=False),
        sa.Column('repetition_score', sa.Float(), nullable=False),
        sa.Column('temporal_distribution', sa.Float(), nullable=False),
        sa.Column('is_saturated', sa.Boolean(), nullable=False, default=False),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['cluster_id'], ['narrative_clusters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create narrative_alerts table
    op.create_table('narrative_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cluster_id', sa.String(100), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('saturation_score', sa.Float(), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['narrative_clusters.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_narrative_clusters_created_at', 'narrative_clusters', ['created_at'])
    op.create_index('ix_narrative_saturation_cluster_id', 'narrative_saturation', ['cluster_id'])
    op.create_index('ix_narrative_saturation_calculated_at', 'narrative_saturation', ['calculated_at'])
    op.create_index('ix_narrative_alerts_cluster_id', 'narrative_alerts', ['cluster_id'])
    op.create_index('ix_narrative_alerts_created_at', 'narrative_alerts', ['created_at'])
    op.create_index('ix_narrative_alerts_active', 'narrative_alerts', ['is_active'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_narrative_alerts_active', table_name='narrative_alerts')
    op.drop_index('ix_narrative_alerts_created_at', table_name='narrative_alerts')
    op.drop_index('ix_narrative_alerts_cluster_id', table_name='narrative_alerts')
    op.drop_index('ix_narrative_saturation_calculated_at', table_name='narrative_saturation')
    op.drop_index('ix_narrative_saturation_cluster_id', table_name='narrative_saturation')
    op.drop_index('ix_narrative_clusters_created_at', table_name='narrative_clusters')

    # Drop tables
    op.drop_table('narrative_alerts')
    op.drop_table('narrative_saturation')
    op.drop_table('narrative_cluster_articles')
    op.drop_table('narrative_clusters')
    op.drop_table('news_articles')
