import requests
import json
import re
import time
import os

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
    'Content-Type': 'application/json'
}

def get_tracks():
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

def get_album_cover():
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}'
    params = {'familyId': FAMILY_ID}
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code == 200:
        data = resp.json().get('data', {})
        # 返回类似 'http://img.benewtech.cn/xxx'
        return data.get('coverUrl')
    return None

def delete_tracks(uids):
    if not uids:
        return True
    url = 'https://gateway.benewtech.cn/resources-app/cloud/web/tracks/delete'
    resp = requests.post(url, headers=HEADERS, json={"uids": uids})
    return resp.status_code == 200

def update_track(uid, data):
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/tracks/{uid}/update?familyId={FAMILY_ID}'
    resp = requests.post(url, headers=HEADERS, json=data)
    return resp.status_code == 200

def reorder_tracks(uids):
    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/{ALBUM_ID}/tracks/reorder?familyId={FAMILY_ID}'
    resp = requests.post(url, headers=HEADERS, json={"trackIds": uids})
    return resp.status_code == 200

def extract_number(name):
    match = re.search(r'^(\d{3})', name.strip())
    if match:
        return match.group(1)
    return None

def normalize_name(name):
    name = re.sub(r'\s*\((\d+)\)\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def optimize():
    global ALBUM_COVER
    if not all([COOKIE, FAMILY_ID, ALBUM_ID, WATCH_DIR]):
        print("错误: 缺少必要的环境变量 (COOKIE, FAMILY_ID, ALBUM_ID, WATCH_DIR)")
        return

    if not ALBUM_COVER:
        print("未提供 ALBUM_COVER 环境变量，正在尝试通过云盘接口自动提取首图封面...")
        fetched_cover = get_album_cover()
        if fetched_cover:
            ALBUM_COVER = fetched_cover
            print(f"成功获取到专辑封面 URL: {ALBUM_COVER}")
        else:
            print("未能自动提取到专辑封面，本次优化将跳过封面更新。")

    print("Step 1: 获取完整列表...")
    tracks = get_tracks()
    print(f"总计找到 {len(tracks)} 条音轨。")

    groups = {} 
    
    for t in tracks:
        name = t.get('name', '')
        num = extract_number(name)
        
        group_key = f"NUM_{num}" if num else f"NAME_{normalize_name(name)}"
        
        if group_key not in groups:
             groups[group_key] = []
        groups[group_key].append(t)

    to_delete = []
    to_keep = []

    print("Step 2: 判定重复 (按序号去重，保留最早版本)...")
    for key, group in groups.items():
        group.sort(key=lambda x: x.get('updated', ''))
        
        keep = group[0]
        rem = group[1:]
        
        to_keep.append(keep)
        for r in rem:
            to_delete.append(r.get('uid'))
            print(f"  [标记删除] 重复项: {r.get('name')} (UID: {r.get('uid')})")

    if to_delete:
        print(f"执行物理删除 {len(to_delete)} 个音轨...")
        delete_tracks(to_delete)
        time.sleep(1)

    print("Step 3: 最终优化 (修正排序、名称、封面)...")
    
    def final_sort_key(t):
        name = t.get('name', '')
        num = extract_number(name)
        if num:
            return (0, int(num)) 
        return (1, name) 

    local_name_map = {}
    if os.path.exists(WATCH_DIR):
        for f in os.listdir(WATCH_DIR):
            if f.endswith('.mp3'):
                name_no_ext = os.path.splitext(f)[0]
                clean_local = normalize_name(name_no_ext)
                num = extract_number(clean_local)
                if num:
                    local_name_map[num] = clean_local

    to_keep.sort(key=final_sort_key)

    sorted_uids = []
    for i, t in enumerate(to_keep, 1):
        uid = t.get('uid')
        num = extract_number(t.get('name', ''))
        
        if num and num in local_name_map:
            name = local_name_map[num]
        else:
            name = normalize_name(t.get('name'))
        
        update_data = {
            "name": name,
        }
        
        if ALBUM_COVER:
            cover_key = ALBUM_COVER.split('/')[-1]
            update_data["coverKey"] = cover_key
            print(f"  [强制更新名称和封面] {name} | UID: {uid}")
        else:
            print(f"  [强制更新名称] {name} | UID: {uid}")
        
        update_track(uid, update_data)
        sorted_uids.append(uid)
        time.sleep(0.3)
        
    print(f"\nStep 4: 批量保存排序...")
    if reorder_tracks(sorted_uids):
        print("  [成功] 专辑排序已在线修正！")
    else:
        print("  [失败] 批量排序请求未能成功生效。")

    print("\n[完成] 专辑已达到理想状态！")

if __name__ == '__main__':
    optimize()
