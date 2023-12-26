import logging
import urllib

import re
import os
from pathlib import Path
from typing import List
from configs import EMBEDDING_MODEL, logger, log_verbose
from urllib.parse import urlparse
from server.utils import BaseResponse, ListResponse
from server.knowledge_base.utils import validate_kb_name
from server.knowledge_base.kb_service.base import KBServiceFactory
from server.knowledge_base.kb_site.base import KBSiteService
from server.knowledge_base.utils import list_files_from_folder
from fastapi import Body, Query
from fastapi.responses import StreamingResponse
from langchain.document_loaders import AsyncChromiumLoader
from langchain.document_transformers import BeautifulSoupTransformer
from bs4 import BeautifulSoup
import json


_request_params = {
    "site_id": Body(..., examples=[1]),
    "hostname":  Body(..., examples=["https://www.langchain.asia"]),
    "start_urls": Body(..., examples=[["/questions", "/modules/agents"]]),
    "pattern": Body(..., examples=["^https://www.langchain.asia/modules/models.*"]),
    "max_urls": Body(..., examples=[10]),
    "knowledge_base_name": Body(..., description="知识库名称", examples=["samples"]),
    "site_name": Body(..., examples=["langchain中文"]),
    "remove_selectors": Body(..., examples=[[
        "aside", "div.nextra-banner-container", "header",
        "footer", "nav", "div.nx-flex.nx-items-center"
    ]]),
    "folder_name": Body(..., description="目录", examples=["langchain_cn_doc"]),
    "site_urls": Body(..., examples=[[
        "https://www.langchain.asia/modules/agents/getting_started",
        "https://www.langchain.asia/modules/agents"
    ]]),
}


def extract_site_urls(
        hostname: str = _request_params["hostname"],
        start_urls: List[str] = _request_params["start_urls"],
        pattern: str = _request_params["pattern"],
        max_urls: int = _request_params["max_urls"],
) -> BaseResponse:
    """
    从网站中提取链接
    :param hostname:
    :param start_urls:
    :param max_urls:
    :param pattern:
    """
    
    start_urls = [hostname + url if not url.startswith('http') else url for url in start_urls]
    try:
        KBSiteService.check_urls(start_urls)
    except ValueError as e:
        return BaseResponse(code=500, msg=e)
    
    enable_pattern = re.compile(pattern)
    
    loader = AsyncChromiumLoader(start_urls)
    htmls = loader.load()
    links = set([])
    
    for html, start_url in zip(htmls, start_urls):
        
        if len(links) >= max_urls:
            break
        
        # url 解析
        url_parse_obj = urlparse(start_url)
        page_content = html.page_content
        hostname = url_parse_obj.scheme + "://" + url_parse_obj.hostname
        
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # 获取连接
        for link in soup.find_all('a'):
            if len(links) >= max_urls:
                break
            
            link_str = link.get('href', None)
            
            if link_str:
                full_link = link_str if link_str.startswith('http') else hostname + link_str
                if re.match(enable_pattern, full_link):
                    links.add(full_link)
    
    return BaseResponse(code=200, msg=f"信息提取成功", data={"links": list(links)})


def create_site(
        hostname: str = _request_params["hostname"],
        knowledge_base_name: str = _request_params["knowledge_base_name"],
        start_urls: List[str] = _request_params["start_urls"],
        pattern: str = _request_params["pattern"],
        max_urls: int = _request_params["max_urls"],
        site_name: str = _request_params["site_name"],
        remove_selectors: List[str] = _request_params["remove_selectors"],
        folder_name: str = _request_params["folder_name"],
):
    """
     创建 site 信息
    """
    
    # check base_name
    if not validate_kb_name(knowledge_base_name):
        return BaseResponse(code=403, msg="Don't attack me")

    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")
    
    doc_path = kb.doc_path  # knowledge_base/xxx/content
    # check start_urls，folder_name
    
    try:
        full_start_urls = [hostname + url if not url.startswith('http') else url for url in start_urls]
        KBSiteService.check_urls(full_start_urls)
        target_folder_path = KBSiteService.check_folder(doc_path, folder_name)
    except ValueError as e:
        return BaseResponse(code=500, msg=f"{e}")
    
    # 写入 db
    site_service = KBSiteService(knowledge_base_name)
    new_site_info = site_service.add_kb_site({
        "hostname": hostname.rstrip('/ '),
        "site_name": site_name,
        "start_urls": start_urls,
        "pattern": pattern,
        "max_urls": max_urls,
        "kb_name": knowledge_base_name,
        "remove_selectors": remove_selectors,
        "folder_name": folder_name.strip('/ ')
    })
    
    os.mkdir(target_folder_path)
    
    return BaseResponse(code=200, msg=f"创建成功", data={"site": new_site_info})


def update_site(
        site_id: int = _request_params["site_id"],
        knowledge_base_name: str = _request_params["knowledge_base_name"],
        hostname: str = _request_params["hostname"],
        start_urls: List[str] = _request_params["start_urls"],
        pattern: str = _request_params["pattern"],
        max_urls: int = _request_params["max_urls"],
        site_name: str = _request_params["site_name"],
        remove_selectors: List[str] = _request_params["remove_selectors"],
):
    """
     修改 site 信息
    """
    
    try:
        full_start_urls = [hostname + url if not url.startswith('http') else url for url in start_urls]
        KBSiteService.check_urls(full_start_urls)
    except ValueError as e:
        return BaseResponse(code=404, msg=e)
    
    site_service = KBSiteService(knowledge_base_name)
    update_site_info = site_service.update_kb_site(site_id, {
        "hostname": hostname.rstrip('/ '),
        "site_name": site_name,
        "start_urls": start_urls,
        "pattern": pattern,
        "max_urls": max_urls,
        "remove_selectors": remove_selectors,
    })
    
    return BaseResponse(code=200, msg=f"更新成功", data={"site": update_site_info})


def crawl_site_urls(
        knowledge_base_name: str = _request_params["knowledge_base_name"],
        site_id: int = _request_params["site_id"],
        site_urls: List[str] = _request_params["site_urls"],
        filter_method: str = Body(..., examples=["all", "new"]),
):
    """
    更新 site_urls 的信息
    """
    
    site_service = KBSiteService(knowledge_base_name)
    site_info = site_service.find_site(site_id=site_id)
    site_urls = list(set(site_urls))
    
    def output():

        kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
        
        if kb is None:
            return {"code": 404, "msg": f"未找到知识库 {knowledge_base_name}"}
        
        try:
            KBSiteService.check_filter_method(filter_method)
        except ValueError as e:
            return {"code": 500, "msg": e}
        
        doc_path = kb.doc_path  # knowledge_base/xxx/content
        
        local_urls = site_service.get_local_site_urls(doc_path, site_info['folder_name'])
        
        pad_local_site_urls = [site_info['hostname'] + local_url.replace(".html", "")
                               for local_url in local_urls]
        
        # 过滤 需要下载的数据
        filter_site_urls = KBSiteService.filter_site_urls(site_urls, filter_method, pad_local_site_urls)
        
        if not len(filter_site_urls):
            return {"code": 404, "msg": "没有需要更新的网址"}
       
        for i, site_url in enumerate(filter_site_urls):
            
            try:
                loader = AsyncChromiumLoader([site_url])
                htmls = loader.load()
                html = htmls[0]
            except Exception as e:
                return {"code": 500, "msg": f"{site_url} 下载失败"}
            # url 解析
            url_parse_obj = urlparse(site_url)
            hostname = url_parse_obj.scheme + "://" + url_parse_obj.hostname
            
            # 文件 与 文件目录
            cur_file_path = site_service.get_folder_url_path(doc_path, site_info['folder_name'], site_url)
            cur_parent_dir = cur_file_path.parent
            os.makedirs(cur_parent_dir, exist_ok=True)
            
            try:
                page_content = html.page_content
                soup = BeautifulSoup(page_content, 'html.parser')
            except Exception as e:
                logger.error(f'{e.__class__.__name__}: {site_url} 网站解析失败',
                             exc_info=e if log_verbose else None)
                return {"code": 500, "msg": f"{site_url} 网站解析失败"}
                
            try:
                # 内容修改
                site_service.soup_remove_selectors(soup, site_info['remove_selectors'])
                site_service.soup_add_base_tag(soup, hostname=hostname)
                site_service.soup_change_link_src(soup, hostname=hostname)
            except Exception as e:
                logger.error(f'{e.__class__.__name__}: {site_url} 网站内容修改失败',
                             exc_info=e if log_verbose else None)
                return {"code": 500, "msg": f"{site_url} 网站内容修改失败"}
            
            with open(cur_file_path, 'w') as f:
                f.write(soup.prettify())
            
            yield json.dumps({
                "code": 200,
                "msg": f"{site_url} 下载成功",
                "doc": str(cur_file_path),
                "url": site_url,
                "finished": i + 1,
                "total": len(filter_site_urls)
            }, ensure_ascii=False)
        
    return StreamingResponse(output(), media_type="text/event-stream")


def crawl_site_url_force(
        knowledge_base_name: str = _request_params["knowledge_base_name"],
        site_id: int = _request_params["site_id"],
        site_url: str = Body(..., examples=["https://www.langchain.asia/modules/agents"]),
):
    """
    更新 site_urls 的信息
    """
    
    site_service = KBSiteService(knowledge_base_name)
    site_info = site_service.find_site(site_id=site_id)
    
    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    
    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")
    
    doc_path = kb.doc_path  # knowledge_base/xxx/content
    
    # 下载 html 并存放
    loader = AsyncChromiumLoader([site_url])
    htmls = loader.load()
    html = htmls[0]
    
    # url 解析
    url_parse_obj = urlparse(site_url)
    hostname = url_parse_obj.scheme + "://" + url_parse_obj.hostname
    
    # 文件
    cur_file_path = site_service.get_folder_url_path(doc_path, site_info['folder_name'], site_url)
    cur_parent_dir = cur_file_path.parent
    os.makedirs(cur_parent_dir, exist_ok=True)
    
    # 内容修改
    page_content = html.page_content
    soup = BeautifulSoup(page_content)
    
    site_service.soup_remove_selectors(soup, site_info['remove_selectors'])
    site_service.soup_add_base_tag(soup, hostname=hostname)
    site_service.soup_change_link_src(soup, hostname=hostname)
    
    with open(cur_file_path, 'w') as f:
        f.write(soup.prettify())
        
    return BaseResponse(code=200, msg=f"更新成功", data={"doc": cur_file_path, "url": site_url})


def remove_local_site_url(
        knowledge_base_name: str = _request_params["knowledge_base_name"],
        site_id: int = _request_params["site_id"],
        site_url: str = Body(..., examples=["https://www.langchain.asia/modules/agents"]),
):
    """
    删除本地网站文件
    """
    site_service = KBSiteService(knowledge_base_name)
    site_info = site_service.find_site(site_id=site_id)
    
    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    
    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")
    
    doc_path = kb.doc_path  # knowledge_base/xxx/content
    
    # 文件
    cur_file_path = site_service.get_folder_url_path(doc_path, site_info['folder_name'], site_url)
    
    if os.path.exists(cur_file_path):
        os.remove(cur_file_path)
    
    return BaseResponse(code=200, msg=f"删除 成功", data={
        "doc": cur_file_path, "url": site_url
    })


def list_local_site_urls(
        knowledge_base_name: str = Query(..., description="知识库名称", examples=["samples"]),
        folder_name: str = Query(..., description="目录", examples=["langchain_cn_doc"]),
) -> BaseResponse:
    kb = KBServiceFactory.get_service_by_name(knowledge_base_name)
    
    if kb is None:
        return BaseResponse(code=404, msg=f"未找到知识库 {knowledge_base_name}")
    
    doc_path = kb.doc_path  # knowledge_base/xxx/content
    
    site_service = KBSiteService(knowledge_base_name)
    site_info = site_service.find_site(folder_name=folder_name)
    
    files = KBSiteService.get_local_site_urls(doc_path, folder_name)
    
    hostname = site_info['hostname']
    folder_name = site_info['folder_name']
    
    result_list = [
        {
            "url": hostname + item.replace(".html", ""),
            "preview_file": folder_name + item,
        } for item in files
    ]
    
    return BaseResponse(code=200, msg=f"文件列表", data=result_list)


def list_kb_sites(
        knowledge_base_name: str = Query(..., description="知识库名称", examples=["samples"])
) -> BaseResponse:
    """
    获取知识库的网站列表
    """
    site_service = KBSiteService(knowledge_base_name)
    sites = site_service.list_kb_sites()
    return BaseResponse(code=200, msg=f"网站列表", data=sites)
