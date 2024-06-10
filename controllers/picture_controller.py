import json
import os
from datetime import datetime, UTC
import numpy as np

import sqlalchemy
from flask import Blueprint, request, jsonify, current_app, session
from sqlalchemy import func
from werkzeug.utils import secure_filename
from model import Record, FishType, Fish, SearchHistory
from model import User
from app import db
from service.fish_service import FishService
from utils.OSSClient import OSSClient

picture_bp = Blueprint('picture', __name__, url_prefix='/pictures')


# 需要数据为：user_id image（文件） fish_name_latin tags
@picture_bp.route('/upload', methods=['POST'])
def upload_picture():
    # 获取 OSS 客户端实例
    oss_client = OSSClient.get_instance()

    # 获取前端传来的数据
    data = request.form.get('data')
    data_json = json.loads(data)

    user_id = data_json.get('user_id')
    #user_id = session.get('user_id')
    #print('user_id:', session['user_id'])

    if not user_id:
        return jsonify({'message': 'User not logged in', 'success': False}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found', 'success': False}), 404

    file = request.files.get('image')
    if not file:
        return jsonify({'message': 'No image file uploaded', 'success': False}), 400

    fish_name_latin = data_json.get('name_latin')
    if not fish_name_latin:
        return jsonify({'message': 'Fish Latin name is required', 'success': False}), 400

    # 根据 fish_name_latin 查找对应的 FishType 记录
    fish_type = FishType.query.filter_by(name_latin=fish_name_latin).first()
    if not fish_type:
        return jsonify({'message': 'Fish type not found', 'success': False}), 404

    tags = data_json.get('tags')

    # 获取图片
    filename = secure_filename(file.filename)

    # 上传文件到 OSS
    try:
        image_url = oss_client.upload_file(filename, file.read())
    except Exception as e:
        return jsonify({'message': str(e), 'success': False}), 500

    # 创建新的 Record 记录
    new_record = Record(
        user_id=user.id,
        image_url=image_url,
        fish_type_id=fish_type.id,
        tags=tags,
        created_at=datetime.now(UTC),
        feedback=None,
        is_approved=False
    )

    try:
        db.session.add(new_record)
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'message': 'Error saving record to database', 'success': False}), 500

    return jsonify({'message': 'Picture uploaded successfully', 'record': new_record.to_dict(), 'success': True}), 200


@picture_bp.route('/fish_type', methods=['GET'])
def get_fishtypes():
    """
    获取所有的 FishType 记录。

    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - fish_types (list): FishType 对象列表
    """
    try:
        # 查询所有的 FishType 记录
        fish_types = FishType.query.all()

        # 将 FishType 对象转换为 JSON 格式
        data = [fish_type.to_dict() for fish_type in fish_types]

        return jsonify({'message': 'FishType list retrieved successfully', 'success': True, 'fish_types': data}), 200

    except Exception as e:
        return jsonify({'message': f'Error: {e}', 'success': False, 'fish_types': []}), 500


@picture_bp.route('/add_fish_type', methods=['POST'])
def upload_new_fishtype():
    try:
        # 获取前端传来的数据
        data = request.get_json()
        name_cn = data.get('name_cn')
        name_latin = data.get('name_latin')
        description = data.get('description')

        print('name_cn:', name_cn)
        print('name_latin:', name_latin)
        print('description:', description)

        # 检查是否有必要的数据
        if not name_cn or not name_latin or not description:
            return jsonify({'message': 'Missing required data', 'success': False}), 400

        # 创建 FishType 记录并保存到数据库
        new_fish_type = FishType(
            name_cn=name_cn,
            name_latin=name_latin,
            description=description
        )
        db.session.add(new_fish_type)
        db.session.commit()

        return jsonify({'message': 'New fish type uploaded successfully', 'success': True,
                        'fish_type': new_fish_type.to_dict()}), 201

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@picture_bp.route('/fish_type', methods=['POST'])
def edit_fishtype():
    try:
        # 获取前端传来的数据
        data = request.get_json()
        fish_type_id = data.get('fish_type_id')
        name_cn = data.get('name_cn')
        name_latin = data.get('name_latin')
        description = data.get('description')

        # 根据 fish_type_id 查找对应的 FishType 记录
        fish_type = FishType.query.get(fish_type_id)
        if not fish_type:
            return jsonify({'error': 'Fish type not found', 'success': False}), 404

        # 更新鱼类型信息
        fish_type.name_cn = name_cn
        fish_type.name_latin = name_latin
        fish_type.description = description

        db.session.commit()

        return jsonify(
            {'message': 'Fish type updated successfully', 'success': True, 'fish_type': fish_type.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@picture_bp.route('/name_search', methods=['GET'])
def get_fish_by_fish_type_name():
    """
    根据 FishType 的 name_cn 或 name_latin 精确匹配对应的 Fish 列表

    参数:
    name (str): FishType 的中文名或拉丁名

    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - fish_list (list): 匹配的 Fish 对象列表
    """
    # 从路径参数中获取 name
    name = request.args.get('name')
    count = request.args.get('count')
    user_id = request.args.get('user_id')

    if not name:
        return jsonify({'message': 'no name', 'success': False}), 401

    try:
        with db.session.begin():
            # 先根据 name_cn 查找 FishType
            fish_type = FishType.query.filter(func.lower(FishType.name_cn) == func.lower(name)).first()

            # 如果没有找到,则根据 name_latin 查找
            if not fish_type:
                fish_type = FishType.query.filter(func.lower(FishType.name_latin) == func.lower(name)).first()

            # 如果 FishType 不存在,返回一个包含错误信息的 JSON 响应
            if not fish_type:
                return jsonify(
                    {'message': f'No FishType found for name: {name}', 'success': False, 'fish_list': []}), 404

            # 根据 fish_type_id 查找关联的 Fish 列表
            fish_list = Fish.query.filter_by(fish_type_id=fish_type.id).limit(count).all()

            # 将 Fish 对象转换为 JSON 格式,并添加 FishType 的名称信息
            data = []
            for fish in fish_list:
                fish_dict = fish.to_dict()
                fish_dict['name_cn'] = fish_type.name_cn
                fish_dict['name_latin'] = fish_type.name_latin
                data.append(fish_dict)

            # 记录搜索历史
            search_history = SearchHistory(
                user_id=user_id,  # 当前用户 ID
                search_method=1,  # 0: image, 1: name, 2: tags
                search_content=name
            )
            db.session.add(search_history)

        return jsonify({'message': 'Fish list found', 'success': True, 'fish_list': data}), 200

    except Exception as e:
        # 处理异常情况
        db.session.rollback()
        return jsonify({'message': f'Error: {e}', 'success': False, 'fish_list': []}), 500


@picture_bp.route('/keyword_search', methods=['GET'])
def get_fish_by_keyword():
    """
    根据关键词搜索 Fish 列表

    参数:
    keyword (str): 搜索关键词

    返回:
    JSON 格式的响应,包含以下字段:
    - message (str): 状态消息
    - success (bool): 是否成功
    - fish_list (list): 匹配的 Fish 对象列表
    """

    # 从路径参数中获取 name
    keyword = request.args.get('keyword')
    count = request.args.get('count')
    user_id = request.args.get('user_id')
    if not keyword:
        return jsonify({'message': 'no keyword', 'success': False}), 401

    try:
        with db.session.begin():
            # 根据关键词搜索 Fish 列表,并联查 FishType 表获取中文名和拉丁名
            fish_list = db.session.query(
                Fish,
                FishType.name_cn,
                FishType.name_latin
            ).join(
                FishType, Fish.fish_type_id == FishType.id
            ).filter(
                func.lower(Fish.tags).contains(func.lower(keyword))
            ).limit(count).all()

            # 将查询结果转换为 JSON 格式
            data = []
            for fish, name_cn, name_latin in fish_list:
                fish_dict = fish.to_dict()
                fish_dict['name_cn'] = name_cn
                fish_dict['name_latin'] = name_latin
                data.append(fish_dict)

            # 记录搜索历史
            search_history = SearchHistory(
                user_id=user_id,  # 当前用户 ID
                search_method=2,  # 0: image, 1: name, 2: tags
                search_content=keyword
            )
            db.session.add(search_history)

        return jsonify({'message': 'Fish list found', 'success': True, 'fish_list': data}), 200

    except Exception as e:
        # 处理异常情况
        db.session.rollback()
        return jsonify({'message': f'Error: {e}', 'success': False, 'fish_list': []}), 500


@picture_bp.route('/picture_search', methods=['POST'])
def get_fish_by_picture():
    # image通过文件上传
    # 获取前端传来的数据
    data = request.form.get('data')
    data_json = json.loads(data)
    count = data_json.get('count')  # 获取top_count的图片
    user_id=data_json.get('user_id')

    file = request.files.get('image')
    if not file:
        return jsonify({'message': 'No image file uploaded', 'success': False}), 400

    # 获取图片
    filename = secure_filename(file.filename)
    file.save(os.path.join('uploads', filename))
    image_path = os.path.join('uploads', filename)

    # 获取 fish_service 的单例实例
    fish_service = FishService.get_instance()

    input_vector = fish_service.extract_image_features(image_path)

    # 计算top-k相似度
    top_k_fish = fish_service.find_top_k_similar_fish(input_vector, top_k=count)

    # 记录搜索历史
    search_history = SearchHistory(
        user_id=user_id,  # 当前用户 ID
        search_method=0,  # 0: image, 1: name, 2: tags
        search_content="图片搜索"
    )
    db.session.add(search_history)
    db.session.commit()

    fish_res = {
        'id': 0,
        'fish_type_id': 0,
        'image_url': '',
        'tags': '',
        'uploaded_by': 0,
        'created_at': None,
        'name_cn': '',
        'name_latin': '',
        'description': ''
    }

    fish_res_list = []

    '''
    for fish, fish_type in top_k_fish:
        fish_res['id'] = fish.id
        fish_res['fish_type_id'] = fish.fish_type_id
        fish_res['image_url'] = fish.image_url
        fish_res['tags'] = fish.tags
        fish_res['uploaded_by'] = fish.uploaded_by
        fish_res['created_at'] = fish.created_at
        fish_res['name_cn'] = fish_type.name_cn
        fish_res['name_latin'] = fish_type.name_latin
        fish_res['description'] = fish_type.description
        fish_res_list.append(fish_res)
    '''
    for fish, fish_type in top_k_fish:
        fish_res = {
            'id': fish.id,
            'fish_type_id': fish.fish_type_id,
            'image_url': fish.image_url,
            'tags': fish.tags,
            'uploaded_by': fish.uploaded_by,
            'created_at': fish.created_at,
            'name_cn': fish_type.name_cn,
            'name_latin': fish_type.name_latin,
            'description': fish_type.description
        }
        fish_res_list.append(fish_res)

    fish_res_list.reverse()

    # 获取返回值
    return jsonify({
        'message': 'Top K similar fish found',
        'success': True,
        'fish_list': fish_res_list
    })
