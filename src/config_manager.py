"""
配置管理模块，负责加载和管理所有配置项
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理类，负责加载和管理所有配置项"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None，则尝试从环境变量或默认位置加载
        """
        self.config: Dict[str, Any] = {}
        self.config_path = config_path
        
        # 加载配置
        self._load_config()
        
        # 设置默认值
        self._set_defaults()
        
        # 验证配置
        self._validate_config()
        
        logger.info("配置管理器初始化完成")
    
    def _load_config(self) -> None:
        """加载配置文件"""
        # 如果未指定配置文件路径，则尝试从环境变量获取
        if not self.config_path:
            self.config_path = os.environ.get('AI_RSS_FILTER_CONFIG', './config/config.yaml')
        
        config_path = Path(self.config_path)
        
        # 如果配置文件存在，则加载
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"从 {self.config_path} 加载配置成功")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self.config = {}
        else:
            logger.warning(f"配置文件 {self.config_path} 不存在，将使用默认配置")
            self.config = {}
    
    def _set_defaults(self) -> None:
        """设置默认配置值"""
        # 全局默认配置
        if 'global' not in self.config:
            self.config['global'] = {}
        
        global_defaults = {
            'data_dir': './data',
            'data_retention_days': 90,
            'cache': {
                'memory_enabled': True,
                'file_enabled': True,
                'db_enabled': True,
                'memory_ttl': 3600,  # 1小时
                'file_ttl': 86400,   # 1天
                'db_ttl': 604800     # 7天
            }
        }
        
        # 更新全局配置默认值
        for key, value in global_defaults.items():
            if key not in self.config['global']:
                self.config['global'][key] = value
            elif isinstance(value, dict) and isinstance(self.config['global'][key], dict):
                # 对于嵌套字典，递归更新默认值
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config['global'][key]:
                        self.config['global'][key][sub_key] = sub_value
        
        # LLM默认配置
        if 'llm' not in self.config:
            self.config['llm'] = {}
        
        llm_defaults = {
            'default_provider': 'openai',
            'openai': {
                'api_key': os.environ.get('OPENAI_API_KEY', ''),
                'base_url': 'https://api.openai.com/v1',
                'model': 'gpt-3.5-turbo'
            },
            'gemini': {
                'api_key': os.environ.get('GEMINI_API_KEY', ''),
                'base_url': 'https://generativelanguage.googleapis.com/v1',
                'model': 'gemini-pro'
            },
            'claude': {
                'api_key': os.environ.get('CLAUDE_API_KEY', ''),
                'base_url': 'https://api.anthropic.com/v1',
                'model': 'claude-2'
            },
            'ollama': {
                'base_url': 'http://localhost:11434/api',
                'model': 'llama2'
            },
            'deepseek': {
                'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
                'base_url': 'https://api.deepseek.com/v1',
                'model': 'deepseek-chat'
            },
            'azure': {
                'api_key': os.environ.get('AZURE_API_KEY', ''),
                'base_url': os.environ.get('AZURE_ENDPOINT', ''),
                'deployment_id': os.environ.get('AZURE_DEPLOYMENT_ID', ''),
                'api_version': '2023-05-15'
            }
        }
        
        # 更新LLM配置默认值
        for key, value in llm_defaults.items():
            if key not in self.config['llm']:
                self.config['llm'][key] = value
            elif isinstance(value, dict) and isinstance(self.config['llm'][key], dict):
                # 对于嵌套字典，递归更新默认值
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config['llm'][key]:
                        self.config['llm'][key][sub_key] = sub_value
        
        # Web服务默认配置
        if 'web' not in self.config:
            self.config['web'] = {}
        
        web_defaults = {
            'host': '0.0.0.0',
            'port': 8000
        }
        
        # 更新Web服务配置默认值
        for key, value in web_defaults.items():
            if key not in self.config['web']:
                self.config['web'][key] = value
        
        # RSS组默认配置
        if 'groups' not in self.config:
            self.config['groups'] = {
                'default': {
                    'urls': [],
                    'interval': 60,
                    'deduplication': {
                        'enabled': True,
                        'days': 3
                    },
                    'filter': {
                        'enabled': False,
                        'prompt': ''
                    },
                    'summary': {
                        'enabled': False,
                        'max_length': 150
                    }
                }
            }
        else:
            # 为每个组设置默认值
            for group_name, group_config in self.config['groups'].items():
                if 'urls' not in group_config:
                    group_config['urls'] = []
                
                if 'interval' not in group_config:
                    group_config['interval'] = 60
                
                if 'deduplication' not in group_config:
                    group_config['deduplication'] = {
                        'enabled': True,
                        'days': 3
                    }
                elif isinstance(group_config['deduplication'], dict):
                    if 'enabled' not in group_config['deduplication']:
                        group_config['deduplication']['enabled'] = True
                    if 'days' not in group_config['deduplication']:
                        group_config['deduplication']['days'] = 3
                
                if 'filter' not in group_config:
                    group_config['filter'] = {
                        'enabled': False,
                        'prompt': ''
                    }
                elif isinstance(group_config['filter'], dict):
                    if 'enabled' not in group_config['filter']:
                        group_config['filter']['enabled'] = False
                    if 'prompt' not in group_config['filter']:
                        group_config['filter']['prompt'] = ''
                
                if 'summary' not in group_config:
                    group_config['summary'] = {
                        'enabled': False,
                        'max_length': 150
                    }
                elif isinstance(group_config['summary'], dict):
                    if 'enabled' not in group_config['summary']:
                        group_config['summary']['enabled'] = False
                    if 'max_length' not in group_config['summary']:
                        group_config['summary']['max_length'] = 150
    
    def _validate_config(self) -> None:
        """验证配置是否有效"""
        # 验证全局配置
        if not isinstance(self.config.get('global', {}).get('data_retention_days', 0), int):
            logger.warning("data_retention_days 必须是整数，设置为默认值 90")
            self.config['global']['data_retention_days'] = 90
        
        # 验证LLM配置
        if self.config['llm']['default_provider'] not in self.config['llm']:
            logger.warning(f"默认LLM提供商 {self.config['llm']['default_provider']} 不存在，设置为 openai")
            self.config['llm']['default_provider'] = 'openai'
        
        # 验证RSS组配置
        for group_name, group_config in self.config['groups'].items():
            if not group_config.get('urls'):
                logger.warning(f"RSS组 {group_name} 没有配置URL")
            
            if not isinstance(group_config.get('interval', 0), int) or group_config.get('interval', 0) <= 0:
                logger.warning(f"RSS组 {group_name} 的更新间隔必须是正整数，设置为默认值 60")
                group_config['interval'] = 60
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置项键名，支持点号分隔的嵌套键
            default: 默认值，如果配置项不存在则返回此值
        
        Returns:
            配置项的值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_group_config(self, group_name: str) -> Dict[str, Any]:
        """
        获取特定RSS组的配置
        
        Args:
            group_name: RSS组名称
        
        Returns:
            RSS组的配置字典
        """
        groups = self.config.get('groups', {})
        return groups.get(group_name, {})
    
    def get_all_groups(self) -> List[str]:
        """
        获取所有RSS组的名称
        
        Returns:
            RSS组名称列表
        """
        return list(self.config.get('groups', {}).keys())
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            是否保存成功
        """
        try:
            config_path = Path(self.config_path)
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到 {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
