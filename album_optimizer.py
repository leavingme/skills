import requests
import json
import re
import time

# ================= 配置区 =================
COOKIE = 'connect.sid=s%3ABexm5lCIEntekycCrYmkTCs60aAHc41m.t487iYVmWtQPUrdm3R24F1Iw9fEnHXKI6w57VvKkSnU'
FAMILY_ID = '3056748'
ALBUM_ID = '1697319904'
ALBUM_COVER = 'http://img.benewtech.cn/FgnKmTeXc_oUPljgh6h4r-8sJtH3'
WATCH_DIR = '/Users/leavingme/Downloads/Knock/第二季（更新中）'
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
    # 提取开头的3位数字编号
    match = re.search(r'^(\d{3})', name.strip())
    if match:
        return match.group(1)
    return None

def normalize_name(name):
    # 压缩空格，去除末尾 (1)
    name = re.sub(r'\s*\((\d+)\)\s*$', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def optimize():
    print("Step 1: 获取完整列表...")
    tracks = get_tracks()
    print(f"总计找到 {len(tracks)} 条音轨。")

    # 分组逻辑
    groups = {} # key: 编号 (str) or 完整名 (str)
    
    for t in tracks:
        name = t.get('name', '')
        num = extract_number(name)
        
        # 用户新要求：序号相同即为相同文件
        group_key = f"NUM_{num}" if num else f"NAME_{normalize_name(name)}"
        
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(t)

    to_delete = []
    to_keep = []

    print("Step 2: 判定重复 (按序号去重，保留最早版本)...")
    for key, group in groups.items():
        # 按更新时间排序 (最早的在前)
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
    # 为了确保排序绝对正确，我们按编号对 to_keep 排序
    # 注意：'重播' 等没有编号的会排在最后 (提取到的 num 为 None)
    
    # 手动定义重播的排序逻辑
    def final_sort_key(t):
        name = t.get('name', '')
        num = extract_number(name)
        if num:
            return (0, int(num)) # 0 表示带编号的在前
        return (1, name) # 1 表示其它的在后

    # 获取本地文件映射 (序号 -> 本地文件名)
    import os
    local_name_map = {}
    if os.path.exists(WATCH_DIR):
        for f in os.listdir(WATCH_DIR):
            if f.endswith('.mp3'):
                name_no_ext = os.path.splitext(f)[0]
                # 按照normalize处理一下本地名
                clean_local = normalize_name(name_no_ext)
                num = extract_number(clean_local)
                if num:
                    local_name_map[num] = clean_local

    to_keep.sort(key=final_sort_key)

    sorted_uids = []
    for i, t in enumerate(to_keep, 1):
        uid = t.get('uid')
        num = extract_number(t.get('name', ''))
        
        # 如果能在本地找到对应序号的名字，以本地为准；否则使用原逻辑
        if num and num in local_name_map:
            name = local_name_map[num]
        else:
            name = normalize_name(t.get('name'))
        
        # 提取封面在七牛云上的 Key (以适应单独修改接口)
        cover_key = ALBUM_COVER.split('/')[-1]
        
        update_data = {
            "name": name,
            "coverKey": cover_key
        }
        
        print(f"  [强制更新名称和封面] {name} | UID: {uid}")
        update_track(uid, update_data)
        sorted_uids.append(uid)
        time.sleep(0.3)
        
    print(f"\\nStep 4: 批量保存排序...")
    if reorder_tracks(sorted_uids):
        print("  [成功] 专辑排序已在线修正！")
    else:
        print("  [失败] 批量排序请求未能成功生效。")

    print("\\n[完成] 专辑已达到理想状态！")

if __name__ == '__main__':
    optimize()
