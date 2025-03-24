"""
RSS处理模块，负责获取和解析RSS源
"""
import os
import uuid
import logging
import hashlib
import feedparser
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from feedgen.feed import FeedGenerator

from src.config_manager import ConfigManager
from src.cache_manager import CacheManager
from src.data_manager import DataManager
from src.filter_manager import FilterManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSProcessor:
    """RSS处理类，负责获取和解析RSS源"""
    
    def __init__(self, config_manager: ConfigManager, cache_manager: CacheManager, 
                data_manager: DataManager, filter_manager: FilterManager):
        """
        初始化RSS处理器
        
        Args:
            config_manager: 配置管理器实例
            cache_manager: 缓存管理器实例
            data_manager: 数据管理器实例
            filter_manager: 过滤器管理器实例
        """
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.data_manager = data_manager
        self.filter_manager = filter_manager
        
        # 获取数据目录
        self.data_dir = os.path.join(
            self.config_manager.get_config('global.data_dir', './data'),
            'rss'
        )
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info("RSS处理器初始化完成")
    
    def fetch_rss(self, rss_url: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        获取RSS源
        
        Args:
            rss_url: RSS源URL
        
        Returns:
            (是否成功, RSS源数据)
        """
        try:
            # 尝试从缓存获取
            cache_key = f"rss:fetch:{rss_url}"
            cached_feed = self.cache_manager.get(cache_key)
            
            if cached_feed is not None:
                logger.info(f"使用缓存的RSS源: {rss_url}")
                return True, cached_feed
            
            # 获取RSS源
            logger.info(f"开始获取RSS源: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            # 检查是否成功
            if feed.get('bozo_exception'):
                logger.error(f"获取RSS源失败: {feed.get('bozo_exception')}")
                return False, None
            
            # 缓存结果
            self.cache_manager.set(cache_key, feed, ttl=3600)  # 缓存1小时
            
            logger.info(f"获取RSS源成功: {rss_url}, 条目数: {len(feed.get('entries', []))}")
            
            return True, feed
        except Exception as e:
            logger.error(f"获取RSS源异常: {e}")
            return False, None
    
    def deduplicate_entries(self, entries: List[Dict[str, Any]], days: int = 3) -> List[Dict[str, Any]]:
        """
        去重文章
        
        Args:
            entries: RSS条目列表
            days: 发布时间相近的天数
        
        Returns:
            去重后的RSS条目列表
        """
        # 如果条目数量小于2，则无需去重
        if len(entries) < 2:
            logger.info("条目数量小于2，无需去重")
            return entries
        
        logger.info(f"开始去重，条目数: {len(entries)}, 时间范围: {days}天")
        
        # 按发布时间排序
        entries.sort(key=lambda x: x.get('published_parsed', datetime.now().timetuple()), reverse=True)
        
        # 去重
        unique_entries = []
        title_time_map = {}
        
        for entry in entries:
            title = entry.get('title', '')
            published_parsed = entry.get('published_parsed')
            
            if not title or not published_parsed:
                logger.info(f"条目缺少标题或发布时间，保留: {title}")
                unique_entries.append(entry)
                continue
            
            published_time = datetime(*published_parsed[:6])
            
            # 检查是否已存在相同标题的条目
            if title in title_time_map:
                existing_time = title_time_map[title]
                
                # 如果发布时间相差超过指定天数，则认为是不同的文章
                if abs((published_time - existing_time).days) > days:
                    logger.info(f"标题相同但发布时间相差超过{days}天，保留: {title}")
                    unique_entries.append(entry)
                    title_time_map[title] = published_time
                else:
                    logger.info(f"标题相同且发布时间相近，去重: {title}")
            else:
                logger.info(f"新标题，保留: {title}")
                unique_entries.append(entry)
                title_time_map[title] = published_time
        
        logger.info(f"去重完成，去重前: {len(entries)}, 去重后: {len(unique_entries)}")
        
        return unique_entries
    
    def generate_rss(self, entries: List[Dict[str, Any]], group_name: str) -> Tuple[bool, Optional[str]]:
        """
        生成新的RSS源
        
        Args:
            entries: RSS条目列表
            group_name: RSS组名称
        
        Returns:
            (是否成功, RSS源文件路径)
        """
        try:
            logger.info(f"开始生成RSS源: {group_name}, 条目数: {len(entries)}")
            
            # 创建Feed生成器
            fg = FeedGenerator()
            
            # 设置Feed信息
            fg.id(f"ai-rss-filter:{group_name}")
            fg.title(f"AI RSS Filter - {group_name}")
            fg.description(f"Filtered RSS feed for {group_name}")
            fg.link(href=f"http://localhost:8000/rss/{group_name}", rel='self')
            fg.language('zh-cn')
            
            # 添加安全随机字符串
            random_suffix = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
            fg.id(f"ai-rss-filter:{group_name}:{random_suffix}")
            
            # 添加条目
            for entry in entries:
                fe = fg.add_entry()
                
                # 设置条目ID
                entry_id = entry.get('id', '')
                if not entry_id:
                    entry_id = hashlib.md5(entry.get('title', '').encode()).hexdigest()
                fe.id(entry_id)
                
                # 设置标题
                fe.title(entry.get('title', ''))
                
                # 设置链接
                link = entry.get('link', '')
                if link:
                    fe.link(href=link)
                
                # 设置发布时间
                published = entry.get('published', '')
                if published:
                    fe.published(published)
                
                # 设置更新时间
                updated = entry.get('updated', '')
                if updated:
                    fe.updated(updated)
                
                # 设置作者
                author = entry.get('author', '')
                if author:
                    fe.author(name=author)
                
                # 设置内容
                content = entry.get('content', '')
                if isinstance(content, dict):
                    content = content.get('value', '')
                elif isinstance(content, list) and len(content) > 0:
                    content = content[0].get('value', '')
                
                # 如果有摘要，则使用摘要
                summary = entry.get('summary', '')
                if summary:
                    logger.info(f"条目有摘要: {entry.get('title', '')}, 摘要长度: {len(summary)}")
                    fe.summary(summary)
                
                # 设置内容
                if content:
                    fe.content(content, type='html')
            
            # 生成RSS文件
            rss_file = os.path.join(self.data_dir, f"{group_name}.xml")
            fg.rss_file(rss_file)
            
            logger.info(f"生成RSS源成功: {group_name}, 文件路径: {rss_file}")
            
            return True, rss_file
        except Exception as e:
            logger.error(f"生成RSS源异常: {e}")
            return False, None
    
    def process_group(self, group_name: str) -> Tuple[bool, Optional[str]]:
        """
        处理特定RSS组
        
        Args:
            group_name: RSS组名称
        
        Returns:
            (是否成功, RSS源文件路径)
        """
        logger.info(f"开始处理RSS组: {group_name}")
        
        # 获取组配置
        group_config = self.config_manager.get_group_config(group_name)
        if not group_config:
            logger.error(f"RSS组 {group_name} 不存在")
            return False, None
        
        # 获取RSS源URL列表
        rss_urls = group_config.get('urls', [])
        if not rss_urls:
            logger.error(f"RSS组 {group_name} 没有配置URL")
            return False, None
        
        # 获取去重配置
        dedup_enabled = group_config.get('deduplication', {}).get('enabled', True)
        dedup_days = group_config.get('deduplication', {}).get('days', 3)
        
        logger.info(f"RSS组配置: {group_name}, URLs: {rss_urls}, 去重: {dedup_enabled}, 去重天数: {dedup_days}")
        
        # 获取最后更新时间
        last_update = self.data_manager.get_last_update_time(group_name)
        if last_update:
            logger.info(f"RSS组 {group_name} 最后更新时间: {last_update}")
        
        # 获取所有RSS源
        all_entries = []
        
        for rss_url in rss_urls:
            success, feed = self.fetch_rss(rss_url)
            
            if not success or not feed:
                logger.warning(f"获取RSS源 {rss_url} 失败，跳过")
                continue
            
            # 提取条目
            entries = feed.get('entries', [])
            logger.info(f"获取到条目数: {len(entries)}, URL: {rss_url}")
            
            # 如果有最后更新时间，则只处理新条目
            if last_update:
                new_entries = []
                
                for entry in entries:
                    published_parsed = entry.get('published_parsed')
                    
                    if published_parsed:
                        published_time = datetime(*published_parsed[:6])
                        
                        # 如果发布时间晚于最后更新时间，则认为是新条目
                        if published_time > last_update:
                            logger.info(f"新条目: {entry.get('title', '')}, 发布时间: {published_time}")
                            new_entries.append(entry)
                        else:
                            logger.info(f"旧条目，跳过: {entry.get('title', '')}, 发布时间: {published_time}")
                    else:
                        # 如果没有发布时间，则默认保留
                        logger.info(f"条目没有发布时间，默认保留: {entry.get('title', '')}")
                        new_entries.append(entry)
                
                logger.info(f"增量更新，新条目数: {len(new_entries)}, URL: {rss_url}")
                entries = new_entries
            
            all_entries.extend(entries)
        
        # 如果没有条目，则返回失败
        if not all_entries:
            logger.warning(f"RSS组 {group_name} 没有新条目")
            return False, None
        
        logger.info(f"总条目数: {len(all_entries)}")
        
        # 去重
        if dedup_enabled:
            all_entries = self.deduplicate_entries(all_entries, dedup_days)
        
        # 过滤和生成摘要
        processed_entries = self.filter_manager.batch_process_entries(all_entries, group_name)
        
        # 如果没有处理后的条目，则返回失败
        if not processed_entries:
            logger.warning(f"RSS组 {group_name} 没有符合条件的条目")
            return False, None
        
        logger.info(f"处理后的条目数: {len(processed_entries)}")
        
        # 保存条目到数据库
        for entry in processed_entries:
            self.data_manager.save_entry(entry, group_name)
        
        # 更新最后更新时间
        self.data_manager.update_last_update_time(group_name)
        
        # 生成RSS源
        success, rss_file = self.generate_rss(processed_entries, group_name)
        
        if success:
            logger.info(f"处理RSS组成功: {group_name}, 生成文件: {rss_file}")
        else:
            logger.error(f"处理RSS组失败: {group_name}")
        
        return success, rss_file
    
    def get_rss_url(self, group_name: str, base_url: str) -> str:
        """
        获取RSS URL
        
        Args:
            group_name: RSS组名称
            base_url: 基础URL
        
        Returns:
            RSS URL
        """
        return f"{base_url}/rss/{group_name}"
