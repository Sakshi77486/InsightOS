from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


# =========================================================
# USERS
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# =========================================================
# DATASETS
# =========================================================

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String(255), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_format = Column(String(30))
    source_location = Column(Text)
    row_count = Column(BigInteger)
    column_count = Column(Integer)
    size_bytes = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())


# =========================================================
# DATASET VERSIONS
# =========================================================

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, nullable=False)
    version_number = Column(Integer, nullable=False)
    row_count = Column(BigInteger)
    column_count = Column(Integer)
    size_bytes = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())


# =========================================================
# DATASET COLUMNS
# =========================================================

class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True)
    dataset_version_id = Column(Integer, nullable=False)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)
    nullable = Column(Boolean, default=True)
    missing_count = Column(BigInteger, default=0)
    unique_count = Column(BigInteger, default=0)


# =========================================================
# ANALYSIS RUNS
# =========================================================

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True)
    dataset_version_id = Column(Integer, nullable=False)
    analysis_type = Column(String(100), nullable=False)
    result = Column(Text)
    status = Column(String(30), default="completed")
    created_at = Column(DateTime, server_default=func.now())


# =========================================================
# AI INSIGHTS
# =========================================================

class AIInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True)
    dataset_version_id = Column(Integer, nullable=False)
    analysis_run_id = Column(Integer, nullable=False)
    insight = Column(Text, nullable=False)
    model_name = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())


# =========================================================
# REPORTS
# =========================================================

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    dataset_version_id = Column(Integer, nullable=False)
    report_type = Column(String(50), nullable=False)
    file_path = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(30), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())


class ProjectDataset(Base):
    __tablename__ = "project_datasets"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    dataset_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ProjectRun(Base):
    __tablename__ = "project_runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    dataset_id = Column(Integer)
    run_type = Column(String(50), nullable=False)
    status = Column(String(30), default="processing")
    result = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)