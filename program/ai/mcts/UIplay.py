# coding=utf-8
import copy
import sys
import time

import pygame

from mcts import MCTSPlayer
from mcts_config import CONFIG
from mcts_game import move_action2move_id, Board

if CONFIG['use_frame'] == 'paddle':
    from paddle_net import PolicyValueNet
elif CONFIG['use_frame'] == 'pytorch':
    from pytorch_net import PolicyValueNet
else:
    print('暂不支持您选择的框架')


class Human:

    def __init__(self):
        self.agent = 'HUMAN'

    def get_action(self, move):
        # move从鼠标点击事件触发
        # print('当前是player2在操作')
        # print(board.current_player_color)
        if  move_action2move_id.__contains__(move):
            move = move_action2move_id[move]
        else:
            move = -1
        # move = random.choice(board.availables)
        return move

    def set_player_ind(self, p):
        self.player = p


if CONFIG['use_frame'] == 'paddle':
    policy_value_net = PolicyValueNet(model_file='current_policy.model')
elif CONFIG['use_frame'] == 'pytorch':
    policy_value_net = PolicyValueNet(model_file='current_policy.pkl')
else:
    print('暂不支持您选择的框架')

# 初始化pygame
pygame.init()
pygame.mixer.init()
try:
    pygame.mixer.music.load('bgm/yinzi.ogg')
    pygame.mixer.music.set_volume(0.03)
    pygame.mixer.music.play(loops=-1, start=0.0)
except pygame.error:
    print("警告: 无法加载音频文件 bgm/yinzi.ogg")

size = width, height = 800, 800
try:
    bg_image = pygame.image.load('imgs/xh_board.png')  #匈汉象棋棋盘图片位置
    bg_image = pygame.transform.smoothscale(bg_image, size)
except pygame.error:
    print("错误: 无法加载棋盘图片 imgs/xh_board.png")
    pygame.quit()
    sys.exit()

clock = pygame.time.Clock()
fullscreen = False
# 创建指定大小的窗口
screen = pygame.display.set_mode(size)
# 设置窗口标题
pygame.display.set_caption("匈汉象棋")

# 加载一个列表进行图像的绘制
# 列表表示的棋盘初始化，红子在上，黑子在下，禁止对该列表进行编辑，使用时必须使用深拷贝
board_list_init = [
    # 0行
    ['黑䠶', '一一', '黑車', '一一', '黑礌', '一一', '一一', '一一', '黑礌', '一一', '黑車', '一一', '黑䠶'],
    # 1行
    ['一一', '一一', '一一', '黑馬', '黑象', '黑士', '黑汗', '黑士', '黑象', '黑馬', '一一', '一一', '一一'],
    # 2行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 3行
    ['一一', '黑砲', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '黑砲', '一一'],
    # 4行
    ['黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒', '一一', '黑卒'],
    # 5行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 6行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 7行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 8行
    ['红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵', '一一', '红兵'],
    # 9行
    ['一一', '红炮', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '红炮', '一一'],
    # 10行
    ['一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一', '一一'],
    # 11行
    ['一一', '一一', '一一', '红傌', '红相', '红仕', '红汉', '红仕', '红相', '红傌', '一一', '一一', '一一'],
    # 12行
    ['红射', '一一', '红俥', '一一', '红檑', '一一', '一一', '一一', '红檑', '一一', '红俥', '一一', '红射']
]

# 加载棋子被选中的图片
try:
    fire_image = pygame.transform.smoothscale(pygame.image.load("imgs/fire.png").convert_alpha(), (width // 10, height // 10))
    fire_image.set_alpha(200)
except pygame.error:
    print("错误: 无法加载选中指示器图片 imgs/fire.png")
    pygame.quit()
    sys.exit()

# 制作一个从字符串到pygame.surface对象的映射
try:
    str2image = {
        '红俥': pygame.transform.smoothscale(pygame.image.load("imgs/hongche.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '红傌': pygame.transform.smoothscale(pygame.image.load("imgs/hongma.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红相': pygame.transform.smoothscale(pygame.image.load("imgs/hongxiang.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红仕': pygame.transform.smoothscale(pygame.image.load("imgs/hongshi.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红汉': pygame.transform.smoothscale(pygame.image.load("imgs/honghan.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红炮': pygame.transform.smoothscale(pygame.image.load("imgs/hongpao.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红兵': pygame.transform.smoothscale(pygame.image.load("imgs/hongbing.png").convert_alpha(), (width // 10 - 10, height // 10 - 10)),
        '红檑': pygame.transform.smoothscale(pygame.image.load("imgs/honglei.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '红射': pygame.transform.smoothscale(pygame.image.load("imgs/hongshe.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑車': pygame.transform.smoothscale(pygame.image.load("imgs/heiche.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑馬': pygame.transform.smoothscale(pygame.image.load("imgs/heima.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑象': pygame.transform.smoothscale(pygame.image.load("imgs/heixiang.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑士': pygame.transform.smoothscale(pygame.image.load("imgs/heishi.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑汗': pygame.transform.smoothscale(pygame.image.load("imgs/heihan.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑砲': pygame.transform.smoothscale(pygame.image.load("imgs/heipao.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑卒': pygame.transform.smoothscale(pygame.image.load("imgs/heibing.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑礌': pygame.transform.smoothscale(pygame.image.load("imgs/heilei.png").convert_alpha(), (width // 13 - 10, height // 13 - 10)),
        '黑䠶': pygame.transform.smoothscale(pygame.image.load("imgs/heishe.png").convert_alpha(), (width // 13 - 10, height // 13 - 10))
    }
except pygame.error as e:
    print(f"错误: 无法加载棋子图片: {e}")
    pygame.quit()
    sys.exit()

str2image_rect = {
    '红俥': str2image['红俥'].get_rect(),
    '红傌': str2image['红傌'].get_rect(),
    '红相': str2image['红相'].get_rect(),
    '红仕': str2image['红仕'].get_rect(),
    '红汉': str2image['红汉'].get_rect(),
    '红炮': str2image['红炮'].get_rect(),
    '红兵': str2image['红兵'].get_rect(),
    '红檑': str2image['红檑'].get_rect(),
    '红射': str2image['红射'].get_rect(),
    '黑車': str2image['黑車'].get_rect(),
    '黑馬': str2image['黑馬'].get_rect(),
    '黑象': str2image['黑象'].get_rect(),
    '黑士': str2image['黑士'].get_rect(),
    '黑汗': str2image['黑汗'].get_rect(),
    '黑砲': str2image['黑砲'].get_rect(),
    '黑卒': str2image['黑卒'].get_rect(),
    '黑礌': str2image['黑礌'].get_rect(),
    '黑䠶': str2image['黑䠶'].get_rect()
}


# 根据棋盘列表获得最新位置
# 返回一个由image和rect对象组成的列表
x_ratio = 60
y_ratio = 60
x_bais = 40
y_bais = 40
def board2image(board):
    return_image_rect = []
    for i in range(13):
        for j in range(13):
            if board[i][j] == '红俥':
                str2image_rect['红俥'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红俥'])
                return_image_rect.append((str2image['红俥'], str2image_rect_copy))
            elif board[i][j] == '红傌':
                str2image_rect['红傌'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红傌'])
                return_image_rect.append((str2image['红傌'], str2image_rect_copy))
            elif board[i][j] == '红兵':
                str2image_rect['红兵'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红兵'])
                return_image_rect.append((str2image['红兵'], str2image_rect_copy))
            elif board[i][j] == '红相':
                str2image_rect['红相'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红相'])
                return_image_rect.append((str2image['红相'], str2image_rect_copy))
            elif board[i][j] == '红炮':
                str2image_rect['红炮'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红炮'])
                return_image_rect.append((str2image['红炮'], str2image_rect_copy))
            elif board[i][j] == '红仕':
                str2image_rect['红仕'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红仕'])
                return_image_rect.append((str2image['红仕'], str2image_rect_copy))
            elif board[i][j] == '红汉':
                str2image_rect['红汉'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红汉'])
                return_image_rect.append((str2image['红汉'], str2image_rect_copy))
            elif board[i][j] == '红檑':
                str2image_rect['红檑'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红檑'])
                return_image_rect.append((str2image['红檑'], str2image_rect_copy))
            elif board[i][j] == '红射':
                str2image_rect['红射'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['红射'])
                return_image_rect.append((str2image['红射'], str2image_rect_copy))
            elif board[i][j] == '黑車':
                str2image_rect['黑車'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑車'])
                return_image_rect.append((str2image['黑車'], str2image_rect_copy))
            elif board[i][j] == '黑馬':
                str2image_rect['黑馬'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑馬'])
                return_image_rect.append((str2image['黑馬'], str2image_rect_copy))
            elif board[i][j] == '黑卒':
                str2image_rect['黑卒'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑卒'])
                return_image_rect.append((str2image['黑卒'], str2image_rect_copy))
            elif board[i][j] == '黑象':
                str2image_rect['黑象'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑象'])
                return_image_rect.append((str2image['黑象'], str2image_rect_copy))
            elif board[i][j] == '黑砲':
                str2image_rect['黑砲'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑砲'])
                return_image_rect.append((str2image['黑砲'], str2image_rect_copy))
            elif board[i][j] == '黑士':
                str2image_rect['黑士'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑士'])
                return_image_rect.append((str2image['黑士'], str2image_rect_copy))
            elif board[i][j] == '黑汗':
                str2image_rect['黑汗'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑汗'])
                return_image_rect.append((str2image['黑汗'], str2image_rect_copy))
            elif board[i][j] == '黑礌':
                str2image_rect['黑礌'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑礌'])
                return_image_rect.append((str2image['黑礌'], str2image_rect_copy))
            elif board[i][j] == '黑䠶':
                str2image_rect['黑䠶'].center = (j * x_ratio + x_bais, i * y_ratio + y_bais)
                str2image_rect_copy = copy.deepcopy(str2image_rect['黑䠶'])
                return_image_rect.append((str2image['黑䠶'], str2image_rect_copy))
    return return_image_rect


fire_rect = fire_image.get_rect()
fire_rect.center = (0 * x_ratio + x_bais, 3 * y_ratio + y_bais)


def main(game_mode=None):
    """主游戏函数，支持命令行参数或交互式选择游戏模式"""
    if game_mode is None:
        # 在命令行提示用户输入
        print("请选择游戏模式:")
        print("1. 人人游戏")
        print("2. 人机游戏")
        choice = input("请输入您的选择 (1 或 2): ")
        if choice == '1':
            game_mode = "human_vs_human"
        elif choice == '2':
            game_mode = "human_vs_ai"
        else:
            print("无效的选择，默认进入人人游戏模式")
            game_mode = "human_vs_human"
    
    # 加载两个玩家，根据选择的游戏模式决定
    board = Board()
    # 开始的玩家
    start_player = 1

    if game_mode == "human_vs_ai" or game_mode == "2":
        # 人机模式：玩家1是AI，玩家2是人类
        player1 = MCTSPlayer(policy_value_net.policy_value_fn,
                             c_puct=5,
                             n_playout=1000,
                             is_selfplay=0)
        player2 = Human()
        print("人机模式：玩家1(AI) vs 玩家2(人类)")
    elif game_mode == "human_vs_human" or game_mode == "1":
        # 人人模式：两个都是人类玩家
        player1 = Human()
        player2 = Human()
        print("人人模式：玩家1(人类) vs 玩家2(人类)")
    else:
        print("无效的游戏模式，请输入1(人人对战)或2(人机对战)")
        return

    board.init_board(start_player)
    p1, p2 = 1, 2
    player1.set_player_ind(1)
    player2.set_player_ind(2)
    players = {p1: player1, p2: player2}


    # 切换玩家
    swicth_player = True
    draw_fire = False
    move_action = ''
    first_button = False
    while True:

        # 填充背景
        screen.blit(bg_image, (0, 0))
        for image, image_rect in board2image(board=board.state_deque[-1]):
            screen.blit(image, image_rect)
        if draw_fire:
            screen.blit(fire_image, fire_rect)
        # 更新界面
        pygame.display.update()
        # 不高于60帧
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:    #按下按键
                # print("[MOUSEBUTTONDOWN]", event.pos, event.button)
                mouse_x, mouse_y = event.pos
                if not first_button:
                    for i in range(13):
                        for j in range(13):
                            if abs(60 * j + 40 - mouse_x) < 30 and abs(60 * i + 40 - mouse_y) < 30:
                                first_button = True
                                start_i_j = j, i
                                fire_rect.center = (start_i_j[0] * x_ratio + x_bais, start_i_j[1] * y_ratio + y_bais)
                                # screen.blit(fire_image, fire_rect)
                                break

                elif first_button:
                    for i in range(13):
                        for j in range(13):
                            if abs(60 * j + 40 - mouse_x) < 30 and abs(60 * i + 40 - mouse_y) < 30:
                                first_button = False
                                end_i_j = j, i
                                move_action = str(start_i_j[1]) + str(start_i_j[0]) + str(end_i_j[1]) + str(end_i_j[0])
                                # screen.blit(fire_image, fire_rect)

        if swicth_player:
            current_player = board.get_current_player_id()  # 红子对应的玩家id
            player_in_turn = players[current_player]  # 决定当前玩家的代理

        # 根据游戏模式处理不同的玩家类型
        if hasattr(player_in_turn, 'agent') and player_in_turn.agent == 'AI':
            pygame.display.update()
            start_time = time.time()
            move = player_in_turn.get_action(board)  # 当前玩家代理拿到动作
            print('AI耗时：', time.time() - start_time)
            board.do_move(move)  # 棋盘做出改变
            swicth_player = True
            draw_fire = False
        elif hasattr(player_in_turn, 'agent') and player_in_turn.agent == 'HUMAN':
            draw_fire = True
            swicth_player = False
            if len(move_action) == 4:
                move = player_in_turn.get_action(move_action)  # 当前玩家代理拿到动作
                if move != -1:
                    board.do_move(move)  # 棋盘做出改变
                    swicth_player = True
                    move_action = ''
                    draw_fire = False
        else:
            # 如果玩家不是AI也不是HUMAN（比如在人人模式中），处理移动
            draw_fire = True
            swicth_player = False
            if len(move_action) == 4:
                move = player_in_turn.get_action(move_action)  # 当前玩家代理拿到动作
                if move != -1:
                    board.do_move(move)  # 棋盘做出改变
                    swicth_player = True
                    move_action = ''
                    draw_fire = False

        end, winner = board.game_end()
        if end:
            if winner != -1:
                print("Game end. Winner is", players[winner])
            else:
                print("Game end. Tie")
            sys.exit()


if __name__ == '__main__':
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == '1':
            main("human_vs_human")
        elif arg == '2':
            main("human_vs_ai")
        else:
            print("无效参数，请输入1(人人对战)或2(人机对战)")
            sys.exit(1)
    else:
        # 没有命令行参数时在命令行提示用户输入
        main()