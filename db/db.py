import json


def load_config(env):
    with open('db/configuration.json', 'r') as config_file:
        config = json.load(config_file)

    db_config = config['database']['mysql']

    print(db_config['user'][env])

    return {
        'SECRET_KEY': config['app']['secret_key'],
        'SQLALCHEMY_DATABASE_URI': f"mysql+pymysql://{db_config['user'][env]}:{db_config['password'][env]}@{db_config['host'][env]}/{db_config['database'][env]}",
        'ACCESS_KEY_ID': config['oss']['access_key_id'],
        'ACCESS_KEY_SECRET': config['oss']['access_key_secret'],
        'ENDPOINT': config['oss']['endpoint'],
        'BUCKET_NAME': config['oss']['bucket_name'],
        'LOGGING_LEVEL': config['logging']['level'],
        'LOGGING_FILE': config['logging']['file']
    }
