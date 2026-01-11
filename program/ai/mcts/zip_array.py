# coding=utf-8
import numpy as np

num2array = dict({1 : np.array([1, 0, 0, 0, 0, 0, 0, 0, 0]), 2: np.array([0, 1, 0, 0, 0, 0, 0, 0, 0]),
                  3: np.array([0, 0, 1, 0, 0, 0, 0, 0, 0]), 4: np.array([0, 0, 0, 1, 0, 0, 0, 0, 0]),
                  5: np.array([0, 0, 0, 0, 1, 0, 0, 0, 0]), 6: np.array([0, 0, 0, 0, 0, 1, 0, 0, 0]),
                  7: np.array([0, 0, 0, 0, 0, 0, 1, 0, 0]), 8: np.array([0, 0, 0, 0, 0, 0, 0, 1, 0]),
                  9: np.array([0, 0, 0, 0, 0, 0, 0, 0, 1]), 10: np.array([-1, 0, 0, 0, 0, 0, 0, 0, 0]),
                  11: np.array([0, -1, 0, 0, 0, 0, 0, 0, 0]), 12: np.array([0, 0, -1, 0, 0, 0, 0, 0, 0]),
                  13: np.array([0, 0, 0, -1, 0, 0, 0, 0, 0]), 14: np.array([0, 0, 0, 0, -1, 0, 0, 0, 0]),
                  15: np.array([0, 0, 0, 0, 0, -1, 0, 0, 0]), 16: np.array([0, 0, 0, 0, 0, 0, -1, 0, 0]),
                  17: np.array([0, 0, 0, 0, 0, 0, 0, -1, 0]), 18: np.array([0, 0, 0, 0, 0, 0, 0, 0, -1]),
                  19: np.array([0, 0, 0, 0, 0, 0, 0, 0, 0])})
def array2num(array):
    return list(filter(lambda string: (num2array[string] == array).all(), num2array))[0]

# 压缩存储
def state_list2state_num_array(state_list):
    _state_array = np.zeros([13, 13, 9])  # 适配13x13棋盘，9种棋子
    for i in range(13):
        for j in range(13):
            _state_array[i][j] = num2array[state_list[i][j]]
    return _state_array

#(state, mcts_prob, winner) ((11,13,13),7712,1) => ((11,169),(2,3856),1)
def zip_state_mcts_prob(tuple):
    state, mcts_prob, winner = tuple
    state = state.reshape((11,-1))  # 适配[11,13,13]棋盘
    mcts_prob = mcts_prob.reshape((2,-1))
    state = zip_array(state)
    mcts_prob = zip_array(mcts_prob)
    return state,mcts_prob,winner

def recovery_state_mcts_prob(tuple):
    state, mcts_prob, winner = tuple
    state = recovery_array(state)
    mcts_prob = recovery_array(mcts_prob)
    state = state.reshape((11,13,13))  # 适配[11,13,13]棋盘
    mcts_prob = mcts_prob.reshape(7712)  # 适配13x13棋盘的动作空间大小
    return state,mcts_prob,winner

def zip_array(array, data=0.):  # 压缩成稀疏数组
    zip_res = []
    zip_res.append([len(array), len(array[0]), 0])
    for i in range(len(array)):
        for j in range(len(array[0])):
            if array[i][j] != data:
                zip_res.append([i, j, array[i][j]])
    res = np.array(zip_res)
    return res


def recovery_array(array, data=0.):  # 恢复数组
    recovery_res = []
    for i in range(np.int32(array[0][0])):
        recovery_res.append([data for i in range(np.int32(array[0][1]))])
    for i in range(1, len(array)):
        # print(len(recovery_res[0]))
        recovery_res[np.int32(array[i][0])][np.int32(array[i][1])] = array[i][2]
    return np.array(recovery_res)