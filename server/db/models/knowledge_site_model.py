from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, JSON, func

from server.db.base import Base


class KnowledgeSiteModel(Base):
    """
    知识网站模型
    """
    __tablename__ = 'knowledge_site'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='网站ID')
    site_name = Column(String(255), comment='网站名')
    folder_name = Column(String(255), comment='目录')
    hostname = Column(String(255), comment='域名信息')
    start_urls = Column(JSON, default=[], comment='起始网站的地址')
    pattern = Column(String(255), comment='正则')
    remove_selectors = Column(JSON, default=[], comment='需要移除的选择器')
    max_urls = Column(Integer, default=1, comment='最大数量')
    kb_name = Column(String(50), comment='所属知识库名称')
    site_version = Column(Integer, default=1, comment='文件版本')
    site_mtime = Column(Float, default=0.0, comment="修改时间")
    create_time = Column(DateTime, default=func.now(), comment='创建时间')

    def __repr__(self):
        return (f"<KnowledgeSite(id='{self.id}', site_name='{self.site_name}',"
                f" start_urls='{self.start_urls}', pattern='{self.pattern}', "
                f"max_urls='{self.max_urls}', "
                f"kb_name='{self.kb_name}', remove_selectors='{self.remove_selectors}', "
                f"site_version='{self.site_version}', create_time='{self.create_time}')>")
