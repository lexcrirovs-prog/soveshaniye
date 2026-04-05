from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    bitrix_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    department = Column(String(255))
    position = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    calls = relationship("Call", back_populates="employee")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True)
    bitrix_call_id = Column(String(64), unique=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    direction = Column(String(10), nullable=False)
    phone_number = Column(String(32))
    duration_sec = Column(Integer, nullable=False)
    call_date = Column(DateTime(timezone=True), nullable=False)
    audio_path = Column(String(512))
    deal_id = Column(Integer)
    deal_name = Column(String(512))
    deal_stage = Column(String(128))
    deal_amount = Column(Float)
    status = Column(String(20), default="new")
    export_job_id = Column(Integer, ForeignKey("export_jobs.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False)
    analysis = relationship("Analysis", back_populates="call", uselist=False)


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), unique=True)
    text = Column(Text, nullable=False)
    language = Column(String(10), default="ru")
    model_used = Column(String(32), default="small")
    confidence = Column(Float)
    segments = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    call = relationship("Call", back_populates="transcript")


class SalesScript(Base):
    __tablename__ = "sales_scripts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    original_file = Column(String(512))
    file_type = Column(String(10))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analyses = relationship("Analysis", back_populates="script")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"))
    script_id = Column(Integer, ForeignKey("sales_scripts.id"), nullable=True)
    greeting_score = Column(SmallInteger)
    needs_discovery = Column(SmallInteger)
    presentation_score = Column(SmallInteger)
    objection_handling = Column(SmallInteger)
    closing_score = Column(SmallInteger)
    initiative_score = Column(SmallInteger)
    overall_score = Column(SmallInteger)
    summary = Column(Text)
    strengths = Column(JSONB)
    weaknesses = Column(JSONB)
    recommendations = Column(JSONB)
    missed_script_steps = Column(JSONB)
    who_leads = Column(String(20))
    next_step_agreed = Column(Boolean)
    crm_note_suggestion = Column(Text)
    raw_response = Column(Text)
    model_used = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    call = relationship("Call", back_populates="analysis")
    script = relationship("SalesScript", back_populates="analyses")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(Integer, primary_key=True)
    period = Column(String(20), nullable=False)
    date_from = Column(DateTime(timezone=True))
    date_to = Column(DateTime(timezone=True))
    department_id = Column(Integer)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    total_calls = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    error_msg = Column(Text)
    report_path = Column(String(512))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
