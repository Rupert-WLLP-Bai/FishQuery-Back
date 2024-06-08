from contextlib import contextmanager

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app import db
from model import Record, Fish, SearchHistory
from datetime import datetime, timezone

records_bp = Blueprint('records', __name__, url_prefix='/record')


# 获取所有记录
@records_bp.route('/records', methods=['GET'])
def get_all_records():
    try:
        # 获取所有 Record 记录,并按照创建时间倒序排列
        records = Record.query.order_by(Record.created_at.desc()).all()

        # 将 Record 对象转换为 JSON 格式
        data = []
        for record in records:
            record_dict = record.to_dict()
            # 手动处理 datetime 对象
            # record_dict['created_at'] = record_dict['created_at'].isoformat()
            # record_dict['reviewed_at'] = record_dict['reviewed_at'].isoformat()
            data.append(record_dict)

        return jsonify({'message': 'Records found', 'success': True, 'records': data}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


# 获取所有待审核的记录
@records_bp.route('/records/pending', methods=['GET'])
def get_pending_records():
    try:
        # 获取所有 is_approved 字段为 False 的 Record 记录,并按照创建时间倒序排列
        pending_records = Record.query.filter_by(reviewed_at=None).order_by(Record.created_at.desc()).all()

        # 将 Record 对象转换为 JSON 格式
        data = []
        for record in pending_records:
            record_dict = record.to_dict()
            # 手动处理 datetime 对象
            # record_dict['created_at'] = record_dict['created_at'].isoformat()
            # record_dict['reviewed_at'] = record_dict['reviewed_at'].isoformat()
            data.append(record_dict)

        return jsonify({'message': 'Records found', 'success': True, 'records': data}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500


@contextmanager
def transaction():
    try:
        with db.session.begin_nested():
            yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


@records_bp.route('/records/approve', methods=['POST'])
def approve_record():
    try:
        # 获取前端传来的 record_id、feedback 和 reviewed_by 数据
        data = request.get_json()
        record_id = data.get('record_id')
        feedback = data.get('feedback')
        reviewed_by = data.get('reviewed_by')

        # 根据 record_id 查找指定的 Record 记录
        record = Record.query.get(record_id)

        if not record:
            return jsonify({'message': 'Record not found', 'success': False}), 404

        # 更新 Record 记录的 is_approved 字段为 True,并更新 feedback、approved_at 和 reviewed_by 字段
        record.is_approved = True
        record.feedback = feedback
        record.reviewed_at = datetime.now(timezone.utc)
        record.reviewed_by = reviewed_by

        # 创建 Fish 记录并保存到数据库
        fish = Fish(
            fish_type_id=record.fish_type_id,
            image_url=record.image_url,
            tags=record.tags,
            uploaded_by=record.user_id,
            created_at=record.created_at
        )
        db.session.add(fish)
        db.session.commit()

        return jsonify({'message': 'Approve record success', 'success': True, 'record': record.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e), 'success': False}), 500


@records_bp.route('/records/reject', methods=['POST'])
def reject_record():
    try:
        # 获取前端传来的 record_id、feedback 和 reviewed_by 数据
        data = request.get_json()
        record_id = data.get('record_id')
        feedback = data.get('feedback')
        reviewed_by = data.get('reviewed_by')

        # 根据 record_id 查找指定的 Record 记录
        record = Record.query.get(record_id)

        if not record:
            return jsonify({'error': 'Record not found', 'success': False}), 404

        # 更新 Record 记录的 is_approved 字段为 False,并更新 feedback 和 rejected_at 字段
        record.is_approved = False
        record.feedback = feedback
        record.reviewed_at = datetime.now(timezone.utc)
        record.reviewed_by = reviewed_by

        # 提交更改
        db.session.commit()

        return jsonify({'message': 'Reject record success', 'success': True, 'record': record.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'message': str(e), 'success': False}), 500


# 获取用户自己提出的所有请求
@records_bp.route('/records/user', methods=['POST'])
def get_user_records():
    try:
        data = request.get_json()

        # 获取前端传来的 user_id 数据
        user_id = data.get('id')

        # 根据 user_id 查找该用户提出的所有 Record 记录
        records = Record.query.filter_by(user_id=user_id).all()

        # 构建要返回的 JSON 数据
        data = []
        for record in records:
            record_dict = record.to_dict()
            # 手动处理 datetime 对象
            # record_dict['created_at'] = record_dict['created_at'].isoformat()
            # record_dict['reviewed_at'] = record_dict['reviewed_at'].isoformat()
            data.append(record_dict)

        return jsonify({'message': 'Records found', 'success': True, 'records': data}), 200
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500


@records_bp.route('/search_history', methods=['GET'])
def get_user_search_history():
    """
    获取指定用户的搜索历史记录。

    参数:
    user_id (int): 用户 ID

    返回:
    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - search_history (list): 用户搜索历史记录列表
    """
    try:

        # 获取用户的搜索历史记录
        search_history = SearchHistory.query.order_by(SearchHistory.search_at.desc()).all()

        # 构建响应数据
        history_data = []
        for record in search_history:
            history_data.append(record.to_dict())

        return jsonify({
            'message': 'Search history retrieved',
            'success': True,
            'search_history': history_data
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Error: {e}',
            'success': False
        }), 500