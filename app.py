from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from groq import Groq
import os
import logging
from dotenv import load_dotenv

from DB_handling import (
    create_user,
    authenticate_user,
    create_conversation,
    get_conversations,
    save_message,
    get_messages,
    get_all_users,
    get_all_conversations_admin,
    delete_conversation,
    update_user_profile,
    get_user_settings,
    save_user_settings,
    save_feedback,
    get_user_by_id
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "my-secret-key-123")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=False,
)

# Configure CORS properly
CORS(app, 
     supports_credentials=True, 
     origins=[
         "http://localhost:5000",
         "http://127.0.0.1:5000",
         "http://localhost:5500",
         "http://127.0.0.1:5500"
     ],
     methods=["GET", "POST", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type"]
)

# Initialize Groq client
try:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
    client = Groq(api_key=groq_api_key)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    client = None


# ================ HEALTH CHECK ================

@app.route("/health", methods=["GET"])
def health():
    """Check if server is running"""
    return jsonify({"status": "ok", "message": "Flask is running"}), 200


# ================ AUTH ROUTES ================

@app.route("/signup", methods=["POST"])
def signup():
    """Create a new user account with username, email, and password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not email or not password:
            return jsonify({"error": "Username, email, and password are required"}), 400
        
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        
        if "@" not in email or "." not in email:
            return jsonify({"error": "Invalid email format"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        user = create_user(username, email, password)
        if not user:
            return jsonify({"error": "Username or email already exists"}), 409
        
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user["email"]
        save_user_settings(user["id"], language="en", theme="dark")
        
        logger.info(f"New user created: {username} ({email})")
        return jsonify({
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "message": "Account created successfully"
        }), 201
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/login", methods=["POST", "GET"])
def login():
    """Login with username and password"""
    try:
        if request.method == "GET":
            return jsonify({"message": "Login endpoint is working"}), 200
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        user = authenticate_user(username, password)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401
        
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["email"] = user.get("email")
        
        logger.info(f"User logged in: {username}")
        return jsonify({
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email"),
            "message": "Logged in successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/logout", methods=["POST"])
def logout():
    """Logout user and clear session"""
    try:
        username = session.get("username", "Unknown")
        session.clear()
        logger.info(f"User logged out: {username}")
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/me", methods=["GET"])
def me():
    """Get current logged-in user information"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_id = session["user_id"]
        user = get_user_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        settings = get_user_settings(user_id)
        
        return jsonify({
            "id": user_id,
            "username": session.get("username"),
            "email": user.get("email"),
            "settings": settings
        }), 200
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/update_profile", methods=["POST"])
def update_profile():
    """Update user profile (username, email, password)"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_id = session["user_id"]
        username = data.get("username", "").strip() if data.get("username") else None
        email = data.get("email", "").strip() if data.get("email") else None
        password = data.get("password", "").strip() if data.get("password") else None
        
        if email and ("@" not in email or "." not in email):
            return jsonify({"error": "Invalid email format"}), 400
        
        if password and len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        success = update_user_profile(user_id, username, email, password)
        
        if success:
            if username:
                session["username"] = username
            if email:
                session["email"] = email
            logger.info(f"Profile updated for user {user_id}")
            return jsonify({"message": "Profile updated successfully"}), 200
        else:
            return jsonify({"error": "Update failed"}), 500
            
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/settings", methods=["GET", "POST"])
def user_settings():
    """Get or update user settings (language, theme)"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        user_id = session["user_id"]
        
        if request.method == "GET":
            settings = get_user_settings(user_id)
            return jsonify(settings), 200
        
        else:  # POST
            data = request.get_json()
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            language = data.get("language")
            theme = data.get("theme")
            
            save_user_settings(user_id, language, theme)
            logger.info(f"Settings updated for user {user_id}")
            return jsonify({"message": "Settings saved successfully"}), 200
            
    except Exception as e:
        logger.error(f"Settings error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/feedback", methods=["POST"])
def feedback():
    """Submit user feedback"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        message = data.get("message", "").strip()
        
        if not message:
            return jsonify({"error": "Feedback message cannot be empty"}), 400
        
        save_feedback(session["user_id"], message)
        logger.info(f"Feedback received from user {session['user_id']}")
        return jsonify({"message": "Thank you for your feedback"}), 200
        
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ================ CHAT ROUTES ================

@app.route("/chat", methods=["POST"])
def chat():
    """Process chat message and secure pipeline handling with PostgreSQL and Groq"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if not client:
            return jsonify({"error": "AI service not available"}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_message = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")
        
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        user_id = session["user_id"]
        
        # 1. Ensure conversation exists in DB
        if not conversation_id:
            conv = create_conversation(user_id, title=user_message[:30] + "...")
            if not conv:
                return jsonify({"error": "Failed to create conversation"}), 500
            conversation_id = conv["id"]
        
        # 2. Append incoming message to PostgreSQL
        save_message(conversation_id, user_message, "user")
        
        # 3. Pull total conversation landscape history from DB
        history = get_messages(conversation_id)
        
        # 4. Format context logs for Groq payload
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        if history:
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 5. Extract response using valid Groq-hosted open engine
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2024
        )
        
        reply = response.choices[0].message.content
        
        # 6. Save final response payload to PostgreSQL
        save_message(conversation_id, reply, "assistant")
        
        logger.info(f"Chat message processed for user {user_id}")
        return jsonify({
            "reply": reply,
            "conversation_id": conversation_id
        }), 200
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": "Failed to process chat request"}), 500


# ================ CONVERSATION ROUTES ================

@app.route("/conversations", methods=["GET"])
def conversations():
    """Get all conversations for the current user"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        convs = get_conversations(session["user_id"])
        return jsonify(convs), 200
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/messages/<int:conversation_id>", methods=["GET"])
def messages(conversation_id):
    """Get all messages in a conversation"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if conversation_id <= 0:
            return jsonify({"error": "Invalid conversation ID"}), 400
        
        msgs = get_messages(conversation_id)
        return jsonify(msgs), 200
        
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_conv(conversation_id):
    """Delete a conversation"""
    try:
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        if conversation_id <= 0:
            return jsonify({"error": "Invalid conversation ID"}), 400
        
        delete_conversation(conversation_id)
        logger.info(f"Conversation {conversation_id} deleted by user {session['user_id']}")
        return jsonify({"status": "deleted"}), 200
        
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ================ ADMIN ROUTES ================

@app.route("/admin/users", methods=["GET"])
def admin_users():
    """Get all users (admin endpoint)"""
    try:
        users = get_all_users()
        return jsonify(users), 200
    except Exception as e:
        logger.error(f"Admin get users error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/admin/conversations", methods=["GET"])
def admin_conversations():
    """Get all conversations (admin endpoint)"""
    try:
        convs = get_all_conversations_admin()
        return jsonify(convs), 200
    except Exception as e:
        logger.error(f"Admin get conversations error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ================ FRONTEND ================

@app.route("/")
def index():
    """Serve the main HTML page"""
    return render_template("index.html")


# ================ ERROR HANDLERS ================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting Flask app on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)