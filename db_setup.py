# db_setup.py
"""
Create the MySQL database & tables and migrate local_store.json into it.
Assumes MySQL on localhost:3306, user=root and empty password.
If your credentials differ, edit DB_* variables below.
"""
import os, json, traceback
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Text, JSON, MetaData, Table, text
from sqlalchemy.orm import declarative_base, sessionmaker
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError

# ---- CONFIG ----
DB_USER = "root"
DB_PASS = ""           # empty string -> no password
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "audit_validator_db"

DB_URI_ROOT = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
DB_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

LOCAL_STORE = os.path.join(os.path.dirname(__file__), "local_store.json")

# ---- Helpers ----
def create_database():
    print("Connecting to MySQL (root) and ensuring database exists...")
    engine = create_engine(DB_URI_ROOT, echo=False)
    try:
        with engine.connect() as conn:
            # Use sqlalchemy.text(...) to execute raw SQL DDL
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            # Some MySQL installs require a commit for DDL via SQLAlchemy connection
            conn.commit()
        print(f"Database `{DB_NAME}` ensured.")
    except SQLAlchemyError as e:
        print("Failed to create database:", e)
        raise
    finally:
        engine.dispose()

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

def create_tables():
    print("Creating tables (if not present)...")
    engine = create_engine(DB_URI, echo=False)
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created (or already existed).")
    except SQLAlchemyError as e:
        print("Failed to create tables:", e)
        raise
    finally:
        engine.dispose()

def migrate_local_store():
    if not os.path.exists(LOCAL_STORE):
        print("No local_store.json found — skipping migration.")
        return
    print("Migrating local_store.json -> MySQL...")
    with open(LOCAL_STORE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    engine = create_engine(DB_URI, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # users
        users = data.get("users", {})
        for email, u in users.items():
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                existing.name = u.get("name")
                existing.role = u.get("role")
            else:
                session.add(User(email=email, name=u.get("name"), role=u.get("role")))
        session.commit()

        # assignments
        for k, owner in data.get("assignments", {}).items():
            existing = session.query(Assignment).filter_by(cfg_key=k).first()
            if existing:
                existing.owner = owner
            else:
                session.add(Assignment(cfg_key=k, owner=owner))
        session.commit()

        # statuses
        for k, status in data.get("statuses", {}).items():
            existing = session.query(Status).filter_by(cfg_key=k).first()
            if existing:
                existing.status = status
            else:
                session.add(Status(cfg_key=k, status=status))
        session.commit()

        # slas
        for k, s in data.get("slas", {}).items():
            sla_date = None
            if s:
                try:
                    sla_date = datetime.fromisoformat(s).date()
                except Exception:
                    # may be already a date string without time
                    try:
                        sla_date = datetime.strptime(s.split("T")[0], "%Y-%m-%d").date()
                    except Exception:
                        sla_date = None
            existing = session.query(SLA).filter_by(cfg_key=k).first()
            if existing:
                existing.sla_date = sla_date
            else:
                session.add(SLA(cfg_key=k, sla_date=sla_date))
        session.commit()

        # ai_prompt_log
        for entry in data.get("ai_prompt_log", []):
            ts = None
            try:
                ts = datetime.fromisoformat(entry.get("time")) if entry.get("time") else datetime.utcnow()
            except Exception:
                ts = datetime.utcnow()
            session.add(AIPromptLog(ts=ts, prompt=entry.get("prompt"), response_snippet=entry.get("response_snippet")))
        session.commit()

        # settings
        for k, v in data.get("settings", {}).items():
            if v is None:
                continue
            existing = session.query(Setting).filter_by(key=k).first()
            if existing:
                existing.value = v
            else:
                session.add(Setting(key=k, value=v))
        session.commit()

        print("Migration complete.")
    except Exception as e:
        print("Failed during migration:", e)
        print(traceback.format_exc())
        session.rollback()
    finally:
        session.close()
        engine.dispose()

if __name__ == "__main__":
    print("==== DB Setup & Migration ====")
    create_database()
    create_tables()
    migrate_local_store()
    print("Done. You can now use the DB from your Streamlit app.")
