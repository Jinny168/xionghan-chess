# coding=utf-8
import pickle
import sys
import os
# 添加上级目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from program.ai.mcts.mcts_config import CONFIG
import redis

def get_redis_cli():

    r = redis.StrictRedis(host=CONFIG['redis_host'], port=CONFIG['redis_port'], db=CONFIG['redis_db'])
    if r.ping():
        print("Redis连接成功！")
    else:
        print("Redis连接失败！")
    return r
def get_list_range(redis_cli,name,l,r=-1):
    assert isinstance(redis_cli,redis.Redis)
    list = redis_cli.lrange(name,l,r)
    return [pickle.loads(d) for d in list]
def emptyRedis(r):
    # 获取所有键
    keys = r.keys()

    # 删除所有键
    r.delete(*keys)

    # 关闭连接
    r.close()


def test_redis_connection():
    """测试Redis连接是否正常"""
    try:
        r = get_redis_cli()
        # 测试连接
        r.ping()
        print("Redis连接成功！")

        # 测试基本操作
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"写入并读取数据: {value.decode('utf-8')}")

        # 清理测试数据
        r.delete('test_key')
        print("测试数据清理完成")

        # 测试列表操作
        r.lpush('test_list', 'item1', 'item2')
        list_items = r.lrange('test_list', 0, -1)
        print(f"列表内容: {[item.decode('utf-8') for item in list_items]}")

        # 清理测试数据
        r.delete('test_list')
        print("测试列表清理完成")

        return True
    except Exception as e:
        print(f"Redis连接失败: {str(e)}")
        return False


# 主程序入口：将训练数据缓冲区加载到Redis数据库中
if __name__ == '__main__':
    # 测试Redis连接
    # success = test_redis_connection()
    # if success:
    #     print("Redis功能测试通过！")
    # else:
    #     print("Redis功能测试失败！")
    #     print(f"当前配置: host={CONFIG['redis_host']}, port={CONFIG['redis_port']}, db={CONFIG['redis_db']}")
    #     print("请确认Redis服务器正在运行并检查网络连接")

    # 连接到Redis数据库
    r = get_redis_cli()
    # # 清空Redis数据库中的现有数据
    # emptyRedis(r)
    # # 从本地文件加载训练数据缓冲区
    # with open(CONFIG['train_data_buffer_path'], 'rb') as data_dict:
    #     data_file = pickle.load(data_dict)
    #     data_buffer = data_file['data_buffer']
    # # 将训练数据逐条存入Redis的train_data_buffer列表中
    # for d in data_buffer:
    #     r.rpush('train_data_buffer',pickle.dumps(d))
    r.rpush('test',pickle.dumps(([8,2],[2,4],5)))
    p = get_list_range(r,'test',0,-1)
    print(p)
