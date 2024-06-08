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
        """
        图像特征向量可以用于计算图像之间的相似度。
        一般来说,使用余弦相似度是一种常见的方法来比较两个向量的相似程度。
        余弦相似度可以反映两个向量之间的夹角大小,值域范围为[-1, 1]。
        当两个向量完全相同时,余弦相似度为1;当两个向量完全正交时,余弦相似度为0;当两个向量完全相反时,余弦相似度为-1
        """

        # Load the pre-trained model
        # ResNet-50 是目前最广泛使用的卷积神经网络模型之一,它在各种图像分类任务上表现都非常优秀
        model = models.resnet50(pretrained=True).to(self.device)
        # 将模型设置为评估模式,禁用诸如 Dropout 和 BatchNorm 等层的训练行为
        model.eval()  # Set the model to evaluation mode

        # Define the image transformations
        transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224), # 从图像中心裁剪出 224x224 大小的区域
            transforms.ToTensor(), # 将 PIL 图像转换为 PyTorch 张量
            # 使用 ImageNet 数据集的平均值和标准差对图像进行归一化
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Load the image
        # 从给定路径加载图像,并确保图像格式为 RGB
        image = Image.open(image_path).convert('RGB')

        # Apply the transformations
        # 对图像应用上述定义的转换操作,得到一个 PyTorch 张量
        # 在第一个维度上添加一个批量维度,因为模型的输入需要是一个批量的图像
        image_tensor = transform(image).unsqueeze(0).to(self.device)

        # Forward pass to get the output from the last hidden layer
        # 对转换后的图像tensor进行前向传播,得到模型最后一个隐藏层的输出
        with torch.no_grad():
            features = model(image_tensor)

        # Convert the features to a 1-D NumPy array
        # 去掉批量维度,得到一个 1D 的特征向量
        # 将 PyTorch 张量转换为 NumPy 数组,并展平成一维
        features_np = features.squeeze(0).cpu().numpy().flatten()  # Flatten the array

        return features_np

