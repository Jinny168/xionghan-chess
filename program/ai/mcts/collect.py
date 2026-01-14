"""自我对弈收集数据"""
import copy
import os
import pickle
import time
from collections import deque

from program.ai.mcts.mcts_config import CONFIG
from program.ai.mcts.mcts_game import Board, Game, move_action2move_id, move_id2move_action, flip_map
from program.ai.mcts.mcts import MCTSPlayer

if CONFIG['use_redis']:
    import program.ai.mcts.my_redis as my_redis

import program.ai.mcts.zip_array as zip_array

if CONFIG['use_frame'] == 'paddle':
    from program.ai.mcts.paddle_net import PolicyValueNet
elif CONFIG['use_frame'] == 'pytorch':
    from  program.ai.mcts.pytorch_net import PolicyValueNet
else:
    print('暂不支持您选择的框架')


# 定义整个对弈收集数据流程
class CollectPipeline:

    def __init__(self, init_model=None):
        # 象棋逻辑和棋盘
        self.board = Board()
        self.game = Game(self.board)
        # 对弈参数
        self.temp = 1  # 温度
        self.n_playout = CONFIG['play_out']  # 每次移动的模拟次数
        self.c_puct = CONFIG['c_puct']  # u的权重
        self.buffer_size = CONFIG['buffer_size']  # 经验池大小
        self.data_buffer = deque(maxlen=self.buffer_size)
        self.iters = 0
        if CONFIG['use_redis']:
            self.redis_cli = my_redis.get_redis_cli()

    # 从主体加载模型
    def load_model(self):
        if CONFIG['use_frame'] == 'paddle':
            model_path = CONFIG['paddle_model_path']
        elif CONFIG['use_frame'] == 'pytorch':
            model_path = CONFIG['pytorch_model_path']
        else:
            print('暂不支持所选框架')
        try:
            self.policy_value_net = PolicyValueNet(model_file=model_path)
            print('已加载最新模型')
        except:
            self.policy_value_net = PolicyValueNet()
            print('已加载初始模型')
        self.mcts_player = MCTSPlayer(self.policy_value_net.policy_value_fn,
                                      c_puct=self.c_puct,
                                      n_playout=self.n_playout,
                                      is_selfplay=1)

    def get_equi_data(self, play_data):
        """左右对称变换，扩充数据集一倍，加速一倍训练速度"""
        extend_data = []
        # 棋盘状态shape is [11, 13, 13], 走子概率，赢家
        for state, mcts_prob, winner in play_data:
            # 原始数据
            extend_data.append(zip_array.zip_state_mcts_prob((state, mcts_prob, winner)))
            # 水平翻转后的数据
            state_flip = state.transpose([0, 2, 1])  # 交换宽和高的维度，保持通道维度不变
            for i in range(11):  # 遍历通道维度
                for j in range(13):  # 适配13x13棋盘
                    state_flip[i][j] = state[i][12 - j]  # 水平翻转
            mcts_prob_flip = copy.deepcopy(mcts_prob)
            for i in range(len(mcts_prob_flip)):
                try:
                    # 检查索引是否在move_id2move_action范围内
                    if i < len(move_id2move_action):
                        original_action = move_id2move_action[i]
                        flipped_action = flip_map(original_action)
                        # 检查翻转后的动作是否在合法动作字典中
                        if flipped_action in move_action2move_id:
                            flipped_id = move_action2move_id[flipped_action]
                            # 确保翻转后的ID在mcts_prob范围内
                            if flipped_id < len(mcts_prob):
                                mcts_prob_flip[i] = mcts_prob[flipped_id]
                            else:
                                mcts_prob_flip[i] = 0.0  # 如果翻转后的ID超出范围，设置为0
                        else:
                            # 如果翻转后的动作无效，设置为0
                            mcts_prob_flip[i] = 0.0
                    else:
                        # 如果索引超出范围，设置为0
                        mcts_prob_flip[i] = 0.0
                except (KeyError, IndexError):
                    # 如果出现任何错误，设置为0
                    mcts_prob_flip[i] = 0.0
            extend_data.append(zip_array.zip_state_mcts_prob((state_flip, mcts_prob_flip, winner)))
        return extend_data

    def collect_selfplay_data(self, n_games=1):
        # 收集自我对弈的数据
        for i in range(n_games):
            self.load_model()  # 从本体处加载最新模型
            winner, play_data = self.game.start_self_play(self.mcts_player, temp=self.temp, is_shown=False)
            play_data = list(play_data)[:]
            self.episode_len = len(play_data)
            # 增加数据
            play_data = self.get_equi_data(play_data)
            if CONFIG['use_redis']:
                while True:
                    try:
                        for d in play_data:
                            self.redis_cli.rpush('train_data_buffer', pickle.dumps(d))
                        self.redis_cli.incr('iters')
                        self.iters = self.redis_cli.get('iters')
                        print("存储完成")
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
            else:
                if os.path.exists(CONFIG['train_data_buffer_path']):
                    while True:
                        try:
                            with open(CONFIG['train_data_buffer_path'], 'rb') as data_dict:
                                data_file = pickle.load(data_dict)
                                self.data_buffer = deque(maxlen=self.buffer_size)
                                self.data_buffer.extend(data_file['data_buffer'])
                                self.iters = data_file['iters']
                                del data_file
                                self.iters += 1
                                self.data_buffer.extend(play_data)
                            print('成功载入数据')
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
                else:
                    print(f"训练数据文件不存在，将在 {CONFIG['train_data_buffer_path']} 创建新的数据文件")
                    self.data_buffer.extend(play_data)
                    self.iters = 0  # 初始化迭代计数
                    self.iters += 1
            data_dict = {'data_buffer': self.data_buffer, 'iters': self.iters}
            with open(CONFIG['train_data_buffer_path'], 'wb') as data_file:
                pickle.dump(data_dict, data_file)
        return self.iters

    def run(self):
        """开始收集数据"""
        try:
            while True:
                iters = self.collect_selfplay_data()
                print('batch i: {}, episode_len: {}'.format(
                    iters, self.episode_len))
        except KeyboardInterrupt:
            print('\n\rquit')


# 根据框架选择正确的初始化
if __name__ == '__main__':
    if CONFIG['use_frame'] == 'paddle':
        collecting_pipeline = CollectPipeline(init_model=CONFIG['paddle_model_path'])
    elif CONFIG['use_frame'] == 'pytorch':
        collecting_pipeline = CollectPipeline(init_model=CONFIG['pytorch_model_path'])
    else:
        print('暂不支持您选择的框架')
        exit()
    collecting_pipeline.run()