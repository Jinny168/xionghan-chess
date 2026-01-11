#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看Redis中收集到的数据
"""
import redis
import pickle
import numpy as np
from program.ai.mcts.mcts_config import CONFIG
from program.ai.mcts.zip_array import recovery_state_mcts_prob

def view_redis_data():
    """
    从Redis中查看收集到的数据
    """
    try:
        # 连接到Redis
        r = redis.StrictRedis(
            host=CONFIG['redis_host'], 
            port=CONFIG['redis_port'], 
            db=CONFIG['redis_db']
        )
        
        # 获取数据列表长度
        data_length = r.llen('train_data_buffer')
        print(f"Redis中 'train_data_buffer' 列表包含 {data_length} 条数据")
        
        # 获取迭代次数
        iters = r.get('iters')
        print(f"迭代次数: {iters}")
        
        if data_length > 0:
            print(f"\n前5条数据样本:")
            # 获取前5条数据
            data_list = r.lrange('train_data_buffer', 0, 4)
            
            for i, data in enumerate(data_list):
                # 解析数据
                compressed_data = pickle.loads(data)
                compressed_state, compressed_mcts_prob, winner = compressed_data
                
                print(f"\n--- 数据样本 {i+1} ---")
                print(f"压缩状态形状: {compressed_state.shape if hasattr(compressed_state, 'shape') else type(compressed_state)}")
                print(f"压缩MCTS概率形状: {compressed_mcts_prob.shape if hasattr(compressed_mcts_prob, 'shape') else type(compressed_mcts_prob)}")
                print(f"赢家: {winner}")
                
                # 尝试解压数据，如果失败则跳过
                try:
                    state, mcts_prob, winner = recovery_state_mcts_prob(compressed_data)
                    
                    print(f"解压后状态矩阵形状: {state.shape}")
                    print(f"解压后MCTS概率数组长度: {len(mcts_prob)}")
                    
                    # 显示一些统计信息
                    print(f"状态矩阵统计 - 最小值: {np.min(state):.4f}, 最大值: {np.max(state):.4f}, 平均值: {np.mean(state):.4f}")
                    print(f"MCTS概率统计 - 最小值: {np.min(mcts_prob):.6f}, 最大值: {np.max(mcts_prob):.6f}, 和: {np.sum(mcts_prob):.4f}")
                    
                    # 显示一些最高概率的移动
                    top_indices = np.argsort(mcts_prob)[-5:][::-1]  # 获取前5个最大值的索引
                    print(f"前5个最高概率的移动索引和概率: {[(idx, mcts_prob[idx]) for idx in top_indices]}")
                except Exception as e:
                    print(f"解压数据时发生错误: {str(e)}")
                    print(f"压缩状态数组形状: {compressed_state.shape if hasattr(compressed_state, 'shape') else 'N/A'}")
                    print(f"压缩MCTS概率数组形状: {compressed_mcts_prob.shape if hasattr(compressed_mcts_prob, 'shape') else 'N/A'}")
                    if hasattr(compressed_state, 'shape'):
                        print(f"压缩状态数组大小: {compressed_state.size if hasattr(compressed_state, 'size') else 'N/A'}")
                    if hasattr(compressed_mcts_prob, 'shape'):
                        print(f"压缩MCTS概率数组大小: {compressed_mcts_prob.size if hasattr(compressed_mcts_prob, 'size') else 'N/A'}")
        else:
            print("Redis中没有数据，请确保collect.py正在运行并收集数据")
            
    except Exception as e:
        print(f"连接Redis或读取数据时发生错误: {str(e)}")
        print(f"请确认Redis服务器 {CONFIG['redis_host']}:{CONFIG['redis_port']} 正常运行且可访问")

if __name__ == "__main__":
    view_redis_data()