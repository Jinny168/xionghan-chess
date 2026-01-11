#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查看训练数据的具体内容
"""

import pickle
import numpy as np
from mcts_config import CONFIG
import my_redis


def view_training_data_details():
    """查看训练数据的详细内容"""
    print("查看训练数据具体内容")
    print("="*50)
    
    if CONFIG['use_redis']:
        # 从Redis获取数据
        print("从Redis获取训练数据...")
        r = my_redis.get_redis_cli()
        data_count = r.llen('train_data_buffer')
        
        if data_count == 0:
            print("Redis中没有训练数据")
            return
        
        print(f"Redis中共有 {data_count} 条训练数据")
        
        # 获取前几条数据进行展示
        sample_count = min(5, data_count)  # 最多显示5条
        print(f"显示前 {sample_count} 条数据:")
        
        # 获取数据样本
        data_samples = my_redis.get_list_range(r, 'train_data_buffer', 0, sample_count-1)
        
        for i, data_item in enumerate(data_samples):
            print(f"\n数据样本 {i+1}:")
            
            if isinstance(data_item, tuple) and len(data_item) >= 3:
                state, mcts_prob, winner = data_item
                
                print(f"  状态 (state) 类型: {type(state)}")
                if hasattr(state, 'shape'):
                    print(f"  状态形状: {state.shape}")
                    print(f"  状态数据类型: {state.dtype}")
                else:
                    print(f"  状态长度: {len(state) if hasattr(state, '__len__') else 'N/A'}")
                
                print(f"  MCTS概率 (mcts_prob) 类型: {type(mcts_prob)}")
                print(f"  MCTS概率数组长度: {len(mcts_prob) if hasattr(mcts_prob, '__len__') else 'N/A'}")
                if hasattr(mcts_prob, '__len__') and len(mcts_prob) > 0:
                    print(f"  MCTS概率前5个值: {mcts_prob[:5]}")
                
                print(f"  胜者 (winner): {winner}")
                
                # 如果状态是numpy数组，显示一些统计信息
                if hasattr(state, 'shape') and hasattr(state, 'flatten'):
                    flat_state = state.flatten()
                    print(f"  状态数值范围: [{flat_state.min():.4f}, {flat_state.max():.4f}]")
                    print(f"  状态均值: {flat_state.mean():.4f}")
                
            else:
                print(f"  数据格式: {type(data_item)}")
                print(f"  数据内容: {data_item}")
    
    else:
        # 从本地文件获取数据
        print("从本地文件获取训练数据...")
        buffer_path = CONFIG['train_data_buffer_path']
        
        if not os.path.exists(buffer_path):
            print(f"本地数据文件 {buffer_path} 不存在")
            return
        
        with open(buffer_path, 'rb') as data_dict:
            data = pickle.load(data_dict)
            data_buffer = data['data_buffer']
            iters = data['iters']
        
        print(f"本地数据缓冲区大小: {len(data_buffer)}")
        print(f"总迭代次数: {iters}")
        
        if len(data_buffer) == 0:
            print("本地数据缓冲区为空")
            return
        
        # 显示前几条数据
        sample_count = min(5, len(data_buffer))
        print(f"显示前 {sample_count} 条数据:")
        
        for i in range(sample_count):
            data_item = data_buffer[i]
            print(f"\n数据样本 {i+1}:")
            
            if isinstance(data_item, tuple) and len(data_item) >= 3:
                state, mcts_prob, winner = data_item
                
                print(f"  状态 (state) 类型: {type(state)}")
                if hasattr(state, 'shape'):
                    print(f"  状态形状: {state.shape}")
                    print(f"  状态数据类型: {state.dtype}")
                else:
                    print(f"  状态长度: {len(state) if hasattr(state, '__len__') else 'N/A'}")
                
                print(f"  MCTS概率 (mcts_prob) 类型: {type(mcts_prob)}")
                print(f"  MCTS概率数组长度: {len(mcts_prob) if hasattr(mcts_prob, '__len__') else 'N/A'}")
                if hasattr(mcts_prob, '__len__') and len(mcts_prob) > 0:
                    print(f"  MCTS概率前5个值: {mcts_prob[:5]}")
                
                print(f"  胜者 (winner): {winner}")
                
                # 如果状态是numpy数组，显示一些统计信息
                if hasattr(state, 'shape') and hasattr(state, 'flatten'):
                    flat_state = state.flatten()
                    print(f"  状态数值范围: [{flat_state.min():.4f}, {flat_state.max():.4f}]")
                    print(f"  状态均值: {flat_state.mean():.4f}")
            
            else:
                print(f"  数据格式: {type(data_item)}")
                print(f"  数据内容: {data_item}")


def view_specific_data_index(index):
    """查看指定索引的数据"""
    print(f"查看索引为 {index} 的数据")
    
    if CONFIG['use_redis']:
        r = my_redis.get_redis_cli()
        data_count = r.llen('train_data_buffer')
        
        if index >= data_count:
            print(f"索引 {index} 超出范围，总共只有 {data_count} 条数据")
            return
        
        # 获取指定索引的数据
        data_bytes = r.lindex('train_data_buffer', index)
        data_item = pickle.loads(data_bytes)
        
    else:
        buffer_path = CONFIG['train_data_buffer_path']
        if not os.path.exists(buffer_path):
            print(f"本地数据文件 {buffer_path} 不存在")
            return
        
        with open(buffer_path, 'rb') as data_dict:
            data = pickle.load(data_dict)
            data_buffer = data['data_buffer']
        
        if index >= len(data_buffer):
            print(f"索引 {index} 超出范围，总共只有 {len(data_buffer)} 条数据")
            return
        
        data_item = data_buffer[index]
    
    print(f"数据索引 {index} 的详细内容:")
    if isinstance(data_item, tuple) and len(data_item) >= 3:
        state, mcts_prob, winner = data_item
        
        print(f"  状态详情:")
        print(f"    类型: {type(state)}")
        if hasattr(state, 'shape'):
            print(f"    形状: {state.shape}")
            print(f"    数据类型: {state.dtype}")
            print(f"    内存大小: {state.nbytes} bytes")
        else:
            print(f"    长度: {len(state) if hasattr(state, '__len__') else 'N/A'}")
        
        print(f"  MCTS概率详情:")
        print(f"    类型: {type(mcts_prob)}")
        print(f"    长度: {len(mcts_prob) if hasattr(mcts_prob, '__len__') else 'N/A'}")
        if hasattr(mcts_prob, '__len__'):
            prob_array = np.array(mcts_prob)
            print(f"    概率和: {prob_array.sum():.6f}")
            print(f"    最大值: {prob_array.max():.6f}")
            print(f"    最小值: {prob_array.min():.6f}")
            print(f"    非零元素数量: {(prob_array > 1e-6).sum()}")
        
        print(f"  胜者: {winner}")


if __name__ == "__main__":
    import os
    
    print("训练数据查看工具")
    print("1. 查看前几条数据的概览")
    print("2. 查看指定索引的数据详情")
    
    choice = input("请选择操作 (1 或 2): ")
    
    if choice == "1":
        view_training_data_details()
    elif choice == "2":
        try:
            idx = int(input("请输入要查看的数据索引: "))
            view_specific_data_index(idx)
        except ValueError:
            print("请输入有效的数字索引")
    else:
        print("无效选择")