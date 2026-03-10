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

class BenewCloudManager:
    """本牛云盘全功能管理类 (文件夹 & 专辑 CRUD)"""
    
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

    # --- 文件夹管理 (Collections) ---

    def list_folders(self):
        """列出根目录下的文件夹"""
        url = "https://gateway.benewtech.cn/resources-app/babyCollection/web/getCloudCollections"
        params = {"offset": 0, "limit": 100, "familyId": self.family_id}
        resp = requests.get(url, headers=self.base_headers, params=params)
        data = resp.json()
        if data.get("code") == 200:
            return data.get("data", {}).get("datas", [])
        return []

    def create_folder(self, name):
        """新建根目录文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/app/createCollection?type=CLOUD&familyId={self.family_id}"
        payload = {"coverKey": "", "name": name}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        return resp.json()

    def rename_folder(self, folder_id, new_name):
        """重命名文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/app/{folder_id}/updateCollection?familyId={self.family_id}"
        payload = {"name": new_name}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        return resp.json()

    def delete_folder(self, folder_id):
        """删除文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/{folder_id}/deleteCollections?familyId={self.family_id}"
        payload = {"collectionIds": [int(folder_id)]}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        return resp.json()

    # --- 专辑管理 (Albums) ---

    def list_albums(self, folder_id):
        """列出指定文件夹下的专辑"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/collection/{folder_id}/albums"
        params = {"offset": 0, "limit": 100, "familyId": self.family_id}
        resp = requests.post(url, headers=self.base_headers, params=params, json={})
        data = resp.json()
        if data.get("code") == 200:
            return data.get("data", {}).get("datas", [])
        return []

    def create_album(self, folder_id, name):
        """在指定页面下新建专辑"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/create?collectionId={folder_id}&familyId={self.family_id}"
        payload = {"name": name, "coverKey": ""}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        return resp.json()

    def update_album(self, album_id, new_name):
        """更新专辑基本信息 (如改名)"""
        url = f"https://gateway.benewtech.cn/resources-app/cloud/web/albums/{album_id}/update?familyId={self.family_id}"
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
        return resp.json()

    def delete_album(self, folder_id, album_id):
        """删除专辑 (从文件夹中移除)"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/web/removeFromCollections?familyId={self.family_id}"
        payload = {
            "collectionIds": [int(folder_id)],
            "albumIds": [int(album_id)]
        }
        resp = requests.post(url, headers=self.base_headers, json=payload)
        return resp.json()

if __name__ == "__main__":
    import sys
    
    manager = BenewCloudManager()
    
    if len(sys.argv) < 2:
        print("Usage: python cloud_manager.py [list_folders | list_albums <folder_id>]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    
    if cmd == "list_folders":
        folders = manager.list_folders()
        print(json.dumps(folders, indent=2, ensure_ascii=False))
    elif cmd == "list_albums" and len(sys.argv) > 2:
        albums = manager.list_albums(sys.argv[2])
        print(json.dumps(albums, indent=2, ensure_ascii=False))
    elif cmd == "create_folder" and len(sys.argv) > 2:
        result = manager.create_folder(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "rename_folder" and len(sys.argv) > 3:
        result = manager.rename_folder(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "delete_folder" and len(sys.argv) > 2:
        result = manager.delete_folder(sys.argv[2])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "create_album" and len(sys.argv) > 3:
        result = manager.create_album(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "update_album" and len(sys.argv) > 3:
        result = manager.update_album(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "delete_album" and len(sys.argv) > 3:
        result = manager.delete_album(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage:")
        print("  list_folders")
        print("  list_albums <folder_id>")
        print("  create_folder <name>")
        print("  rename_folder <folder_id> <new_name>")
        print("  delete_folder <folder_id>")
        print("  create_album <folder_id> <name>")
        print("  update_album <album_id> <new_name>")
        print("  delete_album <folder_id> <album_id>")
