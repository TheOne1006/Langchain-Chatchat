from server.db.models.knowledge_site_model import KnowledgeSiteModel
from server.db.session import with_session
from typing import List, Dict


def instance2json(site: KnowledgeSiteModel) -> dict:
    return {
        "id": site.id,
        "site_name": site.site_name,
        "folder_name": site.folder_name,
        "hostname": site.hostname,
        "start_urls": site.start_urls,
        "pattern": site.pattern,
        "remove_selectors": site.remove_selectors,
        "max_urls": site.max_urls,
        "kb_name": site.kb_name,
        "site_version": site.site_version,
        "site_mtime": site.site_mtime,
        "create_time": site.create_time,
    }


@with_session
def list_site_from_db(session, kb_name: str) -> List[Dict]:
    """
    返回形式：[{"id": str, "site_name": str, "doc_ids": str}, ...]
    """
    docs = session.query(KnowledgeSiteModel).filter_by(kb_name=kb_name)
    
    return [instance2json(x) for x in docs.all()]


# @with_session

@with_session
def get_site_detail(session,
                    kb_name: str,
                    site_name: str = None,
                    site_id: int = None,
                    folder_name: str = None,
                    ) -> dict:
    if not kb_name:
        raise ValueError("kb_name cannot be None.")
    
    if not site_name and not site_id and not folder_name:
        raise ValueError("site_name / site_id / folder_name cannot be None at the same time.")
    
    where = {
        "kb_name": kb_name,
    }
    
    if site_name:
        where["site_name"] = site_name
    if site_id:
        where["id"] = site_id
    if folder_name:
        where["folder_name"] = folder_name

    site: KnowledgeSiteModel = session.query(KnowledgeSiteModel).filter_by(**where).first()

    if site:
        return instance2json(site)
    else:
        return {}


@with_session
def add_site_to_db(session, kb_name: str, site_info: Dict):
    """
    将网站信息添加到数据库。
    site_info形式：[{"site_name": str, "kb_name": str}, ...]
    """
    
    obj = KnowledgeSiteModel(
        kb_name=kb_name,
        site_name=site_info['site_name'],
        folder_name=site_info['folder_name'],
        hostname=site_info['hostname'],
        start_urls=site_info['start_urls'],
        pattern=site_info['pattern'],
        remove_selectors=site_info['remove_selectors'],
        max_urls=site_info['max_urls'],

    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    
    return instance2json(obj)


@with_session
def update_site_to_db(session, kb_name: str, site_id: int, site_info: Dict):
    """
    更新网站信息到数据库。
    site_info形式：[{"site_name": str, "kb_name": str}, ...]
    """
    
    ins = session.query(KnowledgeSiteModel).filter_by(kb_name=kb_name, id=site_id).first()
    
    if not ins:
        raise ValueError(f"site_id={site_id} not found in kb_name={kb_name}")
    
    if site_info.get('id'):
        site_info.pop('id')
    if site_info.get('kb_name'):
        site_info.pop('kb_name')
    
    for k, v in site_info.items():
        setattr(ins, k, v)
    
    session.add(ins)
    session.commit()
    session.refresh(ins)
    
    return instance2json(ins)


@with_session
def delete_site_from_db(session,
                        kb_name: str,
                        site_id: int,
                        ) -> bool:
    """
    删除知识库 knowledge_site，并返回被删除的 Knowledge site。
    返回形式：[{"id": str, "site_name": str, "doc_ids": str}, ...]
    """
    query = session.query(KnowledgeSiteModel).filter_by(kb_name=kb_name, id=site_id)
    query.delete()
    session.commit()
    return True
