"""
LLM集成模块，提供统一的LLM API接口
"""
import os
import logging
import json
import time
import hashlib
from typing import Any, Dict, List, Optional
import requests

from src.config_manager import ConfigManager
from src.cache_manager import CacheManager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMIntegrator:
    """LLM集成类，提供统一的LLM API接口"""
    
    def __init__(self, config_manager: ConfigManager, cache_manager: CacheManager):
        """
        初始化LLM集成器
        
        Args:
            config_manager: 配置管理器实例
            cache_manager: 缓存管理器实例
        """
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        
        # 获取LLM配置
        self.llm_config = self.config_manager.get_config('llm', {})
        
        # 获取默认提供商
        self.default_provider = self.llm_config.get('default_provider', 'openai')
        
        # 初始化API密钥
        self._init_api_keys()
        
        logger.info("LLM集成器初始化完成")
    
    def _init_api_keys(self) -> None:
        """初始化API密钥"""
        # OpenAI
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            openai_api_key = self.llm_config.get('openai', {}).get('api_key', '')
        
        if not openai_api_key:
            logger.warning("OpenAI API密钥未设置")
        
        # Gemini
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        if not gemini_api_key:
            gemini_api_key = self.llm_config.get('gemini', {}).get('api_key', '')
        
        if not gemini_api_key:
            logger.warning("Gemini API密钥未设置")
        
        # Claude
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        if not claude_api_key:
            claude_api_key = self.llm_config.get('claude', {}).get('api_key', '')
        
        if not claude_api_key:
            logger.warning("Claude API密钥未设置")
        
        # Deepseek
        deepseek_api_key = os.environ.get('DEEPSEEK_API_KEY')
        if not deepseek_api_key:
            deepseek_api_key = self.llm_config.get('deepseek', {}).get('api_key', '')
        
        if not deepseek_api_key:
            logger.warning("Deepseek API密钥未设置")
        
        # Azure
        azure_api_key = os.environ.get('AZURE_API_KEY')
        if not azure_api_key:
            azure_api_key = self.llm_config.get('azure', {}).get('api_key', '')
        
        azure_endpoint = os.environ.get('AZURE_ENDPOINT')
        if not azure_endpoint:
            azure_endpoint = self.llm_config.get('azure', {}).get('base_url', '')
        
        azure_deployment_id = os.environ.get('AZURE_DEPLOYMENT_ID')
        if not azure_deployment_id:
            azure_deployment_id = self.llm_config.get('azure', {}).get('deployment_id', '')
        
        if not azure_api_key or not azure_endpoint or not azure_deployment_id:
            logger.warning("Azure API配置不完整")
    
    def generate_text(self, prompt: str, provider: Optional[str] = None) -> str:
        """
        生成文本
        
        Args:
            prompt: 提示词
            provider: 提供商，如果为None则使用默认提供商
        
        Returns:
            生成的文本
        """
        # 如果未指定提供商，则使用默认提供商
        if not provider:
            provider = self.default_provider
        
        # 获取提供商配置
        provider_config = self.llm_config.get(provider, {})
        
        # 获取API密钥
        api_key = os.environ.get(f'{provider.upper()}_API_KEY')
        if not api_key:
            api_key = provider_config.get('api_key', '')
        
        # 如果API密钥未设置，则返回错误
        if not api_key and provider not in ['ollama']:
            logger.error(f"{provider} API密钥未设置")
            return f"错误: {provider} API密钥未设置"
        
        # 获取缓存
        cache_key = f"llm:{provider}:{hashlib.md5(prompt.encode()).hexdigest()}"
        cached_result = self.cache_manager.get(cache_key)
        
        if cached_result is not None:
            logger.info(f"使用缓存的LLM结果，提供商: {provider}")
            return cached_result
        
        # 根据提供商调用不同的API
        try:
            if provider == 'openai':
                result = self._call_openai(prompt, provider_config, api_key)
            elif provider == 'gemini':
                result = self._call_gemini(prompt, provider_config, api_key)
            elif provider == 'claude':
                result = self._call_claude(prompt, provider_config, api_key)
            elif provider == 'ollama':
                result = self._call_ollama(prompt, provider_config)
            elif provider == 'deepseek':
                result = self._call_deepseek(prompt, provider_config, api_key)
            elif provider == 'azure':
                result = self._call_azure(prompt, provider_config, api_key)
            else:
                logger.error(f"不支持的提供商: {provider}")
                return f"错误: 不支持的提供商 {provider}"
            
            # 缓存结果
            self.cache_manager.set(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"调用LLM API异常: {e}")
            return f"错误: 调用LLM API异常 {e}"
    
    def batch_generate_text(self, prompts: List[str], provider: Optional[str] = None) -> List[str]:
        """
        批量生成文本
        
        Args:
            prompts: 提示词列表
            provider: 提供商，如果为None则使用默认提供商
        
        Returns:
            生成的文本列表
        """
        results = []
        
        for prompt in prompts:
            result = self.generate_text(prompt, provider)
            results.append(result)
        
        return results
    
    def _call_openai(self, prompt: str, config: Dict[str, Any], api_key: str) -> str:
        """
        调用OpenAI API
        
        Args:
            prompt: 提示词
            config: 配置
            api_key: API密钥
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', 'https://api.openai.com/v1')
        model = config.get('model', 'gpt-3.5-turbo')
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        # 发送请求
        logger.info(f"调用OpenAI API，模型: {model}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"OpenAI API返回错误: {response.status_code}, {response.text}")
            return f"错误: OpenAI API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        return text
    
    def _call_gemini(self, prompt: str, config: Dict[str, Any], api_key: str) -> str:
        """
        调用Gemini API
        
        Args:
            prompt: 提示词
            config: 配置
            api_key: API密钥
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', 'https://generativelanguage.googleapis.com/v1')
        model = config.get('model', 'gemini-pro')
        
        # 构建请求
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7
            }
        }
        
        # 发送请求
        logger.info(f"调用Gemini API，模型: {model}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"Gemini API返回错误: {response.status_code}, {response.text}")
            return f"错误: Gemini API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        
        return text
    
    def _call_claude(self, prompt: str, config: Dict[str, Any], api_key: str) -> str:
        """
        调用Claude API
        
        Args:
            prompt: 提示词
            config: 配置
            api_key: API密钥
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', 'https://api.anthropic.com/v1')
        model = config.get('model', 'claude-2')
        
        # 构建请求
        url = f"{base_url}/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000
        }
        
        # 发送请求
        logger.info(f"调用Claude API，模型: {model}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"Claude API返回错误: {response.status_code}, {response.text}")
            return f"错误: Claude API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('content', [{}])[0].get('text', '')
        
        return text
    
    def _call_ollama(self, prompt: str, config: Dict[str, Any]) -> str:
        """
        调用Ollama API
        
        Args:
            prompt: 提示词
            config: 配置
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', 'http://localhost:11434/api')
        model = config.get('model', 'llama2')
        
        # 构建请求
        url = f"{base_url}/generate"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "prompt": prompt
        }
        
        # 发送请求
        logger.info(f"调用Ollama API，模型: {model}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"Ollama API返回错误: {response.status_code}, {response.text}")
            return f"错误: Ollama API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('response', '')
        
        return text
    
    def _call_deepseek(self, prompt: str, config: Dict[str, Any], api_key: str) -> str:
        """
        调用Deepseek API
        
        Args:
            prompt: 提示词
            config: 配置
            api_key: API密钥
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', 'https://api.deepseek.com/v1')
        model = config.get('model', 'deepseek-chat')
        
        # 构建请求
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        # 发送请求
        logger.info(f"调用Deepseek API，模型: {model}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"Deepseek API返回错误: {response.status_code}, {response.text}")
            return f"错误: Deepseek API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        return text
    
    def _call_azure(self, prompt: str, config: Dict[str, Any], api_key: str) -> str:
        """
        调用Azure OpenAI API
        
        Args:
            prompt: 提示词
            config: 配置
            api_key: API密钥
        
        Returns:
            生成的文本
        """
        # 获取配置
        base_url = config.get('base_url', '')
        deployment_id = config.get('deployment_id', '')
        api_version = config.get('api_version', '2023-05-15')
        
        # 构建请求
        url = f"{base_url}/openai/deployments/{deployment_id}/chat/completions?api-version={api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        # 发送请求
        logger.info(f"调用Azure OpenAI API，部署ID: {deployment_id}")
        response = requests.post(url, headers=headers, json=data)
        
        # 检查响应
        if response.status_code != 200:
            logger.error(f"Azure OpenAI API返回错误: {response.status_code}, {response.text}")
            return f"错误: Azure OpenAI API返回 {response.status_code}"
        
        # 解析响应
        result = response.json()
        
        # 提取文本
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        return text
