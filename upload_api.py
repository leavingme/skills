import requests
import os
import json

# Configuration
COOKIE = 'connect.sid=s%3ABexm5lCIEntekycCrYmkTCs60aAHc41m.t487iYVmWtQPUrdm3R24F1Iw9fEnHXKI6w57VvKkSnU'
FAMILY_ID = '3056748'
ALBUM_ID = '1697319904'
FILE_PATH = '/Users/leavingme/Downloads/Knock/第二季（更新中）/重播｜伊朗警告封锁霍尔木兹海峡，为什么却可能让你的玩具涨价？.mp3'

HEADERS = {
    'Cookie': COOKIE,
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Origin': 'https://pan.benewtech.cn',
    'Referer': 'https://pan.benewtech.cn/',
}

def upload():
    # 1. Get UpToken
    print("Step 1: Getting UpToken...")
    resp = requests.post(
        'https://gateway.benewtech.cn/resources-app/qiniu/uptoken',
        headers=HEADERS,
        json={'types': ['TRACKS']}
    )
    if resp.status_code != 200:
        print(f"Failed to get uptoken: {resp.status_code} {resp.text}")
        return
    print(f"Response: {resp.text}")
    token_data = resp.json()
    track_token = token_data.get('data', {}).get('trackToken')
    if not track_token:
        print("trackToken not found in response")
        return
    print("UpToken acquired.")

    # 2. Upload to Qiniu
    print("Step 2: Uploading file to Qiniu...")
    file_name = os.path.basename(FILE_PATH)
    file_size = os.path.getsize(FILE_PATH)
    
    with open(FILE_PATH, 'rb') as f:
        files = {
            'file': (file_name, f, 'audio/mpeg'),
            'token': (None, track_token),
            'key': (None, file_name)  # Use filename as key or let Qiniu decide
        }
        resp = requests.post('https://upload.qiniup.com/', files=files)
    
    if resp.status_code != 200:
        print(f"Failed to upload to Qiniu: {resp.status_code} {resp.text}")
        return
    
    qiniu_res = resp.json()
    qiniu_key = qiniu_res.get('key')
    qiniu_hash = qiniu_res.get('hash')
    print(f"File uploaded to Qiniu. Key: {qiniu_key}")

    # 3. Register with Benewtech
    print("Step 3: Registering file with Benewtech...")
    # Typically duration is needed, but maybe optional or we can guess. 
    # Let's try without duration first or provide a dummy one if it fails.
    register_data = {
        "trackUploadResults": [
            {
                "key": qiniu_key,
                "fname": file_name,
                "size": file_size,
                "duration": 845,
                "fileFormat": "mp3"
            }
        ]
    }
    
    register_url = f'https://gateway.benewtech.cn/resources-app/cloud/web/albums/{ALBUM_ID}/tracks/upload?familyId={FAMILY_ID}'
    resp = requests.post(register_url, headers=HEADERS, json=register_data)
    
    if resp.status_code == 200:
        print("Successfully registered file!")
        print(resp.json())
    else:
        print(f"Failed to register file: {resp.status_code} {resp.text}")

if __name__ == '__main__':
    upload()
