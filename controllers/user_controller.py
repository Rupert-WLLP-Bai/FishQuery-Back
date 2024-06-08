from flask import Blueprint, request, jsonify, session
from flask_bcrypt import generate_password_hash, check_password_hash
from model import User
from app import db
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    #role = data.get('role', 0)  # 默认为普通用户
    role = 0  # 默认为普通用户

    # 检查用户名是否已存在
    existing_user = User.query.filter(User.username == username).first()
    if existing_user:
        return jsonify({'error': 'Username already exists', 'success': False}), 400

    # 创建新用户
    new_user = User(username=username, email=email, password=generate_password_hash(password), role=role)
    try:
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user', 'success': False}), 500

    # 返回注册成功信息
    return jsonify({'message': 'Registration successful', 'success': True}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # 查找用户
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Invalid username or password', 'success': False}), 200
    elif not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid username or password', 'success': False}), 200

    # 设置会话
    session['user_id'] = user.id
    session['role'] = user.role
    print('user_id:', session['user_id'])
    print('role:', session['role'])

    return jsonify({'message': 'Login successful', 'success': True, 'user': user.to_dict()}), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    # 清除会话
    session.pop('user_id', None)
    session.pop('role', None)
    return jsonify({'message': 'Logout successful'}), 200
