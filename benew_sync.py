import requests
import os
import json
import subprocess
import re

# ================= 配置区 =================
# 建议通过环境变量或在此处直接修改
COOKIE = 'connect.sid=s%3ABexm5lCIEntekycCrYmkTCs60aAHc41m.t487iYVmWtQPUrdm3R24F1Iw9fEnHXKI6w57VvKkSnU'
FAMILY_ID = '3056748'
ALBUM_ID = '1697319904'
WATCH_DIR = '/Users/leavingme/Downloads/Knock/第二季（更新中）'
# =========================================

HEADERS = {
    'Cookie': COOKIE,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Origin': 'https://pan.benewtech.cn',
    'Referer': 'https://pan.benewtech.cn/',
}

def get_duration(file_path):
    """使用 afinfo 获取音频时长"""
    try:
        result = subprocess.run(['afinfo', file_path], capture_output=True, text=True)
        match = re.search(r'estimated duration: ([\d.]+) sec', result.stdout)
        if match:
            return int(float(match.group(1)))
    except Exception as e:
        print(f"Warning: Could not get duration for {file_path}: {e}")
    return 0

def get_uptoken():
    """获取上传凭证"""
    resp = requests.post(
        'https://gateway.benewtech.cn/resources-app/qiniu/uptoken',
        headers=HEADERS,
        json={'types': ['TRACKS']}
    )
    if resp.status_code == 200:
        return resp.json().get('data', {}).get('trackToken')
    return None

def extract_number(name):
    """提取文件名前3位数字"""
    match = re.search(r'^(\d{3})', name.strip())
    if match:
        return match.group(1)
    return None

def get_cloud_track_names():
    """获取专辑中已存在的音频名称列表"""
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks'
    params = {
        'offset': 0,
        'limit': 100,  # 假设专辑音频不超过100个
        'familyId': FAMILY_ID
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 200:
            tracks_data = resp.json().get('data', {}).get('datas', [])
            # 网站显示的名称通常不带 .mp3 后缀
            return [track.get('name') for track in tracks_data]
    except Exception as e:
        print(f"Warning: Could not fetch cloud tracks: {e}")
    return []

def upload_to_qiniu(file_path, token):
    """上传文件到七牛云"""
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_name, f, 'audio/mpeg'),
            'token': (None, token),
            'key': (None, file_name)
        }
        resp = requests.post('https://upload.qiniup.com/', files=files)
    if resp.status_code == 200:
        return resp.json().get('key')
    return None

def register_file(qiniu_key, file_name, file_size, duration):
    """在本牛云盘注册文件"""
    register_data = {
        "trackUploadResults": [
            {
                "key": qiniu_key,
                "fname": file_name,
                "size": file_size,
                "duration": duration,
                "fileFormat": "mp3"
            }
        ]
    }
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks/upload?familyId={FAMILY_ID}'
    resp = requests.post(url, headers=HEADERS, json=register_data)
    return resp.status_code == 200 and resp.json().get('code') == 200

def sync():
    print(f"开始扫描目录: {WATCH_DIR}")
    local_files = [f for f in os.listdir(WATCH_DIR) if f.endswith('.mp3')]
    
    if not local_files:
        print("未发现待上传的 .mp3 文件。")
        return

    # 获取云端已存在的文件列表
    print("正在获取云端已存在的文件列表...")
    cloud_names = get_cloud_track_names()
    print(f"云端共发现 {len(cloud_names)} 条音频。")

    # 提取云端所有音频的序号
    cloud_numbers = set()
    for name in cloud_names:
        num = extract_number(name)
        if num:
            cloud_numbers.add(num)

    # 过滤出真正需要上传的文件
    to_upload = []
    for f in local_files:
        name_no_ext = os.path.splitext(f)[0]
        num = extract_number(name_no_ext)
        
        # 判断逻辑：如果云端包含同样前3位数字的文件，或者文件名完全一致，则跳过
        if (num and num in cloud_numbers) or (name_no_ext in cloud_names):
            print(f"跳过已存在文件: {f}")
        else:
            to_upload.append(f)

    if not to_upload:
        print("所有本地文件均已存在于云端。")
        return

    print(f"发现 {len(to_upload)} 个新文件，准备开始上传...")
    
    # 获取 Uptoken
    token = get_uptoken()
    if not token:
        print("错误: 无法获取 UpToken，请检查 Cookie 是否过期。")
        return

    for file_name in to_upload:
        file_path = os.path.join(WATCH_DIR, file_name)
        file_size = os.path.getsize(file_path)
        
        print(f"\n正在上传: {file_name}")
        
        # 执行上传
        qiniu_key = upload_to_qiniu(file_path, token)
        if qiniu_key:
            duration = get_duration(file_path)
            if register_file(qiniu_key, file_name, file_size, duration):
                print(f"成功: {file_name} 已同步。")
            else:
                print(f"失败: {file_name} 注册到云盘失败。")
        else:
            print(f"失败: {file_name} 上传失败。")

if __name__ == '__main__':
    sync()
