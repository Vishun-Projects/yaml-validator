# GDPR-Compliant Database for Audit Validator

This document explains the GDPR-compliant database implementation for the Audit Validator application, which provides secure storage, audit trails, and compliance features for all validation activities.

## 🎯 Overview

The GDPR database ensures that all data processing activities are:
- **Transparent**: Clear information about what data is collected and why
- **Accountable**: Complete audit trails for all actions
- **Secure**: Encrypted storage with integrity verification
- **Compliant**: Meets GDPR requirements for data protection and user rights

## 🗄️ Database Schema

### Core Tables

#### 1. `validation_sessions`
- **Purpose**: Main session tracking for each validation run
- **Key Fields**: 
  - `session_id`: Unique identifier for each session
  - `data_retention_until`: When data should be automatically deleted
  - `data_processing_purpose`: Legal basis for data processing
  - `user_agent` & `ip_address`: User context for audit purposes

#### 2. `uploaded_files`
- **Purpose**: Secure storage of all uploaded files
- **Key Features**:
  - File content stored with SHA-256 integrity hashing
  - Support for both binary and text files
  - Automatic retention period management
  - Encryption-ready storage

#### 3. `validation_details`
- **Purpose**: Detailed findings from configuration validation
- **Key Fields**:
  - `config_key`: Configuration parameter being validated
  - `status`: Match/partial/mismatch status
  - `severity`: Critical/High/Medium/Low risk level
  - `expected_value` & `actual_value`: Configuration comparison

#### 4. `chat_messages`
- **Purpose**: Complete conversation history with AI assistant
- **Key Features**:
  - User and AI message tracking
  - AI model information and performance metrics
  - Token usage and response time tracking
  - Context preservation for compliance

#### 5. `audit_logs`
- **Purpose**: Comprehensive audit trail for all actions
- **Key Features**:
  - All user actions logged with timestamps
  - IP address and user agent tracking
  - Action details stored as JSON for flexibility
  - 7-year retention for compliance requirements

#### 6. `gdpr_consents`
- **Purpose**: Legal consent management
- **Key Features**:
  - Consent type tracking (data processing, storage, cookies)
  - Timestamp for consent given/withdrawn
  - Legal basis documentation
  - Purpose and scope documentation

## 🚀 Setup Instructions

### Prerequisites
- MySQL 5.7+ or MariaDB 10.2+
- Python 3.7+
- Access to MySQL root user (or create dedicated user)

### 1. Install Dependencies
```bash
cd audit_validator
pip install -r requirements.txt
```

### 2. Configure Database Connection
Set environment variables or update the database configuration in `gdpr_database.py`:

```bash
export AV_DB_USER="your_mysql_user"
export AV_DB_PASS="your_mysql_password"
export AV_DB_HOST="localhost"
export AV_DB_PORT="3306"
export AV_DB_NAME="audit_validator_db"
```

### 3. Run Database Setup
```bash
python setup_gdpr_database.py
```

This script will:
- Check MySQL connectivity
- Create the database if it doesn't exist
- Create all required tables
- Run comprehensive tests
- Provide setup confirmation

### 4. Start the Application
```bash
python custom_server.py
```

## 🔐 GDPR Compliance Features

### Data Processing Principles

#### 1. **Lawfulness, Fairness, and Transparency**
- Clear consent banner on application startup
- Detailed information about data processing
- Transparent purpose and legal basis

#### 2. **Purpose Limitation**
- Data collected only for configuration validation
- No secondary processing without consent
- Clear scope definition in consent

#### 3. **Data Minimization**
- Only necessary data is collected
- File content stored with integrity hashing
- Minimal metadata collection

#### 4. **Accuracy**
- File integrity verification via SHA-256 hashing
- Validation results stored with full context
- Audit trails for all modifications

#### 5. **Storage Limitation**
- **Operational Data**: 2 years retention
- **Audit Logs**: 7 years retention
- Automatic cleanup of expired data

#### 6. **Integrity and Confidentiality**
- Encrypted storage capabilities
- Secure file handling
- Access control and audit logging

### User Rights Implementation

#### 1. **Right to Access**
- `/api/gdpr/export/<session_id>` endpoint
- Complete data export in JSON format
- Includes all files, validation results, and chat history

#### 2. **Right to Rectification**
- Contact system administrator
- Audit trail shows all modifications
- Data integrity maintained

#### 3. **Right to Erasure**
- Contact system administrator
- Complete session deletion capability
- Audit trail preserved for compliance

#### 4. **Right to Portability**
- Structured data export
- Machine-readable format
- Complete data transfer capability

## 📊 API Endpoints

### GDPR-Specific Endpoints

#### Export Session Data
```http
GET /api/gdpr/export/{session_id}
```
Returns complete session data in GDPR-compliant format.

#### Clean Up Expired Data
```http
POST /api/gdpr/cleanup
```
Automatically removes data that has exceeded retention periods.

#### List Sessions
```http
GET /api/gdpr/sessions
```
Lists all validation sessions (placeholder implementation).

### Enhanced Existing Endpoints

All existing endpoints now include session tracking:
- File uploads are linked to sessions
- Validation results are stored with session context
- Chat messages are tracked per session
- Export actions are logged for audit

## 🔍 Data Flow

### 1. **Session Creation**
```
User opens app → GDPR consent → Session created → Database record
```

### 2. **File Upload**
```
File selected → Content hashed → Stored in database → Audit logged
```

### 3. **Validation Process**
```
Config validated → Results stored → Details logged → Audit updated
```

### 4. **Chat Interaction**
```
Message sent → AI response → Both stored → Context preserved
```

### 5. **Data Export**
```
Export requested → All data collected → GDPR metadata added → File downloaded
```

## 🛡️ Security Features

### Data Protection
- **Encryption**: File content can be encrypted at rest
- **Hashing**: SHA-256 integrity verification for all files
- **Access Control**: Session-based data isolation
- **Audit Logging**: Complete action tracking

### Privacy Safeguards
- **Data Isolation**: Each session is completely separate
- **Minimal Collection**: Only necessary data is stored
- **Retention Limits**: Automatic data lifecycle management
- **User Control**: Full data export and deletion capabilities

## 📈 Monitoring and Maintenance

### Regular Tasks
1. **Data Cleanup**: Run `/api/gdpr/cleanup` periodically
2. **Audit Review**: Monitor audit logs for unusual activity
3. **Performance**: Monitor database performance and optimize as needed
4. **Backup**: Regular database backups for disaster recovery

### Health Checks
- Database connectivity verification
- Table structure validation
- Data integrity checks
- Performance monitoring

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check MySQL service
sudo systemctl status mysql

# Test connection
mysql -u root -p -h localhost
```

#### Tables Not Created
```bash
# Run setup script again
python setup_gdpr_database.py

# Check for errors in output
```

#### Permission Denied
```bash
# Ensure MySQL user has proper privileges
GRANT ALL PRIVILEGES ON audit_validator_db.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Debug Mode
Enable verbose logging by setting `echo=True` in the database initialization:
```python
gdpr_db = get_gdpr_db(echo=True)
```

## 📋 Compliance Checklist

- [ ] GDPR consent banner implemented
- [ ] Data retention policies configured
- [ ] Audit logging enabled for all actions
- [ ] User rights implementation complete
- [ ] Data export functionality working
- [ ] Security measures in place
- [ ] Regular cleanup procedures established
- [ ] Documentation and training provided

## 🔗 Related Documentation

- [Main README](../README.md)
- [Custom Server Documentation](custom_server.py)
- [Database Schema](gdpr_database.py)
- [Setup Script](setup_gdpr_database.py)

## 📞 Support

For GDPR compliance questions or technical issues:
1. Check the troubleshooting section above
2. Review the audit logs for error details
3. Contact the system administrator
4. Refer to GDPR compliance guidelines

---

**Note**: This implementation provides a solid foundation for GDPR compliance but should be reviewed by legal professionals to ensure it meets your specific regulatory requirements.
