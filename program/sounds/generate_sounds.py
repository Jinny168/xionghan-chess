import numpy as np
import wave
import struct

# 创建棋子走动的音效
def create_move_sound(filename="move.wav", duration=0.3):
    # 参数设置
    sample_rate = 44100
    amplitude = 8000
    
    # 生成木头击打声音 - 一个短暂的降低频率的正弦波
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    frequency = np.linspace(900, 500, len(t))
    tone = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # 添加衰减因子
    fade_out = np.linspace(1.0, 0.0, len(t)) ** 1.5
    tone = tone * fade_out
    
    # 添加一点随机噪声模拟木质触感
    noise = np.random.uniform(-0.1, 0.1, len(tone)) * amplitude * fade_out
    tone = tone + noise
    
    # 转换为整数值
    tone = tone.astype(np.int16)
    
    # 保存为WAV文件
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        for sample in tone:
            wav_file.writeframes(struct.pack('h', int(sample)))

# 创建吃子音效
def create_capture_sound(filename="capture.wav", duration=0.4):
    # 参数设置
    sample_rate = 44100
    amplitude = 10000
    
    # 生成音调 - 两个部分: 木头击打声 + 短促高音
    t1 = np.linspace(0, duration*0.6, int(duration*0.6 * sample_rate), False)
    t2 = np.linspace(0, duration*0.4, int(duration*0.4 * sample_rate), False)
    
    # 第一部分 - 木头击打声
    freq1 = np.linspace(1200, 600, len(t1))
    tone1 = amplitude * np.sin(2 * np.pi * freq1 * t1)
    fade1 = np.linspace(1.0, 0.2, len(t1)) ** 2
    tone1 = tone1 * fade1
    
    # 第二部分 - 短促高音
    freq2 = np.linspace(2000, 1000, len(t2))
    tone2 = amplitude * 0.7 * np.sin(2 * np.pi * freq2 * t2)
    fade2 = np.linspace(0.8, 0.0, len(t2)) ** 1.2
    tone2 = tone2 * fade2
    
    # 合并两部分
    tone = np.concatenate((tone1, tone2))
    
    # 添加随机噪声
    noise = np.random.uniform(-0.2, 0.2, len(tone)) * amplitude * np.linspace(1.0, 0.1, len(tone))
    tone = tone + noise
    
    # 转换为整数
    tone = tone.astype(np.int16)
    
    # 保存为WAV文件
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        for sample in tone:
            wav_file.writeframes(struct.pack('h', int(sample)))

# 创建将军音效
def create_check_sound(filename="check.wav", duration=0.8):
    # 参数设置
    sample_rate = 44100
    amplitude = 12000
    
    # 生成警报类型的声音 - 振幅调制的正弦波
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    
    # 基础频率和调制
    carrier_freq = 800  # 基础频率
    mod_freq = 12  # 调制频率
    
    # 创建振幅调制信号
    modulation = 0.7 + 0.3 * np.sin(2 * np.pi * mod_freq * t)
    carrier = np.sin(2 * np.pi * carrier_freq * t)
    
    # 添加一些泛音增加丰富度
    harmonic1 = 0.3 * np.sin(2 * np.pi * carrier_freq * 1.5 * t)
    harmonic2 = 0.2 * np.sin(2 * np.pi * carrier_freq * 2 * t)
    
    # 组合信号
    tone = amplitude * ((carrier + harmonic1 + harmonic2) * modulation)
    
    # 淡入淡出
    fade_in = np.linspace(0.0, 1.0, int(0.1 * sample_rate)) ** 0.5
    fade_out = np.linspace(1.0, 0.0, int(0.2 * sample_rate)) ** 0.5
    
    # 应用淡入
    tone[:len(fade_in)] *= fade_in
    # 应用淡出
    tone[-len(fade_out):] *= fade_out
    
    # 转换为整数
    tone = tone.astype(np.int16)
    
    # 保存为WAV文件
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        for sample in tone:
            wav_file.writeframes(struct.pack('h', int(sample)))

if __name__ == "__main__":
    print("生成音效文件...")
    create_move_sound("move.wav")
    create_capture_sound("capture.wav")
    create_check_sound("check.wav")
    print("音效文件生成完成。") 