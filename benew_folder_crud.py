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

class BenewFolderCRUD:
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

    def create_folder(self, name):
        """新建根目录文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/app/createCollection?type=CLOUD&familyId={self.family_id}"
        payload = {"coverKey": "", "name": name}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            folder_id = data.get("data", {}).get("uid")
            print(f"[Create] 成功创建文件夹 '{name}', ID: {folder_id}")
            return folder_id
        else:
            print(f"[Create] 失败: {data.get('message')}")
            return None

    def rename_folder(self, folder_id, new_name):
        """重命名文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/app/{folder_id}/updateCollection?familyId={self.family_id}"
        payload = {"name": new_name}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            print(f"[Rename] 成功将文件夹 ID {folder_id} 重命名为 '{new_name}'")
            return True
        else:
            print(f"[Rename] 失败: {data.get('message')}")
            return False

    def delete_folder(self, folder_id):
        """删除文件夹"""
        url = f"https://gateway.benewtech.cn/resources-app/babyCollection/{folder_id}/deleteCollections?familyId={self.family_id}"
        payload = {"collectionIds": [int(folder_id)]}
        resp = requests.post(url, headers=self.base_headers, json=payload)
        data = resp.json()
        if data.get("code") == 200:
            print(f"[Delete] 成功删除文件夹 ID {folder_id}")
            return True
        else:
            print(f"[Delete] 失败: {data.get('message')}")
            return False

    def list_folders(self):
        """列出根目录下的文件夹"""
        url = "https://gateway.benewtech.cn/resources-app/babyCollection/web/getCloudCollections"
        params = {"offset": 0, "limit": 50, "familyId": self.family_id}
        resp = requests.get(url, headers=self.base_headers, params=params)
        data = resp.json()
        if data.get("code") == 200:
            return data.get("data", {}).get("datas", [])
        return []

if __name__ == "__main__":
    crud = BenewFolderCRUD()
    
    print("--- 开始根目录文件夹 CRUD 测试 ---")
    # 1. Create
    folder_id = crud.create_folder("Script_Folder_Test")
    
    if folder_id:
        time.sleep(1)
        # 2. Update/Rename
        crud.rename_folder(folder_id, "Script_Folder_Test_Renamed")
        
        time.sleep(1)
        # 3. Read
        print("\n当前根目录下的文件夹列表:")
        folders = crud.list_folders()
        for f in folders:
            print(f"- {f.get('name')} (ID: {f.get('uid')})")
        
        time.sleep(1)
        # 4. Delete
        # 验证是否是测试创建的文件夹，双重保险
        if folder_id:
            crud.delete_folder(folder_id)
    
    print("\n--- 根目录文件夹 CRUD 测试结束 ---")
