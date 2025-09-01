"""
db.py

SQLAlchemy-backed DB helper for Audit Validator.

Usage:
    from db import get_db, seed_default_users_via_api
    db = get_db()
    users = db.get_users()
    db.set_assignment("ssh.password_auth","alice@example.com")
    db.add_ai_log(prompt, response_snippet)
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

# EDIT THESE or use environment variables
DB_USER = os.getenv("AV_DB_USER", "root")
DB_PASS = os.getenv("AV_DB_PASS", "")
DB_HOST = os.getenv("AV_DB_HOST", "localhost")
DB_PORT = int(os.getenv("AV_DB_PORT", 3306))
DB_NAME = os.getenv("AV_DB_NAME", "audit_validator_db")

DB_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    role = Column(String(80))

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfg_key = Column(String(512), unique=True, nullable=False)
    owner = Column(String(255))

class Status(Base):
    __tablename__ = "statuses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfg_key = Column(String(512), unique=True, nullable=False)
    status = Column(String(80))

class SLA(Base):
    __tablename__ = "slas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfg_key = Column(String(512), unique=True, nullable=False)
    sla_date = Column(Date)

class AIPromptLog(Base):
    __tablename__ = "ai_prompt_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, default=datetime.utcnow)
    prompt = Column(Text)
    response_snippet = Column(Text)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True)
    value = Column(JSON)

class DB:
    def __init__(self, echo=False):
        # pool_pre_ping avoids "MySQL has gone away" in long-lived apps
        self.engine = create_engine(DB_URI, echo=echo, pool_pre_ping=True, pool_recycle=3600)
        self.Session = sessionmaker(bind=self.engine)
        # ensure tables exist (safe even if db_setup.py already ran)
        Base.metadata.create_all(self.engine)

    # --- Users ---
    def get_users(self):
        s = self.Session()
        try:
            rows = s.query(User).all()
            return {r.email: {"name": r.name, "role": r.role} for r in rows}
        finally:
            s.close()

    def add_or_update_user(self, email, name=None, role=None):
        s = self.Session()
        try:
            existing = s.query(User).filter_by(email=email).first()
            if existing:
                existing.name = name or existing.name
                existing.role = role or existing.role
            else:
                s.add(User(email=email, name=name, role=role))
            s.commit()
        except IntegrityError:
            s.rollback()
        finally:
            s.close()

    def create_default_users(self):
        """Create demo users only if users table is empty."""
        s = self.Session()
        try:
            count = s.query(User).count()
            if count == 0:
                demo = [
                    {"email": "admin@example.com", "name": "Admin", "role": "Admin"},
                    {"email": "owner@example.com", "name": "Owner", "role": "Owner"},
                    {"email": "auditor@example.com", "name": "Auditor", "role": "Auditor"},
                    {"email": "viewer@example.com", "name": "Viewer", "role": "Viewer"},
                ]
                for u in demo:
                    s.add(User(email=u["email"], name=u["name"], role=u["role"]))
                s.commit()
                return True
            return False
        finally:
            s.close()

    # --- Assignments ---
    def get_assignments(self):
        s = self.Session()
        try:
            return {r.cfg_key: r.owner for r in s.query(Assignment).all()}
        finally:
            s.close()

    def set_assignment(self, cfg_key, owner):
        s = self.Session()
        try:
            existing = s.query(Assignment).filter_by(cfg_key=cfg_key).first()
            if existing:
                existing.owner = owner
            else:
                s.add(Assignment(cfg_key=cfg_key, owner=owner))
            s.commit()
        finally:
            s.close()

    # --- Statuses ---
    def get_statuses(self):
        s = self.Session()
        try:
            return {r.cfg_key: r.status for r in s.query(Status).all()}
        finally:
            s.close()

    def set_status(self, cfg_key, status):
        s = self.Session()
        try:
            existing = s.query(Status).filter_by(cfg_key=cfg_key).first()
            if existing:
                existing.status = status
            else:
                s.add(Status(cfg_key=cfg_key, status=status))
            s.commit()
        finally:
            s.close()

    # --- SLAs ---
    def get_slas(self):
        s = self.Session()
        try:
            return {r.cfg_key: (r.sla_date.isoformat() if r.sla_date else None) for r in s.query(SLA).all()}
        finally:
            s.close()

    def set_sla(self, cfg_key, sla_iso_date):
        s = self.Session()
        try:
            d = None
            if sla_iso_date:
                try:
                    d = datetime.fromisoformat(sla_iso_date).date()
                except Exception:
                    d = None
            existing = s.query(SLA).filter_by(cfg_key=cfg_key).first()
            if existing:
                existing.sla_date = d
            else:
                s.add(SLA(cfg_key=cfg_key, sla_date=d))
            s.commit()
        finally:
            s.close()

    # --- AI prompt logs ---
    def add_ai_log(self, prompt, response_snippet):
        s = self.Session()
        try:
            s.add(AIPromptLog(ts=datetime.utcnow(), prompt=prompt, response_snippet=response_snippet))
            s.commit()
        finally:
            s.close()

    def get_ai_logs(self, limit=200):
        s = self.Session()
        try:
            rows = s.query(AIPromptLog).order_by(AIPromptLog.ts.desc()).limit(limit).all()
            return [{"time": r.ts.isoformat(), "prompt": r.prompt, "response_snippet": r.response_snippet} for r in rows]
        finally:
            s.close()

    # --- Settings ---
    def get_settings(self):
        s = self.Session()
        try:
            return {r.key: r.value for r in s.query(Setting).all()}
        finally:
            s.close()

    def set_setting(self, key, value):
        s = self.Session()
        try:
            existing = s.query(Setting).filter_by(key=key).first()
            if existing:
                existing.value = value
            else:
                s.add(Setting(key=key, value=value))
            s.commit()
        finally:
            s.close()


# simple singleton factory
_db_singleton = None
def get_db(echo=False):
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = DB(echo=echo)
    return _db_singleton


def seed_default_users_via_api(db_inst=None):
    """
    Idempotently seed default/demo users via public API.
    This function does not use Streamlit or any UI helpers and
    can be safely imported by the app.
    Returns True if users were created, False otherwise.
    """
    try:
        if db_inst is None:
            db_inst = get_db()
        users = db_inst.get_users()
        if not users:
            db_inst.add_or_update_user("admin@example.com", name="Admin", role="Admin")
            db_inst.add_or_update_user("owner@example.com", name="Owner", role="Owner")
            db_inst.add_or_update_user("auditor@example.com", name="Auditor", role="Auditor")
            db_inst.add_or_update_user("viewer@example.com", name="Viewer", role="Viewer")
            return True
    except Exception:
        # swallow exceptions here; caller can decide how to log
        return False
    return False
