from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from model import Favorite, Fish, User
from app import db

favorite_bp = Blueprint('favorite', __name__, url_prefix='/favorites')

@favorite_bp.route('/', methods=['GET'])
def get_user_favorites():
    """
    获取指定用户的收藏夹列表。

    参数:
    user_id (int): 用户 ID

    返回:
    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - favorites (list): 收藏夹列表,每个元素是一个字典,包含鱼类信息
    """
    try:
        user_id = request.args.get('user_id')

        # 获取用户的收藏夹
        favorites = Favorite.query.filter_by(user_id=user_id).all()
        favorite_info = [
            favorite.to_dict() for favorite in favorites
        ]

        return jsonify({
            'message': 'Favorites retrieved successfully',
            'success': True,
            'favorites': favorite_info
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Error: {e}',
            'success': False
        }), 500


@favorite_bp.route('/', methods=['POST'])
def add_to_favorites():
    """
    将指定的鱼类添加到用户的收藏夹。

    参数:
    user_id (int): 用户 ID
    fish_id (int): 鱼类 ID

    返回:
    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - favorite_info (dict): 新添加的收藏夹项目信息
    """
    try:
        #获取前端数据
        data = request.get_json()
        user_id= data.get('user_id')
        fish_id = data.get('fish_id')

        # 检查是否已经收藏过该鱼类
        existing_favorite = Favorite.query.filter_by(user_id=user_id, fish_id=fish_id).first()
        if existing_favorite:
            return jsonify({
                'message': 'Fish already in favorites',
                'success': False
            }), 423

        # 创建新的收藏夹项目
        new_favorite = Favorite(user_id=user_id, fish_id=fish_id,
                                created_at=datetime.now(timezone.utc))
        db.session.add(new_favorite)
        db.session.commit()

        return jsonify({
            'message': 'Fish added to favorites',
            'success': True,
            'favorite_info': new_favorite.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Error: {e}',
            'success': False
        }), 500


@favorite_bp.route('/favorite', methods=['DELETE'])
def remove_from_favorites():
    """
    从用户的收藏夹中删除指定的项目。

    参数:
    user_id (int): 用户 ID
    favorite_id (int): 收藏夹项目 ID

    返回:
    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    """
    try:

        data = request.get_json()
        favorite_id = data.get('favorite_id')

        # 查找要删除的收藏夹项目
        favorite = Favorite.query.filter_by(id=favorite_id).first()
        if not favorite:
            return jsonify({
                'message': 'Favorite not found',
                'success': False
            }), 404

        # 删除收藏夹项目
        db.session.delete(favorite)
        db.session.commit()

        return jsonify({
            'message': 'Favorite removed successfully',
            'success': True
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Error: {e}',
            'success': False
        }), 500