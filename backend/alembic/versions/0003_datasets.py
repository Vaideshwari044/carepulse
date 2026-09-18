"""Create dataset management tables

Revision ID: 0003_datasets
Revises: 0002_chatbot
Create Date: 2026-09-19 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_datasets'
down_revision: Union[str, None] = '0002_chatbot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Datasets Table ────────────────────────────────────────────────────────
    op.create_table(
        'datasets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_format', sa.String(length=50), nullable=False, server_default='parquet'),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('patient_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('meta_info', sa.JSON(), nullable=False),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasets_name'), 'datasets', ['name'], unique=False)

    # ─── Dataset Imports Table ─────────────────────────────────────────────────
    op.create_table(
        'dataset_imports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dataset_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='completed'),
        sa.Column('imported_by', sa.UUID(), nullable=True),
        sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('invalid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('patient_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('columns_detected', sa.JSON(), nullable=False),
        sa.Column('column_mappings', sa.JSON(), nullable=False),
        sa.Column('summary_stats', sa.JSON(), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['imported_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_imports_dataset_id'), 'dataset_imports', ['dataset_id'], unique=False)

    # ─── Dataset Records Table ─────────────────────────────────────────────────
    op.create_table(
        'dataset_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dataset_id', sa.UUID(), nullable=False),
        sa.Column('patient_code', sa.String(length=50), nullable=False),
        sa.Column('raw_patient_id', sa.String(length=100), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('heart_rate', sa.Float(), nullable=True),
        sa.Column('spo2', sa.Float(), nullable=True),
        sa.Column('respiratory_rate', sa.Float(), nullable=True),
        sa.Column('systolic_bp', sa.Float(), nullable=True),
        sa.Column('diastolic_bp', sa.Float(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('raw_label', sa.String(length=100), nullable=True),
        sa.Column('scenario', sa.String(length=100), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_records_dataset_id'), 'dataset_records', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_dataset_records_patient_code'), 'dataset_records', ['patient_code'], unique=False)
    op.create_index(op.f('ix_dataset_records_recorded_at'), 'dataset_records', ['recorded_at'], unique=False)
    op.create_index('idx_dataset_record_patient_time', 'dataset_records', ['patient_code', 'recorded_at'])
    op.create_index('idx_dataset_record_dataset_patient', 'dataset_records', ['dataset_id', 'patient_code'])


def downgrade() -> None:
    op.drop_index('idx_dataset_record_dataset_patient', table_name='dataset_records')
    op.drop_index('idx_dataset_record_patient_time', table_name='dataset_records')
    op.drop_index(op.f('ix_dataset_records_recorded_at'), table_name='dataset_records')
    op.drop_index(op.f('ix_dataset_records_patient_code'), table_name='dataset_records')
    op.drop_index(op.f('ix_dataset_records_dataset_id'), table_name='dataset_records')
    op.drop_table('dataset_records')

    op.drop_index(op.f('ix_dataset_imports_dataset_id'), table_name='dataset_imports')
    op.drop_table('dataset_imports')

    op.drop_index(op.f('ix_datasets_name'), table_name='datasets')
    op.drop_table('datasets')
