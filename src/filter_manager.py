"""
过滤器模块，负责过滤和生成摘要
"""
import logging
import hashlib
from typing import Any, Dict, List, Optional
import time

from src.config_manager import ConfigManager
from src.llm_integrator import LLMIntegrator
from src.cache_manager import CacheManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FilterManager:
    """过滤器管理类，负责过滤和生成摘要"""
    
    def __init__(self, config_manager: ConfigManager, llm_integrator: LLMIntegrator, cache_manager: CacheManager):
        """
        初始化过滤器管理器
        
        Args:
            config_manager: 配置管理器实例
            llm_integrator: LLM集成器实例
            cache_manager: 缓存管理器实例
        """
        self.config_manager = config_manager
        self.llm_integrator = llm_integrator
        self.cache_manager = cache_manager
        
        logger.info("过滤器管理器初始化完成")
    
    def filter_entry(self, entry: Dict[str, Any], group_name: str) -> bool:
        """
        过滤条目
        
        Args:
            entry: RSS条目
            group_name: RSS组名称
        
        Returns:
            是否保留
        """
        # 获取组配置
        group_config = self.config_manager.get_group_config(group_name)
        if not group_config:
            logger.warning(f"RSS组 {group_name} 不存在，默认保留条目")
            return True
        
        # 获取过滤配置
        filter_config = group_config.get('filter', {})
        filter_enabled = filter_config.get('enabled', False)
        
        # 如果未启用过滤，则保留所有条目
        if not filter_enabled:
            logger.info(f"RSS组 {group_name} 未启用过滤，保留条目: {entry.get('title', '')}")
            return True
        
        # 获取过滤提示
        prompt = filter_config.get('prompt', '')
        if not prompt:
            logger.warning(f"RSS组 {group_name} 未配置过滤提示，默认保留条目: {entry.get('title', '')}")
            return True
        
        # 获取提供商
        provider = filter_config.get('provider')
        
        # 尝试从缓存获取结果
        cache_key = f"filter:{group_name}:{self._get_entry_hash(entry)}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            logger.info(f"使用缓存的过滤结果: {entry.get('title', '')}, 结果: {cached_result}")
            return cached_result
        
        # 构建过滤内容
        content = self._build_filter_content(entry)
        
        # 构建过滤提示
        filter_prompt = f"""
        请根据以下条件判断文章是否符合要求：
        
        {prompt}
        
        文章内容：
        标题：{entry.get('title', '')}
        链接：{entry.get('link', '')}
        内容：{content}
        
        请只回答"是"或"否"，表示是否保留该文章。
        """
        
        try:
            # 调用LLM进行过滤
            logger.info(f"开始过滤条目: {entry.get('title', '')}")
            start_time = time.time()
            response = self.llm_integrator.generate_text(filter_prompt, provider)
            end_time = time.time()
            logger.info(f"过滤条目完成，耗时: {end_time - start_time:.2f}秒")
            
            # 解析结果
            result = '是' in response.lower() or 'yes' in response.lower()
            
            # 缓存结果
            self.cache_manager.set(cache_key, result)
            
            logger.info(f"过滤结果: {entry.get('title', '')}, 结果: {result}, 响应: {response}")
            
            return result
        except Exception as e:
            logger.error(f"过滤条目异常: {e}")
            return True
    
    def generate_summary(self, entry: Dict[str, Any], group_name: str) -> Optional[str]:
        """
        生成摘要
        
        Args:
            entry: RSS条目
            group_name: RSS组名称
        
        Returns:
            摘要
        """
        # 获取组配置
        group_config = self.config_manager.get_group_config(group_name)
        if not group_config:
            logger.warning(f"RSS组 {group_name} 不存在，跳过摘要生成")
            return None
        
        # 获取摘要配置
        summary_config = group_config.get('summary', {})
        summary_enabled = summary_config.get('enabled', False)
        
        # 如果未启用摘要生成，则返回None
        if not summary_enabled:
            logger.info(f"RSS组 {group_name} 未启用摘要生成，跳过条目: {entry.get('title', '')}")
            return None
        
        # 获取最大摘要长度
        max_length = summary_config.get('max_length', 150)
        
        # 获取提供商
        provider = summary_config.get('provider')
        
        # 尝试从缓存获取结果
        cache_key = f"summary:{group_name}:{self._get_entry_hash(entry)}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            logger.info(f"使用缓存的摘要结果: {entry.get('title', '')}")
            return cached_result
        
        # 构建摘要内容
        content = self._build_filter_content(entry)
        
        # 构建摘要提示
        summary_prompt = f"""
        请为以下文章生成一个简短的摘要，不超过{max_length}个字：
        
        标题：{entry.get('title', '')}
        链接：{entry.get('link', '')}
        内容：{content}
        
        摘要要求：
        1. 简明扼要，突出文章核心内容
        2. 不超过{max_length}个字
        3. 不要包含"以下是摘要"等无关文字
        """
        
        try:
            # 调用LLM生成摘要
            logger.info(f"开始生成摘要: {entry.get('title', '')}")
            start_time = time.time()
            summary = self.llm_integrator.generate_text(summary_prompt, provider)
            end_time = time.time()
            logger.info(f"生成摘要完成，耗时: {end_time - start_time:.2f}秒")
            
            # 缓存结果
            self.cache_manager.set(cache_key, summary)
            
            logger.info(f"摘要结果: {entry.get('title', '')}, 长度: {len(summary)}")
            
            return summary
        except Exception as e:
            logger.error(f"生成摘要异常: {e}")
            return None
    
    def batch_process_entries(self, entries: List[Dict[str, Any]], group_name: str) -> List[Dict[str, Any]]:
        """
        批量处理条目
        
        Args:
            entries: RSS条目列表
            group_name: RSS组名称
        
        Returns:
            处理后的RSS条目列表
        """
        # 获取组配置
        group_config = self.config_manager.get_group_config(group_name)
        if not group_config:
            logger.warning(f"RSS组 {group_name} 不存在，跳过批量处理")
            return entries
        
        # 获取过滤配置
        filter_config = group_config.get('filter', {})
        filter_enabled = filter_config.get('enabled', False)
        
        # 获取摘要配置
        summary_config = group_config.get('summary', {})
        summary_enabled = summary_config.get('enabled', False)
        
        # 如果未启用过滤和摘要生成，则返回原始条目
        if not filter_enabled and not summary_enabled:
            logger.info(f"RSS组 {group_name} 未启用过滤和摘要生成，跳过批量处理")
            return entries
        
        # 批量处理条目
        processed_entries = []
        
        logger.info(f"开始批量处理条目，总数: {len(entries)}")
        start_time = time.time()
        
        for entry in entries:
            # 过滤条目
            if filter_enabled:
                if not self.filter_entry(entry, group_name):
                    logger.info(f"条目被过滤: {entry.get('title', '')}")
                    continue
            
            # 生成摘要
            if summary_enabled:
                summary = self.generate_summary(entry, group_name)
                if summary:
                    entry['summary'] = summary
            
            # 标记为已处理
            entry['filtered'] = True
            
            # 添加到处理后的条目列表
            processed_entries.append(entry)
        
        end_time = time.time()
        logger.info(f"批量处理条目完成，处理前: {len(entries)}，处理后: {len(processed_entries)}，耗时: {end_time - start_time:.2f}秒")
        
        return processed_entries
    
    def _build_filter_content(self, entry: Dict[str, Any]) -> str:
        """
        构建过滤内容
        
        Args:
            entry: RSS条目
        
        Returns:
            过滤内容
        """
        # 获取内容
        content = entry.get('content', '')
        
        # 如果内容是字典，则获取值
        if isinstance(content, dict):
            content = content.get('value', '')
        
        # 如果内容是列表，则获取第一个元素的值
        elif isinstance(content, list) and len(content) > 0:
            content = content[0].get('value', '')
        
        # 如果没有内容，则使用摘要
        if not content:
            content = entry.get('summary', '')
        
        # 如果没有摘要，则使用描述
        if not content:
            content = entry.get('description', '')
        
        return content
    
    def _get_entry_hash(self, entry: Dict[str, Any]) -> str:
        """
        获取条目哈希
        
        Args:
            entry: RSS条目
        
        Returns:
            条目哈希
        """
        # 使用标题和链接生成哈希
        title = entry.get('title', '')
        link = entry.get('link', '')
        
        # 生成哈希
        return hashlib.md5(f"{title}{link}".encode()).hexdigest()
