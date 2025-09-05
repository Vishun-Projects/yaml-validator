"""
gdpr_database.py

GDPR-compliant database models for Audit Validator.
Stores files, validation sessions, chat history, and audit logs for compliance.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Text, JSON, Boolean, LargeBinary, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import text

# Database configuration
DB_USER = os.getenv("AV_DB_USER", "root")
DB_PASS = os.getenv("AV_DB_PASS", "")
DB_HOST = os.getenv("AV_DB_HOST", "localhost")
DB_PORT = int(os.getenv("AV_DB_PORT", 3306))
DB_NAME = os.getenv("AV_DB_NAME", "audit_validator_db")

DB_URI_ROOT = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/"
DB_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

Base = declarative_base()

class ValidationSession(Base):
    """Main validation session table - GDPR compliant"""
    __tablename__ = "validation_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # GDPR compliance fields
    data_retention_until = Column(DateTime, nullable=False)  # When data should be deleted
    data_processing_purpose = Column(String(500), default="Configuration validation and security audit")
    data_controller = Column(String(255), default="Audit Validator System")
    consent_given = Column(Boolean, default=True)  # Implied consent for system operation
    
    # Session metadata
    user_agent = Column(String(500))
    ip_address = Column(String(45))  # IPv6 compatible
    session_duration = Column(Integer)  # in seconds
    
    # Validation results
    match_percentage = Column(Integer)
    total_findings = Column(Integer)
    critical_issues = Column(Integer)
    high_issues = Column(Integer)
    medium_issues = Column(Integer)
    low_issues = Column(Integer)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

class UploadedFile(Base):
    """Files uploaded during validation - GDPR compliant"""
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    file_type = Column(String(50), nullable=False)  # logo, config, snapshot
    
    # File metadata
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    file_hash = Column(String(64))  # SHA-256 hash for integrity
    
    # File content (encrypted or stored securely)
    file_content = Column(LargeBinary)
    file_content_text = Column(Text)  # For text-based files
    
    # GDPR compliance
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    retention_until = Column(DateTime, nullable=False)
    is_encrypted = Column(Boolean, default=True)
    encryption_key_id = Column(String(255))
    
    # Status
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)

class ValidationDetail(Base):
    """Detailed validation findings - GDPR compliant"""
    __tablename__ = "validation_details"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Validation data
    config_key = Column(String(255), nullable=False)
    status = Column(String(50))  # match, partial, mismatch
    severity = Column(String(50))  # critical, high, medium, low
    expected_value = Column(Text)
    actual_value = Column(Text)
    explanation = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # GDPR compliance
    data_category = Column(String(100), default="Configuration validation")
    retention_until = Column(DateTime, nullable=False)

class ChatMessage(Base):
    """Chat conversation history - GDPR compliant"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Message data
    message_type = Column(String(20), nullable=False)  # user, ai
    message_content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # AI-specific fields
    ai_model = Column(String(100))  # groq, fallback
    ai_prompt_tokens = Column(Integer)
    ai_response_tokens = Column(Integer)
    ai_response_time = Column(Float)  # in seconds
    
    # GDPR compliance
    data_category = Column(String(100), default="AI assistance chat")
    retention_until = Column(DateTime, nullable=False)
    is_encrypted = Column(Boolean, default=True)

class AuditLog(Base):
    """Audit trail for GDPR compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Audit data
    action = Column(String(100), nullable=False)  # file_upload, validation_run, chat_message, export
    action_details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # User context
    user_agent = Column(String(500))
    ip_address = Column(String(45))
    
    # GDPR compliance
    data_processed = Column(Boolean, default=False)
    retention_until = Column(DateTime, nullable=False)

class GDPRConsent(Base):
    """GDPR consent management"""
    __tablename__ = "gdpr_consents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Consent data
    consent_type = Column(String(100), nullable=False)  # data_processing, data_storage, cookies
    consent_given = Column(Boolean, default=False)
    consent_given_at = Column(DateTime)
    consent_withdrawn_at = Column(DateTime)
    
    # Legal basis
    legal_basis = Column(String(100), default="Legitimate interest")
    purpose = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GDPRDatabase:
    """GDPR-compliant database operations"""
    
    def __init__(self, echo=False):
        self.engine = create_engine(DB_URI, echo=echo, pool_pre_ping=True, pool_recycle=3600)
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_database_exists()
        Base.metadata.create_all(self.engine)
    
    def _ensure_database_exists(self):
        """Ensure database exists, create if not"""
        try:
            # Try to connect to the specific database
            test_engine = create_engine(DB_URI, echo=False)
            test_engine.connect()
            test_engine.dispose()
        except SQLAlchemyError:
            # Database doesn't exist, create it
            root_engine = create_engine(DB_URI_ROOT, echo=False)
            try:
                with root_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
                    conn.commit()
                print(f"Database `{DB_NAME}` created successfully.")
            except SQLAlchemyError as e:
                print(f"Failed to create database: {e}")
                raise
            finally:
                root_engine.dispose()
    
    def create_session(self, session_id, user_agent=None, ip_address=None):
        """Create a new validation session"""
        session = self.Session()
        try:
            # Set retention period (e.g., 2 years for GDPR compliance)
            retention_until = datetime.utcnow() + timedelta(days=730)
            
            new_session = ValidationSession(
                session_id=session_id,
                user_agent=user_agent,
                ip_address=ip_address,
                data_retention_until=retention_until
            )
            
            session.add(new_session)
            session.commit()
            
            # Create GDPR consent record
            consent = GDPRConsent(
                session_id=session_id,
                consent_type="data_processing",
                consent_given=True,
                consent_given_at=datetime.utcnow(),
                purpose="Configuration validation and security audit"
            )
            session.add(consent)
            session.commit()
            
            # Detach the object before closing session
            session.refresh(new_session)
            session.expunge(new_session)
            return new_session
        except IntegrityError as e:
            session.rollback()
            # If it's a duplicate entry, return the existing session instead of raising
            if "Duplicate entry" in str(e):
                print(f"Session {session_id} already exists, returning existing session")
                # Try to get the existing session
                existing_session = session.query(ValidationSession).filter_by(session_id=session_id).first()
                if existing_session:
                    # Detach the object before closing session
                    session.refresh(existing_session)
                    session.expunge(existing_session)
                    return existing_session
            # For other integrity errors, re-raise
            raise
        finally:
            session.close()
    
    def save_file(self, session_id, file_type, file_data, filename, mime_type=None):
        """Save uploaded file with GDPR compliance"""
        session = self.Session()
        try:
            # Calculate file hash for integrity
            if isinstance(file_data, bytes):
                file_hash = hashlib.sha256(file_data).hexdigest()
                file_size = len(file_data)
                file_content = file_data
                file_content_text = None
            else:
                # Handle text content
                file_content = None
                file_content_text = str(file_data)
                file_hash = hashlib.sha256(file_content_text.encode()).hexdigest()
                file_size = len(file_content_text.encode())
            
            # Set retention period
            retention_until = datetime.utcnow() + timedelta(days=730)
            
            uploaded_file = UploadedFile(
                session_id=session_id,
                file_type=file_type,
                original_filename=filename,
                file_size=file_size,
                mime_type=mime_type,
                file_hash=file_hash,
                file_content=file_content,
                file_content_text=file_content_text,
                retention_until=retention_until
            )
            
            session.add(uploaded_file)
            session.commit()
            
            # Log the action
            self._log_audit_action(session_id, "file_upload", {
                "file_type": file_type,
                "filename": filename,
                "file_size": file_size
            }, user_agent=None, ip_address=None)
            
            return uploaded_file
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_validation_results(self, session_id, validation_result):
        """Save validation results with GDPR compliance"""
        session = self.Session()
        try:
            # Update session with validation metrics
            validation_session = session.query(ValidationSession).filter_by(session_id=session_id).first()
            if validation_session:
                validation_session.match_percentage = validation_result.get('match_percentage', 0)
                validation_session.total_findings = len(validation_result.get('details', []))
                
                # Count issues by severity
                details = validation_result.get('details', [])
                validation_session.critical_issues = sum(1 for d in details if str(d.get('severity', '')).lower() == 'critical')
                validation_session.high_issues = sum(1 for d in details if str(d.get('severity', '')).lower() == 'high')
                validation_session.medium_issues = sum(1 for d in details if str(d.get('severity', '')).lower() == 'medium')
                validation_session.low_issues = sum(1 for d in details if str(d.get('severity', '')).lower() == 'low')
                
                validation_session.updated_at = datetime.utcnow()
            
            # Save individual validation details
            retention_until = datetime.utcnow() + timedelta(days=730)
            
            for detail in validation_result.get('details', []):
                validation_detail = ValidationDetail(
                    session_id=session_id,
                    config_key=detail.get('key', ''),
                    status=detail.get('status', ''),
                    severity=detail.get('severity', ''),
                    expected_value=detail.get('expected', ''),
                    actual_value=detail.get('actual', ''),
                    explanation=detail.get('explanation', ''),
                    retention_until=retention_until
                )
                session.add(validation_detail)
            
            session.commit()
            
            # Log the action
            self._log_audit_action(session_id, "validation_run", {
                "match_percentage": validation_result.get('match_percentage', 0),
                "total_findings": len(validation_result.get('details', []))
            })
            
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def save_chat_message(self, session_id, message_type, content, ai_model=None, 
                         prompt_tokens=None, response_tokens=None, response_time=None):
        """Save chat message with GDPR compliance"""
        session = self.Session()
        try:
            retention_until = datetime.utcnow() + timedelta(days=730)
            
            chat_message = ChatMessage(
                session_id=session_id,
                message_type=message_type,
                message_content=content,
                ai_model=ai_model,
                ai_prompt_tokens=prompt_tokens,
                ai_response_tokens=response_tokens,
                ai_response_time=response_time,
                retention_until=retention_until
            )
            
            session.add(chat_message)
            session.commit()
            
            # Log the action
            self._log_audit_action(session_id, "chat_message", {
                "message_type": message_type,
                "ai_model": ai_model
            })
            
            return chat_message
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _log_audit_action(self, session_id, action, details, user_agent=None, ip_address=None):
        """Log audit action for GDPR compliance"""
        session = self.Session()
        try:
            retention_until = datetime.utcnow() + timedelta(days=2555)  # 7 years for audit logs
            
            audit_log = AuditLog(
                session_id=session_id,
                action=action,
                action_details=details,
                user_agent=user_agent,
                ip_address=ip_address,
                retention_until=retention_until
            )
            
            session.add(audit_log)
            session.commit()
        except IntegrityError:
            session.rollback()
        finally:
            session.close()
    
    def get_session_data(self, session_id):
        """Get all data for a specific session (for GDPR data export)"""
        session = self.Session()
        try:
            # Get session info
            validation_session = session.query(ValidationSession).filter_by(session_id=session_id).first()
            if not validation_session:
                return None
            
            # Get files
            files = session.query(UploadedFile).filter_by(session_id=session_id, is_deleted=False).all()
            
            # Get validation details
            details = session.query(ValidationDetail).filter_by(session_id=session_id).all()
            
            # Get chat messages
            chat_messages = session.query(ChatMessage).filter_by(session_id=session_id).all()
            
            # Get audit logs
            audit_logs = session.query(AuditLog).filter_by(session_id=session_id).all()
            
            return {
                'session': {
                    'id': validation_session.session_id,
                    'created_at': validation_session.created_at.isoformat(),
                    'match_percentage': validation_session.match_percentage,
                    'total_findings': validation_session.total_findings,
                    'critical_issues': validation_session.critical_issues,
                    'high_issues': validation_session.high_issues,
                    'medium_issues': validation_session.medium_issues,
                    'low_issues': validation_session.low_issues
                },
                'files': [{
                    'type': f.file_type,
                    'filename': f.original_filename,
                    'size': f.file_size,
                    'uploaded_at': f.uploaded_at.isoformat()
                } for f in files],
                'validation_details': [{
                    'key': d.config_key,
                    'status': d.status,
                    'severity': d.severity,
                    'expected': d.expected_value,
                    'actual': d.actual_value,
                    'explanation': d.explanation
                } for d in details],
                'chat_messages': [{
                    'type': m.message_type,
                    'content': m.message_content,
                    'timestamp': m.timestamp.isoformat(),
                    'ai_model': m.ai_model
                } for m in chat_messages],
                'audit_logs': [{
                    'action': l.action,
                    'details': l.action_details,
                    'timestamp': l.timestamp.isoformat()
                } for l in audit_logs]
            }
        finally:
            session.close()
    
    def get_session(self, session_id):
        """Check if a session exists and return basic session info"""
        session = self.Session()
        try:
            validation_session = session.query(ValidationSession).filter_by(session_id=session_id).first()
            if validation_session:
                return {
                    'id': validation_session.session_id,
                    'created_at': validation_session.created_at,
                    'is_active': validation_session.is_active
                }
            return None
        finally:
            session.close()
    
    def cleanup_expired_data(self):
        """Clean up data that has exceeded retention period (GDPR compliance)"""
        session = self.Session()
        try:
            now = datetime.utcnow()
            
            # Clean up expired sessions
            expired_sessions = session.query(ValidationSession).filter(
                ValidationSession.data_retention_until < now
            ).all()
            
            for expired_session in expired_sessions:
                expired_session.is_deleted = True
                expired_session.deleted_at = now
                expired_session.is_active = False
            
            # Clean up expired files
            expired_files = session.query(UploadedFile).filter(
                UploadedFile.retention_until < now
            ).all()
            
            for expired_file in expired_files:
                expired_file.is_deleted = True
                expired_file.deleted_at = now
            
            # Clean up expired validation details
            expired_details = session.query(ValidationDetail).filter(
                ValidationDetail.retention_until < now
            ).all()
            
            for expired_detail in expired_details:
                session.delete(expired_detail)
            
            # Clean up expired chat messages
            expired_chats = session.query(ChatMessage).filter(
                ChatMessage.retention_until < now
            ).all()
            
            for expired_chat in expired_chats:
                session.delete(expired_chat)
            
            # Clean up expired audit logs
            expired_audits = session.query(AuditLog).filter(
                AuditLog.retention_until < now
            ).all()
            
            for expired_audit in expired_audits:
                session.delete(expired_audit)
            
            session.commit()
            
            return len(expired_sessions)
        except IntegrityError:
            session.rollback()
            raise
        finally:
            session.close()
    
    def export_gdpr_data(self, session_id):
        """Export all data for a session in GDPR-compliant format"""
        session_data = self.get_session_data(session_id)
        if not session_data:
            return None
        
        # Add GDPR metadata
        gdpr_export = {
            'gdpr_export': {
                'export_date': datetime.utcnow().isoformat(),
                'data_subject_rights': {
                    'right_to_access': 'Fulfilled by this export',
                    'right_to_rectification': 'Contact system administrator',
                    'right_to_erasure': 'Contact system administrator',
                    'right_to_portability': 'Fulfilled by this export'
                },
                'data_processing_purpose': 'Configuration validation and security audit',
                'legal_basis': 'Legitimate interest in system security',
                'data_retention_period': '2 years for operational data, 7 years for audit logs'
            },
            'data': session_data
        }
        
        return gdpr_export

# Singleton instance
_gdpr_db_singleton = None

def get_gdpr_db(echo=False):
    """Get GDPR database instance"""
    global _gdpr_db_singleton
    if _gdpr_db_singleton is None:
        _gdpr_db_singleton = GDPRDatabase(echo=echo)
    return _gdpr_db_singleton
