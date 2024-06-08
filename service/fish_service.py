import os
import tempfile
from typing import List

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

import requests
from scipy.spatial.distance import cosine
import numpy as np

from app import db
from model import Fish, FishType


class FishService:
    __instance = None

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.fish_vectors = self.load_fish_vectors()

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def load_fish_vectors(self) -> dict:
        """
        在项目启动时,下载所有 Fish 对象的图片并计算向量数据,存储在内存中
        """
        fish_vectors = {}
        fish_list = Fish.query.all()
        for fish in fish_list:
            image_vector = self.calculate_image_vector(fish.image_url)
            fish_vectors[fish.id] = image_vector
        return fish_vectors

    def find_top_k_similar_fish(self, image_vector: np.ndarray, top_k: int = 5) -> List[Fish]:
        """
        根据给定的图片 URL,查找前 top_k 个最相似的鱼类

        参数:
        image_vector (np.ndarray): 待查找的图片向量
        top_k (int): 需要返回的最相似鱼类的数量

        返回:
        List[Fish]: 前 top_k 个最相似的鱼类对象列表
        """
        similarities = []
        for fish_id, fish_vector in self.fish_vectors.items():
            distance = cosine(image_vector, fish_vector)
            similarities.append((fish_id, distance))

        similarities.sort(key=lambda x: x[1])
        top_k_fish_ids = [x[0] for x in similarities[:top_k]]

        top_k_fish = (
            db.session.query(Fish, FishType)
            .filter(Fish.id.in_(top_k_fish_ids))
            .join(FishType, Fish.fish_type_id == FishType.id)
            .all()
        )

        return top_k_fish

    def calculate_image_vector(self, image_url: str) -> np.ndarray:
        """
        下载给定图片 URL 的图片,并计算其向量表示

        参数:
        image_url (str): 图片的 URL

        返回:
        np.ndarray: 图片的向量表示
        """
        # 下载图片
        print('Downloading image:', image_url)
        response = requests.get(image_url)
        image_path = os.path.join('uploads', os.path.basename(image_url))
        with open(image_path, 'wb') as f:
            f.write(response.content)

        # 计算图片向量
        # 这里需要实现具体的图像特征提取算法,比如使用预训练的深度学习模型
        image_vector = self.extract_image_features(image_path)

        # 删除临时文件
        os.remove(image_path)

        return image_vector

    def calculate_image_vector_binary(self, image_binary: bytes) -> np.ndarray:
        """
        计算给定二进制图片的向量表示

        参数:
        image_binary (bytes): 图片的二进制数据

        返回:
        np.ndarray: 图片的向量表示
        """
        # 将二进制数据保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(image_binary)
            tmp_file.flush()
            image_path = tmp_file.name

        # 计算图片向量
        image_vector = self.extract_image_features(image_path)

        # 删除临时文件
        os.remove(image_path)

        return image_vector

    def extract_image_features(self, image_path: str) -> np.ndarray:
        # Load the pre-trained model
        model = models.resnet50(pretrained=True).to(self.device)
        model.eval()  # Set the model to evaluation mode

        # Define the image transformations
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Load the image
        image = Image.open(image_path).convert('RGB')

        # Apply the transformations
        image_tensor = transform(image).unsqueeze(0).to(self.device)

        # Forward pass to get the output from the last hidden layer
        with torch.no_grad():
            features = model(image_tensor)

        # Convert the features to a 1-D NumPy array
        features_np = features.squeeze(0).cpu().numpy().flatten()  # Flatten the array

        return features_np

