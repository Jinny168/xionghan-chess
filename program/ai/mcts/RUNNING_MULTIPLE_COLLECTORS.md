# 启动多个数据收集器

匈汉象棋AI系统支持同时运行多个数据收集器（[collect.py](file:///C:/Users/27415/PycharmProjects/xionghan-chess/program/ai/mcts/collect.py)），以加速训练数据的生成。

## 配置说明

系统支持两种数据存储方式：

### Redis模式（推荐）
- 设置 `use_redis: True`（默认）
- 多个收集器进程可以安全并发运行
- 数据统一存储到Redis数据库中
- 需要确保Redis服务正在运行

### 文件模式
- 设置 `use_redis: False`
- 所有进程共享同一个数据文件
- 系统会自动处理并发写入

## 启动方法

### 方法1：手动启动多个终端
打开多个命令行终端，分别运行：
```bash
cd C:\Users\27415\PycharmProjects\xionghan-chess\program\ai\mcts
python collect.py
```

### 方法2：使用批处理脚本
运行提供的批处理脚本：
```bash
# 启动4个收集器进程
run_multiple_collectors.bat

# 或者指定进程数量
run_multiple_collectors.bat 6  # 启动6个进程
```

### 方法3：使用Python脚本
使用更高级的进程管理：
```bash
# 启动4个收集器进程
python start_multiple_collectors.py 4
```

## 注意事项

1. **资源消耗**：每个收集器进程都会消耗CPU和内存资源，请根据您的硬件配置合理设置进程数量
2. **模型同步**：所有收集器共享同一个模型文件，当训练进程更新模型时，收集器会在下次对弈开始时加载新模型
3. **Redis配置**：如果使用Redis模式，请确保Redis服务器正常运行并配置了正确的IP地址和端口
4. **进程监控**：使用Python脚本启动可以更好地监控和管理进程状态

## 推荐配置

- **4-8核CPU**：建议运行2-4个收集器进程
- **8-16核CPU**：建议运行4-6个收集器进程
- **16核以上**：可根据实际情况运行更多进程

## 与训练进程配合

通常的做法是：
1. 启动多个收集器进程生成训练数据
2. 启动一个训练进程（[train.py](file:///C:/Users/27415/PycharmProjects/xionghan-chess/program/ai/mcts/train.py)）持续训练模型
3. 收集器和训练器通过共享模型文件和数据缓冲区协同工作