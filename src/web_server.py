"""
Web服务模块，提供RSS订阅链接
"""
import os
import logging
from typing import Dict, Optional
from flask import Flask, send_file, jsonify, request, Response
from werkzeug.serving import run_simple

from src.config_manager import ConfigManager
from src.data_manager import DataManager
from src.rss_processor import RSSProcessor
from src.scheduler_manager import SchedulerManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebServer:
    """Web服务类，提供RSS订阅链接"""
    
    def __init__(self, config_manager: ConfigManager, data_manager: DataManager, 
                rss_processor: RSSProcessor, scheduler_manager: SchedulerManager):
        """
        初始化Web服务器
        
        Args:
            config_manager: 配置管理器实例
            data_manager: 数据管理器实例
            rss_processor: RSS处理器实例
            scheduler_manager: 调度管理器实例
        """
        self.config_manager = config_manager
        self.data_manager = data_manager
        self.rss_processor = rss_processor
        self.scheduler_manager = scheduler_manager
        
        # 获取Web配置
        self.host = config_manager.get_config('web.host', '0.0.0.0')
        self.port = config_manager.get_config('web.port', 8000)
        
        # 获取数据目录
        self.data_dir = os.path.join(
            self.config_manager.get_config('global.data_dir', './data'),
            'rss'
        )
        
        # 创建Flask应用
        self.app = Flask(__name__)
        
        # 注册路由
        self._register_routes()
        
        # 服务器实例
        self.server = None
        
        logger.info("Web服务器初始化完成")
    
    def _register_routes(self) -> None:
        """注册路由"""
        # 首页
        @self.app.route('/')
        def index():
            groups = self.config_manager.get_all_groups()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>AI RSS Filter</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    h1 {
                        color: #333;
                    }
                    ul {
                        list-style-type: none;
                        padding: 0;
                    }
                    li {
                        margin: 10px 0;
                        padding: 10px;
                        background-color: #f5f5f5;
                        border-radius: 5px;
                    }
                    a {
                        color: #0066cc;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <h1>AI RSS Filter</h1>
                <p>可用的RSS订阅源:</p>
                <ul>
            """
            
            for group in groups:
                rss_url = f"/rss/{group}"
                html += f'<li><a href="{rss_url}">{group}</a></li>'
            
            html += """
                </ul>
            </body>
            </html>
            """
            
            return html
        
        # RSS订阅源
        @self.app.route('/rss/<group_name>')
        def get_rss(group_name):
            # 检查组是否存在
            group_config = self.config_manager.get_group_config(group_name)
            if not group_config:
                return jsonify({"error": f"RSS组 {group_name} 不存在"}), 404
            
            # 检查RSS文件是否存在
            rss_file = os.path.join(self.data_dir, f"{group_name}.xml")
            if not os.path.exists(rss_file):
                # 尝试生成RSS文件
                success, _ = self.rss_processor.process_group(group_name)
                
                if not success:
                    return jsonify({"error": f"生成RSS源失败: {group_name}"}), 500
            
            # 返回RSS文件
            return send_file(rss_file, mimetype='application/rss+xml')
        
        # 手动更新RSS
        @self.app.route('/update/<group_name>', methods=['POST'])
        def update_rss(group_name):
            # 检查组是否存在
            group_config = self.config_manager.get_group_config(group_name)
            if not group_config:
                return jsonify({"error": f"RSS组 {group_name} 不存在"}), 404
            
            # 处理RSS组
            success, rss_file = self.rss_processor.process_group(group_name)
            
            if success:
                return jsonify({"success": True, "message": f"更新RSS源成功: {group_name}", "file": rss_file})
            else:
                return jsonify({"success": False, "message": f"更新RSS源失败: {group_name}"}), 500
        
        # 获取组信息
        @self.app.route('/groups')
        def get_groups():
            groups = self.config_manager.get_all_groups()
            
            result = {}
            for group in groups:
                group_config = self.config_manager.get_group_config(group)
                entry_count = self.data_manager.get_entry_count(group)
                filtered_count = self.data_manager.get_entry_count(group, filtered_only=True)
                
                result[group] = {
                    "config": group_config,
                    "entry_count": entry_count,
                    "filtered_count": filtered_count
                }
            
            return jsonify(result)
        
        # 健康检查
        @self.app.route('/health')
        def health_check():
            return jsonify({"status": "ok"})
    
    def start(self) -> None:
        """启动服务器"""
        logger.info(f"启动Web服务器: {self.host}:{self.port}")
        
        # 使用线程启动服务器
        import threading
        self.server_thread = threading.Thread(
            target=run_simple,
            args=(self.host, self.port, self.app),
            kwargs={'threaded': True},
            daemon=True
        )
        self.server_thread.start()
    
    def stop(self) -> None:
        """停止服务器"""
        # Flask开发服务器没有优雅的停止方法
        # 在生产环境中，应该使用更健壮的WSGI服务器
        logger.info("停止Web服务器")
    
    def get_rss_url(self, group_name: str) -> str:
        """
        获取RSS URL
        
        Args:
            group_name: RSS组名称
        
        Returns:
            RSS URL
        """
        base_url = f"http://{self.host}:{self.port}"
        return self.rss_processor.get_rss_url(group_name, base_url)
