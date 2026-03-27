from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import re
from db import get_db_connection
from security_utils import (
    get_client_ip,
    is_login_rate_limited,
    register_failed_login_attempt,
    clear_failed_login_attempts,
)

# Naya blueprint banaya voter ke liye
voter_bp = Blueprint('voter', __name__)
VOTER_ID_PATTERN = re.compile(r'^[A-Z]{3}\d{7}$')
MOBILE_PATTERN = re.compile(r'^\d{10}$')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _ensure_voter_contact_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM voters LIKE 'mobile_number'")
    has_mobile = cursor.fetchone()
    if not has_mobile:
        cursor.execute("ALTER TABLE voters ADD COLUMN mobile_number VARCHAR(15) NULL")

    cursor.execute("SHOW COLUMNS FROM voters LIKE 'email'")
    has_email = cursor.fetchone()
    if not has_email:
        cursor.execute("ALTER TABLE voters ADD COLUMN email VARCHAR(120) NULL")

# --- Voter Registration Route ---
@voter_bp.route('/voter-register', methods=['GET', 'POST'])
def voter_register():
    error = None
    success = None
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        voter_id = request.form['voter_id'].strip().upper()
        mobile_number = request.form.get('mobile_number', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form['password']

        if len(name) < 3:
            error = "Name must be at least 3 characters long."
        elif not VOTER_ID_PATTERN.fullmatch(voter_id):
            error = "Voter ID format must be like ABC1234567."
        elif not MOBILE_PATTERN.fullmatch(mobile_number):
            error = "Mobile number must be 10 digits."
        elif not EMAIL_PATTERN.fullmatch(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            # VIVA POINT: Password ko hash (encrypt) kar rahe hain security ke liye
            hashed_password = generate_password_hash(password)

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    _ensure_voter_contact_columns(cursor)
                    # Default has_voted FALSE rahega
                    cursor.execute(
                        "INSERT INTO voters (voter_id, password, name, mobile_number, email) VALUES (%s, %s, %s, %s, %s)",
                        (voter_id, hashed_password, name, mobile_number, email)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return redirect(url_for('voter.voter_login', registered='1'))
                except mysql.connector.IntegrityError:
                    # Agar koi same Voter ID dubara daalega toh error aayega (Kyunki DB me UNIQUE constraint hai)
                    error = "This Voter ID is already registered!"
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()

    return render_template('voter-register.html', error=error, success=success)

# --- Voter Login Route ---
@voter_bp.route('/voter-login', methods=['GET', 'POST'])
def voter_login():
    error = None
    success = None

    if request.args.get('registered') == '1':
        success = 'Registration successful! Please login to continue.'

    if request.method == 'POST':
        form_voter_id = request.form['voter_id'].strip().upper()
        form_password = request.form['password']
        client_ip = get_client_ip(request)
        rate_key = f"voter:{client_ip}:{form_voter_id}"

        is_limited, retry_after = is_login_rate_limited(rate_key)
        if is_limited:
            error = f'Too many failed attempts. Try again in {retry_after} seconds.'
            return render_template('voter-login.html', error=error, success=success)

        if not VOTER_ID_PATTERN.fullmatch(form_voter_id):
            error = 'Voter ID format must be like ABC1234567'
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM voters WHERE voter_id = %s", (form_voter_id,))
                voter = cursor.fetchone()
                cursor.close()
                conn.close()

                if not voter:
                    register_failed_login_attempt(rate_key)
                    error = 'Invalid Voter ID'
                elif not check_password_hash(voter['password'], form_password):
                    register_failed_login_attempt(rate_key)
                    error = 'Invalid Voter ID or Password'
                else:
                    # Login successful
                    clear_failed_login_attempts(rate_key)
                    session.permanent = True
                    session['voter_loggedin'] = True
                    session['voter_id'] = voter['voter_id']
                    session['voter_name'] = voter['name']
                    session['has_voted'] = voter['has_voted']
                    session['show_voter_login_alert'] = True
                    return redirect(url_for('voter.voter_dashboard'))

    return render_template('voter-login.html', error=error, success=success)


# --- Main Voting Dashboard ---
@voter_bp.route('/voter-dashboard')
def voter_dashboard():
    if 'voter_loggedin' not in session:
        return redirect(url_for('voter.voter_login'))
    
    conn = get_db_connection()
    candidates = []
    election_status = 'stopped'
    
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Check Election Status First
        cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status'")
        status_row = cursor.fetchone()
        if status_row:
            election_status = status_row['setting_value']
            
        cursor.execute("SELECT * FROM candidates")
        candidates = cursor.fetchall()
        cursor.close()
        conn.close()

    show_login_alert = session.pop('show_voter_login_alert', False)

    return render_template('voter-dashboard.html', 
                           voter_name=session['voter_name'], 
                           has_voted=session['has_voted'],
                           candidates=candidates,
                           election_status=election_status,
                           show_login_alert=show_login_alert)

# --- Cast Vote Logic ---
@voter_bp.route('/cast-vote', methods=['POST'])
def cast_vote():
    if 'voter_loggedin' not in session:
        return redirect(url_for('voter.voter_login'))

    if session.get('has_voted'):
        return redirect(url_for('voter.voter_dashboard'))

    candidate_id = request.form.get('candidate_id')
    voter_id = session['voter_id']

    if not candidate_id or not str(candidate_id).isdigit():
        return redirect(url_for('voter.voter_dashboard'))

    conn = get_db_connection()
    if conn:
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        try:
            # Check election status within the same transaction
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key = 'election_status' FOR UPDATE")
            status_row = cursor.fetchone()

            if not status_row or status_row['setting_value'] == 'stopped':
                conn.rollback()
                return redirect(url_for('voter.voter_dashboard'))

            # Lock voter row and ensure one-vote-only guarantee
            cursor.execute("SELECT has_voted FROM voters WHERE voter_id = %s FOR UPDATE", (voter_id,))
            voter_row = cursor.fetchone()
            if not voter_row or voter_row['has_voted']:
                conn.rollback()
                session['has_voted'] = True
                return redirect(url_for('voter.voter_dashboard'))

            # Validate candidate exists before increment
            cursor.execute("SELECT id FROM candidates WHERE id = %s FOR UPDATE", (candidate_id,))
            candidate_row = cursor.fetchone()
            if not candidate_row:
                conn.rollback()
                return redirect(url_for('voter.voter_dashboard'))

            cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE id = %s", (candidate_id,))
            cursor.execute("UPDATE voters SET has_voted = TRUE WHERE voter_id = %s AND has_voted = FALSE", (voter_id,))

            if cursor.rowcount != 1:
                conn.rollback()
                return redirect(url_for('voter.voter_dashboard'))

            conn.commit()
            session['has_voted'] = True
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
        finally:
            cursor.close()
            conn.close()

    return redirect(url_for('voter.voter_dashboard'))

# --- Voter Logout ---
@voter_bp.route('/voter-logout')
def voter_logout():
    session.clear() # Voter ka saara data session se hta do
    return redirect(url_for('home'))   