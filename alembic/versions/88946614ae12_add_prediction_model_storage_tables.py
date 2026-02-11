"""Add prediction model storage tables

Revision ID: 88946614ae12
Revises: 493bb1bc3261
Create Date: 2026-02-09 20:09:23.594534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88946614ae12'
down_revision: Union[str, None] = '493bb1bc3261'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prediction_models table
    op.create_table('prediction_models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('keyword_id', sa.Integer(), nullable=False),
        sa.Column('model_type', sa.String(length=50), nullable=False),
        sa.Column('model_version', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('training_data_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_data_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('training_samples', sa.Integer(), nullable=True),
        sa.Column('model_parameters', sa.JSON(), nullable=False),
        sa.Column('training_mae', sa.Float(), nullable=True),
        sa.Column('training_rmse', sa.Float(), nullable=True),
        sa.Column('training_mape', sa.Float(), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('last_prediction_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('prediction_count', sa.Integer(), nullable=False),
        sa.Column('retrain_required', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['keyword_id'], ['trend_keywords.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Create indexes for prediction_models
    op.create_index('idx_prediction_models_keyword_active', 'prediction_models', ['keyword_id', 'is_active'], unique=False)
    op.create_index('idx_prediction_models_type_version', 'prediction_models', ['model_type', 'model_version'], unique=False)

    # Create prediction_results table
    op.create_table('prediction_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('prediction_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('horizon_hours', sa.Integer(), nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=True),
        sa.Column('confidence_upper', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('actual_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('prediction_error', sa.Float(), nullable=True),
        sa.Column('prediction_accuracy', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['model_id'], ['prediction_models.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Create indexes for prediction_results
    op.create_index('idx_prediction_results_model_timestamp', 'prediction_results', ['model_id', 'prediction_timestamp'], unique=False)
    op.create_index('idx_prediction_results_horizon', 'prediction_results', ['horizon_hours'], unique=False)


def downgrade() -> None:
    # Drop indexes for prediction_results
    op.drop_index('idx_prediction_results_horizon', table_name='prediction_results')
    op.drop_index('idx_prediction_results_model_timestamp', table_name='prediction_results')
    # Drop prediction_results table
    op.drop_table('prediction_results')

    # Drop indexes for prediction_models
    op.drop_index('idx_prediction_models_type_version', table_name='prediction_models')
    op.drop_index('idx_prediction_models_keyword_active', table_name='prediction_models')
    # Drop prediction_models table
    op.drop_table('prediction_models')
