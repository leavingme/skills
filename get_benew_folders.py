import requests
import os
import json
import urllib.parse

# ================= 配置区 =================
# 脚本会自动尝试从 .env.benew 读取配置
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

def get_cloud_folders():
    env = load_env()
    
    cookie = env.get('COOKIE')
    family_id = env.get('FAMILY_ID')
    
    if not cookie or not family_id:
        print("错误: 缺少必要的配置参数 (COOKIE 或 FAMILY_ID)。")
        print(f"请确保已经在 {ENV_PATH} 中定义了这些参数。")
        return

    url = "https://gateway.benewtech.cn/resources-app/babyCollection/web/getCloudCollections"
    params = {
        "offset": 0,
        "limit": 50,
        "familyId": family_id
    }
    headers = {
        "Cookie": cookie,
        "Origin": "https://pan.benewtech.cn",
        "Referer": "https://pan.benewtech.cn/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }

    print(f"正在请求接口: {url}")
    print(f"Family ID: {family_id}")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            folders = data.get("data", {}).get("datas", [])
            print(f"\n成功获取共 {len(folders)} 个文件夹：")
            print("-" * 50)
            for folder in folders:
                name = folder.get('name')
                uid = folder.get('uid')
                album_count = folder.get('albumCount', 0)
                created = folder.get('created', '')
                print(f"文件夹: {name}")
                print(f"  ID (UID): {uid}")
                print(f"  专辑数量: {album_count}")
                print(f"  创建时间: {created}")
                print("-" * 50)
        else:
            print(f"请求失败: 业务错误代码 {data.get('code')}, 消息: {data.get('message')}")
            
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    get_cloud_folders()
