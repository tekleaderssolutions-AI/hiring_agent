"""
Authentication views for login/logout
"""
import json
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from db import get_connection

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@csrf_exempt
@require_POST
def login_view(request):
    """Handle login requests"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')  # 'admin' or 'recruiter'
        
        if not username or not password or not role:
            return JsonResponse({'success': False, 'message': 'Missing credentials'}, status=400)
        
        # Hash the provided password
        password_hash = hash_password(password)
        
        # Query database
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, role, email 
            FROM users 
            WHERE username = %s AND password_hash = %s AND role = %s
        """, (username, password_hash, role))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user:
            # Set session data
            request.session['user_id'] = str(user[0])
            request.session['username'] = user[1]
            request.session['role'] = user[2]
            
            return JsonResponse({
                'success': True,
                'user': {
                    'username': user[1],
                    'role': user[2],
                    'email': user[3]
                }
            })
        else:
            return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=401)
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST", "GET"])
def logout_view(request):
    """Handle logout requests"""
    try:
        request.session.flush()
        return JsonResponse({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def check_auth(request):
    """Check if user is authenticated"""
    if 'user_id' in request.session:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'username': request.session.get('username'),
                'role': request.session.get('role')
            }
        })
    else:
        return JsonResponse({'authenticated': False})

@csrf_exempt
@require_POST
def register_view(request):
    """Handle user registration"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'recruiter')
        
        if not username or not password or not email:
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
            
        if role not in ['admin', 'recruiter']:
            return JsonResponse({'success': False, 'message': 'Invalid role'}, status=400)
            
        # Hash password
        password_hash = hash_password(password)
        
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            # Check if username exists
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return JsonResponse({'success': False, 'message': 'Username already exists'}, status=400)
            
            cur.execute("""
                INSERT INTO users (username, password_hash, role, email)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, password_hash, role, email))
            
            user_id = cur.fetchone()
            conn.commit()
            
            return JsonResponse({'success': True, 'message': 'User created successfully'})
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
