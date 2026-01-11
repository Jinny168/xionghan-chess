#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试单个收集器的工作情况
"""

import os
import time
import pickle
from program.ai.mcts.mcts_config import CONFIG
from program.ai.mcts.collect import CollectPipeline


def test_single_collector():
    """测试单个收集器"""
    print("启动单个收集器进行测试...")
    
    # 创建收集器实例
    collector = CollectPipeline()
    
    print("开始收集一局自我对弈数据...")
    
    # 收集一局数据
    iters = collector.collect_selfplay_data(n_games=1)
    
    print(f"收集完成，迭代次数: {iters}")
    
    # 检查数据文件
    buffer_path = CONFIG['train_data_buffer_path']
    
    if os.path.exists(buffer_path):
        with open(buffer_path, 'rb') as data_dict:
            data = pickle.load(data_dict)
        
        data_buffer = data['data_buffer']
        iters = data['iters']
        
        print(f"数据缓冲区大小: {len(data_buffer)}")
        print(f"总迭代次数: {iters}")
        
        if len(data_buffer) > 0:
            print("成功生成训练数据！")
            # 显示第一条数据的信息
            first_data = list(data_buffer)[0] if isinstance(data_buffer, (list, tuple)) else data_buffer[0]
            state, mcts_prob, winner = first_data
            print(f"数据示例: 状态形状={state.shape}, 概率数组长度={len(mcts_prob)}, 胜者={winner}")
        else:
            print("数据缓冲区仍然为空")
    else:
        print(f"数据文件 {buffer_path} 仍未创建")


if __name__ == "__main__":
    test_single_collector()