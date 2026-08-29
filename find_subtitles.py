import os
import sys

# 1. 彻底关闭 Intel oneDNN 硬件加速，防止 Windows CPU 报错闪退
os.environ["FLAGS_use_onednn"] = "0"

# 2. 导入核心多进程与 AI 工具
from concurrent.futures import ProcessPoolExecutor, as_completed
import cv2  # 如果提示缺少 cv2，请在 CMD 运行: pip install opencv-python
from paddleocr import PaddleOCR

# =====================================================================
# 一、 核心字幕检测函数（重新为你写好的真实业务逻辑）
# =====================================================================
def check_video_for_subtitles(video_path):
    """
    读取视频，截取底部区域并使用 PaddleOCR 检测是否存在字幕。
    检测到字幕后，会将结果自动保存为同名的 .txt 文本文件。
    """
    # 自动去重：如果对应的字幕文件已经存在，直接跳过不重复处理
    txt_path = os.path.splitext(video_path)[0] + "_字幕.txt"
    if os.path.exists(txt_path):
        return True

    # 1. 初始化当前进程独占的 OCR 引擎（降级版 2.8.1 的经典语法）
    ocr = PaddleOCR(use_gpu=False, lang="ch", show_log=False)
    
    # 2. 开启视频流
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 25
    frame_interval = int(fps * 2)  # 每 2 秒抽样检查一帧，大幅节约计算算力
    
    frame_count = 0
    detected_texts = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            h, w, _ = frame.shape
            # 截取视频底部 20% 的区域（字幕通常在这里）
            bottom_zone = frame[int(h*0.8):h, 0:w]
            
            # 使用 PaddleOCR 进行识别
            result = ocr.ocr(bottom_zone, cls=False)
            
            # 解析并记录提取到的文字
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0].strip()
                    if text and text not in detected_texts:
                        detected_texts.append(text)
                        
        frame_count += 1
        
    cap.release()
    
    # 3. 将提取出来的文字写入到同名的 .txt 文件中
    if detected_texts:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(detected_texts))
            
    return True

# =====================================================================
# 二、 多进程并行任务分发
# =====================================================================
def process_single_folder(folder_path):
    """处理单个子文件夹（全面扫描其内部所有子、孙层级）"""
    import os
    video_files = []
    
    # 精准、无限层级剥洋葱式扫描所有孙文件夹下的视频
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                video_files.append(os.path.join(root, file))
                
    folder_name = os.path.basename(folder_path)
    if not video_files:
        return f"📁 子文件夹 [{folder_name}]：未找到任何视频。"
        
    print(f"⏳ 进程 {os.getpid()} 正在处理 [{folder_name}]，共 {len(video_files)} 个视频文件...")
    
    success_count = 0
    for video_path in video_files:
        try:
            # 执行刚刚重新写好的真实处理函数
            check_video_for_subtitles(video_path)
            success_count += 1
        except Exception as e:
            print(f"❌ 视频 {os.path.basename(video_path)} 提取失败: {e}")
            
    return f"✅ 子文件夹 [{folder_name}] 处理完成：成功提取 {success_count}/{len(video_files)} 个视频。"


def main_parallel(root_folder):
    """主控多进程调度中心"""
    sub_folders = []
    for item in os.listdir(root_folder):
        full_path = os.path.join(root_folder, item)
        if os.path.isdir(full_path):
            sub_folders.append(full_path)
            
    sub_folders.append(root_folder)
    print(f"📦 共发现 {len(sub_folders)} 个目标目录，准备开始并行处理...")

    # 启动 3 个进程同时处理不同的子文件夹，兼顾速度与系统稳定性
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_single_folder, folder): folder for folder in sub_folders}
        for future in as_completed(futures):
            folder_name = futures[future]
            try:
                result = future.result()
                print(result)
            except Exception as exc:
                print(f"❌ 文件夹 {os.path.basename(folder_name)} 并行时崩溃: {exc}")

# =====================================================================
# 三、 程序唯一合法的启动入口
# =====================================================================
if __name__ == '__main__':
    # 你的大目录路径，使用完美兼容的正斜杠，避免任何转义乱码
    video_folder_path = "E:/各种抖音软件/jianghu2/video/jianghu2主页作品"
    
    main_parallel(video_folder_path)