
try:
    import paddle
    print("PaddlePaddle GPU可用：", paddle.device.is_compiled_with_cuda())
except ImportError as e:
    print(f"PaddlePaddle 导入失败: {e}")
    print("这可能是由于 PyTorch 和 PaddlePaddle 之间的兼容性问题，请考虑分开使用或更新版本")