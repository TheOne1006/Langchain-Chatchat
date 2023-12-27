import streamlit as st
from urllib.parse import quote
from streamlit_tags import st_tags
from webui_pages.utils import *
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder
from configs.server_config import API_SERVER
import pandas as pd
from server.knowledge_base.utils import get_file_path, LOADER_DICT
from server.knowledge_base.kb_service.base import get_kb_details, get_kb_file_details
from typing import Literal, Dict, Tuple
from configs import (kbs_config, KB_ROOT_PATH,
                     EMBEDDING_MODEL, DEFAULT_VS_TYPE,
                     CHUNK_SIZE, OVERLAP_SIZE, ZH_TITLE_ENHANCE)
from server.utils import list_embed_models, list_online_embed_models
import os
import time

# SENTENCE_SIZE = 100

cell_renderer = JsCode("""function(params) {if(params.value==true){return '✓'}else{return '×'}}""")


def config_aggrid(
        df: pd.DataFrame,
        columns: Dict[Tuple[str, str], Dict] = {},
        selection_mode: Literal["single", "multiple", "disabled"] = "single",
        use_checkbox: bool = False,
) -> GridOptionsBuilder:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("No", width=40)
    for (col, header), kw in columns.items():
        gb.configure_column(col, header, wrapHeaderText=True, **kw)
    gb.configure_selection(
        selection_mode=selection_mode,
        use_checkbox=use_checkbox,
        # pre_selected_rows=st.session_state.get("selected_rows", [0]),
    )
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=10
    )
    return gb


def file_exists(kb: str, selected_rows: List) -> Tuple[str, str]:
    """
    check whether a doc file exists in local knowledge base folder.
    return the file's name and path if it exists.
    """
    if selected_rows:
        file_name = selected_rows[0]["file_name"]
        file_path = get_file_path(kb, file_name)
        if os.path.isfile(file_path):
            return file_name, file_path
    return "", ""


def knowledge_base_page(api: ApiRequest, is_lite: bool = None):
    try:
        kb_list = {x["kb_name"]: x for x in get_kb_details()}
    except Exception as e:
        st.error(
            "获取知识库信息错误，请检查是否已按照 `README.md` 中 `4 知识库初始化与迁移` 步骤完成初始化或迁移，或是否为数据库连接错误。")
        st.stop()
    kb_names = list(kb_list.keys())
    
    if "selected_kb_name" in st.session_state and st.session_state["selected_kb_name"] in kb_names:
        selected_kb_index = kb_names.index(st.session_state["selected_kb_name"])
    else:
        selected_kb_index = 0
    
    if "selected_kb_info" not in st.session_state:
        st.session_state["selected_kb_info"] = ""
    
    def format_selected_kb(kb_name: str) -> str:
        if kb := kb_list.get(kb_name):
            return f"{kb_name} ({kb['vs_type']} @ {kb['embed_model']})"
        else:
            return kb_name
    
    selected_kb = st.selectbox(
        "请选择或新建知识库：",
        kb_names + ["新建知识库"],
        format_func=format_selected_kb,
        index=selected_kb_index
    )
    
    if selected_kb == "新建知识库":
        with st.form("新建知识库"):
            
            kb_name = st.text_input(
                "新建知识库名称",
                placeholder="新知识库名称，不支持中文命名",
                key="kb_name",
            )
            kb_info = st.text_input(
                "知识库简介",
                placeholder="知识库简介，方便Agent查找",
                key="kb_info",
            )
            
            cols = st.columns(2)
            
            vs_types = list(kbs_config.keys())
            vs_type = cols[0].selectbox(
                "向量库类型",
                vs_types,
                index=vs_types.index(DEFAULT_VS_TYPE),
                key="vs_type",
            )
            
            if is_lite:
                embed_models = list_online_embed_models()
            else:
                embed_models = list_embed_models() + list_online_embed_models()
            
            embed_model = cols[1].selectbox(
                "Embedding 模型",
                embed_models,
                index=embed_models.index(EMBEDDING_MODEL),
                key="embed_model",
            )
            
            submit_create_kb = st.form_submit_button(
                "新建",
                # disabled=not bool(kb_name),
                use_container_width=True,
            )
        
        if submit_create_kb:
            if not kb_name or not kb_name.strip():
                st.error(f"知识库名称不能为空！")
            elif kb_name in kb_list:
                st.error(f"名为 {kb_name} 的知识库已经存在！")
            else:
                ret = api.create_knowledge_base(
                    knowledge_base_name=kb_name,
                    vector_store_type=vs_type,
                    embed_model=embed_model,
                )
                st.toast(ret.get("msg", " "))
                st.session_state["selected_kb_name"] = kb_name
                st.session_state["selected_kb_info"] = kb_info
                st.rerun()
    
    elif selected_kb:
        kb = selected_kb
        st.session_state["selected_kb_info"] = kb_list[kb]['kb_info']
        # 上传文件
        files = st.file_uploader("上传知识文件：",
                                 [i for ls in LOADER_DICT.values() for i in ls],
                                 accept_multiple_files=True,
                                 )
        kb_info = st.text_area("请输入知识库介绍:", value=st.session_state["selected_kb_info"], max_chars=None,
                               key=None,
                               help=None, on_change=None, args=None, kwargs=None)
        
        if kb_info != st.session_state["selected_kb_info"]:
            st.session_state["selected_kb_info"] = kb_info
            api.update_kb_info(kb, kb_info)
        
        with ((st.expander(
                "知识库网站",
                expanded=True,
        ))):
            kb_sites_key = f"kb_sites_{kb}"
            selected_kb_folder_name_key = f"selected_kb_folder_name_key_{kb}"
            
            if kb_sites_key not in st.session_state:
                st.session_state[kb_sites_key] = api.list_sites(kb)
            
            kb_sites = st.session_state.get(kb_sites_key, [])
            
            kb_folder_names = [site.get('folder_name') for site in kb_sites]
            kb_sites_dict = {site["folder_name"]: site for site in kb_sites}
            
            # cache data
            if selected_kb_folder_name_key in st.session_state and st.session_state[selected_kb_folder_name_key] in kb_folder_names:
                selected_kb_site_index = kb_folder_names.index(st.session_state[selected_kb_folder_name_key])
            else:
                selected_kb_site_index = 0
            
            def format_selected_kb_site(kb_folder_name: str) -> str:
                if kb_site := kb_sites_dict.get(kb_folder_name):
                    return f"{kb_site['site_name']} @ ( ID:{kb_site['id']} - 目录: {kb_site['folder_name']}) "
                else:
                    return kb_folder_name
            
            selected_kb_site = st.selectbox(
                "请选择或新建站点目录：",
                kb_folder_names + ["新建站点"],
                format_func=format_selected_kb_site,
                index=selected_kb_site_index
            )
            
            cur_kb_site_dict = kb_sites_dict.get(selected_kb_site, {})
            
            site_folder = st.text_input(
                '目录',
                placeholder="html存放目录",
                key="folder_name",
                value=cur_kb_site_dict.get("folder_name", ""),
                disabled=selected_kb_site != "新建站点",
            )
            
            site_cols_1 = st.columns(2)
            site_name = site_cols_1[0].text_input(
                '网站名',
                placeholder="知识网站名名称",
                key="site_name",
                value=cur_kb_site_dict.get("site_name", ""),
            )
            
            site_pattern = site_cols_1[1].text_input(
                '正则',
                placeholder="匹配链接的正则",
                key="pattern",
                value=cur_kb_site_dict.get("pattern", ""),
            )
            
            site_cols_2 = st.columns(2)
            site_hostname = site_cols_2[0].text_input(
                '域名信息',
                placeholder="https://xxx.com",
                key="hostname",
                value=cur_kb_site_dict.get("hostname", ""),
            )
            site_max_urls = site_cols_2[1].number_input(
                '最大链接数',
                min_value=1,
                max_value=500,
                key="max_urls",
                value=cur_kb_site_dict.get("max_urls", 1),
            )
            
            site_start_urls = st_tags(
                label='起始网址：',
                text="回车键添加多个",
                value=cur_kb_site_dict.get("start_urls", []),
                maxtags=10,
            )
            
            remove_selectors = st_tags(
                label='移除元素的选择器：',
                text="回车键添加多个",
                value=cur_kb_site_dict.get("remove_selectors", []),
                maxtags=10,
            )
            
            # st.write('result', remove_selectors)
            kb_sites_urls_key = f"kb_sites_urls_{kb}_{cur_kb_site_dict.get('id')}"
            
            site_cols_btns = st.columns(3)
            
            if site_cols_btns[0].button(
                    "创建站点" if selected_kb_site == "新建站点" else "更新站点",
                    disabled=not (site_pattern and site_name and site_folder
                                  and site_start_urls and site_max_urls and remove_selectors),
                    use_container_width=True,
            ):
                if selected_kb_site == "新建站点" and not cur_kb_site_dict.get("id"):
                    
                    api.create_kb_site(
                        hostname=site_hostname,
                        site_name=site_name.strip(),
                        folder_name=site_folder.strip(),
                        pattern=site_pattern,
                        knowledge_base_name=kb,
                        start_urls=site_start_urls,
                        remove_selectors=remove_selectors,
                        max_urls=site_max_urls,
                    )
                    st.toast(f"站点{site_name}创建成功", icon='😍')
                    st.session_state[selected_kb_folder_name_key] = site_folder.strip()
                    
                elif cur_kb_site_dict.get("id"):
                    
                    # 更新站点
                    api.update_kb_site(
                        site_id=cur_kb_site_dict.get("id"),
                        hostname=site_hostname,
                        site_name=site_name.strip(),
                        pattern=site_pattern,
                        knowledge_base_name=kb,
                        start_urls=site_start_urls,
                        remove_selectors=remove_selectors,
                        max_urls=site_max_urls,
                    )
                    st.toast(f"站点{site_name}更新成功", icon='😍')
                    st.session_state[selected_kb_folder_name_key] = cur_kb_site_dict.get("folder_name")
                
                time.sleep(2)
                # 更新数据
                st.session_state[kb_sites_key] = api.list_sites(kb)
                
                time.sleep(1)
                st.rerun()
                
            
            def extract_site_urls_then_download(
                    filter_method: str = "all",
            ):
                extract_data = api.extract_site_urls(hostname=site_hostname,
                                                     pattern=site_pattern,
                                                     start_urls=site_start_urls,
                                                     max_urls=site_max_urls)
                
                links = extract_data.get("links", [])
                
                with st.spinner("抓取数据中...请勿关闭页面或刷新"):
                    empty = st.empty()
                    empty.progress(0.0, "")
                    for d in api.crawl_site_urls(kb, cur_kb_site_dict.get("id"), links, filter_method):
                        if msg := check_error_msg(d):
                            st.toast(msg)
                        else:
                            empty.progress(d["finished"] / d["total"], d["msg"])
                
            
            
            if site_cols_btns[1].button(
                    "解析&全量下载(已存在重新下载)",
                    type="secondary",
                    disabled=not (
                            site_max_urls and len(site_start_urls) and site_pattern and cur_kb_site_dict.get("id")),
                    use_container_width=True,
            ):
                extract_site_urls_then_download()
                del st.session_state[kb_sites_urls_key]
                st.rerun()
            
            if site_cols_btns[2].button(
                    "解析&增量下载(已存在跳过)",
                    type="primary",
                    disabled=not (
                            site_max_urls and len(site_start_urls) and site_pattern and cur_kb_site_dict.get("id")),
                    use_container_width=True,
            ):
                extract_site_urls_then_download("new")
                del st.session_state[kb_sites_urls_key]
                st.rerun()
           
            if kb_sites_urls_key not in st.session_state:
                local_urls = api.list_local_site_urls(kb, cur_kb_site_dict.get('folder_name'))
                st.session_state[kb_sites_urls_key] = local_urls
            
            link_df = pd.DataFrame([
                {"url": item['url'],
                 "preview": f"{api.base_url}/knowledge_base/download_doc?" +
                            f"knowledge_base_name={kb}&file_name={quote(item['preview_file'], 'utf-8')}&preview=true"}
                for item in st.session_state.get(kb_sites_urls_key, [])
            ])
            
            st.dataframe(link_df,
                         use_container_width=True,
                         column_config={
                             "url": st.column_config.LinkColumn(
                                 "原地址",
                                 width="medium",
                                 required=True,
                             ),
                             "preview": st.column_config.LinkColumn(
                                 "预览",
                                 width="medium",
                                 required=True,
                             ),
                         })
        
        # with st.sidebar:
        with st.expander(
                "文件处理配置",
                expanded=True,
        ):
            cols = st.columns(3)
            chunk_size = cols[0].number_input("单段文本最大长度：", 1, 1000, CHUNK_SIZE)
            chunk_overlap = cols[1].number_input("相邻文本重合长度：", 0, chunk_size, OVERLAP_SIZE)
            cols[2].write("")
            cols[2].write("")
            zh_title_enhance = cols[2].checkbox("开启中文标题加强", ZH_TITLE_ENHANCE)
        
        if st.button(
                "添加文件到知识库",
                # use_container_width=True,
                disabled=len(files) == 0,
        ):
            ret = api.upload_kb_docs(files,
                                     knowledge_base_name=kb,
                                     override=True,
                                     chunk_size=chunk_size,
                                     chunk_overlap=chunk_overlap,
                                     zh_title_enhance=zh_title_enhance)
            if msg := check_success_msg(ret):
                st.toast(msg, icon="✔")
            elif msg := check_error_msg(ret):
                st.toast(msg, icon="✖")
        
        st.divider()
        
        # 知识库详情
        # st.info("请选择文件，点击按钮进行操作。")
        doc_details = pd.DataFrame(get_kb_file_details(kb))
        if not len(doc_details):
            st.info(f"知识库 `{kb}` 中暂无文件")
        else:
            st.write(f"知识库 `{kb}` 中已有文件:")
            st.info("知识库中包含源文件与向量库，请从下表中选择文件后操作")
            doc_details.drop(columns=["kb_name"], inplace=True)
            doc_details = doc_details[[
                "No", "file_name", "document_loader", "text_splitter", "docs_count", "in_folder", "in_db",
            ]]
            # doc_details["in_folder"] = doc_details["in_folder"].replace(True, "✓").replace(False, "×")
            # doc_details["in_db"] = doc_details["in_db"].replace(True, "✓").replace(False, "×")
            kb_content_path = KB_ROOT_PATH + '/' + kb + '/content/'
            len_ignore_prefix = len(kb_content_path)
            gb = config_aggrid(
                doc_details,
                {
                    ("No", "序号"): {},
                    ("file_name", "文档名称"): {
                        "cellRenderer": JsCode(f"""function(params) {{
                                return params.value.substring({len_ignore_prefix})}}"""),
                    },
                    # ("file_ext", "文档类型"): {},
                    # ("file_version", "文档版本"): {},
                    ("document_loader", "文档加载器"): {},
                    ("docs_count", "文档数量"): {},
                    ("text_splitter", "分词器"): {},
                    # ("create_time", "创建时间"): {},
                    ("in_folder", "源文件"): {"cellRenderer": cell_renderer},
                    ("in_db", "向量库"): {"cellRenderer": cell_renderer},
                },
                "multiple",
            )
            
            doc_grid = AgGrid(
                doc_details,
                gb.build(),
                columns_auto_size_mode="FIT_CONTENTS",
                theme="alpine",
                custom_css={
                    "#gridToolBar": {"display": "none"},
                },
                allow_unsafe_jscode=True,
                enable_enterprise_modules=False
            )
            
            selected_rows = doc_grid.get("selected_rows", [])
            
            cols = st.columns(4)
            file_name, file_path = file_exists(kb, selected_rows)
            if file_path:
                with open(file_path, "rb") as fp:
                    cols[0].download_button(
                        "下载选中文档",
                        fp,
                        file_name=file_name,
                        use_container_width=True, )
            else:
                cols[0].download_button(
                    "下载选中文档",
                    "",
                    disabled=True,
                    use_container_width=True, )
            
            st.write()
            # 将文件分词并加载到向量库中
            if cols[1].button(
                    "重新添加至向量库" if selected_rows and (
                            pd.DataFrame(selected_rows)["in_db"]).any() else "添加至向量库",
                    disabled=not file_exists(kb, selected_rows)[0],
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.update_kb_docs(kb,
                                   file_names=file_names,
                                   chunk_size=chunk_size,
                                   chunk_overlap=chunk_overlap,
                                   zh_title_enhance=zh_title_enhance)
                st.rerun()
            
            # 将文件从向量库中删除，但不删除文件本身。
            if cols[2].button(
                    "从向量库删除",
                    disabled=not (selected_rows and selected_rows[0]["in_db"]),
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.delete_kb_docs(kb, file_names=file_names)
                st.rerun()
            
            if cols[3].button(
                    "从知识库中删除",
                    type="primary",
                    use_container_width=True,
            ):
                file_names = [row["file_name"] for row in selected_rows]
                api.delete_kb_docs(kb, file_names=file_names, delete_content=True)
                st.rerun()
        
        st.divider()
        
        cols = st.columns(3)
        
        if cols[0].button(
                "依据源文件重建向量库",
                # help="无需上传文件，通过其它方式将文档拷贝到对应知识库content目录下，点击本按钮即可重建知识库。",
                use_container_width=True,
                type="primary",
        ):
            with st.spinner("向量库重构中，请耐心等待，勿刷新或关闭页面。"):
                empty = st.empty()
                empty.progress(0.0, "")
                for d in api.recreate_vector_store(kb,
                                                   chunk_size=chunk_size,
                                                   chunk_overlap=chunk_overlap,
                                                   zh_title_enhance=zh_title_enhance):
                    if msg := check_error_msg(d):
                        st.toast(msg)
                    else:
                        empty.progress(d["finished"] / d["total"], d["msg"])
                st.rerun()
        
        if cols[2].button(
                "删除知识库",
                use_container_width=True,
        ):
            ret = api.delete_knowledge_base(kb)
            st.toast(ret.get("msg", " "))
            time.sleep(1)
            st.rerun()
