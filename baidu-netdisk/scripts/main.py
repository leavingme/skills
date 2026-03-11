#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘操作 Skill
支持功能：文件列表、上传、下载、分享链接提取、转存、搜索
"""

import os
import sys
import json
import re
import requests
from urllib.parse import quote, unquote
from pathlib import Path

class BaiduNetdiskAPI:
    """百度网盘 API 封装"""
    
    BASE_URL = "https://pan.baidu.com/rest/2.0/xpan"
    
    def __init__(self, bduss: str, stoken: str):
        self.bduss = bduss
        self.stoken = stoken
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://pan.baidu.com/disk/home',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
    def _get_cookies(self):
        """获取认证 cookies"""
        return {
            'BDUSS': self.bduss,
            'STOKEN': self.stoken,
            'BAIDUID': 'undefined',
            'BAIDUID_BFESS': 'undefined'
        }
    
    def list_files(self, path: str = "/", order: str = "time"):
        """列出指定目录的文件"""
        url = f"{self.BASE_URL}/file"
        params = {
            'method': 'list',
            'dir': path,
            'order': order,
            'desc': 1,
            'showempty': 0,
            'web': 1,
            'page': 1,
            'num': 1000
        }
        
        try:
            resp = self.session.get(url, params=params, cookies=self._get_cookies())
            data = resp.json()
            
            if data.get('errno') == 0:
                files = data.get('list', [])
                result = []
                for f in files:
                    result.append({
                        'name': f.get('server_filename'),
                        'path': f.get('path'),
                        'size': self._format_size(f.get('size', 0)),
                        'is_dir': f.get('isdir') == 1,
                        'modify_time': f.get('server_mtime'),
                        'fs_id': f.get('fs_id')
                    })
                return {'success': True, 'files': result, 'count': len(result)}
            else:
                return {'success': False, 'error': f"API错误: {data.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_files(self, keyword: str, path: str = "/"):
        """搜索文件"""
        url = f"{self.BASE_URL}/file"
        params = {
            'method': 'search',
            'key': keyword,
            'dir': path,
            'web': 1,
            'page': 1,
            'num': 1000
        }
        
        try:
            resp = self.session.get(url, params=params, cookies=self._get_cookies())
            data = resp.json()
            
            if data.get('errno') == 0:
                files = data.get('list', [])
                result = []
                for f in files:
                    result.append({
                        'name': f.get('server_filename'),
                        'path': f.get('path'),
                        'size': self._format_size(f.get('size', 0)),
                        'is_dir': f.get('isdir') == 1
                    })
                return {'success': True, 'files': result, 'count': len(result)}
            else:
                return {'success': False, 'error': f"API错误: {data.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _verify_and_get_share_params(self, share_url: str, extract_code: str = ""):
        """辅助方法：提取分享链接信息并验证提取码"""
        match = re.search(r'/s/([\w-]+)', share_url)
        if not match:
            return {'success': False, 'error': '无效的分享链接'}
        
        shorturl = match.group(1)
        surl = shorturl[1:] if shorturl.startswith('1') else shorturl
        
        # 1. Fetch metadata
        uk = None
        shareid = None
        try:
            resp_html = self.session.get(share_url, cookies=self._get_cookies())
            html = resp_html.text
            uk_match = re.search(r'"share_uk"\s*:\s*"?(\d+)"?', html)
            shareid_match = re.search(r'"shareid"\s*:\s*"?(\d+)"?', html)
            if uk_match: uk = uk_match.group(1)
            if shareid_match: shareid = shareid_match.group(1)
        except Exception as e:
            pass # ignore, maybe verify will still work without them
            
        # 2. Verify extract code
        if extract_code:
            verify_url = "https://pan.baidu.com/share/verify"
            params = {'surl': surl}
            data = {'pwd': extract_code}
            self.session.headers.update({'Referer': share_url})
            try:
                resp = self.session.post(verify_url, params=params, data=data, cookies=self._get_cookies())
                verify_data = resp.json()
                if verify_data.get('errno') != 0:
                    return {'success': False, 'error': f"提取码错误或请求失败 (errno: {verify_data.get('errno')})"}
            except Exception as e:
                return {'success': False, 'error': f'验证失败: {str(e)}'}
                
        # 3. Get sekey
        sekey = self.session.cookies.get('BDCLND')
        if sekey:
            from urllib.parse import unquote
            sekey = unquote(sekey)
            
        return {
            'success': True,
            'surl': surl,
            'uk': uk,
            'shareid': shareid,
            'sekey': sekey
        }

    def extract_share(self, share_url: str, extract_code: str = ""):
        """提取分享链接的文件列表（根目录）"""
        params_info = self._verify_and_get_share_params(share_url, extract_code)
        if not params_info.get('success'):
            return params_info
        
        url = "https://pan.baidu.com/share/list"
        params = {
            'shorturl': params_info['surl'],
            'root': 1,
            'page': 1,
            'num': 1000
        }
        if params_info['uk']: params['uk'] = params_info['uk']
        if params_info['shareid']: params['shareid'] = params_info['shareid']
        if params_info['sekey']: params['sekey'] = params_info['sekey']
        
        try:
            resp = self.session.get(url, params=params, cookies=self._get_cookies())
            data = resp.json()
            
            if data.get('errno') == 0:
                files = data.get('list', [])
                result = []
                for f in files:
                    result.append({
                        'name': f.get('server_filename'),
                        'path': f.get('path'),
                        'size': self._format_size(f.get('size', 0)),
                        'is_dir': f.get('isdir') == 1,
                        'fs_id': f.get('fs_id')
                    })
                return {
                    'success': True, 
                    'files': result, 
                    'count': len(result),
                    'shareid': params_info['shareid'],
                    'uk': params_info['uk'],
                    'sekey': params_info['sekey']
                }
            else:
                return {'success': False, 'error': f"API错误: {data.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def list_share(self, share_url: str, extract_code: str = "", path: str = ""):
        """浏览分享链接中的指定子目录
        注：path 参数必须是完整的绝对路径，如 '/我的资源/文件夹/子文件夹'。
        """
        params_info = self._verify_and_get_share_params(share_url, extract_code)
        if not params_info.get('success'):
            return params_info

        url = "https://pan.baidu.com/share/list"
        params = {
            'shorturl': params_info['surl'],
            'page': 1,
            'num': 1000,
        }
        if params_info['uk']: params['uk'] = params_info['uk']
        if params_info['shareid']: params['shareid'] = params_info['shareid']
        if params_info['sekey']: params['sekey'] = params_info['sekey']

        if path:
            params['dir'] = path
            params['root'] = 0
        else:
            params['root'] = 1

        try:
            resp = self.session.get(url, params=params, cookies=self._get_cookies())
            data = resp.json()

            if data.get('errno') == 0:
                files = data.get('list', [])
                result = []
                for f in files:
                    result.append({
                        'name': f.get('server_filename'),
                        'path': f.get('path'),
                        'size': self._format_size(f.get('size', 0)),
                        'is_dir': f.get('isdir') == 1,
                        'fs_id': f.get('fs_id')
                    })
                return {
                    'success': True,
                    'files': result,
                    'count': len(result),
                    'shareid': params_info['shareid'],
                    'uk': params_info['uk'],
                    'sekey': params_info['sekey']
                }
            else:
                return {'success': False, 'error': f"API错误: {data.get('errno')} (注: path 需要提供分享文件基于分享者网盘完整的路径名)"}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def transfer_share(self, share_url: str, extract_code: str = "", save_path: str = "/我的资源", fsids: str = "", share_path: str = ""):
        """转存分享文件到自己的网盘
        
        :param fsids: 可选，逗号分隔的 fsid 列表。
        :param share_path: 可选，分享链接内的子目录路径。如果提供，则转存该目录下的文件。
        """
        # 使用 list_share 获取指定目录的文件信息及元数据 (shareid, uk, sekey)
        list_result = self.list_share(share_url, extract_code, share_path)
        if not list_result['success']:
            return list_result
        
        shareid = list_result.get('shareid')
        uk = list_result.get('uk')
        sekey = list_result.get('sekey')
        
        # 确定要转存的 fsid 列表
        target_fsids = []
        if fsids:
            try:
                target_fsids = [int(fid.strip()) for fid in str(fsids).split(',') if fid.strip()]
            except ValueError:
                return {'success': False, 'error': 'fsids 格式错误，必须是逗号分隔的数字列表'}
        else:
            files = list_result.get('files', [])
            if not files:
                return {'success': False, 'error': f"分享链接的目录 '{share_path or '根目录'}' 中没有文件"}
            target_fsids = [f['fs_id'] for f in files if 'fs_id' in f]
        
        if not target_fsids:
            return {'success': False, 'error': '未找到有效的待转存文件 ID'}
            
        # 执行转存
        bdstoken = self._get_bdstoken()
        url = "https://pan.baidu.com/share/transfer"
        params = {
            'shareid': shareid,
            'from': uk,
            'ondup': 'newcopy',
            'async': 0,
            'channel': 'chunlei',
            'web': 1,
            'app_id': 250528,
            'bdstoken': bdstoken or '',
            'clienttype': 0
        }
        if sekey:
            params['sekey'] = sekey
            
        data = {
            'fsidlist': json.dumps(target_fsids),
            'path': save_path
        }
        
        try:
            resp = self.session.post(url, params=params, data=data, cookies=self._get_cookies())
            result = resp.json()
            
            if result.get('errno') == 0:
                source_desc = f"目录 '{share_path}'" if share_path else "根目录"
                return {
                    'success': True,
                    'message': f'成功从分享{source_desc}转存 {len(target_fsids)} 个文件到 {save_path}'
                }
            else:
                return {'success': False, 'error': f"转存失败，错误码: {result.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': f"转存异常: {str(e)} - 响应内容: {resp.text if 'resp' in locals() else '无'}"}
    
    def create_dir(self, path: str):
        """创建目录"""
        url = "https://pan.baidu.com/api/create"
        
        # 获取父目录
        parent = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
        name = path.split('/')[-1]
        
        data = {
            'path': path,
            'isdir': '1',
            'rtype': '1',
            'block_list': '[]'
        }
        
        try:
            resp = self.session.post(url, data=data, cookies=self._get_cookies())
            data = resp.json()
            
            if data.get('errno') == 0:
                return {'success': True, 'message': f'目录创建成功: {path}'}
            else:
                return {'success': False, 'error': f"创建失败: {data.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_bdstoken(self):
        """获取 bdstoken"""
        try:
            url = "https://pan.baidu.com/api/gettemplatevariable"
            params = {
                'clienttype': 0,
                'app_id': 250528,
                'web': 1,
                'fields': '["bdstoken"]'
            }
            resp = self.session.get(url, params=params, cookies=self._get_cookies())
            data = resp.json()
            if data.get('errno') == 0:
                return data.get('result', {}).get('bdstoken')
            return None
        except:
            return None
    
    def delete_file(self, path: str):
        """删除文件或目录
        
        使用 filemanager API，需要 bdstoken
        """
        try:
            # 获取 bdstoken
            bdstoken = self._get_bdstoken()
            if not bdstoken:
                return {'success': False, 'error': '无法获取 bdstoken，请检查登录状态'}
            
            url = "https://pan.baidu.com/api/filemanager"
            params = {
                'opera': 'delete',
                'async': '2',
                'onnest': 'fail',
                'channel': 'chunlei',
                'web': 1,
                'app_id': 250528,
                'bdstoken': bdstoken,
                'clienttype': 0
            }
            
            # filelist 是 JSON 数组格式
            data = {
                'filelist': json.dumps([path])
            }
            
            resp = self.session.post(url, params=params, data=data, cookies=self._get_cookies())
            result = resp.json()
            
            if result.get('errno') == 0:
                return {'success': True, 'message': f'删除成功: {path}'}
            else:
                return {'success': False, 'error': f"删除失败，错误码: {result.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def rename_file(self, path: str, new_name: str):
        """重命名文件或目录
        
        使用 filemanager API，需要 bdstoken
        """
        try:
            # 获取 bdstoken
            bdstoken = self._get_bdstoken()
            if not bdstoken:
                return {'success': False, 'error': '无法获取 bdstoken，请检查登录状态'}
            
            # 获取父目录
            parent = '/'.join(path.rstrip('/').split('/')[:-1]) or '/'
            new_path = f"{parent}/{new_name}" if parent != '/' else f"/{new_name}"
            
            url = "https://pan.baidu.com/api/filemanager"
            params = {
                'opera': 'rename',
                'async': '2',
                'onnest': 'fail',
                'channel': 'chunlei',
                'web': 1,
                'app_id': 250528,
                'bdstoken': bdstoken,
                'clienttype': 0
            }
            
            # newname 是 JSON 对象格式: {path: newname}
            data = {
                'newname': json.dumps({path: new_name})
            }
            
            resp = self.session.post(url, params=params, data=data, cookies=self._get_cookies())
            result = resp.json()
            
            if result.get('errno') == 0:
                return {'success': True, 'message': f'重命名成功: {path} -> {new_path}'}
            else:
                return {'success': False, 'error': f"重命名失败，错误码: {result.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def move_file(self, path: str, dest: str):
        """移动文件或目录
        
        使用 filemanager API，需要 bdstoken
        """
        try:
            # 获取 bdstoken
            bdstoken = self._get_bdstoken()
            if not bdstoken:
                return {'success': False, 'error': '无法获取 bdstoken，请检查登录状态'}
            
            url = "https://pan.baidu.com/api/filemanager"
            params = {
                'opera': 'move',
                'async': '2',
                'onnest': 'fail',
                'channel': 'chunlei',
                'web': 1,
                'app_id': 250528,
                'bdstoken': bdstoken,
                'clienttype': 0
            }
            
            # filelist 是 JSON 数组格式，dest 是目标目录
            data = {
                'filelist': json.dumps([path]),
                'dest': dest
            }
            
            resp = self.session.post(url, params=params, data=data, cookies=self._get_cookies())
            result = resp.json()
            
            if result.get('errno') == 0:
                return {'success': True, 'message': f'移动成功: {path} -> {dest}'}
            else:
                return {'success': False, 'error': f"移动失败，错误码: {result.get('errno')}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _format_size(self, size) -> str:
        """格式化文件大小"""
        try:
            size = int(size)
        except (ValueError, TypeError):
            size = 0
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


def main():
    """主入口函数"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'success': False,
            'error': '缺少操作参数'
        }))
        sys.exit(1)
    
    action = sys.argv[1]
    
    # 读取配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {}
    
    bduss = config.get('bduss', os.getenv('BAIDU_BDUSS', ''))
    stoken = config.get('stoken', os.getenv('BAIDU_STOKEN', ''))
    
    if not bduss or not stoken:
        print(json.dumps({
            'success': False,
            'error': '缺少 BDUSS 或 STOKEN 配置，请运行 python scripts/get_cookie_cdp.py 获取凭证'
        }))
        sys.exit(1)
    
    api = BaiduNetdiskAPI(bduss, stoken)
    
    # 解析参数
    params = {}
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            params[key] = value
            
    # 执行操作
    if action == 'login':
        try:
            import get_cookie_cdp
            ok = get_cookie_cdp.fetch_cookies_cdp()
            if ok:
                result = {'success': True, 'message': '登录凭证已获取并保存'}
            else:
                result = {'success': False, 'error': '凭证获取失败，请重试'}
        except ImportError:
            result = {'success': False, 'error': '无法加载获取凭证模块'}
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get('success') else 1)
        
    if action == 'list':
        result = api.list_files(
            path=params.get('path', '/'),
            order=params.get('order', 'time')
        )
    elif action == 'search':
        result = api.search_files(
            keyword=params.get('keyword', ''),
            path=params.get('path', '/')
        )
    elif action == 'extract':
        result = api.extract_share(
            share_url=params.get('share_url', ''),
            extract_code=params.get('extract_code', '')
        )
    elif action == 'list_share':
        result = api.list_share(
            share_url=params.get('share_url', ''),
            extract_code=params.get('extract_code', ''),
            path=params.get('path', '')
        )
    elif action == 'transfer':
        result = api.transfer_share(
            share_url=params.get('share_url', ''),
            extract_code=params.get('extract_code', ''),
            save_path=params.get('save_path', '/我的资源'),
            fsids=params.get('fsids', ''),
            share_path=params.get('share_path', '')
        )
    elif action == 'mkdir':
        result = api.create_dir(
            path=params.get('path', '/')
        )
    elif action == 'delete':
        result = api.delete_file(
            path=params.get('path', '')
        )
    elif action == 'rename':
        result = api.rename_file(
            path=params.get('path', ''),
            new_name=params.get('new_name', '')
        )
    elif action == 'move':
        result = api.move_file(
            path=params.get('path', ''),
            dest=params.get('dest', '')
        )
    else:
        result = {'success': False, 'error': f'未知操作: {action}'}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
