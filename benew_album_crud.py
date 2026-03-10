import requests
import os
import json
import time

# ================= 配置区 =================
ENV_PATH = os.path.join(os.getcwd(), ".env.benew")

def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'").strip('"')
    return env

class BenewAlbumCRUD:
    def __init__(self):
        env = load_env()
        self.cookie = env.get('COOKIE')
        self.family_id = env.get('FAMILY_ID')
        self.base_headers = {
            "Cookie": self.cookie,
            "Origin": "https://pan.benewtech.cn",
            "Referer": "https://pan.benewtech.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }

    def create_album(self, folder_id, name):
        """新建专辑"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/create?collectionId={folder_id}&familyId={self.family_id}"
        payload = {"name": name, "coverKey": ""}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            album_id = data.get("data", {}).get("uid")
            print(f"[Create] 成功创建专辑 '{name}', ID: {album_id}")
            return album_id
        else:
            print(f"[Create] 失败: {data.get('message')}")
            return None

    def update_album(self, album_id, new_name):
        """更新专辑名称"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/{album_id}/update?familyId={self.family_id}"
        # 这里简化了 payload，只保留核心结构
        payload = {
            "name": new_name,
            "introduce": "",
            "fileList": [{
                "uid": "-1",
                "status": "done",
                "url": "http://img.benewtech.cn/ntt%2Fdefault%2Falbum.png",
                "name": "album.png"
            }],
            "inde": 1
        }
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            print(f"[Update] 成功将专辑 ID {album_id} 重命名为 '{new_name}'")
            return True
        else:
            print(f"[Update] 失败: {data.get('message')}")
            return False

    def delete_album(self, folder_id, album_id):
        """删除专辑 (实际上是从集合中移除)"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/web/removeFromCollections?familyId={self.family_id}"
        payload = {
            "collectionIds": [int(folder_id)],
            "albumIds": [int(album_id)]
        }
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            print(f"[Delete] 成功删除专辑 ID {album_id}")
            return True
        else:
            print(f"[Delete] 失败: {data.get('message')}")
            return False

    def list_albums(self, folder_id):
        """列出文件夹下的专辑"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/collection/{folder_id}/albums"
        params = {"offset": 0, "limit": 20, "familyId": self.family_id}
        resp = requests.post(url, headers=self.base_headers, params=params, json={})
        data = resp.json()
        if data.get("code") == 200:
            return data.get("data", {}).get("datas", [])
        return []

if __name__ == "__main__":
    curd = BenewAlbumCRUD()
    folder_id = "56070300" # testdir2
    
    print("--- 开始 CRUD 测试 ---")
    # 1. Create
    album_id = curd.create_album(folder_id, "Magic_CRUD_Test")
    
    if album_id:
        time.sleep(1)
        # 2. Update
        curd.update_album(album_id, "Magic_CRUD_Test_Updated")
        
        time.sleep(1)
        # 3. Read
        print("\n当前文件夹下的专辑:")
        albums = curd.list_albums(folder_id)
        for a in albums:
            print(f"- {a.get('name')} (ID: {a.get('uid')})")
        
        time.sleep(1)
        # 4. Delete
        curd.delete_album(folder_id, album_id)
    
    print("\n--- CRUD 测试结束 ---")
