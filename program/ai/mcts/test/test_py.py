# coding=utf-8
from collections import deque  # 这个队列用来判断长将或长捉

import torch
import torch.nn.functional as F


def try_gpu():
    """如果GPU可用则返回GPU设备，否则返回CPU设备"""
    if torch.cuda.is_available():
        return torch.device('cuda')
    else:
        return torch.device('cpu')

que = deque(maxlen=2)

def softmax(X):
    exp_X = torch.exp(X)
    partition = exp_X.sum(dim=1, keepdim=True)
    return exp_X/partition

for i in range(4):
    tensor = torch.randn(size=(4,4)).to(try_gpu())
    tensor = tensor.clone()
    que.append(tensor)


policy = torch.randn(size=(4,4)).to(try_gpu())
print(policy)
a=softmax(policy)
print(a.sum(dim=1), a)
print(F.log_softmax(policy, dim=1))
nnsoftmax=torch.nn.LogSoftmax(dim=1)
a = nnsoftmax(policy)
print(a.sum(dim=1), a)
a = torch.exp(a)
print(a.sum(dim=1), a)#e^(log(softmax))

a = 0