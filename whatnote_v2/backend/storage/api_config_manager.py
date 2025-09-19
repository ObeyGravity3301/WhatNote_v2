import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

class APIConfigManager:
    """全局API配置管理器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.config_file = data_dir / "api_config.json"
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """确保配置文件存在"""
        if not self.config_file.exists():
            # 创建默认配置
            default_config = {
                "current_provider": "openai",
                "providers": {
                    "openai": {
                        "apiKey": "",
                        "model": "gpt-4",
                        "baseUrl": "https://api.openai.com/v1"
                    },
                    "anthropic": {
                        "apiKey": "",
                        "model": "claude-3-5-sonnet-20241022",
                        "baseUrl": "https://api.anthropic.com"
                    },
                    "gemini": {
                        "apiKey": "",
                        "model": "gemini-1.5-pro",
                        "baseUrl": "https://generativelanguage.googleapis.com/v1"
                    },
                    "qwen": {
                        "apiKey": "",
                        "model": "qwen-plus",
                        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    }
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def get_config(self) -> Dict:
        """获取完整配置"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取API配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "current_provider": "openai",
            "providers": {
                "openai": {"apiKey": "", "model": "gpt-4", "baseUrl": "https://api.openai.com/v1"},
                "anthropic": {"apiKey": "", "model": "claude-3-5-sonnet-20241022", "baseUrl": "https://api.anthropic.com"},
                "gemini": {"apiKey": "", "model": "gemini-1.5-pro", "baseUrl": "https://generativelanguage.googleapis.com/v1"},
                "qwen": {"apiKey": "", "model": "qwen-plus", "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1"}
            }
        }
    
    def update_config(self, provider: str, config: Dict) -> bool:
        """更新指定服务商的配置"""
        try:
            full_config = self.get_config()
            
            # 更新服务商配置
            if "providers" not in full_config:
                full_config["providers"] = {}
            
            full_config["providers"][provider] = config
            full_config["updated_at"] = datetime.now().isoformat()
            
            # 保存配置
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(full_config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"更新API配置失败: {e}")
            return False
    
    def set_current_provider(self, provider: str) -> bool:
        """设置当前使用的服务商"""
        try:
            full_config = self.get_config()
            full_config["current_provider"] = provider
            full_config["updated_at"] = datetime.now().isoformat()
            
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(full_config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"设置当前服务商失败: {e}")
            return False
    
    def get_current_provider(self) -> str:
        """获取当前服务商"""
        config = self.get_config()
        return config.get("current_provider", "openai")
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """获取指定服务商的配置"""
        config = self.get_config()
        providers = config.get("providers", {})
        return providers.get(provider)
    
    def get_current_config(self) -> Optional[Dict]:
        """获取当前服务商的配置"""
        current_provider = self.get_current_provider()
        return self.get_provider_config(current_provider)
    
    def is_provider_configured(self, provider: str) -> bool:
        """检查服务商是否已配置"""
        config = self.get_provider_config(provider)
        if not config:
            return False
        return bool(config.get("apiKey", "").strip())
    
    def get_configured_providers(self) -> list:
        """获取已配置的服务商列表"""
        config = self.get_config()
        providers = config.get("providers", {})
        configured = []
        
        for provider, provider_config in providers.items():
            if provider_config.get("apiKey", "").strip():
                configured.append(provider)
        
        return configured
