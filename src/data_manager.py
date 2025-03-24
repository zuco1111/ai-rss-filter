"""
数据存储模块，负责管理数据的持久化存储
"""
import os
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.config_manager import ConfigManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataManager:
    """数据管理类，负责管理数据的持久化存储"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化数据管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.data_dir = Path(config_manager.get_config('global.data_dir', './data'))
        self.db_path = self.data_dir / 'rss_data.db'
        
        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        logger.info("数据管理器初始化完成")
    
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建条目表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                group_name TEXT NOT NULL,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                published TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                filtered INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(entry_id, group_name)
            )
            ''')
            
            # 创建元数据表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                last_update TEXT NOT NULL,
                UNIQUE(group_name)
            )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    def save_entry(self, entry: Dict[str, Any], group_name: str) -> bool:
        """
        保存RSS条目
        
        Args:
            entry: RSS条目数据
            group_name: RSS组名称
        
        Returns:
            是否保存成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # 准备数据
            entry_id = entry.get('id', '')
            title = entry.get('title', '')
            link = entry.get('link', '')
            published = entry.get('published', now)
            content = json.dumps(entry.get('content', ''))
            summary = entry.get('summary', '')
            filtered = 1 if entry.get('filtered', False) else 0
            
            # 检查条目是否已存在
            cursor.execute(
                'SELECT id FROM entries WHERE entry_id = ? AND group_name = ?',
                (entry_id, group_name)
            )
            result = cursor.fetchone()
            
            if result:
                # 更新现有条目
                cursor.execute('''
                UPDATE entries
                SET title = ?, link = ?, published = ?, content = ?, summary = ?, 
                    filtered = ?, updated_at = ?
                WHERE entry_id = ? AND group_name = ?
                ''', (title, link, published, content, summary, filtered, now, entry_id, group_name))
            else:
                # 插入新条目
                cursor.execute('''
                INSERT INTO entries 
                (entry_id, group_name, title, link, published, content, summary, 
                 filtered, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entry_id, group_name, title, link, published, content, summary, 
                      filtered, now, now))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"保存条目失败: {e}")
            return False
    
    def get_entries(self, group_name: str, limit: Optional[int] = None, 
                   filtered_only: bool = False) -> List[Dict[str, Any]]:
        """
        获取RSS条目
        
        Args:
            group_name: RSS组名称
            limit: 限制返回的条目数量
            filtered_only: 是否只返回已过滤的条目
        
        Returns:
            RSS条目列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM entries WHERE group_name = ?'
            params = [group_name]
            
            if filtered_only:
                query += ' AND filtered = 1'
            
            query += ' ORDER BY published DESC'
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            entries = []
            for row in rows:
                entry = dict(row)
                # 将JSON字符串转换回字典
                if entry['content']:
                    try:
                        entry['content'] = json.loads(entry['content'])
                    except:
                        entry['content'] = entry['content']
                
                entries.append(entry)
            
            conn.close()
            
            return entries
        except Exception as e:
            logger.error(f"获取条目失败: {e}")
            return []
    
    def get_entry_by_id(self, entry_id: str, group_name: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取RSS条目
        
        Args:
            entry_id: 条目ID
            group_name: RSS组名称
        
        Returns:
            RSS条目，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM entries WHERE entry_id = ? AND group_name = ?',
                (entry_id, group_name)
            )
            row = cursor.fetchone()
            
            if row:
                entry = dict(row)
                # 将JSON字符串转换回字典
                if entry['content']:
                    try:
                        entry['content'] = json.loads(entry['content'])
                    except:
                        entry['content'] = entry['content']
                
                conn.close()
                return entry
            
            conn.close()
            return None
        except Exception as e:
            logger.error(f"获取条目失败: {e}")
            return None
    
    def delete_old_entries(self, days: Optional[int] = None) -> bool:
        """
        删除旧条目
        
        Args:
            days: 保留的天数，如果为None则使用配置中的值
        
        Returns:
            是否删除成功
        """
        try:
            if days is None:
                days = self.config_manager.get_config('global.data_retention_days', 90)
            
            if not isinstance(days, int) or days <= 0:
                logger.warning(f"保留天数必须是正整数，使用默认值90")
                days = 90
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM entries WHERE created_at < ?',
                (cutoff_date,)
            )
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"已删除 {deleted_count} 条旧数据（超过 {days} 天）")
            
            return True
        except Exception as e:
            logger.error(f"删除旧条目失败: {e}")
            return False
    
    def update_last_update_time(self, group_name: str) -> bool:
        """
        更新最后更新时间
        
        Args:
            group_name: RSS组名称
        
        Returns:
            是否更新成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute(
                'SELECT id FROM metadata WHERE group_name = ?',
                (group_name,)
            )
            result = cursor.fetchone()
            
            if result:
                cursor.execute(
                    'UPDATE metadata SET last_update = ? WHERE group_name = ?',
                    (now, group_name)
                )
            else:
                cursor.execute(
                    'INSERT INTO metadata (group_name, last_update) VALUES (?, ?)',
                    (group_name, now)
                )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"更新最后更新时间失败: {e}")
            return False
    
    def get_last_update_time(self, group_name: str) -> Optional[datetime]:
        """
        获取最后更新时间
        
        Args:
            group_name: RSS组名称
        
        Returns:
            最后更新时间，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT last_update FROM metadata WHERE group_name = ?',
                (group_name,)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return datetime.fromisoformat(result[0])
            
            return None
        except Exception as e:
            logger.error(f"获取最后更新时间失败: {e}")
            return None
    
    def get_entry_count(self, group_name: str, filtered_only: bool = False) -> int:
        """
        获取条目数量
        
        Args:
            group_name: RSS组名称
            filtered_only: 是否只计算已过滤的条目
        
        Returns:
            条目数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = 'SELECT COUNT(*) FROM entries WHERE group_name = ?'
            params = [group_name]
            
            if filtered_only:
                query += ' AND filtered = 1'
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取条目数量失败: {e}")
            return 0
