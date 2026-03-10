import requests
import os
import json

# ================= 配置区 =================
COOKIE = os.environ.get('COOKIE')
FAMILY_ID = os.environ.get('FAMILY_ID')
COLLECTION_ID = os.environ.get('COLLECTION_ID')
# =========================================

HEADERS = {
    'Cookie': COOKIE,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Content-Type': 'application/json'
}

def create_album(name, cover_key=""):
    """
    新建一个专辑
    必须依靠 COLLECTION_ID，表示建在哪个父文件夹下。
    """
    if not all([COOKIE, FAMILY_ID, COLLECTION_ID]):
        print("错误: 缺少必要的环境变量 (COOKIE, FAMILY_ID, COLLECTION_ID)")
        return None

    url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/create?collectionId={COLLECTION_ID}&familyId={FAMILY_ID}'
    data = {"name": name, "coverKey": cover_key}
    
    resp = requests.post(url, headers=HEADERS, json=data)
    if resp.status_code == 200:
        return resp.json().get('data') # 会返回刚建好的专辑的信息，包含相册 ID 等
    return None

if __name__ == '__main__':
    # usage example ...
    pass
