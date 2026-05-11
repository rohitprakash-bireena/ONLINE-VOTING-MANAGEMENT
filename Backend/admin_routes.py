import os
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from db import get_db_connection
from security_utils import (
    get_client_ip,
    is_login_rate_limited,
    register_failed_login_attempt,
    clear_failed_login_attempts,
)

admin_bp = Blueprint('admin', __name__)
ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}
MOBILE_PATTERN = __import__('re').compile(r'^\d{10}$')


def _is_allowed_logo(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS


def _ensure_admin_mobile_column(cursor):
    cursor.execute("SHOW COLUMNS FROM admin LIKE 'mobile_number'")
    has_mobile = cursor.fetchone()
    if not has_mobile:
        cursor.execute("ALTER TABLE admin ADD COLUMN mobile_number VARCHAR(15) UNIQUE NULL")


def _delete_logo_file(logo_path):
    cursor.execute("SHOW COLUMNS FROM candidates LIKE 'logo_path'")
    has_column = cursor.fetchone()
    if not has_column:
        cursor.execute("ALTER TABLE candidates ADD COLUMN logo_path VARCHAR(255) NULL")


def _delete_logo_file(logo_path):
    if not logo_path:
        return

    normalized = os.path.normpath(logo_path).replace('\\', '/')
    if not normalized.startswith('candidate_logos/'):
        return

    absolute_logo_path = os.path.join(current_app.static_folder, normalized)
    if os.path.isfile(absolute_logo_path):
        os.remove(absolute_logo_path)


# --- Admin Register Route ---
@admin_bp.route('/admin-register', methods=['GET', 'POST'])
def admin_register():
    error = None
    success = None

    if request.method == 'POST':
        username = request.form['username'].strip()
        mobile_number = request.form.get('mobile_number', '').strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')

        if len(username) < 3:
            error = 'Username must be at least 3 characters long.'
        elif not MOBILE_PATTERN.fullmatch(mobile_number):
            error = 'Mobile number must be 10 digits.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters long.'
        elif password != confirm_password:
            error = 'Password and Confirm Password do not match.'
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                try:
                    _ensure_admin_mobile_column(cursor)
                    
                    # Check if username already exists
                    cursor.execute("SELECT id FROM admin WHERE username = %s", (username,))
                    existing_admin = cursor.fetchone()

                    if existing_admin:
                        error = 'This username is already registered.'
                    else:
                        # Check if mobile_number already exists in admin table
                        cursor.execute("SELECT id FROM admin WHERE mobile_number = %s", (mobile_number,))
                        existing_mobile_admin = cursor.fetchone()

                        if existing_mobile_admin:
                            error = 'This mobile number is already registered as admin!'
                        else:
                            # Check if mobile_number already exists in voters table
                            cursor.execute("SELECT id FROM voters WHERE mobile_number = %s", (mobile_number,))
                            existing_mobile_voter = cursor.fetchone()

                            if existing_mobile_voter:
                                error = 'This mobile number is already registered as voter!'
                            else:
                                hashed_password = generate_password_hash(password)
                                cursor.execute("INSERT INTO admin (username, mobile_number, password) VALUES (%s, %s, %s)", 
                                             (username, mobile_number, hashed_password))
                                conn.commit()
                                success = 'Admin registered successfully. Please login.'
                finally:
                    cursor.close()
                    conn.close()

            if success:
                return redirect(url_for('admin.admin_login', registered='1'))

    return render_template('admin-register.html', error=error, success=success)


# --- Check Mobile Number Availability (AJAX) ---
@admin_bp.route('/check-mobile', methods=['POST'])
def check_mobile_availability():
    from flask import jsonify
    mobile_number = request.form.get('mobile_number', '').strip()
    
    if not MOBILE_PATTERN.fullmatch(mobile_number):
        return jsonify({'available': False, 'message': 'Invalid mobile number format'})
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Ensure column exists first
            _ensure_admin_mobile_column(cursor)
            
            # Check in admin table
            cursor.execute("SELECT id FROM admin WHERE mobile_number = %s", (mobile_number,))
            if cursor.fetchone():
                return jsonify({'available': False, 'message': 'Already registered as admin'})
            
            # Check in voters table
            cursor.execute("SELECT id FROM voters WHERE mobile_number = %s", (mobile_number,))
            if cursor.fetchone():
                return jsonify({'available': False, 'message': 'Already registered as voter'})
            
            return jsonify({'available': True, 'message': 'Mobile number is available'})
        finally:
            cursor.close()
            conn.close()
    
    return jsonify({'available': False, 'message': 'Database error'})

# --- Admin Login Route ---
@admin_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    success = None

    if request.args.get('registered') == '1':
        success = 'Admin registration successful. Please login.'

    if request.method == 'POST':
        form_username = request.form['username'].strip()
        form_password = request.form['password']
        client_ip = get_client_ip(request)
        rate_key = f"admin:{client_ip}:{form_username.lower()}"

        is_limited, retry_after = is_login_rate_limited(rate_key)
        if is_limited:
            error = f'Too many failed attempts. Try again in {retry_after} seconds.'
            return render_template('admin-login.html', error=error, success=success)

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM admin WHERE username = %s", (form_username,))
            admin_user = cursor.fetchone()

            if not admin_user:
                register_failed_login_attempt(rate_key)
                error = 'Invalid Username'
            else:
                stored_password = admin_user['password']
                is_hashed = stored_password.startswith(('pbkdf2:', 'scrypt:'))

                password_ok = check_password_hash(stored_password, form_password) if is_hashed else (stored_password == form_password)
                if not password_ok:
                    register_failed_login_attempt(rate_key)
                    error = 'Invalid Username or Password'
                else:
                    # Auto-migrate legacy plaintext admin password to hashed format.
                    if not is_hashed:
                        migrated_hash = generate_password_hash(form_password)
                        cursor.execute("UPDATE admin SET password = %s WHERE id = %s", (migrated_hash, admin_user['id']))
                        conn.commit()

                    clear_failed_login_attempts(rate_key)
                    session.permanent = True
                    session['admin_loggedin'] = True
                    session['admin_username'] = admin_user['username']
                    flash('Login Successfully', 'success')
                    cursor.close()
                    conn.close()
                    return redirect(url_for('admin.admin_dashboard'))

            cursor.close()
            conn.close()

            if not admin_user:
                error = 'Invalid Username'
            elif error is None:
                error = 'Invalid Username or Password'

    return render_template('admin-login.html', error=error, success=success)


# --- Admin Dashboard Route ---
@admin_bp.route('/admin-dashboard')
def admin_dashboard():
    # Security check
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))
    
    conn = get_db_connection()
    candidates = []
    total_voters = 0
    total_votes = 0
    election_status = 'stopped'
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Dashboard Analytics Data nikalna
        cursor.execute("SELECT COUNT(*) as count FROM voters")
        total_voters = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM voters WHERE has_voted = TRUE")
        total_votes = cursor.fetchone()['count']
        
        # 2. Candidates ko unke votes ke hisaab se descending order (sabse zyada pehle) mein lana
        cursor.execute("SELECT * FROM candidates ORDER BY votes DESC")
        candidates = cursor.fetchall()

        # Election Status Check
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status'")
        status_row = cursor.fetchone()
        if status_row:
            election_status = status_row['setting_value']
        
        cursor.close()
        conn.close()

    # Turnout percentage calculate karna
    turnout_percentage = 0
    if total_voters > 0:
        turnout_percentage = round((total_votes / total_voters) * 100, 1)

    return render_template('admin-dashboard.html', 
                           username=session['admin_username'], 
                           candidates=candidates,
                           total_voters=total_voters,
                           total_votes=total_votes,
                           turnout=turnout_percentage,
                           election_status=election_status)

# --- NAYA: Election ko Start/Stop karne ka route ---
@admin_bp.route('/toggle-election', methods=['POST'])
def toggle_election():
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))
        
    new_status = request.form['status']
    if new_status not in ('started', 'stopped'):
        flash('Invalid election status.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET setting_value = %s WHERE setting_key = 'election_status'", (new_status,))
        conn.commit()
        cursor.close()
        conn.close()

    if new_status == 'started':
        flash('Election Started Successfully. Voters can now cast votes.', 'success')
    else:
        flash('Election Stopped Successfully.', 'success')
        
    return redirect(url_for('admin.admin_dashboard'))

# --- Add Candidate Route ---
@admin_bp.route('/add-candidate', methods=['POST'])
def add_candidate():
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))
        
    name = request.form['candidate_name'].strip()
    party = request.form['candidate_party'].strip()

    if len(name) < 2 or len(party) < 2:
        flash('Candidate name and party must be at least 2 characters long.', 'error')
        return redirect(url_for('admin.admin_dashboard'))
    
    logo_file = request.files.get('candidate_logo')
    logo_path = None

    if logo_file and logo_file.filename:
        raw_filename = secure_filename(logo_file.filename)
        if not _is_allowed_logo(raw_filename):
            flash('Only logo images are allowed: png, jpg, jpeg, webp, svg.', 'error')
            return redirect(url_for('admin.admin_dashboard'))

        upload_dir = os.path.join(current_app.static_folder, 'candidate_logos')
        os.makedirs(upload_dir, exist_ok=True)

        ext = raw_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"candidate_{uuid4().hex}.{ext}"
        logo_file.save(os.path.join(upload_dir, stored_filename))
        logo_path = f"candidate_logos/{stored_filename}"

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status'")
        status_row = cursor.fetchone()
        election_running = bool(status_row and status_row['setting_value'] == 'started')

        if election_running:
            flash('Cannot add candidates while election is running. Please stop election first.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.admin_dashboard'))

        _ensure_candidate_logo_column(cursor)
        cursor.execute("INSERT INTO candidates (name, party, logo_path) VALUES (%s, %s, %s)", (name, party, logo_path))
        conn.commit()
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin.admin_dashboard'))


# --- Delete Candidate Route ---
@admin_bp.route('/delete-candidate/<int:id>', methods=['POST'])
def delete_candidate(id):
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status'")
        status_row = cursor.fetchone()
        if status_row and status_row['setting_value'] == 'started':
            flash('Cannot delete candidate while election is running.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.admin_dashboard'))

        _ensure_candidate_logo_column(cursor)
        cursor.execute("SELECT id, logo_path FROM candidates WHERE id = %s", (id,))
        candidate_row = cursor.fetchone()

        if not candidate_row:
            flash('Candidate not found.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.admin_dashboard'))

        cursor.execute("DELETE FROM candidates WHERE id = %s", (id,))
        conn.commit()

        logo_path = candidate_row.get('logo_path')
        cursor.close()
        conn.close()

        _delete_logo_file(logo_path)
        flash('Candidate deleted successfully.', 'success')

    return redirect(url_for('admin.admin_dashboard'))

# --- NAYA: Manage Voters Page ---
@admin_bp.route('/manage-voters')
def manage_voters():
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))
        
    conn = get_db_connection()
    voters = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, voter_id, name, has_voted FROM voters ORDER BY id DESC")
        voters = cursor.fetchall()
        cursor.close()
        conn.close()
        
    return render_template('manage-voters.html', voters=voters)

# --- NAYA: Delete Voter Route ---
@admin_bp.route('/delete-voter/<int:id>', methods=['POST'])
def delete_voter(id):
    if 'admin_loggedin' not in session:
        return redirect(url_for('admin.admin_login'))
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status'")
        status_row = cursor.fetchone()
        if status_row and status_row['setting_value'] == 'started':
            flash('Cannot delete voters while election is running.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.manage_voters'))

        cursor.execute("SELECT has_voted FROM voters WHERE id = %s", (id,))
        voter_row = cursor.fetchone()

        if not voter_row:
            flash('Voter not found.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.manage_voters'))

        if voter_row['has_voted']:
            flash('Cannot delete a voter who has already cast a vote.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('admin.manage_voters'))

        cursor.execute("DELETE FROM voters WHERE id = %s", (id,))
        conn.commit()
        flash('Voter deleted successfully.', 'success')
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin.manage_voters'))

# --- Admin Logout Route ---
@admin_bp.route('/admin-logout')
def admin_logout():
    # Session data clear karna
    session.pop('admin_loggedin', None)
    session.pop('admin_username', None)
    return redirect(url_for('home'))