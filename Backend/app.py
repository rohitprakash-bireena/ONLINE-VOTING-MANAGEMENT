import os
import secrets
from datetime import timedelta
from flask import Flask, render_template, jsonify, session, request, abort
from db import get_db_connection         # db.py se import
from admin_routes import admin_bp        # admin_routes.py se blueprint import
from voter_routes import voter_bp      # voter_routes.py se blueprint import

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _load_env_fallback(env_path):
    if not os.path.isfile(env_path):
        return

    with open(env_path, 'r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

# ==========================================
# 1. Folder Paths Configuration
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'Frontend', 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'Frontend', 'static')

env_path = os.path.join(BASE_DIR, '.env')
if load_dotenv:
    load_dotenv(env_path)
else:
    _load_env_fallback(env_path)


def require_env(name):
    value = os.getenv(name)
    if value is None or value.strip() == '':
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# ==========================================
# 2. Flask App Initialization
# ==========================================
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Secret key session ko secure rakhne ke liye zaroori hai (Login maintain karne ke liye)
app.secret_key = require_env('FLASK_SECRET_KEY')

# Session and cookie hardening
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = require_env('SESSION_COOKIE_SAMESITE')
app.config['SESSION_COOKIE_SECURE'] = require_env('SESSION_COOKIE_SECURE').lower() == 'true'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=int(require_env('SESSION_TIMEOUT_MINUTES')))


def generate_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {'csrf_token': generate_csrf_token}


@app.before_request
def protect_post_requests_with_csrf():
    if request.method != 'POST':
        return

    # Compatibility: keep auth entry points usable even if user submits a stale page.
    csrf_exempt_endpoints = {
        'admin.admin_login', 
        'voter.voter_login', 
        'voter.voter_register',
        'admin.admin_register',
        'admin.check_mobile_availability',
        'voter.check_voter_mobile_availability'
    }
    if request.endpoint in csrf_exempt_endpoints:
        return

    token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
    if not token or token != session.get('_csrf_token'):
        abort(400, description='Invalid CSRF token')

# ==========================================
# 3. Register Blueprints (Modularity)
# ==========================================
# Yahan hum app ko bata rahe hain ki admin ke routes admin_routes.py me hain
app.register_blueprint(admin_bp)
app.register_blueprint(voter_bp)
# ==========================================
# 4. Main Application Routes
# ==========================================
@app.route('/')
def home():
    # Database connection test karna
    conn = get_db_connection()
    
    if conn and conn.is_connected():
        db_status = "Database Connected Successfully! 🎉"
        conn.close() 
    else:
        db_status = "Database Connection Failed! ❌ Alert: Check Password and Database name."

    # index.html render karega aur status pass karega
    return render_template('index.html', status=db_status)

# Ek sample API route (Future me voting ya candidates ka data laane ke liye)
@app.route('/api/test')
def test_api():
    # Maine yahan jsonify import add kar diya hai taaki error na aaye
    return jsonify({"message": "Backend API is working good!"})

# ==========================================
# 5. Run the Server
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)