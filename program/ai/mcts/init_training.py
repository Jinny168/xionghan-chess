#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化训练环境，创建必要文件和目录
"""

import os
import pickle
from collections import deque
from mcts_config import CONFIG


def init_training_environment():
    """初始化训练环境"""
    print("初始化匈汉象棋AI训练环境...")
    
    # 创建models目录
    models_dir = "models"
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)
        print(f"创建目录: {models_dir}")
    else:
        print(f"目录已存在: {models_dir}")
    
    # 检查或创建初始数据缓冲文件
    buffer_path = CONFIG['train_data_buffer_path']
    if not os.path.exists(buffer_path):
        print(f"创建初始数据缓冲文件: {buffer_path}")
        # 创建一个空的数据缓冲
        data_dict = {
            'data_buffer': deque(maxlen=CONFIG['buffer_size']),
            'iters': 0
        }
        with open(buffer_path, 'wb') as f:
            pickle.dump(data_dict, f)
        print("初始数据缓冲文件创建完成")
    else:
        print(f"数据缓冲文件已存在: {buffer_path}")
    
    # 检查模型文件是否存在
    model_path = CONFIG['pytorch_model_path'] if CONFIG['use_frame'] == 'pytorch' else CONFIG['paddle_model_path']
    if not os.path.exists(model_path):
        print(f"模型文件不存在: {model_path}，训练将从随机初始化开始")
    else:
        print(f"模型文件已存在: {model_path}")
    
    print("初始化完成！")
    print("\n接下来的步骤:")
    print("1. 运行 collect.py 生成训练数据")
    print("2. 在另一个终端运行 train.py 开始训练")
    print("\n或者运行多个 collect.py 实例以加速数据生成")


if __name__ == "__main__":
    init_training_environment()