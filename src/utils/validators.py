import re
import uuid


class QueryValidator:
    """Validates and sanitizes user input"""
    
    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r'<script>',
        r'javascript:',
        r'onerror=',
        r'onclick=',
        r'eval\(',
        r'exec\(',
        r'__import__',
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('\s*OR\s*'1'\s*=\s*'1)",
        r"(\bDROP\s+TABLE\b)",
        r"(\bUNION\s+SELECT\b)",
        r"(--\s*$)",
    ]
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """Sanitize user query"""
        if not query:
            raise ValueError("Query cannot be empty")
        
        # Check length
        if len(query) > 1000:
            raise ValueError("Query too long (max 1000 characters)")
        
        # Check for dangerous patterns
        query_lower = query.lower()
        for pattern in QueryValidator.BLOCKED_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                print(f"Blocked malicious query pattern: {pattern}")
                raise ValueError("Query contains potentially malicious content")
        
        # Check for SQL injection
        for pattern in QueryValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                print(f"Blocked SQL injection attempt: {pattern}")
                raise ValueError("Query contains invalid characters")
        
        # Strip and normalize whitespace
        query = ' '.join(query.split())
        
        print(f"Query validated and sanitized: {query[:50]}...")
        return query
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """Validate session ID format"""
        if not session_id:
            return True  # Allow empty for new sessions
        
        # Must be UUID format
        try:
            uuid.UUID(session_id)
            return True
        except ValueError:
            print(f"Invalid session ID format: {session_id}")
            return False