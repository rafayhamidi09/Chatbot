import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DB_Host = os.getenv("DB_HOST", "127.0.0.1")
DB_Port = os.getenv("DB_PORT", "5432")
DB_name = os.getenv("DB_NAME", "mychatdb")
DB_user = os.getenv("DB_USER", "postgres")
DB_password = os.getenv("DB_PASSWORD", "2009")


def DB_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_Host,
            port=DB_Port,
            database=DB_name,
            user=DB_user,
            password=DB_password
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


# ================= USERS =================

def create_user(username, email, password):
    """Create a new user with username, email, and password"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if user already exists by username or email
        cur.execute(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (username, email)
        )
        if cur.fetchone():
            cur.close()
            conn.close()
            return None
        
        # Hash password and insert user
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id, username, email",
            (username, email, hashed_pw.decode("utf-8"))
        )
        user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return None


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            return None
        
        # Check password
        try:
            if bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
                return user
        except ValueError:
            return None
        
        return None
    except Exception as e:
        logger.error(f"Authenticate user error: {e}")
        return None


def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT id, username, email FROM users WHERE id = %s",
            (user_id,)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Get user by ID error: {e}")
        return None


def update_user_profile(user_id, username=None, email=None, password=None):
    """Update user profile information"""
    conn = None
    try:
        conn = DB_connection()
        cur = conn.cursor()
        
        updates = []
        params = []
        
        if username:
            updates.append("username = %s")
            params.append(username)
        
        if email:
            updates.append("email = %s")
            params.append(email)
        
        if password:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            updates.append("password = %s")
            params.append(hashed.decode("utf-8"))
        
        if updates:
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
            cur.execute(query, params)
            conn.commit()
            cur.close()
            conn.close()
            return True
        
        cur.close()
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Update user profile error: {e}")
        if conn:
            conn.rollback()
        return False


# ================= CONVERSATIONS =================

def create_conversation(user_id, title="New Chat"):
    """Create a new conversation"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING *",
            (user_id, title)
        )
        conv = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return conv
    except Exception as e:
        logger.error(f"Create conversation error: {e}")
        return None


def get_conversations(user_id):
    """Get all conversations for a user"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return []


def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        conn = DB_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        return False


# ================= MESSAGES =================

def save_message(conversation_id, content, role):
    """Save a message to a conversation"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "INSERT INTO messages (conversation_id, content, role) VALUES (%s, %s, %s) RETURNING *",
            (conversation_id, content, role)
        )
        msg = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return msg
    except Exception as e:
        logger.error(f"Save message error: {e}")
        return None


def get_messages(conversation_id):
    """Get all messages in a conversation"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return []


# ================= ADMIN =================

def get_all_users():
    """Get all users (admin)"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT id, username, email, created_at FROM users")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        return []


def get_all_conversations_admin():
    """Get all conversations (admin)"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT c.id, c.title, u.username, u.email, c.created_at
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            ORDER BY c.created_at DESC
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Get all conversations error: {e}")
        return []


# ================= SETTINGS =================

def get_user_settings(user_id):
    """Get user settings"""
    try:
        conn = DB_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT language, theme FROM user_settings WHERE user_id = %s",
            (user_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return {"language": row["language"], "theme": row["theme"]}
        return {"language": "en", "theme": "dark"}
    except Exception as e:
        logger.error(f"Get user settings error: {e}")
        return {"language": "en", "theme": "dark"}


def save_user_settings(user_id, language=None, theme=None):
    """Save or update user settings"""
    conn = None
    try:
        conn = DB_connection()
        cur = conn.cursor()
        
        # Check if settings exist
        cur.execute("SELECT 1 FROM user_settings WHERE user_id = %s", (user_id,))
        exists = cur.fetchone()
        
        if exists:
            # Update existing settings
            updates = []
            params = []
            
            if language:
                updates.append("language = %s")
                params.append(language)
            
            if theme:
                updates.append("theme = %s")
                params.append(theme)
            
            if updates:
                params.append(user_id)
                query = f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = %s"
                cur.execute(query, params)
        else:
            # Insert new settings
            cur.execute(
                "INSERT INTO user_settings (user_id, language, theme) VALUES (%s, %s, %s)",
                (user_id, language or "en", theme or "dark")
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save user settings error: {e}")
        if conn:
            conn.rollback()
        return False


# ================= FEEDBACK =================

def save_feedback(user_id, message):
    """Save user feedback"""
    conn = None
    try:
        conn = DB_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO feedback (user_id, message) VALUES (%s, %s)",
            (user_id, message)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Save feedback error: {e}")
        if conn:
            conn.rollback()
        return False
print("hello world")
a = 1   