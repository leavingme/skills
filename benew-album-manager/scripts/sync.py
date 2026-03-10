import requests
import os
import json
import subprocess
import re

# ================= 配置区 =================
COOKIE = os.environ.get('COOKIE')
FAMILY_ID = os.environ.get('FAMILY_ID')
ALBUM_ID = os.environ.get('ALBUM_ID')
ALBUM_COVER = os.environ.get('ALBUM_COVER')
WATCH_DIR = os.environ.get('WATCH_DIR')
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

def get_album_cover_key():
    """获取相册封面的最终 Key 以便在上传时捆绑"""
    if ALBUM_COVER:
        return ALBUM_COVER.split('/')[-1]
    
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}'
    params = {'familyId': FAMILY_ID}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 200:
            cover_url = resp.json().get('data', {}).get('coverUrl')
            if cover_url:
                return cover_url.split('/')[-1]
    except Exception as e:
        print(f"Warning: Could not get album cover: {e}")
    return None

def extract_number(name):
    """提取文件名前3位数字"""
    match = re.search(r'^(\d{3})', name.strip())
    if match:
        return match.group(1)
    return None

def normalize_name(name):
    """标准化名称：去除尾部 (1) 等重复标记，合并多余空格"""
    name = re.sub(r'\s*\((\d+)\)\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def get_cloud_track_names():
    """获取专辑中已存在的音频名称列表"""
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks'
    params = {
        'offset': 0,
        'limit': 200, 
        'familyId': FAMILY_ID
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 200:
            tracks_data = resp.json().get('data', {}).get('datas', [])
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

def register_file(qiniu_key, file_name, file_size, duration, cover_key=None):
    """在本牛云盘注册文件"""
    track_data = {
        "key": qiniu_key,
        "fname": file_name,
        "size": file_size,
        "duration": duration,
        "fileFormat": "mp3"
    }
    
    # 💥 直接在注册时硬塞入相册的封面图哈希
    if cover_key:
        track_data["coverKey"] = cover_key
        
    register_data = {
        "trackUploadResults": [track_data]
    }
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks/upload?familyId={FAMILY_ID}'
    resp = requests.post(url, headers=HEADERS, json=register_data)
    return resp.status_code == 200 and resp.json().get('code') == 200

def reorder_tracks(uids):
    """保存最终排序"""
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/{ALBUM_ID}/tracks/reorder?familyId={FAMILY_ID}'
    resp = requests.post(url, headers=HEADERS, json={"trackIds": uids})
    return resp.status_code == 200

def get_all_tracks():
    """获取所有音轨对象详细列表"""
    tracks = []
    offset = 0
    limit = 50
    while True:
        url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks'
        params = {'offset': offset, 'limit': limit, 'familyId': FAMILY_ID}
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 200:
            data = resp.json().get('data', {})
            batch = data.get('datas', [])
            tracks.extend(batch)
            if len(tracks) >= data.get('count', 0) or not batch:
                break
            offset += limit
        else:
            break
    return tracks

def sync():
    if not all([COOKIE, FAMILY_ID, ALBUM_ID, WATCH_DIR]):
        print("错误: 缺少必要的环境变量 (COOKIE, FAMILY_ID, ALBUM_ID, WATCH_DIR)")
        return

    print(f"开始扫描目录: {WATCH_DIR}")
    if not os.path.exists(WATCH_DIR):
        print("错误: 目录不存在")
        return
        
    local_files = [f for f in os.listdir(WATCH_DIR) if f.endswith('.mp3')]
    
    if not local_files:
        print("未发现待上传的 .mp3 文件。")
        return

    print("正在获取云端已存在的文件列表...")
    cloud_names = get_cloud_track_names()
    print(f"云端共发现 {len(cloud_names)} 条音频。")

    cloud_numbers = set()
    cloud_names_normalized = set()
    for name in cloud_names:
        name = normalize_name(name)
        num = extract_number(name)
        if num:
            cloud_numbers.add(num)
        else:
            cloud_names_normalized.add(name)

    to_upload = []
    for f in local_files:
        name_no_ext = normalize_name(os.path.splitext(f)[0])
        num = extract_number(name_no_ext)

        if (num and num in cloud_numbers) or (name_no_ext in cloud_names_normalized):
            print(f"跳过已存在文件: {f}")
        else:
            to_upload.append(f)

    if not to_upload:
        print("所有本地文件均已存在于云端。")
        return

    print(f"发现 {len(to_upload)} 个新文件，准备开始上传...")
    
    token = get_uptoken()
    if not token:
        print("错误: 无法获取 UpToken，请检查 Cookie 是否过期。")
        return

    # 尝试自动嗅探专辑封面，准备在上传第一秒就将封面盖上
    cover_key = get_album_cover_key()
    if cover_key:
        print(f"✔ 成功抓取当前专辑默认封面 ({cover_key})，将为新音频捆绑自动打封！")

    for file_name in sorted(to_upload):
        file_path = os.path.join(WATCH_DIR, file_name)
        file_size = os.path.getsize(file_path)
        
        print(f"\n正在上传: {file_name}")
        
        qiniu_key = upload_to_qiniu(file_path, token)
        if qiniu_key:
            duration = get_duration(file_path)
            normalized_name = normalize_name(os.path.splitext(file_name)[0]) + '.mp3'
            if register_file(qiniu_key, normalized_name, file_size, duration, cover_key):
                print(f"成功: {file_name} 已同步。")
            else:
                print(f"失败: {file_name} 注册到云盘失败。")
        else:
            print(f"失败: {file_name} 上传失败。")

    print("\n📦 所有新文件上传处理结束。")
    print("正在进行云端一致性健康检查...")
    
    all_tracks = get_all_tracks()
    needs_optimize = False
    
    seen_nums = set()
    cover_keys = set()
    
    for t in all_tracks:
        name = t.get('name', '')
        
        # 1. 检查去重
        num = extract_number(name)
        if num:
            if num in seen_nums:
                needs_optimize = True
            seen_nums.add(num)
            
        # 2. 检查后缀如 (1) 是否被清洗
        if re.search(r'\(\d+\)\s*$', name.strip()):
            needs_optimize = True
            
        # 3. 检查封面统一性
        c_key = t.get('coverKey')
        if c_key:
            cover_keys.add(c_key)
        elif cover_key: # 如果存在相册基础封面但有个别音轨为空
            needs_optimize = True

    if len(cover_keys) > 1:
        needs_optimize = True
        
    # 4. 检查顺序是否已经完美
    def sort_key(t):
        name = t.get('name', '')
        num = extract_number(name)
        if num:
            return (0, int(num))
        return (1, name)
        
    sorted_tracks = sorted(all_tracks, key=sort_key)
    if [t.get('uid') for t in all_tracks] != [t.get('uid') for t in sorted_tracks]:
        needs_optimize = True
        
    if needs_optimize:
        print("⚠️ 检测到当前专辑存在：乱序 / 封面缺少或不一 / 命名不规范 / 出现多余复本。")
        print("🔗 自动触发深度优化流 (optimize.py) ...\n")
        try:
            import optimize
            optimize.optimize()
        except ImportError:
            print("未能成功加载 optimize.py 模块。")
    else:
        print("✅ 经多维检测，当前云盘音轨去重、排序、命名与封面均已达到完美稳态！全流程结束。")

if __name__ == '__main__':
    sync()
