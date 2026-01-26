import os
from pathlib import Path
from pydub import AudioSegment
import subprocess


def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_with_ffmpeg(mp3_file_path, wav_file_path):
    """使用ffmpeg转换音频文件"""
    try:
        subprocess.run([
            'ffmpeg',
            '-i', mp3_file_path,
            '-vn',  # no video
            '-acodec', 'pcm_s16le',  # pcm 16-bit little endian
            '-ar', '44100',  # 44.1kHz
            '-ac', '2',  # stereo
            wav_file_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_with_pydub(mp3_file_path, wav_file_path):
    """使用pydub转换音频文件"""
    try:
        audio = AudioSegment.from_mp3(mp3_file_path)
        audio.export(wav_file_path, format="wav", parameters={
            "-ar": "44100",
            "-ac": "2",
            "-bits": "16"
        })
        return True
    except Exception:
        return False


def convert_mp3_to_wav(mp3_file_path, wav_file_path):
    """
    尝试多种方法将MP3文件转换为WAV文件
    """
    print(f"正在转换: {mp3_file_path} -> {wav_file_path}")
    
    # 首先尝试使用ffmpeg（如果可用）
    if check_ffmpeg():
        print("  使用系统ffmpeg进行转换...")
        if convert_with_ffmpeg(mp3_file_path, wav_file_path):
            print(f"  成功转换: {mp3_file_path} -> {wav_file_path}")
            return True
        else:
            print("  系统ffmpeg转换失败，尝试其他方法...")
    
    # 如果ffmpeg不可用或失败，尝试使用pydub
    print("  使用pydub进行转换...")
    if convert_with_pydub(mp3_file_path, wav_file_path):
        print(f"  成功转换: {mp3_file_path} -> {wav_file_path}")
        return True
    else:
        print(f"  转换失败: {mp3_file_path}")
        return False


def main():
    # 定义声音文件目录
    sounds_dir = Path(__file__).parent
    
    # 查找所有mp3文件
    mp3_files = list(sounds_dir.glob("*.mp3"))
    
    if not mp3_files:
        print("在目录中未找到MP3文件")
        return
    
    print(f"找到 {len(mp3_files)} 个MP3文件需要转换:")
    for mp3_file in mp3_files:
        print(f"  - {mp3_file.name}")
    
    # 转换每个MP3文件为WAV
    converted_count = 0
    for mp3_file in mp3_files:
        # 生成WAV文件名（替换扩展名为.wav）
        wav_file = mp3_file.with_suffix('.wav')
        
        # 如果WAV文件已存在，询问是否覆盖
        if wav_file.exists():
            response = input(f"WAV文件 {wav_file.name} 已存在，是否覆盖? (y/N): ")
            if response.lower() != 'y':
                print(f"跳过: {mp3_file.name}")
                continue
        
        # 执行转换
        if convert_mp3_to_wav(str(mp3_file), str(wav_file)):
            converted_count += 1
    
    print(f"\n转换完成! 成功转换 {converted_count}/{len(mp3_files)} 个文件")


if __name__ == "__main__":
    main()