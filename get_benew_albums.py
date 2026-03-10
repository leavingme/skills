import requests
import os
import json

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

def get_albums_in_folder(collection_id):
    env = load_env()
    
    cookie = env.get('COOKIE')
    family_id = env.get('FAMILY_ID')
    
    if not cookie or not family_id:
        print("错误: 缺少必要的配置参数 (COOKIE 或 FAMILY_ID)。")
        return

    # 接口 URL 中包含 collection_id
    url = f"https://gateway.benewtech.cn/resources-app/cloud/web/collection/{collection_id}/albums"
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
    print(f"Folder ID (Collection ID): {collection_id}")
    
    try:
        # 注意：这是 POST 请求
        response = requests.post(url, params=params, headers=headers, json={})
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 200:
            albums = data.get("data", {}).get("datas", [])
            print(f"\n成功在该文件夹下获取共 {len(albums)} 个专辑：")
            print("-" * 50)
            for album in albums:
                print(f"专辑名称: {album.get('name')}")
                print(f"  专辑 ID (UID): {album.get('uid')}")
                print(f"  音频数量: {album.get('trackCnt')}")
                print(f"  创建时间: {album.get('created')}")
                print(f"  更新时间: {album.get('updated')}")
                print("-" * 50)
        else:
            print(f"请求失败: 业务错误代码 {data.get('code')}, 消息: {data.get('message')}")
            
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    # 配置 Knock Knock 世界文件夹 ID: 55835185
    DEFAULT_FOLDER_ID = "55835185"
    get_albums_in_folder(DEFAULT_FOLDER_ID)
