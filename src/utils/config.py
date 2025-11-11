"""
配置管理模块

负责加载和管理系统配置
"""

import os
import yaml
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.yaml"
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            
            if not config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_path}")
                self._config = self._get_default_config()
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            # 处理环境变量替换
            self._config = self._replace_env_vars(self._config)
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            self._config = self._get_default_config()
    
    def _replace_env_vars(self, config: Any) -> Any:
        """替换配置中的环境变量"""
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            return os.getenv(env_var, config)
        else:
            return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "system": {
                "name": "Multi-Agent Collaboration System",
                "version": "1.0.0",
                "debug": True,
                "log_level": "INFO"
            },
            "database": {
                "type": "sqlite",
                "url": "sqlite:///./multi_agent.db",
                "echo": False
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None
            },
            "models": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "models": {
                            "gpt-4": "gpt-4",
                            "gpt-3.5-turbo": "gpt-3.5-turbo"
                        }
                    }
                }
            },
            "agents": {
                "planner": {
                    "name": "任务规划智能体",
                    "model": "gpt-4",
                    "provider": "openai",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                "executor": {
                    "name": "任务执行智能体",
                    "model": "gpt-3.5-turbo",
                    "provider": "openai",
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                "monitor": {
                    "name": "任务监督智能体",
                    "model": "gpt-4",
                    "provider": "openai",
                    "temperature": 0.5,
                    "max_tokens": 1500
                },
                "browser": {
                    "name": "浏览器操作智能体",
                    "model": "gpt-4",
                    "provider": "openai",
                    "temperature": 0.2,
                    "max_tokens": 1000
                }
            },
            "web": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": True,
                "secret_key": "your-secret-key-here"
            },
            "logging": {
                "level": "INFO",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
                "rotation": "1 day",
                "retention": "30 days"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 节名称
            
        Returns:
            配置节字典
        """
        return self.get(section, {})
    
    def has(self, key: str) -> bool:
        """
        检查配置键是否存在
        
        Args:
            key: 配置键
            
        Returns:
            是否存在
        """
        return self.get(key) is not None
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        logger.info("配置已重新加载")
    
    def save(self, config_path: Optional[str] = None):
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
        """
        save_path = config_path or self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        return self._config.copy()
    
    def update(self, other: Dict[str, Any]):
        """
        更新配置
        
        Args:
            other: 其他配置字典
        """
        self._deep_update(self._config, other)
        logger.info("配置已更新")
    
    def _deep_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def validate(self) -> bool:
        """
        验证配置
        
        Returns:
            是否有效
        """
        try:
            # 检查必需的配置项
            required_keys = [
                "system.name",
                "system.version",
                "models.default_provider",
                "agents.planner",
                "agents.executor",
                "agents.monitor"
            ]
            
            for key in required_keys:
                if not self.has(key):
                    logger.error(f"缺少必需的配置项: {key}")
                    return False
            
            # 检查API密钥
            if self.get("models.providers.openai.api_key") == "":
                logger.warning("OpenAI API密钥未设置")
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return self.has(key)
