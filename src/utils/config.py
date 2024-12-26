import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv, find_dotenv

# 加载环境变量
dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

class Config:
    # 单例实例
    _instance = None
    _initialized = False
    
    # Twitter API Configuration
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Tweet Generation Configuration
    MAX_RECENT_TWEETS = 20
    TWEET_LENGTH = 280
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._env = 'production'  # 默认生产环境
        self._validate_config()
    
    def _validate_config(self):
        """验证必要的配置是否存在"""
        required_keys = [
            'TWITTER_API_KEY',
            'TWITTER_API_SECRET',
            'TWITTER_ACCESS_TOKEN',
            'TWITTER_ACCESS_TOKEN_SECRET',
            'OPENAI_API_KEY'
        ]
        
        missing = []
        for key in required_keys:
            if not getattr(self, key):
                missing.append(key)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    def set_environment(self, is_prod: bool = True):
        """设置环境"""
        self._env = 'production' if is_prod else 'development'
    
    def is_production(self) -> bool:
        """是否是生产环境"""
        return self._env == 'production'
    
    def is_development(self) -> bool:
        """是否是开发环境"""
        return self._env == 'development'
    
    def get_data_dir(self) -> str:
        """获取数据目录"""
        base_dir = os.path.join('nodeSrc', 'data')
        env_dir = 'prod' if self.is_production() else 'dev'
        return os.path.join(base_dir, env_dir)