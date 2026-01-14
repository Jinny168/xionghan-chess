#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查训练数据生成状态
"""

import os
import pickle

import program.ai.mcts.my_redis as my_redis
from program.ai.mcts.mcts_config import CONFIG


def check_data_status():
    """检查训练数据状态"""
    # 检查是否使用Redis
    if CONFIG['use_redis']:
        print("当前配置: 使用Redis存储训练数据")
        print(f"Redis服务器: {CONFIG['redis_host']}:{CONFIG['redis_port']}, 数据库: {CONFIG['redis_db']}")
        
        try:
            # 连接Redis
            r = my_redis.get_redis_cli()
            
            # 检查Redis中训练数据的数量
            data_count = r.llen('train_data_buffer')
            print(f"Redis中训练数据条数: {data_count}")
            
            # 获取迭代次数
            iters = r.get('iters')
            if iters is not None:
                iters = int(iters)
                print(f"总迭代次数: {iters}")
            else:
                print("总迭代次数: 未设置")
            
            # 如果有数据，显示前几条的示例
            if data_count > 0:
                print(f"\n数据示例 (前3条):")
                # 获取前3条数据
                sample_indices = min(3, data_count)
                sample_data = my_redis.get_list_range(r, 'train_data_buffer', 0, sample_indices-1)
                
                for i, item in enumerate(sample_data):
                    if isinstance(item, tuple) and len(item) >= 3:
                        state, mcts_prob, winner = item
                        print(f"  数据 {i+1}: 状态形状={getattr(state, 'shape', 'N/A')}, 概率数组长度={len(mcts_prob) if hasattr(mcts_prob, '__len__') else 'N/A'}, 胜者={winner}")
                    else:
                        print(f"  数据 {i+1}: 格式未知 - {type(item)}")
            else:
                print("\nRedis中训练数据为空，等待收集器生成数据...")
                
        except Exception as e:
            print(f"连接Redis或读取数据时出错: {e}")
            print("请确保Redis服务器正在运行且配置正确")
    else:
        # 如果不使用Redis，则检查本地文件
        buffer_path = CONFIG['train_data_buffer_path']
        
        if not os.path.exists(buffer_path):
            print(f"训练数据文件不存在: {buffer_path}")
            print("请先运行 collect.py 生成一些训练数据")
            return
        
        try:
            # 读取数据缓冲
            with open(buffer_path, 'rb') as data_dict:
                data = pickle.load(data_dict)
            
            data_buffer = data['data_buffer']
            iters = data['iters']
            
            print(f"训练数据文件: {buffer_path}")
            print(f"数据缓冲区大小: {len(data_buffer)}")
            print(f"总迭代次数: {iters}")
            print(f"最大缓冲区大小: {CONFIG['buffer_size']}")
            
            if len(data_buffer) > 0:
                print("\n数据示例 (前3条):")
                for i, item in enumerate(list(data_buffer)[:3]):
                    state, mcts_prob, winner = item
                    print(f"  数据 {i+1}: 状态形状={state.shape}, 概率数组长度={len(mcts_prob)}, 胜者={winner}")
            else:
                print("\n数据缓冲区为空，等待收集器生成数据...")
                
        except Exception as e:
            print(f"读取数据文件时出错: {e}")


def monitor_data_generation():
    """持续监控数据生成"""
    import time
    
    print("开始监控数据生成...")
    print("按 Ctrl+C 停止监控")
    
    if CONFIG['use_redis']:
        print(f"当前监控Redis: {CONFIG['redis_host']}:{CONFIG['redis_port']}, 数据库: {CONFIG['redis_db']}")
        
        try:
            r = my_redis.get_redis_cli()
            
            while True:
                # 检查Redis中训练数据的数量
                data_count = r.llen('train_data_buffer')
                
                # 获取迭代次数
                iters = r.get('iters')
                if iters is not None:
                    iters = int(iters)
                else:
                    iters = 0
                
                print(f"[{time.strftime('%H:%M:%S')}] Redis数据条数: {data_count}, 总迭代次数: {iters}")
                
                time.sleep(10)  # 每10秒检查一次
                
        except KeyboardInterrupt:
            print("\n监控已停止")
        except Exception as e:
            print(f"\n连接Redis时出错: {e}")
    else:
        # 如果不使用Redis，则监控本地文件
        try:
            while True:
                buffer_path = CONFIG['train_data_buffer_path']
                
                if os.path.exists(buffer_path):
                    with open(buffer_path, 'rb') as data_dict:
                        data = pickle.load(data_dict)
                    
                    data_buffer = data['data_buffer']
                    iters = data['iters']
                    
                    print(f"[{time.strftime('%H:%M:%S')}] 数据缓冲区大小: {len(data_buffer)}, 总迭代次数: {iters}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 数据文件不存在，等待创建...")
                
                time.sleep(10)  # 每10秒检查一次
                
        except KeyboardInterrupt:
            print("\n监控已停止")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        monitor_data_generation()
    else:
        check_data_status()