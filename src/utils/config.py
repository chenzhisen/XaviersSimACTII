from dataclasses import dataclass
from enum import Enum
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class AIProvider(Enum):
    XAI = "XAI"
    ANTHROPIC = "ANTHROPIC"
    OPENAI = "OPENAI"

@dataclass
class AIConfig:
    api_key: str
    model: str
    base_url: Optional[str] = None

@dataclass
class Config:
    # GitHub Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")
    GITHUB_OWNER: str = os.getenv("GITHUB_OWNER")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO")
    
    # Tweet Generation Configuration
    MAX_RECENT_TWEETS: int = 20
    TWEET_LENGTH: int = 280
    
    # Twitter API Configuration
    TWITTER_API_KEY: str = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET: str = os.getenv("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN: str = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET: str = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN")

    # AI Providers Configuration
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
        config = cls.PROVIDERS.get(provider)
        if not config:
            raise ValueError(f"Unknown AI provider: {provider}")
        if not config.api_key:
            raise ValueError(f"API key not found for provider: {provider}")
        return config