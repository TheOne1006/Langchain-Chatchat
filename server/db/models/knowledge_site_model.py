from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, func

from server.db.base import Base


class KnowledgeSiteModel(Base):
    """
    知识网站模型
    """
    __tablename__ = 'knowledge_site'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='网站ID')
    site_name = Column(String(255), comment='网站名')
    start_url = Column(String(255), comment='起始网站的地址')
    rule = Column(JSON, default={}, comment='抓取规则')
    site_urls = Column(JSON, default=[], comment='需要抓取的连接')
    kb_name = Column(String(50), comment='所属知识库名称')
    document_loader_name = Column(String(50), comment='文档加载器名称')
    text_splitter_name = Column(String(50), comment='文本分割器名称')
    site_version = Column(Integer, default=1, comment='文件版本')
    site_mtime = Column(Float, default=0.0, comment="文件修改时间")
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (f"<KnowledgeSite(id='{self.id}', site_name='{self.site_name}',"
                f" start_url='{self.start_url}', kb_name='{self.kb_name}', "
                f" rule='{self.rule}', site_urls='{self.site_urls}',"
                f"document_loader_name='{self.document_loader_name}', "
                f"text_splitter_name='{self.text_splitter_name}', "
                f"site_version='{self.site_version}', create_time='{self.create_time}')>")


class KnowledgeSitEndPointModel(Base):
    """
    知识网站连接模型
    """
    __tablename__ = 'knowledge_site_end_point'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='site end point ID')
    site_id = Column(Integer, comment='网站id')
    url = Column(String(255), comment='采集地址')
    kb_name = Column(String(50), comment='所属知识库名称')
    document_loader_name = Column(String(50), comment='文档加载器名称')
    text_splitter_name = Column(String(50), comment='文本分割器名称')
    link_version = Column(Integer, default=1, comment='文件版本')
    link_mtime = Column(Float, default=0.0, comment="文件修改时间")
    link_size = Column(Integer, default=0, comment="文件大小")
    custom_docs = Column(Boolean, default=False, comment="是否自定义docs")
    docs_count = Column(Integer, default=0, comment="切分文档数量")
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (f"<KnowledgeSiteEndPoint(id='{self.id}', site_id='{self.site_id}',"
                f" url='{self.url}', kb_name='{self.kb_name}', "
                f"document_loader_name='{self.document_loader_name}', "
                f"text_splitter_name='{self.text_splitter_name}', "
                f"link_version='{self.link_version}', create_time='{self.create_time}')>")
