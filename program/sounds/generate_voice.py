import asyncio
import subprocess
import os
import edge_tts

# 象棋配音列表，增加更多常用语句
voice_scripts = [
    ("将军！", "jiangjun.wav"),
    ("绝杀无解！", "juesha.wav")
]

async def generate_voice(text, output):
    communicate = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural")  # 女声
    await communicate.save(output)
    
    # 检查是否安装了FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ffmpeg_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        ffmpeg_available = False
    
    if ffmpeg_available:
        # 用FFmpeg转码为标准WAV
        try:
            result = subprocess.run([
                "ffmpeg", "-i", output, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                output.replace(".wav", "_final.wav")
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 如果FFmpeg成功运行，替换原文件
            if result.returncode == 0:
                # 删除原始文件，保留转换后的文件
                os.remove(output)
                os.rename(output.replace(".wav", "_final.wav"), output)
                print(f"已使用FFmpeg将 {output} 转换为标准WAV格式")
            else:
                print(f"FFmpeg转换失败，使用原始文件: {output}")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg转换出错，使用原始文件: {output}, 错误: {e}")
    else:
        print(f"未检测到FFmpeg，跳过格式转换，使用原始文件: {output}\n提示：安装FFmpeg可获得更好的音频兼容性，详情请参考：https://ffmpeg.org/")

def main():
    """主函数，用于生成所有语音文件"""
    print("开始生成象棋语音文件...")
    for text, output in voice_scripts:
        print(f"正在生成语音: {text} -> {output}")
        asyncio.run(generate_voice(text, output))
    print("语音生成完成！")

if __name__ == "__main__":
    main()

