# 1. 导入核心库
import torch
import sys

# 2. 验证 Python 版本（确认使用虚拟环境的 3.12.3）
print("当前使用的 Python 版本：", sys.version)

# 3. 验证 PyTorch CUDA 可用性（关键：确认 GPU 加速生效）
print("CUDA 是否可用：", torch.cuda.is_available())
print("PyTorch 版本：", torch.__version__)
if torch.cuda.is_available():
    print("GPU 设备名称：", torch.cuda.get_device_name(0))
    print("CUDA 版本（PyTorch 适配的版本）：", torch.version.cuda)
    # 验证张量加载到 GPU
    test_tensor = torch.tensor([1, 2, 3]).cuda()
    print("GPU 张量设备：", test_tensor.device)