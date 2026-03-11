#!/usr/bin/env python3
"""
网盘MCP服务器
包含用户配额、用户信息查询、文件管理、上传下载以及搜索工具
"""
import os
import sys
from typing import Dict, Any, Optional, List
import hashlib
import requests
import datetime
import json
import io
import time
import random
import re
# 添加当前目录到系统路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# 导入MCP相关库
from mcp.server.fastmcp import FastMCP, Context

# 导入网盘SDK相关库
import openapi_client
from openapi_client.api import fileupload_api, fileinfo_api, filemanager_api, userinfo_api, multimediafile_api
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "config.json")
access_token = os.getenv('BAIDU_NETDISK_ACCESS_TOKEN')

def get_or_save_access_token():
    global access_token
    config_data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception:
            pass
            
    token_from_config = config_data.get('BAIDU_NETDISK_ACCESS_TOKEN', '')
    
    if token_from_config and str(token_from_config).strip():
        access_token = str(token_from_config).strip()
    elif access_token and str(access_token).strip():
        config_data['BAIDU_NETDISK_ACCESS_TOKEN'] = str(access_token).strip()
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save access_token to config.json: {e}", file=sys.stderr)

get_or_save_access_token()

# 创建MCP服务器
mcp = FastMCP("网盘服务")

@mcp.tool()
def configure_token(auth_url: str) -> Dict[str, Any]:
    """
    配置百度网盘 Access Token。
    当 API 调用提示未授权或是未配置 Token 时，可调用此工具。
    请先向用户发送授权链接：https://openapi.baidu.com/oauth/2.0/authorize?response_type=token&client_id=QHOuRXiepJBMjtk0esLhrPoNlQyYd0mF&redirect_uri=oob&scope=basic,netdisk
    点击授权后，请将最终跳转页面浏览器地址栏里的 完整URL 传入本工具解析。
    
    参数:
    - auth_url: 用户授权后由浏览器跳转的完整 URL
    """
    global access_token
    match = re.search(r'access_token=([^&]+)', auth_url)
    if not match:
        return {"status": "error", "message": "未能从 URL 中找到 access_token，请确保提供的 URL 正确。"}
    
    token = match.group(1)
    access_token = token
    
    config_data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception:
            pass
            
    config_data['BAIDU_NETDISK_ACCESS_TOKEN'] = token
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return {"status": "error", "message": f"Token 提取成功，但保存到配置文件失败: {e}"}
        
    return {"status": "success", "message": "Token 配置并保存成功！可以开始使用其他网盘工具了。"}

# 定义分片大小为4MB
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB
# 定义重试次数和超时时间
MAX_RETRIES = 3
RETRY_BACKOFF = 2
TIMEOUT = 30

def get_api_client():
    configuration = openapi_client.Configuration()
    configuration.connection_pool_maxsize = 10
    configuration.retries = MAX_RETRIES
    return openapi_client.ApiClient(configuration)

@mcp.tool()
def get_user_info() -> Dict[str, Any]:
    """获取当前登录用户的基础信息"""
    with get_api_client() as api_client:
        api_instance = userinfo_api.UserinfoApi(api_client)
        try:
            return api_instance.xpanuinfo(access_token=access_token)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def get_quota() -> Dict[str, Any]:
    """获取网盘容量配额信息"""
    with get_api_client() as api_client:
        api_instance = userinfo_api.UserinfoApi(api_client)
        try:
            return api_instance.xpanuserquota(access_token=access_token, checkfree=1, checkexpire=1)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def list_files(path: str = "/", order: str = "name", desc: int = 0, start: int = 0, limit: int = 100) -> Dict[str, Any]:
    """
    列出指定目录下的文件列表
    
    参数:
    - path: 目录路径，以/开头
    - order: 排序字段 (time, name, size)
    - desc: 是否降序 (0: 升序, 1: 降序)
    - start: 起始位置
    - limit: 返回数量限制
    """
    with get_api_client() as api_client:
        api_instance = fileinfo_api.FileinfoApi(api_client)
        try:
            return api_instance.xpanfilelist(access_token=access_token, dir=path, order=order, desc=desc, start=str(start), limit=limit)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def search_files(keyword: str, path: str = "/", recursion: int = 1) -> Dict[str, Any]:
    """
    搜索网盘内的文件
    
    参数:
    - keyword: 搜索关键词
    - path: 搜索起始目录
    - recursion: 是否递归搜索 (0: 不递归, 1: 递归)
    """
    with get_api_client() as api_client:
        api_instance = fileinfo_api.FileinfoApi(api_client)
        try:
            return api_instance.xpanfilesearch(access_token=access_token, key=keyword, dir=path, recursion=str(recursion))
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def get_file_metas(fsids: List[int]) -> Dict[str, Any]:
    """
    获取指定文件的详细元数据
    
    参数:
    - fsids: 文件标识列表 (fs_id 列表)
    """
    with get_api_client() as api_client:
        api_instance = multimediafile_api.MultimediafileApi(api_client)
        try:
            fsids_str = json.dumps(fsids)
            return api_instance.xpanfilemultimedia(access_token=access_token, fsids=fsids_str)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def mkdir(path: str) -> Dict[str, Any]:
    """
    创建文件夹
    
    参数:
    - path: 文件夹路径，以/开头
    """
    with get_api_client() as api_client:
        api_instance = fileupload_api.FileuploadApi(api_client)
        try:
            # 创建目录在网盘 API 中通过 xpanfilecreate 实现，isdir=1
            return api_instance.xpanfilecreate(
                access_token=access_token, 
                path=path, 
                isdir=1, 
                size=0, 
                uploadid="0", 
                block_list='[]', 
                rtype=3
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def list_documents(path: str = "/", recursion: int = 1, page: int = 1, num: int = 100) -> Dict[str, Any]:
    """获取指定目录下的文档列表"""
    with get_api_client() as api_client:
        api_instance = fileinfo_api.FileinfoApi(api_client)
        try:
            return api_instance.xpanfiledoclist(access_token=access_token, parent_path=path, recursion=str(recursion), page=page, num=num)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def list_images(path: str = "/", recursion: int = 1, page: int = 1, num: int = 100) -> Dict[str, Any]:
    """获取指定目录下的图片列表"""
    with get_api_client() as api_client:
        api_instance = fileinfo_api.FileinfoApi(api_client)
        try:
            return api_instance.xpanfileimagelist(access_token=access_token, parent_path=path, recursion=str(recursion), page=page, num=num)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def copy_files(filelist: List[Dict[str, str]], ondup: str = "fail") -> Dict[str, Any]:
    """批量复制文件或目录"""
    with get_api_client() as api_client:
        api_instance = filemanager_api.FilemanagerApi(api_client)
        try:
            return api_instance.filemanagercopy(access_token=access_token, _async=0, filelist=json.dumps(filelist), ondup=ondup)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def move_files(filelist: List[Dict[str, str]], ondup: str = "fail") -> Dict[str, Any]:
    """批量移动文件或目录"""
    with get_api_client() as api_client:
        api_instance = filemanager_api.FilemanagerApi(api_client)
        try:
            return api_instance.filemanagermove(access_token=access_token, _async=0, filelist=json.dumps(filelist), ondup=ondup)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def rename_file(path: str, new_name: str) -> Dict[str, Any]:
    """重命名文件或目录"""
    with get_api_client() as api_client:
        api_instance = filemanager_api.FilemanagerApi(api_client)
        try:
            filelist = json.dumps([{"path": path, "newname": new_name}])
            return api_instance.filemanagerrename(access_token=access_token, _async=0, filelist=filelist)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def delete_files(fsids: List[int]) -> Dict[str, Any]:
    """删除网盘文件"""
    with get_api_client() as api_client:
        api_instance = filemanager_api.FilemanagerApi(api_client)
        try:
            filelist = json.dumps(fsids)
            return api_instance.filemanagerdelete(access_token=access_token, _async=0, filelist=filelist)
        except Exception as e:
            return {"status": "error", "message": str(e)}

@mcp.tool()
def create_share_link(fsids: List[int], password: str = "", period: int = 1) -> Dict[str, Any]:
    """创建文件的分享链接"""
    try:
        import requests
        url = f"https://pan.baidu.com/rest/2.0/xpan/share?method=set&access_token={access_token}"
        data = {
            "fid_list": json.dumps(fsids),
            "schannel": "4",
            "channel_list": "[]",
            "period": str(period)
        }
        if password:
            data["pwd"] = password
        
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def upload_file(local_file_path: str, remote_path: str = None) -> Dict[str, Any]:
    """上传本地文件到网盘指定路径 (支持断点续传和大文件分片)"""
    try:
        if not os.path.isfile(local_file_path):
            return {"status": "error", "message": f"本地文件不存在: {local_file_path}"}
        
        filename = os.path.basename(local_file_path)
        if not remote_path:
            remote_path = f"/来自：mcp_server/{filename}"
        elif remote_path.endswith('/'):
            remote_path = f"{remote_path}{filename}"
        
        file_size = os.path.getsize(local_file_path)
        configuration = openapi_client.Configuration()
        
        if file_size <= CHUNK_SIZE:
            return upload_small_file(local_file_path, remote_path, file_size, access_token, configuration)
        else:
            return upload_large_file(local_file_path, remote_path, file_size, access_token, configuration)
                
    except Exception as e:
        return {"status": "error", "message": f"上传错误: {str(e)}"}

def upload_small_file(local_file_path, remote_path, file_size, access_token, configuration=None):
    with open(local_file_path, 'rb') as f:
        file_content = f.read()
    file_md5 = hashlib.md5(file_content).hexdigest()
    block_list = f'["{file_md5}"]'
    with openapi_client.ApiClient(configuration) as api_client:
        api_instance = fileupload_api.FileuploadApi(api_client)
        pre = api_instance.xpanfileprecreate(access_token=access_token, path=remote_path, isdir=0, size=file_size, autoinit=1, block_list=block_list, rtype=3)
        uploadid = pre['uploadid']
        with open(local_file_path, 'rb') as file:
            api_instance.pcssuperfile2(access_token=access_token, partseq="0", path=remote_path, uploadid=uploadid, type="tmpfile", file=file)
        res = api_instance.xpanfilecreate(access_token=access_token, path=remote_path, isdir=0, size=file_size, uploadid=uploadid, block_list=block_list, rtype=3)
        return {"status": "success", "remote_path": remote_path, "fs_id": res.get('fs_id')}

def upload_large_file(local_file_path, remote_path, file_size, access_token, configuration=None):
    chunk_count = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    md5_list = []
    with open(local_file_path, 'rb') as f:
        for i in range(chunk_count):
            md5_list.append(hashlib.md5(f.read(CHUNK_SIZE)).hexdigest())
    block_list = json.dumps(md5_list)
    with openapi_client.ApiClient(configuration) as api_client:
        api_instance = fileupload_api.FileuploadApi(api_client)
        pre = api_instance.xpanfileprecreate(access_token=access_token, path=remote_path, isdir=0, size=file_size, autoinit=1, block_list=block_list, rtype=3)
        uploadid = pre['uploadid']
        with open(local_file_path, 'rb') as f:
            for i in range(chunk_count):
                chunk_data = f.read(CHUNK_SIZE)
                file_obj = io.BytesIO(chunk_data)
                file_obj.name = os.path.basename(local_file_path)
                api_instance.pcssuperfile2(access_token=access_token, partseq=str(i), path=remote_path, uploadid=uploadid, type="tmpfile", file=file_obj)
        res = api_instance.xpanfilecreate(access_token=access_token, path=remote_path, isdir=0, size=file_size, uploadid=uploadid, block_list=block_list, rtype=3)
        return {"status": "success", "remote_path": remote_path, "fs_id": res.get('fs_id')}

if __name__ == "__main__":
    mcp.run(transport="stdio")