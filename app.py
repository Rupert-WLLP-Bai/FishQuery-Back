import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler
from flask_cors import CORS
from sqlalchemy import text

from db.db import load_config


def create_app(env):
    app = Flask(__name__)
    config = load_config(env)
    app.config.update(config)

    if not app.debug and not app.testing:
        handler = RotatingFileHandler(app.config['LOGGING_FILE'], maxBytes=10000, backupCount=1)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)

    return app

env = 'development'
app = create_app(env)
db = SQLAlchemy(app)

# 注册蓝图
from controllers.user_controller import auth_bp
from controllers.picture_controller import picture_bp
from controllers.record_controller import records_bp
from controllers.favorite_controller import favorite_bp

app.register_blueprint(auth_bp)
app.register_blueprint(picture_bp)
app.register_blueprint(records_bp)
app.register_blueprint(favorite_bp)

# 允许跨域请求
CORS(app)

# 创建所有数据库表（在应用程序上下文中）
with app.app_context():
    db.create_all()


@app.route('/')
def test_db_connection():
    try:
        db.session.execute(text('SELECT 1'))
        return 'Database connection successful'
    except Exception as e:
        return f'Database connection failed: {str(e)}'

if __name__ == '__main__':
    app.run()
