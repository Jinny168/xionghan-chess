# coding=utf-8
"""使用收集到数据进行训练"""


import pickle
import random
import time
import os
from collections import defaultdict, deque

import numpy as np

from mcts import MCTSPlayer
from mcts_config import CONFIG
from mcts_game import Game, Board
from mcts_pure import MCTS_Pure

if CONFIG['use_redis']:
    import my_redis
    import zip_array

if CONFIG['use_frame'] == 'paddle':
    from paddle_net import PolicyValueNet
elif CONFIG['use_frame'] == 'pytorch':
    from pytorch_net import PolicyValueNet
else:
    print('暂不支持您选择的框架')


# 定义整个训练流程
class TrainPipeline:

    def __init__(self, init_model=None):
        # 训练参数
        self.board = Board()
        self.game = Game(self.board)
        self.n_playout = CONFIG['play_out']
        self.c_puct = CONFIG['c_puct']
        self.learn_rate = 1e-3
        self.lr_multiplier = 1  # 基于KL自适应的调整学习率
        self.temp = 1.0
        self.batch_size = CONFIG['batch_size']  # 训练的batch大小
        self.epochs = CONFIG['epochs']  # 每次更新的train_step数量
        self.kl_targ = CONFIG['kl_targ']  # kl散度控制
        self.check_freq = 100  # 保存模型的频率
        self.game_batch_num = CONFIG['game_batch_num']  # 训练更新的次数
        self.best_win_ratio = 0.0
        self.pure_mcts_playout_num = 500
        if CONFIG['use_redis']:
            self.redis_cli = my_redis.get_redis_cli()
        self.buffer_size = CONFIG['buffer_size']
        self.data_buffer = deque(maxlen=self.buffer_size)
        # 检查是否为模型迁移，如果是从中国象棋迁移到匈汉象棋，需要特别注意
        if init_model:
            try:
                self.policy_value_net = PolicyValueNet(model_file=init_model)
                print('已加载上次最终模型')
                
                # 检查模型是否适合当前棋盘大小（匈汉象棋与传统象棋不同）
                print('警告: 正在加载预训练模型，请注意模型可能需要适应匈汉象棋的特殊规则')
                print('建议在训练初期使用较小的学习率以减少迁移影响')
                
            except Exception as e:
                # 从零开始训练
                print(f'模型路径不存在或模型格式不兼容: {e}')
                print('从零开始训练')
                self.policy_value_net = PolicyValueNet()
        else:
            print('从零开始训练')
            self.policy_value_net = PolicyValueNet()
        
        # 记录训练进度信息
        self.training_start_time = time.time()
        self.last_update_time = time.time()
        self.total_updates = 0


    def policy_evaluate(self, n_games=10):
        """
        Evaluate the trained policy by playing against the pure MCTS player
        Note: this is only for monitoring the progress of training
        """
        current_mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                         c_puct=self.c_puct,
                                         n_playout=self.n_playout)
        pure_mcts_player = MCTS_Pure(c_puct=5,
                                     n_playout=self.pure_mcts_playout_num)
        win_cnt = defaultdict(int)
        for i in range(n_games):
            winner = self.game.start_play(current_mcts_player,
                                          pure_mcts_player,
                                          start_player=i % 2 + 1,
                                          is_shown=1)
            win_cnt[winner] += 1
        win_ratio = 1.0*(win_cnt[1] + 0.5*win_cnt[-1]) / n_games
        print("num_playouts:{}, win: {}, lose: {}, tie:{}".format(
                self.pure_mcts_playout_num,
                win_cnt[1], win_cnt[2], win_cnt[-1]))
        return win_ratio


    def policy_updata(self):
        """更新策略价值网络"""
        mini_batch = random.sample(self.data_buffer, self.batch_size)
        # print(mini_batch[0][1],mini_batch[1][1])
        mini_batch = [zip_array.recovery_state_mcts_prob(data) for data in mini_batch]
        state_batch = [data[0] for data in mini_batch]
        state_batch = np.array(state_batch).astype('float32')

        mcts_probs_batch = [data[1] for data in mini_batch]
        mcts_probs_batch = np.array(mcts_probs_batch).astype('float32')

        winner_batch = [data[2] for data in mini_batch]
        winner_batch = np.array(winner_batch).astype('float32')

        # 旧的策略，旧的价值函数
        old_probs, old_v = self.policy_value_net.policy_value(state_batch)

        for i in range(self.epochs):
            loss, entropy, torch_value_loss, torch_policy_loss = self.policy_value_net.train_step(
                state_batch,
                mcts_probs_batch,
                winner_batch,
                self.learn_rate * self.lr_multiplier
            )
            # 新的策略，新的价值函数
            new_probs, new_v = self.policy_value_net.policy_value(state_batch)
        
            kl = np.mean(np.sum(old_probs * (
                np.log(old_probs + 1e-10) - np.log(new_probs + 1e-10)),
                                axis=1))
            if kl > self.kl_targ * 4:  # 如果KL散度很差，则提前终止
                break

        # 自适应调整学习率
        if kl > self.kl_targ * 2 and self.lr_multiplier > 0.1:
            self.lr_multiplier /= 1.5
        elif kl < self.kl_targ / 2 and self.lr_multiplier < 10:
            self.lr_multiplier *= 1.5
        # print(old_v.flatten(),new_v.flatten())
        explained_var_old = (1 -
                             np.var(np.array(winner_batch) - old_v.flatten()) /
                             np.var(np.array(winner_batch)))
        explained_var_new = (1 -
                             np.var(np.array(winner_batch) - new_v.flatten()) /
                             np.var(np.array(winner_batch)))

        print(("kl:{:.5f},"
               "lr_multiplier:{:.3f},"
               "value_loss:{:.3f},"
               "policy_loss:{:.3f},"
               "loss:{:.3f},"
               "entropy:{:.3f},"
               "explained_var_old:{:.3f},"
               "explained_var_new:{:.3f}"
               ).format(kl,
                        self.lr_multiplier,
                        torch_value_loss, 
                        torch_policy_loss,
                        loss,
                        entropy,
                        explained_var_old,
                        explained_var_new))

        #test code
        '''self.policy_value_net.save_model('current_policy_test.pkl')
        self.policy_value_net = PolicyValueNet(model_file='current_policy_test.pkl')
         # 新的策略，新的价值函数
        new_probs, new_v = self.policy_value_net.policy_value(state_batch)
        explained_var_old = (1 -
                             np.var(np.array(winner_batch) - old_v.flatten()) /
                             np.var(np.array(winner_batch)))
        explained_var_new = (1 -
                             np.var(np.array(winner_batch) - new_v.flatten()) /
                             np.var(np.array(winner_batch)))

        print(("kl:{:.5f},"
               "lr_multiplier:{:.3f},"
               "loss:{},"
               "entropy:{},"
               "explained_var_old:{:.9f},"
               "explained_var_new:{:.9f}"
               ).format(kl,
                        self.lr_multiplier,
                        loss,
                        entropy,
                        explained_var_old,
                        explained_var_new))'''

        
        return loss, entropy

    def run(self):
        """开始训练"""
        try:
            print(f"开始训练 - 总批次数: {self.game_batch_num}")
            print(f"训练起始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"使用数据源: {'Redis' if CONFIG['use_redis'] else '本地文件'}")
            print(f"使用框架: {CONFIG['use_frame']}")
            
            for i in range(self.game_batch_num):
                if not CONFIG['use_redis']:
                    # 检查数据文件是否存在
                    if not os.path.exists(CONFIG['train_data_buffer_path']):
                        print(f"等待训练数据文件创建... ({CONFIG['train_data_buffer_path']})")
                        time.sleep(30)  # 等待30秒后重试
                        continue
                    
                    while True:
                        try:
                            with open(CONFIG['train_data_buffer_path'], 'rb') as data_dict:
                                data_file = pickle.load(data_dict)
                                self.data_buffer = data_file['data_buffer']
                                self.iters = data_file['iters']
                                del data_file
                            print(f'已载入数据，当前数据量: {len(self.data_buffer)}')
                            break
                        except FileNotFoundError:
                            print("载入数据失败，文件未找到")
                            time.sleep(30)
                        except IOError:
                            print("载入数据失败，文件读取错误")
                            time.sleep(30)
                        except Exception as e:
                            print("载入数据失败，其他异常:", str(e))
                            time.sleep(30)
                else:
                    while True:
                        try:
                            l = len(self.data_buffer)
                            data = my_redis.get_list_range(self.redis_cli,'train_data_buffer', l if l == 0 else l - 1,-1)
                            self.data_buffer.extend(data)
                            self.iters = self.redis_cli.get('iters')
                            buffsize = self.redis_cli.llen('train_data_buffer')
                            if buffsize > self.buffer_size:
                                rn = int(self.buffer_size/10)
                                for _ in range(rn):
                                    self.redis_cli.lpop('train_data_buffer')
                            break
                        except FileNotFoundError:
                            print("载入数据失败，文件未找到")
                        except IOError:
                            print("载入数据失败，文件读取错误")
                        except Exception as e:
                            print("载入数据失败，其他异常:", str(e))
                        except:
                            print('载入数据失败')
                        time.sleep(30)

                # 计算训练进度
                progress_percent = (i + 1) / self.game_batch_num * 100
                elapsed_time = time.time() - self.training_start_time
                avg_time_per_iter = elapsed_time / (i + 1) if i + 1 > 0 else 0
                estimated_total_time = avg_time_per_iter * self.game_batch_num
                remaining_time = estimated_total_time - elapsed_time
                
                print(f'[进度: {progress_percent:.2f}%] step i {self.iters} , data_buffer len {len(self.data_buffer)}')
                print(f'已用时间: {elapsed_time/3600:.2f}小时, 预估剩余时间: {remaining_time/3600:.2f}小时')
                
                if len(self.data_buffer) > self.batch_size:
                    print(f"开始训练更新 #{i+1}, 数据批量大小: {self.batch_size}")
                    loss, entropy = self.policy_updata()
                    self.total_updates += 1
                    
                    # 保存模型
                    if CONFIG['use_frame'] == 'paddle':
                        self.policy_value_net.save_model(CONFIG['paddle_model_path'])
                        print(f'已保存Paddle模型到 {CONFIG["paddle_model_path"]}')
                    elif CONFIG['use_frame'] == 'pytorch':
                        self.policy_value_net.save_model(CONFIG['pytorch_model_path'])
                        print(f'已保存PyTorch模型到 {CONFIG["pytorch_model_path"]}')
                    else:
                        print('不支持所选框架')
                else:
                    print(f"数据量不足，当前数据量: {len(self.data_buffer)}, 需要至少: {self.batch_size}")

                print(f"等待下次更新... ({CONFIG['train_update_interval']}秒)")
                time.sleep(CONFIG['train_update_interval'])  # 每x分钟更新一次模型

                if (i + 1) % self.check_freq == 0:
                    # win_ratio = self.policy_evaluate()
                    # print("current self-play batch: {},win_ratio: {}".format(i + 1, win_ratio))
                    # self.policy_value_net.save_model('./current_policy.model')
                    # if win_ratio > self.best_win_ratio:
                    #     print("New best policy!!!!!!!!")
                    #     self.best_win_ratio = win_ratio
                    #     # update the best_policy
                    #     self.policy_value_net.save_model('./best_policy.model')
                    #     if (self.best_win_ratio == 1.0 and
                    #             self.pure_mcts_playout_num < 5000):
                    #         self.pure_mcts_playout_num += 1000
                    #         self.best_win_ratio = 0.0
                    print("current self-play batch: {}".format(i + 1))
                    self.policy_value_net.save_model('models/current_policy_batch{}.model'.format(i + 1))
                    print(f'已保存检查点模型到 models/current_policy_batch{i+1}.model')
            
            print(f"训练完成 - 总更新次数: {self.total_updates}")
            print(f"训练结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except KeyboardInterrupt:
            print('\n\rquit')
            print(f"训练被中断 - 总更新次数: {self.total_updates}")
            print(f"实际训练时间: {(time.time() - self.training_start_time)/3600:.2f}小时")


import os

if CONFIG['use_frame'] == 'paddle':
    training_pipeline = TrainPipeline(init_model='current_policy.model')
    training_pipeline.run()
elif CONFIG['use_frame'] == 'pytorch':
    training_pipeline = TrainPipeline(init_model='current_policy.pkl')
    training_pipeline.run()
else:
    print('暂不支持您选择的框架')
print('训练结束')