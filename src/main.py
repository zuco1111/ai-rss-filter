"""
主程序入口
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_manager import ConfigManager
from src.data_manager import DataManager
from src.cache_manager import CacheManager
from src.llm_integrator import LLMIntegrator
from src.filter_manager import FilterManager
from src.rss_processor import RSSProcessor
from src.scheduler_manager import SchedulerManager
from src.web_server import WebServer

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIRSSFilter:
    """AI RSS Filter主类"""
    
    def __init__(self, config_path=None):
        """
        初始化AI RSS Filter
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        # 初始化配置管理器
        self.config_manager = ConfigManager(config_path)
        
        # 初始化数据管理器
        self.data_manager = DataManager(self.config_manager)
        
        # 初始化缓存管理器
        self.cache_manager = CacheManager(self.config_manager)
        
        # 初始化LLM集成器
        self.llm_integrator = LLMIntegrator(self.config_manager, self.cache_manager)
        
        # 初始化过滤器管理器
        self.filter_manager = FilterManager(self.config_manager, self.llm_integrator, self.cache_manager)
        
        # 初始化RSS处理器
        self.rss_processor = RSSProcessor(self.config_manager, self.cache_manager, self.data_manager, self.filter_manager)
        
        # 初始化调度管理器
        self.scheduler_manager = SchedulerManager(self.config_manager, self.rss_processor, self.data_manager)
        
        # 初始化Web服务器
        self.web_server = WebServer(self.config_manager, self.data_manager, self.rss_processor, self.scheduler_manager)
        
        logger.info("AI RSS Filter初始化完成")
    
    def start(self):
        """启动AI RSS Filter"""
        # 启动调度器
        self.scheduler_manager.start()
        
        # 启动Web服务器
        self.web_server.start()
        
        logger.info("AI RSS Filter已启动")
    
    def stop(self):
        """停止AI RSS Filter"""
        # 停止Web服务器
        self.web_server.stop()
        
        # 停止调度器
        self.scheduler_manager.stop()
        
        logger.info("AI RSS Filter已停止")

def main():
    """主函数"""
    # 获取配置文件路径
    config_path = os.environ.get('AI_RSS_FILTER_CONFIG')
    
    # 创建AI RSS Filter实例
    app = AIRSSFilter(config_path)
    
    # 启动服务
    app.start()
    
    # 保持主线程运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止服务...")
        app.stop()

if __name__ == "__main__":
    main()
