import os
import re
import time
import json
import sys
import subprocess
import requests

# ================= SDK Core: BenewClient =================

class BenewClient:
    """本牛云盘 SDK 核心类，封装所有 API 与 业务逻辑"""

    def __init__(self, cookie=None, family_id=None):
        self.env_path = os.path.join(os.getcwd(), ".env.benew")
        env = self._load_env()
        self.cookie = cookie or env.get('COOKIE')
        self.family_id = family_id or env.get('FAMILY_ID')
        
        self.base_headers = {
            "Cookie": self.cookie,
            "Origin": "https://pan.benewtech.cn",
            "Referer": "https://pan.benewtech.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }

    def _load_env(self):
        env = {}
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip().strip("'").strip('"')
        return env

    def _update_env(self, key, value):
        content = ""
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                content = f.read()

        if f"{key}=" in content:
            content = re.sub(f'{key}=[\'"].*?[\'"]', f'{key}={repr(value)}', content)
            content = re.sub(f'{key}=.*?\n', f'{key}={repr(value)}\n', content)
        else:
            content += f'\n{key}={repr(value)}\n'

        with open(self.env_path, "w") as f:
            f.write(content)

    # --- 文件夹与专辑管理 ---

    def folders_list(self):
        url = "https://gateway.benewtech.cn/resources-app/babyCollection/web/getCloudCollections"
        params = {"offset": 0, "limit": 100, "familyId": self.family_id}
        resp = requests.get(url, headers=self.base_headers, params=params).json()
        return resp.get("data", {}).get("datas", []) if resp.get("code") == 200 else []

    def folders_create(self, name):
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/app/createCollection?type=CLOUD&familyId={self.family_id}"
        return requests.post(url, headers=self.base_headers, json={"coverKey": "", "name": name}).json()

    def albums_list(self, folder_id):
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/collection/{folder_id}/albums"
        params = {"offset": 0, "limit": 100, "familyId": self.family_id}
        resp = requests.post(url, headers=self.base_headers, params=params, json={}).json()
        return resp.get("data", {}).get("datas", []) if resp.get("code") == 200 else []

    def albums_create(self, folder_id, name):
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/create?collectionId={folder_id}&familyId={self.family_id}"
        return requests.post(url, headers=self.base_headers, json={"name": name, "coverKey": ""}).json()

    # --- 轨道管理 (Tracks) ---

    def tracks_list(self, album_id):
        tracks = []
        offset = 0
        while True:
            url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/{album_id}/tracks"
            params = {"offset": offset, "limit": 50, "familyId": self.family_id}
            resp = requests.get(url, headers=self.base_headers, params=params).json()
            if resp.get("code") == 200:
                batch = resp.get("data", {}).get("datas", [])
                tracks.extend(batch)
                if len(tracks) >= resp.get("data", {}).get("count", 0) or not batch: break
                offset += 50
            else: break
        return tracks

    def tracks_delete(self, track_ids):
        if isinstance(track_ids, (str, int)): track_ids = [int(track_ids)]
        url = "https://gateway.benewtech.cn/resources-app/cloud/web/tracks/delete"
        return requests.post(url, headers=self.base_headers, json={"uids": track_ids}).json()

    def tracks_update(self, track_id, name=None, cover_key=None):
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/tracks/{track_id}/update?familyId={self.family_id}"
        payload = {k: v for k, v in {"name": name, "coverKey": cover_key}.items() if v is not None}
        return requests.post(url, headers=self.base_headers, json=payload).json()

    # --- 核心同步逻辑 (Sync) ---

    def sync(self, album_id, watch_dir):
        print(f"📦 开始同步目录: {watch_dir} 到专辑: {album_id}")
        if not os.path.exists(watch_dir): return "目录不存在"
        
        local_files = sorted([f for f in os.listdir(watch_dir) if f.endswith('.mp3')])
        if not local_files: return "未发现待上传文件"

        # 获取已存在音轨避免重复
        cloud_tracks = self.tracks_list(album_id)
        cloud_names = {self._normalize_name(t['name']) for t in cloud_tracks}
        
        # 获取上传凭证
        token_resp = requests.post('https://gateway.benewtech.cn/resources-app/qiniu/uptoken', 
                                  headers=self.base_headers, json={'types': ['TRACKS']}).json()
        token = token_resp.get('data', {}).get('trackToken')
        if not token: return "无法获取上传凭证"

        # 嗅探专辑封面
        album_info = requests.get(f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{album_id}', 
                                 headers=self.base_headers, params={'familyId': self.family_id}).json()
        cover_key = album_info.get('data', {}).get('coverUrl', '').split('/')[-1]

        for file_name in local_files:
            clean_name = self._normalize_name(os.path.splitext(file_name)[0])
            if clean_name in cloud_names:
                print(f"⏩ 跳过已存在: {file_name}")
                continue
            
            file_path = os.path.join(watch_dir, file_name)
            print(f"⬆️ 正在上传: {file_name}")
            
            with open(file_path, 'rb') as f:
                qiniu_resp = requests.post('https://upload.qiniup.com/', 
                    files={'file': (file_name, f, 'audio/mpeg'), 'token': (None, token), 'key': (None, file_name)}).json()
            
            qiniu_key = qiniu_resp.get('key')
            if qiniu_key:
                duration = self._get_duration(file_path)
                reg_url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{album_id}/tracks/upload?familyId={self.family_id}'
                reg_data = {"trackUploadResults": [{"key": qiniu_key, "fname": file_name, "size": os.path.getsize(file_path), "duration": duration, "fileFormat": "mp3", "coverKey": cover_key}]}
                requests.post(reg_url, headers=self.base_headers, json=reg_data)
                print(f"✅ 完成: {file_name}")
        
        print("🎉 同步结束，正在触发自动优化...")
        self.optimize(album_id, watch_dir)

    # --- 辅助与优化逻辑 ---

    def optimize(self, album_id, watch_dir=None):
        print(f"🛠️ 正在优化专辑: {album_id}...")
        tracks = self.tracks_list(album_id)
        
        # 1. 去重 (基于编号或清洗后的名称)
        groups = {}
        for t in tracks:
            num = self._extract_number(t['name'])
            key = f"N_{num}" if num else f"T_{self._normalize_name(t['name'])}"
            groups.setdefault(key, []).append(t)
        
        to_delete, to_keep = [], []
        for g in groups.values():
            g.sort(key=lambda x: x.get('updated', ''))
            to_keep.append(g[0])
            to_delete.extend([t['uid'] for t in g[1:]])
        
        if to_delete:
            print(f"🗑️ 删除重复项: {len(to_delete)} 个")
            self.tracks_delete(to_delete)

        # 2. 排序与名称修正
        to_keep.sort(key=lambda t: (0, int(n)) if (n := self._extract_number(t['name'])) else (1, t['name']))
        sorted_uids = []
        for t in to_keep:
            uid = t['uid']
            self.tracks_update(uid, name=self._normalize_name(t['name']))
            sorted_uids.append(uid)
        
        url = f'https://gateway.benewtech.cn/resources-app/cloud/web/{album_id}/tracks/reorder?familyId={self.family_id}'
        requests.post(url, headers=self.base_headers, json={"trackIds": sorted_uids})
        print("✅ 优化完成")

    def _normalize_name(self, name):
        name = re.sub(r'\s*\((\d+)\)\s*$', '', name)
        return re.sub(r'\s+', ' ', name).strip()

    def _extract_number(self, name):
        match = re.search(r'^(\d{3})', name.strip())
        return match.group(1) if match else None

    def _get_duration(self, file_path):
        try:
            res = subprocess.run(['afinfo', file_path], capture_output=True, text=True)
            match = re.search(r'estimated duration: ([\d.]+) sec', res.stdout)
            return int(float(match.group(1))) if match else 0
        except: return 0

# ================= CLI Interface =================

def main():
    client = BenewClient()
    if len(sys.argv) < 2:
        print("Usage: python benew_tool.py <subcommand> [args...]")
        return

    cmd = sys.argv[1]
    
    if cmd == "folder":
        if sys.argv[2] == "list":
            print(json.dumps(client.folders_list(), indent=2, ensure_ascii=False))
        elif sys.argv[2] == "create":
            print(json.dumps(client.folders_create(sys.argv[3]), indent=2, ensure_ascii=False))
    elif cmd == "album":
        if sys.argv[2] == "list":
            print(json.dumps(client.albums_list(sys.argv[3]), indent=2, ensure_ascii=False))
        elif sys.argv[2] == "create":
            print(json.dumps(client.albums_create(sys.argv[3], sys.argv[4]), indent=2, ensure_ascii=False))
    elif cmd == "track":
        if sys.argv[2] == "list":
            print(json.dumps(client.tracks_list(sys.argv[3]), indent=2, ensure_ascii=False))
        elif sys.argv[2] == "delete":
            print(json.dumps(client.tracks_delete(sys.argv[3]), indent=2, ensure_ascii=False))
        elif sys.argv[2] == "update":
            print(json.dumps(client.tracks_update(sys.argv[3], name=sys.argv[4]), indent=2, ensure_ascii=False))
    elif cmd == "sync":
        client.sync(sys.argv[2], sys.argv[3])
    elif cmd == "optimize":
        client.optimize(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
