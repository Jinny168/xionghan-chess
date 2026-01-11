#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Redis连接和数据收集功能
"""

import os
import time
import pickle


from tqdm import tqdm
from program.ai.mcts.mcts_config import CONFIG
from program.ai.mcts.collect import CollectPipeline
import program.ai.mcts.my_redis as my_redis


def test_redis_connection():
    """测试Redis连接是否正常"""
    try:
        r = my_redis.get_redis_cli()
        # 测试连接
        r.ping()
        print("✓ Redis连接成功！")
        print(f"  当前配置: host={CONFIG['redis_host']}, port={CONFIG['redis_port']}, db={CONFIG['redis_db']}")

        # 获取当前数据量
        current_count = r.llen('train_data_buffer')
        print(f"  当前Redis中已有 {current_count} 条训练数据")
        
        return r
    except Exception as e:
        print(f"✗ Redis连接失败: {str(e)}")
        return None


def clear_redis_data(redis_client):
    """清空Redis中的训练数据"""
    try:
        # 只清空train_data_buffer列表，保留其他数据
        removed_count = redis_client.llen('train_data_buffer')
        redis_client.delete('train_data_buffer')
        print(f"  已清空Redis中的 {removed_count} 条旧数据")
        return True
    except Exception as e:
        print(f"  清空Redis数据失败: {str(e)}")
        return False


def test_single_collector_with_progress():
    """测试单个收集器并添加进度条"""
    print("启动单个收集器进行测试...")
    
    # 测试Redis连接
    redis_client = test_redis_connection()
    if not redis_client:
        print("无法连接到Redis，终止测试")
        return
    
    # 询问是否清空Redis数据
    current_count = redis_client.llen('train_data_buffer')
    if current_count > 0:
        response = input(f"Redis中已有 {current_count} 条数据，是否清空？(y/N): ")
        if response.lower() == 'y':
            if not clear_redis_data(redis_client):
                print("清空数据失败，继续使用现有数据")
        else:
            print("保留现有数据，新数据将追加到列表末尾")
    
    # 创建收集器实例
    collector = CollectPipeline()
    
    print("开始收集一局自我对弈数据...")
    
    # 添加进度条
    print("正在进行自我对弈...")
    with tqdm(total=1, desc="收集游戏数据") as pbar:
        # 收集一局数据
        iters = collector.collect_selfplay_data(n_games=1)
        pbar.update(1)
    
    print(f"收集完成，迭代次数: {iters}")
    
    # 检查Redis中的数据
    new_count = redis_client.llen('train_data_buffer')
    print(f"Redis中现在有 {new_count} 条训练数据")
    
    # 获取最后几条数据进行验证
    if new_count > 0:
        # 获取最后3条数据（如果有的话）
        sample_count = min(3, new_count)
        samples = my_redis.get_list_range(redis_client, 'train_data_buffer', -sample_count, -1)
        
        print(f"\n最后 {sample_count} 条数据样本:")
        for i, data in enumerate(samples):
            if isinstance(data, bytes):
                try:
                    data = pickle.loads(data)
                except:
                    pass
            
            if isinstance(data, tuple) and len(data) >= 3:
                state, mcts_prob, winner = data
                print(f"  样本 {i+1}: 状态形状={getattr(state, 'shape', 'N/A')}, "
                      f"概率数组长度={len(mcts_prob) if hasattr(mcts_prob, '__len__') else 'N/A'}, "
                      f"胜者={winner}")
            else:
                print(f"  样本 {i+1}: 数据格式={type(data)}")
    
    print("\n✓ 数据收集测试完成!")
    print(f"  总计数据条数: {new_count}")
    print(f"  当前迭代次数: {iters}")


def check_redis_status():
    """检查Redis状态"""
    redis_client = test_redis_connection()
    if redis_client:
        # 获取Redis信息
        info = redis_client.info()
        print(f"  Redis版本: {info.get('redis_version', 'Unknown')}")
        print(f"  连接客户端数: {info.get('connected_clients', 'Unknown')}")
        print(f"  使用内存: {info.get('used_memory_human', 'Unknown')}")
        
        # 检查特定键
        keys = ['train_data_buffer', 'iters', 'test']
        for key in keys:
            if redis_client.exists(key):
                length = redis_client.llen(key) if redis_client.type(key) == b'list' else 'N/A'
                print(f"  键 '{key}' 存在，类型: {redis_client.type(key).decode()}, 长度: {length}")
            else:
                print(f"  键 '{key}' 不存在")


if __name__ == "__main__":
    print("Redis连接和数据收集测试")
    print("="*50)
    
    action = input("请选择操作: \n1. 检查Redis状态 \n2. 测试数据收集 \n请输入 (1 或 2): ")
    
    if action == "1":
        check_redis_status()
    elif action == "2":
        test_single_collector_with_progress()
    else:
        print("无效输入，退出")