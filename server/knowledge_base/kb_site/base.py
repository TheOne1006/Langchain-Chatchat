from typing import List, Dict
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse
from abc import ABC, abstractmethod
import re
import os
import shutil
from server.db.repository.knowledge_site_repository import (list_site_from_db, get_site_detail, delete_site_from_db,
                                                            add_site_to_db, update_site_to_db)

from server.knowledge_base.utils import list_files_from_folder


class KBSiteService(ABC):
    kb_name: str
    
    def __init__(self, kb_name: str):
        self.kb_name = kb_name
    
    def find_site(self, site_name: str):
        """
        查找知识库网站
        :param site_name:
        :return:
        """
        site = get_site_detail(kb_name=self.kb_name, site_name=site_name)
        return site
    
    def find_site_by_id(self, site_id: int):
        """
        查找知识库网站
        :param site_id:
        :return:
        """
        site = get_site_detail(kb_name=self.kb_name, site_id=site_id)
        return site
    
    def add_kb_site(self, site_doc: Dict) -> Dict:
        """
        添加知识库网站
        :param site_doc:
        """
        site = add_site_to_db(kb_name=self.kb_name, site_info=site_doc)
        return site
    
    def update_kb_site(self, site_id: int, site_doc: Dict) -> Dict:
        """
        添加知识库网站
        :param site_id:
        :param site_doc:
        """
        site = update_site_to_db(kb_name=self.kb_name, site_id=site_id, site_info=site_doc)
        return site
    
    @staticmethod
    def check_filter_method(filter_method: str) -> bool:
        allow_filter_methods = ["none", "append"]
        
        if filter_method not in allow_filter_methods:
            raise ValueError(f"filter_method={filter_method} 不在允许的范围内")
        
        return True
    
    # todo
    @staticmethod
    def filter_site_urls(site_urls: List[str], filter_method: str) -> List[str]:
        """
        过滤 site_urls
        :param site_urls:
        :param filter_method:
        :return:
        """
        if filter_method == "none":
            return site_urls
        
        elif filter_method == "append":
            return site_urls
    
    @staticmethod
    def check_urls(urls: List[str]) -> bool:
        """
        校验 urls 格式
        """
        pattern = re.compile(r'^https?://\S+')
        for item_url in urls:
            if not pattern.match(item_url):
                msg = f"{item_url} 格式错误"
                raise ValueError(msg)
        return True
    
    @staticmethod
    def check_folder(kb_doc_path: str, folder_name: str) -> str:
        """
        校验文件夹名称
        """
        pattern = re.compile(r'^[0-9a-zA-Z-_]+$')
        
        if not pattern.match(folder_name):
            msg = f" 目录 {folder_name} 格式错误"
            raise ValueError(msg)
        
        target_folder_path = os.path.join(kb_doc_path, folder_name)
        
        if os.path.exists(target_folder_path):
            msg = f" 目录 {folder_name} 已存在"
            raise ValueError(msg)
        
        return target_folder_path
    
    @staticmethod
    def soup_change_link_src(soup: BeautifulSoup, hostname: str):
        """
        修改 href 和 src
        :param soup:
        :param hostname:
        """
        for tag in soup.find_all(attrs={"href": re.compile(r'^/')}):
            # 将链接替换为新的链接，例如"https://newlink.com"
            tag['href'] = f"{hostname}{tag['href']}"
        
        for tag in soup.find_all(attrs={"src": re.compile(r'^/')}):
            # 将链接替换为新的链接，例如"https://newlink.com"
            tag['src'] = f"{hostname}{tag['src']}"
    
    @staticmethod
    def soup_remove_selectors(soup: BeautifulSoup, selector: List[str]):
        """
        删除不需要的标签
        :param soup:
        :param selector:
        """
        for selector in selector:
            for ele in soup.select(selector):
                ele.decompose()
    
    @staticmethod
    def soup_add_base_tag(soup: BeautifulSoup, hostname: str):
        """
        添加base标签
        :param soup:
        :param hostname:
        """
        head_tag = soup.find("head")
        base_tag = soup.new_tag('base', href=hostname)
        head_tag.append(base_tag)
    
    @staticmethod
    def get_folder_url_path(kb_doc_path: str, folder: str, url: str) -> Path:
        """
        获取 url 路径
        :param kb_doc_path:
        :param folder:
        :param url:
        :return:
        """
        # url 解析
        url_parse_obj = urlparse(url)
        file_name = url_parse_obj.path.lstrip('/') + '.html'
        cur_file_path = Path(os.path.join(kb_doc_path, folder.lstrip('/'), file_name))
        
        return cur_file_path
    
    @staticmethod
    def get_local_site_urls(kb_doc_path: str, folder: str) -> List[str]:
        """
        获取 url 路径
        :param kb_doc_path:
        :param folder:
        :return:
        """
        cur_file_path = Path(os.path.join(kb_doc_path, folder.lstrip('/')))
        
        # copy from server/knowledge_base/utils.py
        result = []
        
        def is_skiped_path(path: str):
            tail = os.path.basename(path).lower()
            for x in ["temp", "tmp", ".", "~$"]:
                if tail.startswith(x):
                    return True
            return False
        
        def process_entry(entry):
            if is_skiped_path(entry.path):
                return
            
            if entry.is_symlink():
                target_path = os.path.realpath(entry.path)
                with os.scandir(target_path) as target_it:
                    for target_entry in target_it:
                        process_entry(target_entry)
            elif entry.is_file():
                result.append(entry.path)
            elif entry.is_dir():
                with os.scandir(entry.path) as it:
                    for sub_entry in it:
                        process_entry(sub_entry)
        
        with os.scandir(cur_file_path) as it:
            for entry in it:
                process_entry(entry)
        
        return result
