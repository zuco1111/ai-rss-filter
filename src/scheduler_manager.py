"""
调度模块，管理处理频率和定时任务
"""
import logging
import threading
from typing import Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config_manager import ConfigManager
from src.data_manager import DataManager
from src.rss_processor import RSSProcessor

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SchedulerManager:
    """调度管理类，管理处理频率和定时任务"""
    
    def __init__(self, config_manager: ConfigManager, rss_processor: RSSProcessor, data_manager: DataManager):
        """
        初始化调度管理器
        
        Args:
            config_manager: 配置管理器实例
            rss_processor: RSS处理器实例
            data_manager: 数据管理器实例
        """
        self.config_manager = config_manager
        self.rss_processor = rss_processor
        self.data_manager = data_manager
        
        # 创建调度器
        self.scheduler = BackgroundScheduler()
        
        # 任务映射
        self.jobs: Dict[str, str] = {}
        
        # 锁，防止并发问题
        self.lock = threading.Lock()
        
        logger.info("调度管理器初始化完成")
    
    def start(self) -> None:
        """启动调度器"""
        # 添加数据清理任务
        self._add_cleanup_job()
        
        # 添加RSS处理任务
        self._add_rss_jobs()
        
        # 启动调度器
        self.scheduler.start()
        
        logger.info("调度器已启动")
    
    def stop(self) -> None:
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("调度器已停止")
    
    def _add_cleanup_job(self) -> None:
        """添加数据清理任务"""
        # 每天执行一次数据清理
        self.scheduler.add_job(
            self.data_manager.delete_old_entries,
            trigger=IntervalTrigger(days=1),
            id='cleanup_job',
            replace_existing=True
        )
        
        logger.info("已添加数据清理任务")
    
    def _add_rss_jobs(self) -> None:
        """添加RSS处理任务"""
        # 获取所有RSS组
        groups = self.config_manager.get_all_groups()
        
        for group_name in groups:
            self.add_job(group_name)
    
    def add_job(self, group_name: str, interval: Optional[int] = None) -> bool:
        """
        添加任务
        
        Args:
            group_name: RSS组名称
            interval: 更新间隔（分钟），如果为None则使用配置中的值
        
        Returns:
            是否添加成功
        """
        with self.lock:
            # 获取组配置
            group_config = self.config_manager.get_group_config(group_name)
            if not group_config:
                logger.error(f"RSS组 {group_name} 不存在")
                return False
            
            # 获取更新间隔
            if interval is None:
                interval = group_config.get('interval', 60)
            
            # 确保间隔是正整数
            if not isinstance(interval, int) or interval <= 0:
                logger.warning(f"更新间隔必须是正整数，使用默认值60")
                interval = 60
            
            # 创建任务ID
            job_id = f"rss_job_{group_name}"
            
            # 如果任务已存在，则移除
            if job_id in self.jobs:
                self.remove_job(group_name)
            
            # 添加任务
            self.scheduler.add_job(
                self._process_group,
                args=[group_name],
                trigger=IntervalTrigger(minutes=interval),
                id=job_id,
                replace_existing=True
            )
            
            # 记录任务
            self.jobs[job_id] = group_name
            
            logger.info(f"已添加RSS处理任务: {group_name}，更新间隔: {interval}分钟")
            
            return True
    
    def remove_job(self, group_name: str) -> bool:
        """
        移除任务
        
        Args:
            group_name: RSS组名称
        
        Returns:
            是否移除成功
        """
        with self.lock:
            # 创建任务ID
            job_id = f"rss_job_{group_name}"
            
            # 如果任务不存在，则返回失败
            if job_id not in self.jobs:
                logger.warning(f"RSS处理任务不存在: {group_name}")
                return False
            
            # 移除任务
            self.scheduler.remove_job(job_id)
            
            # 移除记录
            del self.jobs[job_id]
            
            logger.info(f"已移除RSS处理任务: {group_name}")
            
            return True
    
    def update_job(self, group_name: str, interval: int) -> bool:
        """
        更新任务
        
        Args:
            group_name: RSS组名称
            interval: 更新间隔（分钟）
        
        Returns:
            是否更新成功
        """
        # 移除旧任务
        self.remove_job(group_name)
        
        # 添加新任务
        return self.add_job(group_name, interval)
    
    def _process_group(self, group_name: str) -> None:
        """
        处理RSS组
        
        Args:
            group_name: RSS组名称
        """
        logger.info(f"开始处理RSS组: {group_name}")
        
        try:
            success, rss_file = self.rss_processor.process_group(group_name)
            
            if success:
                logger.info(f"处理RSS组成功: {group_name}，生成文件: {rss_file}")
            else:
                logger.warning(f"处理RSS组失败: {group_name}")
        except Exception as e:
            logger.error(f"处理RSS组异常: {group_name}, {e}")
