#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单查看收集到的数据（不进行解压）
"""
import redis
import pickle
from program.ai.mcts.mcts_config import CONFIG

def simple_view_data():
    """
    简单查看收集到的数据
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
            print(f"\n随机查看一些数据样本:")
            
            # 查看前10条和后10条数据（如果数据足够多）
            indices_to_check = []
            if data_length <= 20:
                indices_to_check = list(range(min(10, data_length)))
            else:
                # 前5条和后5条
                indices_to_check = list(range(5)) + list(range(data_length-5, data_length))
            
            for i in indices_to_check:
                # 获取单条数据
                data = r.lindex('train_data_buffer', i)
                if data:
                    try:
                        compressed_data = pickle.loads(data)
                        compressed_state, compressed_mcts_prob, winner = compressed_data
                        
                        print(f"数据样本 {i+1}:")
                        print(f"  - 压缩状态数组大小: {compressed_state.size if hasattr(compressed_state, 'size') else 'N/A'}")
                        print(f"  - 压缩MCTS概率数组大小: {compressed_mcts_prob.size if hasattr(compressed_mcts_prob, 'size') else 'N/A'}")
                        print(f"  - 赢家: {winner}")
                        print(f"  - 数据类型: 状态={type(compressed_state)}, 概率={type(compressed_mcts_prob)}")
                        print()
                    except Exception as e:
                        print(f"处理第 {i+1} 条数据时出错: {str(e)}")
                        print()
        else:
            print("Redis中没有数据，请确保collect.py正在运行并收集数据")
            
        # 统计赢家分布
        if data_length > 0:
            print("赢家分布统计:")
            wins_player1 = 0  # 赢家为1.0
            wins_player2 = 0  # 赢家为-1.0
            wins_unknown = 0  # 其他值
            
            # 为了效率，只统计前100条和后100条数据
            sample_indices = []
            sample_size = min(50, data_length)
            if data_length <= 100:
                sample_indices = list(range(data_length))
            else:
                sample_indices = (list(range(sample_size)) + 
                                list(range(data_length-sample_size, data_length)))
            
            for i in sample_indices:
                data = r.lindex('train_data_buffer', i)
                if data:
                    try:
                        compressed_data = pickle.loads(data)
                        _, _, winner = compressed_data
                        if winner == 1.0:
                            wins_player1 += 1
                        elif winner == -1.0:
                            wins_player2 += 1
                        else:
                            wins_unknown += 1
                    except:
                        continue
            
            print(f"  - 玩家1获胜: {wins_player1} 次")
            print(f"  - 玩家2获胜: {wins_player2} 次") 
            print(f"  - 未知结果: {wins_unknown} 次")
            print(f"  - 统计样本: {len(sample_indices)} 条数据")
            
    except Exception as e:
        print(f"连接Redis或读取数据时发生错误: {str(e)}")
        print(f"请确认Redis服务器 {CONFIG['redis_host']}:{CONFIG['redis_port']} 正常运行且可访问")

if __name__ == "__main__":
    simple_view_data()