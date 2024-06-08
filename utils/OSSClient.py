import oss2
from flask import current_app

class OSSClient:
    __instance = None

    @staticmethod
    def get_instance():
        if OSSClient.__instance is None:
            OSSClient()
        return OSSClient.__instance

    def __init__(self):
        if OSSClient.__instance is not None:
            raise Exception("OSSClient is a singleton class")
        else:
            self.auth = oss2.Auth(current_app.config['ACCESS_KEY_ID'], current_app.config['ACCESS_KEY_SECRET'])
            self.bucket = oss2.Bucket(self.auth, current_app.config['ENDPOINT'], current_app.config['BUCKET_NAME'])
            self.image_url_template = f'https://{current_app.config["BUCKET_NAME"]}.{current_app.config["ENDPOINT"]}/{{file_path}}'

            OSSClient.__instance = self

    def get_image_url(self, file_path):
        return self.image_url_template.format(file_path=file_path)

    def upload_file(self, file_path, file_content):
        try:
            self.bucket.put_object(file_path, file_content)
            return self.get_image_url(file_path)
        except oss2.exceptions.OssError as e:
            raise Exception(f"Error uploading file to OSS: {e}")

    def delete_file(self, file_path):
        try:
            self.bucket.delete_object(file_path)
        except oss2.exceptions.OssError as e:
            raise Exception(f"Error deleting file from OSS: {e}")


'''

# 获取OSS客户端实例
oss_client = OSSClient.get_instance()

# controller使用示例
def upload_image():
    # 获取上传的文件
    file = request.files['image']

    # 生成文件名
    filename = f"{os.path.splitext(file.filename)[0]}_{os.urandom(8).hex()}{os.path.splitext(file.filename)[1]}"

    # 上传文件到OSS
    oss_client.bucket.put_object(filename, file)

    # 返回上传成功的响应
    return {'url': f"https://{app.config['BUCKET_NAME']}.{app.config['ENDPOINT']}/{filename}"}

'''