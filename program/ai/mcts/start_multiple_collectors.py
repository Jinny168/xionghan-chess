#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启动多个collect.py进程的脚本
"""

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
import my_redis
from mcts_config import CONFIG


class MultiCollector:
    def __init__(self, num_processes=4, target_data_count=None):
        self.num_processes = num_processes
        self.processes = []
        self.running = True
        # 记录每个进程的统计数据
        self.process_stats = {}
        # 目标数据量
        self.target_data_count = target_data_count
        # Redis客户端
        self.redis_client = None
        
        # 初始化Redis连接
        if CONFIG['use_redis']:
            try:
                self.redis_client = my_redis.get_redis_cli()
            except Exception as e:
                print(f"无法连接到Redis: {e}")
                print("请确保Redis服务器正在运行")

    def start_single_process(self, process_id):
        """启动单个collect.py进程"""
        try:
            # 使用绝对路径确保安全性
            collect_script = os.path.join(os.getcwd(), "collect.py")
            cmd = [sys.executable, collect_script]
            env = os.environ.copy()
            env["COLLECTOR_ID"] = str(process_id)  # 为每个进程设置标识
            
            print(f"启动收集进程 #{process_id}")
            # 使用shell=False避免命令注入风险
            process = subprocess.Popen(cmd, cwd=os.getcwd(), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 初始化进程统计信息
            self.process_stats[process_id] = {
                'start_time': datetime.now(),
                'restart_count': 0,
                'last_check_time': time.time(),
                'data_count': 0  # 记录数据收集数量
            }
            
            return process
        except Exception as e:
            print(f"启动进程 #{process_id} 失败: {e}")
            return None

    def start_all_processes(self):
        """启动所有收集进程"""
        print(f"准备启动 {self.num_processes} 个数据收集进程...")
        
        for i in range(self.num_processes):
            process = self.start_single_process(i)
            if process:
                self.processes.append((i, process))
            time.sleep(2)  # 避免同时启动造成资源竞争
        
        print(f"已启动 {len(self.processes)} 个数据收集进程")
        
        # 监控进程状态
        while self.running:
            active_processes = 0
            for pid, process in self.processes[:]:  # 使用切片复制列表以避免修改时的问题
                if process.poll() is not None:  # 进程已退出
                    print(f"进程 #{pid} 已退出，返回码: {process.returncode}")
                    # 记录重启次数
                    self.process_stats[pid]['restart_count'] += 1
                    
                    # 从列表中移除已退出的进程
                    self.processes.remove((pid, process))
                    
                    if self.running:  # 如果还在运行，尝试重启
                        print(f"尝试重启进程 #{pid}")
                        new_process = self.start_single_process(pid)
                        if new_process:
                            self.processes.append((pid, new_process))
                        else:
                            print(f"进程 #{pid} 重启失败")
                else:
                    active_processes += 1
            
            # 检查数据收集情况
            if self.redis_client:
                try:
                    current_data_count = self.redis_client.llen('train_data_buffer')
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 当前数据量: {current_data_count}", end="")
                    
                    if self.target_data_count:
                        print(f", 目标: {self.target_data_count}", end="")
                        if current_data_count >= self.target_data_count:
                            print(f"\n已达到目标数据量 {self.target_data_count}，停止所有进程...")
                            self.stop_all_processes()
                            return
                    print("")  # 换行
                except Exception as e:
                    print(f"检查Redis数据量失败: {e}")
            
            # 每30秒输出一次总体状态
            if int(time.time()) % 30 == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 运行中的进程数: {active_processes}/{self.num_processes}")
                
                # 输出每个进程的统计信息
                for pid in range(self.num_processes):
                    if pid in self.process_stats:
                        stats = self.process_stats[pid]
                        uptime = datetime.now() - stats['start_time']
                        print(f"  进程 #{pid}: 运行时间 {uptime}, 重启次数 {stats['restart_count']}")
            
            time.sleep(5)  # 每5秒检查一次进程状态

    def stop_all_processes(self):
        """停止所有收集进程"""
        print("正在停止所有数据收集进程...")
        self.running = False
        
        for pid, process in self.processes:
            try:
                process.terminate()  # 尝试优雅终止
                process.wait(timeout=5)  # 等待5秒
            except subprocess.TimeoutExpired:
                print(f"进程 #{pid} 未能优雅终止，强制杀死...")
                process.kill()  # 强制杀死
            except Exception as e:
                print(f"终止进程 #{pid} 时出错: {e}")
        
        print("所有进程已停止")
        
        # 输出最终统计信息
        print("\n最终统计信息:")
        for pid, stats in self.process_stats.items():
            uptime = datetime.now() - stats['start_time']
            print(f"  进程 #{pid}: 运行时间 {uptime}, 重启次数 {stats['restart_count']}")


def signal_handler(signum, frame):
    print("\n收到终止信号，正在停止所有进程...")
    collector.stop_all_processes()
    sys.exit(0)


if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 默认启动4个进程，可以通过命令行参数调整
    num_procs = 4
    target_data_count = None
    
    if len(sys.argv) > 1:
        try:
            num_procs = int(sys.argv[1])
            if num_procs <= 0:
                print("进程数必须大于0，默认使用4个进程")
                num_procs = 4
        except ValueError:
            print("第一个参数必须是数字，默认使用4个进程")
    
    if len(sys.argv) > 2:
        try:
            target_data_count = int(sys.argv[2])
            if target_data_count <= 0:
                print("目标数据量必须大于0，不限制数据量")
                target_data_count = None
        except ValueError:
            print("第二个参数（目标数据量）必须是数字，不限制数据量")
    
    print(f"启动 {num_procs} 个数据收集进程")
    if target_data_count:
        print(f"目标数据量: {target_data_count}")
    else:
        print("目标数据量: 无限制")
    
    collector = MultiCollector(num_procs, target_data_count)
    
    try:
        collector.start_all_processes()
    except KeyboardInterrupt:
        print("\n收到键盘中断信号")
        collector.stop_all_processes()
    except Exception as e:
        print(f"发生错误: {e}")
        collector.stop_all_processes()