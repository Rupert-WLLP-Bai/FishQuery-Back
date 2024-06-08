from flask_sqlalchemy import SQLAlchemy
import datetime

from app import db


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False) # Bcrypt 算法,它会产生一个 60 个字符长的字符串
    email = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.Integer, nullable=False)  # 0: normal user, 1: admin
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat()
        }

class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(2083), nullable=False)
    fish_type_id = db.Column(db.Integer, db.ForeignKey('fish_type.id'), nullable=False)
    tags = db.Column(db.String(255))  # 逗号分割 e.g., "tag1,tag2,tag3"
    is_approved = db.Column(db.Boolean, default=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    feedback = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_url': self.image_url,
            'fish_type_id': self.fish_type_id,
            'tags': self.tags,
            'is_approved': self.is_approved,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat()
        }

class FishType(db.Model):
    __tablename__ = 'fish_type'
    id = db.Column(db.Integer, primary_key=True)
    name_cn = db.Column(db.String(40), unique=True, nullable=False)  # 中文名
    name_latin = db.Column(db.String(40), unique=True, nullable=False)  # 拉丁名
    description = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name_cn': self.name_cn,
            'name_latin': self.name_latin,
            'description': self.description
        }

class Fish(db.Model):
    __tablename__ = 'fish'
    id = db.Column(db.Integer, primary_key=True)
    fish_type_id = db.Column(db.Integer, db.ForeignKey('fish_type.id'), nullable=False)
    image_url = db.Column(db.String(2083), nullable=False)
    tags = db.Column(db.String(256))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            'id': self.id,
            'fish_type_id': self.fish_type_id,
            'image_url': self.image_url,
            'tags': self.tags,
            'uploaded_by': self.uploaded_by,
            'created_at': self.created_at.isoformat()
        }
class Favorite(db.Model):
    __tablename__ = 'favorite'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fish_id = db.Column(db.Integer, db.ForeignKey('fish.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'fish_id': self.fish_id,
            'created_at': self.created_at.isoformat()
        }


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_method = db.Column(db.Integer, nullable=False)  # 0: image, 1: name, 2: tags
    search_content = db.Column(db.Text, nullable=False)  # URL, name, tags
    search_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'search_method': self.search_method,
            'search_content': self.search_content,
            'search_at': self.search_at.isoformat()
        }