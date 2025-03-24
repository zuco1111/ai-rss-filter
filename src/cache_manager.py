"""
缓存模块，实现多级缓存策略
"""
import os
import json
import pickle
import logging
import sqlite3
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta

from src.config_manager import ConfigManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryCache:
    """内存缓存实现"""
    
    def __init__(self, ttl: int = 3600):
        """
        初始化内存缓存
        
        Args:
            ttl: 缓存生存时间（秒）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
        
        cache_item = self.cache[key]
        
        # 检查是否过期
        if datetime.now() > cache_item['expires_at']:
            del self.cache[key]
            return None
        
        return cache_item['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存生存时间（秒），如果为None则使用默认值
        
        Returns:
            是否设置成功
        """
        if ttl is None:
            ttl = self.ttl
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        
        return True
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        if key in self.cache:
            del self.cache[key]
            return True
        
        return False
    
    def clear(self) -> bool:
        """
        清除所有缓存
        
        Returns:
            是否清除成功
        """
        self.cache.clear()
        return True
    
    def cleanup(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        expired_keys = []
        now = datetime.now()
        
        for key, cache_item in self.cache.items():
            if now > cache_item['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)


class FileCache:
    """文件缓存实现"""
    
    def __init__(self, cache_dir: Union[str, Path], ttl: int = 86400):
        """
        初始化文件缓存
        
        Args:
            cache_dir: 缓存目录
            ttl: 缓存生存时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径
        
        Args:
            key: 缓存键
        
        Returns:
            缓存文件路径
        """
        # 使用MD5哈希作为文件名，避免文件名过长或包含非法字符
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            # 检查文件是否过期
            modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.now() - modified_time > timedelta(seconds=self.ttl):
                cache_path.unlink(missing_ok=True)
                return None
            
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"读取文件缓存失败: {e}")
            cache_path.unlink(missing_ok=True)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存生存时间（秒），如果为None则使用默认值
        
        Returns:
            是否设置成功
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            
            return True
        except Exception as e:
            logger.error(f"写入文件缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except Exception as e:
                logger.error(f"删除文件缓存失败: {e}")
                return False
        
        return False
    
    def clear(self) -> bool:
        """
        清除所有缓存
        
        Returns:
            是否清除成功
        """
        try:
            for cache_file in self.cache_dir.glob('*.cache'):
                cache_file.unlink()
            
            return True
        except Exception as e:
            logger.error(f"清除文件缓存失败: {e}")
            return False
    
    def cleanup(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        count = 0
        now = datetime.now()
        
        try:
            for cache_file in self.cache_dir.glob('*.cache'):
                modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if now - modified_time > timedelta(seconds=self.ttl):
                    cache_file.unlink()
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"清理过期文件缓存失败: {e}")
            return count


class DatabaseCache:
    """数据库缓存实现"""
    
    def __init__(self, db_path: Union[str, Path], ttl: int = 604800):
        """
        初始化数据库缓存
        
        Args:
            db_path: 数据库文件路径
            ttl: 缓存生存时间（秒）
        """
        self.db_path = Path(db_path)
        self.ttl = ttl
        
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建缓存表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"初始化数据库缓存失败: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT value, created_at FROM cache WHERE key = ?',
                (key,)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                return None
            
            value_blob, created_at_str = result
            created_at = datetime.fromisoformat(created_at_str)
            
            # 检查是否过期
            if datetime.now() - created_at > timedelta(seconds=self.ttl):
                self.delete(key)
                return None
            
            return pickle.loads(value_blob)
        except Exception as e:
            logger.error(f"获取数据库缓存失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存生存时间（秒），如果为None则使用默认值
        
        Returns:
            是否设置成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            value_blob = pickle.dumps(value)
            
            cursor.execute(
                'INSERT OR REPLACE INTO cache (key, value, created_at) VALUES (?, ?, ?)',
                (key, value_blob, now)
            )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"设置数据库缓存失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM cache WHERE key = ?',
                (key,)
            )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"删除数据库缓存失败: {e}")
            return False
    
    def clear(self) -> bool:
        """
        清除所有缓存
        
        Returns:
            是否清除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM cache')
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"清除数据库缓存失败: {e}")
            return False
    
    def cleanup(self) -> int:
        """
        清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(seconds=self.ttl)).isoformat()
            
            cursor.execute(
                'DELETE FROM cache WHERE created_at < ?',
                (cutoff_date,)
            )
            
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return deleted_count
        except Exception as e:
            logger.error(f"清理过期数据库缓存失败: {e}")
            return 0


class CacheManager:
    """缓存管理类，实现多级缓存策略"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化缓存管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.data_dir = Path(config_manager.get_config('global.data_dir', './data'))
        
        # 获取缓存配置
        cache_config = config_manager.get_config('global.cache', {})
        
        # 初始化各级缓存
        self.memory_enabled = cache_config.get('memory_enabled', True)
        self.file_enabled = cache_config.get('file_enabled', True)
        self.db_enabled = cache_config.get('db_enabled', True)
        
        self.memory_ttl = cache_config.get('memory_ttl', 3600)
        self.file_ttl = cache_config.get('file_ttl', 86400)
        self.db_ttl = cache_config.get('db_ttl', 604800)
        
        # 创建缓存实例
        if self.memory_enabled:
            self.memory_cache = MemoryCache(ttl=self.memory_ttl)
        else:
            self.memory_cache = None
        
        if self.file_enabled:
            cache_dir = self.data_dir / 'cache' / 'file'
            self.file_cache = FileCache(cache_dir=cache_dir, ttl=self.file_ttl)
        else:
            self.file_cache = None
        
        if self.db_enabled:
            db_path = self.data_dir / 'cache' / 'db_cache.db'
            self.db_cache = DatabaseCache(db_path=db_path, ttl=self.db_ttl)
        else:
            self.db_cache = None
        
        logger.info("缓存管理器初始化完成")
    
    def get(self, key: str, cache_type: Optional[str] = None) -> Optional[Any]:
        """
        获取缓存，按照内存缓存 -> 文件缓存 -> 数据库缓存的顺序查找
        
        Args:
            key: 缓存键
            cache_type: 缓存类型，可选值为'memory'、'file'、'db'，如果为None则按顺序查找
        
        Returns:
            缓存值，如果不存在则返回None
        """
        # 如果指定了缓存类型，则只查找指定类型的缓存
        if cache_type == 'memory':
            return self.memory_cache.get(key) if self.memory_cache else None
        elif cache_type == 'file':
            return self.file_cache.get(key) if self.file_cache else None
        elif cache_type == 'db':
            return self.db_cache.get(key) if self.db_cache else None
        
        # 按顺序查找各级缓存
        value = None
        
        # 先查找内存缓存
        if self.memory_cache:
            value = self.memory_cache.get(key)
            if value is not None:
                return value
        
        # 再查找文件缓存
        if self.file_cache:
            value = self.file_cache.get(key)
            if value is not None:
                # 如果在文件缓存中找到，则更新内存缓存
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                return value
        
        # 最后查找数据库缓存
        if self.db_cache:
            value = self.db_cache.get(key)
            if value is not None:
                # 如果在数据库缓存中找到，则更新内存缓存和文件缓存
                if self.memory_cache:
                    self.memory_cache.set(key, value)
                if self.file_cache:
                    self.file_cache.set(key, value)
                return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: Optional[str] = None) -> bool:
        """
        设置缓存，默认同时设置内存缓存、文件缓存和数据库缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 缓存生存时间（秒），如果为None则使用默认值
            cache_type: 缓存类型，可选值为'memory'、'file'、'db'，如果为None则设置所有启用的缓存
        
        Returns:
            是否设置成功
        """
        # 如果指定了缓存类型，则只设置指定类型的缓存
        if cache_type == 'memory':
            return self.memory_cache.set(key, value, ttl) if self.memory_cache else False
        elif cache_type == 'file':
            return self.file_cache.set(key, value, ttl) if self.file_cache else False
        elif cache_type == 'db':
            return self.db_cache.set(key, value, ttl) if self.db_cache else False
        
        # 设置所有启用的缓存
        success = True
        
        if self.memory_cache:
            memory_success = self.memory_cache.set(key, value, ttl)
            success = success and memory_success
        
        if self.file_cache:
            file_success = self.file_cache.set(key, value, ttl)
            success = success and file_success
        
        if self.db_cache:
            db_success = self.db_cache.set(key, value, ttl)
            success = success and db_success
        
        return success
    
    def delete(self, key: str, cache_type: Optional[str] = None) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            cache_type: 缓存类型，可选值为'memory'、'file'、'db'，如果为None则删除所有缓存
        
        Returns:
            是否删除成功
        """
        # 如果指定了缓存类型，则只删除指定类型的缓存
        if cache_type == 'memory':
            return self.memory_cache.delete(key) if self.memory_cache else False
        elif cache_type == 'file':
            return self.file_cache.delete(key) if self.file_cache else False
        elif cache_type == 'db':
            return self.db_cache.delete(key) if self.db_cache else False
        
        # 删除所有缓存
        success = True
        
        if self.memory_cache:
            memory_success = self.memory_cache.delete(key)
            success = success and memory_success
        
        if self.file_cache:
            file_success = self.file_cache.delete(key)
            success = success and file_success
        
        if self.db_cache:
            db_success = self.db_cache.delete(key)
            success = success and db_success
        
        return success
    
    def clear(self, cache_type: Optional[str] = None) -> bool:
        """
        清除缓存
        
        Args:
            cache_type: 缓存类型，可选值为'memory'、'file'、'db'，如果为None则清除所有缓存
        
        Returns:
            是否清除成功
        """
        # 如果指定了缓存类型，则只清除指定类型的缓存
        if cache_type == 'memory':
            return self.memory_cache.clear() if self.memory_cache else False
        elif cache_type == 'file':
            return self.file_cache.clear() if self.file_cache else False
        elif cache_type == 'db':
            return self.db_cache.clear() if self.db_cache else False
        
        # 清除所有缓存
        success = True
        
        if self.memory_cache:
            memory_success = self.memory_cache.clear()
            success = success and memory_success
        
        if self.file_cache:
            file_success = self.file_cache.clear()
            success = success and file_success
        
        if self.db_cache:
            db_success = self.db_cache.clear()
            success = success and db_success
        
        return success
    
    def cleanup(self, cache_type: Optional[str] = None) -> Dict[str, int]:
        """
        清理过期缓存
        
        Args:
            cache_type: 缓存类型，可选值为'memory'、'file'、'db'，如果为None则清理所有缓存
        
        Returns:
            各级缓存清理的数量
        """
        result = {
            'memory': 0,
            'file': 0,
            'db': 0
        }
        
        # 如果指定了缓存类型，则只清理指定类型的缓存
        if cache_type == 'memory':
            if self.memory_cache:
                result['memory'] = self.memory_cache.cleanup()
            return result
        elif cache_type == 'file':
            if self.file_cache:
                result['file'] = self.file_cache.cleanup()
            return result
        elif cache_type == 'db':
            if self.db_cache:
                result['db'] = self.db_cache.cleanup()
            return result
        
        # 清理所有缓存
        if self.memory_cache:
            result['memory'] = self.memory_cache.cleanup()
        
        if self.file_cache:
            result['file'] = self.file_cache.cleanup()
        
        if self.db_cache:
            result['db'] = self.db_cache.cleanup()
        
        return result
