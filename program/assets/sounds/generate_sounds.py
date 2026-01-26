import numpy as np
import wave
import struct
import os
from typing import Optional


# 音频参数常量
SAMPLE_RATE = 44100
AMPLITUDE_MOVE = 8000
AMPLITUDE_SELECT = 6000
AMPLITUDE_CAPTURE = 10000
AMPLITUDE_CHECK = 12000


def _validate_params(filename: str, duration: float) -> None:
    """验证输入参数"""
    if not isinstance(filename, str) or not filename.endswith('.wav'):
        raise ValueError("文件名必须是以.wav结尾的字符串")
    if duration <= 0:
        raise ValueError("持续时间必须大于0")


def _write_wav_file(filename: str, tone: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    """通用的WAV文件写入函数"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # 单声道
        wav_file.setsampwidth(2)  # 16位
        wav_file.setframerate(sample_rate)
        
        # 批量写入数据以提高性能
        packed_data = b''.join(struct.pack('<h', int(sample)) for sample in tone)
        wav_file.writeframes(packed_data)


def create_move_sound(filename: str = "move.wav", duration: float = 0.3) -> None:
    """创建棋子走动的音效"""
    _validate_params(filename, duration)
    
    try:
        # 参数设置
        amplitude = AMPLITUDE_MOVE
        
        # 生成更柔和的滑音效果 - 代表轻柔的移动
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
            
        # 使用较低频率范围和更平滑的变化
        frequency = np.linspace(600, 400, len(t))
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 平滑的衰减
        fade_out = np.linspace(1.0, 0.0, len(t)) ** 2
        tone = tone * fade_out
        
        # 添加轻微的谐波
        harmonic = 0.3 * amplitude * np.sin(2 * np.pi * frequency * 2 * t)
        harmonic_fade = np.linspace(1.0, 0.1, len(t)) ** 1.5
        tone = tone + harmonic * harmonic_fade
        
        # 转换为整数值
        tone = tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建移动音效时发生错误: {e}")
        raise


def create_select_sound(filename: str = "select.wav", duration: float = 0.25) -> None:
    """创建选子音效"""
    _validate_params(filename, duration)
    
    try:
        # 参数设置
        amplitude = AMPLITUDE_SELECT
        
        # 生成双音调的确认音效 - 更明显的反馈
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
            
        # 使用更高频率并添加谐波
        base_freq = 1800
        tone = amplitude * np.sin(2 * np.pi * base_freq * t)
        
        # 添加高次谐波以产生更明显的声音特征
        harmonic_freq = base_freq * 1.5
        harmonic = 0.4 * amplitude * np.sin(2 * np.pi * harmonic_freq * t)
        
        # 创建一个双音调效果
        combined_tone = tone + harmonic
        
        # 特殊的衰减模式 - 先保持一段时间再快速下降
        sustain_time = int(len(t) * 0.6)  # 保持前60%的时间
        fade_out = np.ones(len(t))
        fade_out[sustain_time:] = np.linspace(1.0, 0.0, len(t) - sustain_time) ** 2
        combined_tone = combined_tone * fade_out
        
        # 转换为整数
        combined_tone = combined_tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, combined_tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建选择音效时发生错误: {e}")
        raise


def create_capture_sound(filename: str = "capture.wav", duration: float = 0.4) -> None:
    """创建吃子音效"""
    _validate_params(filename, duration)
    
    try:
        # 参数设置
        amplitude = AMPLITUDE_CAPTURE
        
        # 生成更具冲击力的音效 - 代表激烈的碰撞
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
        
        # 高频起始然后快速衰减
        frequency = 1400 * np.exp(-4 * t / duration)  # 指数衰减
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 快速衰减
        fade_out = np.linspace(1.0, 0.0, len(t)) ** 3
        tone = tone * fade_out
        
        # 添加低频冲击波
        low_freq = 100  # 低频成分
        impact = 0.5 * amplitude * np.sin(2 * np.pi * low_freq * t) * np.exp(-t / (duration * 0.3))
        tone = tone + impact
        
        # 转换为整数
        tone = tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建捕获音效时发生错误: {e}")
        raise


def create_check_sound(filename: str = "check.wav", duration: float = 0.8) -> None:
    """创建将军音效"""
    _validate_params(filename, duration)
    
    try:
        # 参数设置
        amplitude = AMPLITUDE_CHECK
        
        # 生成警报类型的声音 - 振幅调制的正弦波
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
        
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
        fade_in_len = int(0.1 * SAMPLE_RATE)
        fade_out_len = int(0.2 * SAMPLE_RATE)
        
        if len(tone) > fade_in_len:
            fade_in = np.linspace(0.0, 1.0, fade_in_len) ** 0.5
            tone[:fade_in_len] *= fade_in
        if len(tone) > fade_out_len:
            fade_out = np.linspace(1.0, 0.0, fade_out_len) ** 0.5
            tone[-fade_out_len:] *= fade_out
        
        # 转换为整数
        tone = tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建将军音效时发生错误: {e}")
        raise


def create_victory_sound(filename: str = "victory.wav", duration: float = 1.5) -> None:
    """创建胜利音效"""
    _validate_params(filename, duration)
    
    try:
        amplitude = AMPLITUDE_CHECK  # 使用较高的幅度
        
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
        
        # 创建上升的音调序列，象征胜利
        base_freq = 440  # A4音符
        note_duration = duration / 3  # 将时间分为三个部分
        
        # 第一个音符
        segment1 = np.linspace(0, note_duration, int(note_duration * SAMPLE_RATE))
        tone1 = amplitude * np.sin(2 * np.pi * base_freq * segment1)
        
        # 第二个音符（稍高）
        segment2 = np.linspace(0, note_duration, int(note_duration * SAMPLE_RATE))
        tone2 = amplitude * np.sin(2 * np.pi * base_freq * 1.2 * segment2)
        
        # 第三个音符（更高且持续较长）
        segment3 = np.linspace(0, duration - 2 * note_duration, int((duration - 2 * note_duration) * SAMPLE_RATE))
        tone3 = amplitude * np.sin(2 * np.pi * base_freq * 1.5 * segment3)
        
        # 组合音调
        tone = np.concatenate([tone1, tone2, tone3])
        
        # 如果长度不匹配，截断或填充
        if len(tone) > len(t):
            tone = tone[:len(t)]
        elif len(tone) < len(t):
            tone = np.pad(tone, (0, len(t) - len(tone)), 'constant')
        
        # 添加淡入淡出效果
        fade_in_len = int(0.05 * SAMPLE_RATE)
        fade_out_len = int(0.1 * SAMPLE_RATE)
        
        if len(tone) > fade_in_len:
            fade_in = np.linspace(0.0, 1.0, fade_in_len)
            tone[:fade_in_len] *= fade_in
        if len(tone) > fade_out_len:
            fade_out = np.linspace(1.0, 0.0, fade_out_len)
            tone[-fade_out_len:] *= fade_out
        
        # 转换为整数
        tone = tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建胜利音效时发生错误: {e}")
        raise


def create_defeat_sound(filename: str = "defeat.wav", duration: float = 1.2) -> None:
    """创建失败音效"""
    _validate_params(filename, duration)
    
    try:
        amplitude = AMPLITUDE_CAPTURE  # 使用适中的幅度
        
        t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
        if len(t) == 0:
            raise ValueError("计算出的样本数量为0，请检查持续时间参数")
        
        # 创建下降的音调，象征失败
        base_freq = 440  # A4音符
        frequency = np.linspace(base_freq, base_freq * 0.5, len(t))  # 频率逐渐降低
        tone = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # 添加指数衰减
        decay_factor = np.exp(-3 * t / duration)
        tone = tone * decay_factor
        
        # 转换为整数
        tone = tone.astype(np.int16)
        
        # 保存为WAV文件
        _write_wav_file(filename, tone, SAMPLE_RATE)
    except Exception as e:
        print(f"创建失败音效时发生错误: {e}")
        raise


if __name__ == "__main__":
    print("生成音效文件...")
    create_move_sound("move.wav")
    create_capture_sound("capture.wav")
    create_check_sound("check.wav")
    create_select_sound("select.wav")
    create_victory_sound("victory.wav")
    create_defeat_sound("defeat.wav")
    
    # 生成QQ风格的胜利和失败音效
    create_victory_sound("qq_victory_sound.wav")
    create_defeat_sound("qq_defeat_sound.wav")
    
    print("音效文件生成完成。")