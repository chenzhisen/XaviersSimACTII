from dataclasses import dataclass
from enum import Enum
import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv, dotenv_values

# 加载环境变量配置
dotenv_path = find_dotenv()
load_dotenv()

# 获取所有环境变量值
env_file_values = dotenv_values()

# 强制重新加载 .env 文件
load_dotenv(override=True)

class AIProvider(Enum):
    """AI 提供商枚举类
    
    定义支持的 AI 服务提供商：
    XAI: XAI 的服务
    ANTHROPIC: Anthropic 的 Claude
    OPENAI: OpenAI 的 GPT
    """
    XAI = "XAI"
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"

@dataclass
class AIConfig:
    """AI 配置数据类
    
    存储 AI 服务的配置信息：
    api_key: API 密钥
    model: 使用的模型名称
    base_url: API 基础 URL（可选）
    """
    api_key: str
    model: str
    base_url: Optional[str] = None

@dataclass
class Config:
    """配置管理类
    
    管理所有配置信息，包括：
    - GitHub 配置
    - 推文生成配置
    - Twitter API 配置
    - AI 提供商配置
    """
    
    # GitHub 配置
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")
    GITHUB_OWNER: str = os.getenv("GITHUB_OWNER")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO")
    
    # 推文生成配置
    MAX_RECENT_TWEETS: int = 20
    TWEET_LENGTH: int = 280
    
    # Twitter API 配置
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET: str = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN")

    # AI 提供商配置
    PROVIDERS = {
        AIProvider.XAI: AIConfig(
            api_key=os.getenv('XAI_API_KEY'),
            model="grok-beta",
            base_url="https://api.x.ai"
        ),
        AIProvider.ANTHROPIC: AIConfig(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            model="claude-3-opus-20240229"
        ),
        AIProvider.OPENAI: AIConfig(
            api_key=os.getenv('OPENAI_API_KEY'),
            model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            base_url="https://api.openai.com/v1"
        )
    }

    @classmethod
    def get_ai_config(cls, provider: AIProvider) -> AIConfig:
        """获取指定提供商的 AI 配置
        
        参数:
            provider: AI 提供商枚举值
            
        返回:
            对应提供商的配置信息
            
        异常:
            ValueError: 如果提供商未知或 API 密钥未配置
        """
        config = cls.PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"未知的 AI 提供商: {provider}")
        if not config.api_key:
            raise ValueError(f"未找到提供商的 API 密钥: {provider}")
        return config