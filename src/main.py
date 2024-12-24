from src.storage.github_operations import GithubOperations  # 导入 GitHub 操作相关功能
from src.generation.tech_evolution_generator import TechEvolutionGenerator  # 导入技术进化生成器
from src.generation.digest_generator import DigestGenerator  # 导入摘要生成器
from src.generation.tweet_generator import TweetGenerator  # 导入推文生成器
from src.utils.config import Config, AIProvider  # 导入配置和 AI 提供商
from anthropic import Anthropic  # 导入 Anthropic AI 客户端
from openai import OpenAI  # 导入 OpenAI 客户端

import anthropic
import json
from datetime import datetime, timedelta
import math
import traceback
import os
import argparse

class SimulationWorkflow:
    def __init__(self, tweets_per_year=96, digest_interval=16, provider: AIProvider = AIProvider.XAI, is_production=False):
        """初始化模拟工作流
        
        参数:
            tweets_per_year: 每年生成的推文数量，默认96条
            digest_interval: 生成摘要的间隔，默认16条推文
            provider: AI提供商，默认使用XAI
            is_production: 是否为生产环境��默认为False
        """
        print("\n=== 初始化模拟工作流 [main.py:SimulationWorkflow.__init__] ===")
        print(f"- 环境: {'生产环境' if is_production else '开发环境'}")
        print(f"- AI提供商: {provider}")
        print(f"- 每年推文数: {tweets_per_year}")
        print(f"- 摘要间隔: {digest_interval}")
        print()
        
        # 根据提供商配置初始化 AI 客户端
        ai_config = Config.get_ai_config(provider)
        
        if provider == AIProvider.ANTHROPIC:
            # 新版本 Anthropic 客户端初始化
            client_kwargs = {'api_key': ai_config.api_key}
            if hasattr(ai_config, 'base_url') and ai_config.base_url:
                client_kwargs['base_url'] = ai_config.base_url
            self.client = Anthropic(**client_kwargs)
        elif provider == AIProvider.OPENAI:
            self.client = OpenAI(api_key=ai_config.api_key)
        elif provider == AIProvider.XAI:
            # XAI 使用 Anthropic 客户端
            client_kwargs = {
                'api_key': ai_config.api_key,
                'base_url': ai_config.base_url if hasattr(ai_config, 'base_url') else None
            }
            # 移除 None 值的参数
            client_kwargs = {k: v for k, v in client_kwargs.items() if v is not None}
            self.client = Anthropic(**client_kwargs)
        
        self.model = ai_config.model
        self.digest_interval = digest_interval
        self.is_production = is_production
        
        # 根据是否为生产环境设置是否发送推文到 Twitter
        self.post_to_twitter = is_production

        # 初始化 GitHub 操作
        self.github_ops = GithubOperations(is_production=is_production)
        self.tweets_per_year = tweets_per_year
        self.tech_preview_months = 6
        self.start_date = datetime(2025, 1, 1)  # 设置起始日期
        self.days_per_tweet = 384 / tweets_per_year  # 使用384天以对齐推文数量
        self.start_age = 22.0  # 起始年龄
        
        # 初始化推文生成器
        self.tweet_gen = TweetGenerator(
            client=self.client,
            model=self.model,
            tweets_per_year=tweets_per_year,
            digest_interval=self.digest_interval,
            is_production=is_production,
            start_date=self.start_date
        )

    def get_current_date(self, tweet_count):
        """计算当前模拟日期"""
        days_elapsed = tweet_count * self.days_per_tweet
        return self.start_date + timedelta(days=days_elapsed)
        
    def get_age(self, tweet_count):
        """根据推文数量计算当前年龄"""
        years_elapsed = tweet_count / self.tweets_per_year
        return self.start_age + years_elapsed
        
    def run(self):
        """运行模拟工作流"""
        try:
            print("\n=== 开始运行模拟工作流 [main.py:77] ===")
            
            # 1. 读取现有推文和历史记录
            print("\n1. [main.py:80] 正在读取现有推文和历史记录...")
            ongoing_tweets, acti_tweets_by_age = self.tweet_gen.get_ongoing_tweets()
            print(f"- [main.py:82] 获取到 {len(ongoing_tweets) if ongoing_tweets else 0} 条现有推文")
            
            ongoing_comments = None
            trends = None

            # 初始化计数器
            tweet_count = 0
            
            # 从现有推文中提取最新状态
            if ongoing_tweets:
                last_tweet = ongoing_tweets[-1]
                if isinstance(last_tweet, dict):
                    tweet_count = last_tweet.get('tweet_count', 0)

            # 计算当前日期和年龄
            current_date = self.get_current_date(tweet_count + 1)
            age = self.get_age(tweet_count + 1)
            print(f"当前推文数量: {tweet_count}")
            print(f"当前模拟日期: {current_date.strftime('%Y-%m-%d')}")
            print(f"当前年龄: {age:.2f}")
            
            # 2. 初始化各个组件
            tech_gen = TechEvolutionGenerator(
                client=self.client,
                model=self.model,
                is_production=self.is_production,
            )
            
            digest_gen = DigestGenerator(
                client=self.client,
                model=self.model,
                tweet_generator=self.tweet_gen,
                is_production=self.is_production
            )
            
            # 3. 检查并获取最新的技术进化数据
            print("\n3. [main.py:110] 正在生成技术进化数据...")
            tech_evolution = tech_gen.check_and_generate_tech_evolution(current_date)
            if not tech_evolution:
                print("[main.py:113] 错误: 获取技术进化数据失败")
                print("- 检查 tech_evolution.json 是否存在")
                print("- 检查生成过程中的错误信息")
                return

            # 4. 检查/生成摘要
            print("\n4. 正在生成内容摘要...")
            latest_digest = digest_gen.check_and_generate_digest(
                ongoing_tweets=acti_tweets_by_age if acti_tweets_by_age else ongoing_tweets,
                age=age,
                current_date=current_date,
                tweet_count=tweet_count,
                tech_evolution=tech_evolution
            )

            if latest_digest is None:
                print("错误: 生成摘要失败")
                print("- 检查 digest_history.json")
                print("- 检查生成过程中的错误信息")
                return
            
            # 5. 生成并存储新推文
            new_tweet = self.tweet_gen.generate_tweet(
                latest_digest=latest_digest,
                recent_tweets=ongoing_tweets[-self.digest_interval:] if ongoing_tweets else None,
                recent_comments=ongoing_comments[-self.digest_interval:] if ongoing_comments else None,
                age=age,
                tweet_count=tweet_count,
                trends=trends,
                sequence_length=self.digest_interval
            )

            if new_tweet:
                # 如果设置了发送到 Twitter
                if self.post_to_twitter:
                    from src.twitter.twitter_client import TwitterClientV2
                    twitter_client = TwitterClientV2()
                    
                    # 添加测试前缀并确保长度在限制内
                    test_prefix = ""
                    max_content_length = 280 - len(test_prefix)
                    tweet_content = test_prefix + new_tweet['content'][:max_content_length]
                    
                    # 发送推文到 Twitter
                    tweet_id = twitter_client.post_tweet(tweet_content)
                    
                    if tweet_id:
                        print(f"成功发送推文到 Twitter，ID: {tweet_id}")
                        print(f"推文内容: {tweet_content}")
                        # 使用 Twitter ID 存储推文
                        self.tweet_gen.github_ops.add_tweet(
                            new_tweet,
                            id=tweet_id,
                            tweet_count=tweet_count + 1,
                            simulated_date=current_date.strftime('%Y-%m-%d'),
                            age=age
                        )
                    else:
                        print("发送推文到 Twitter 失败")
                        # 如果发送失败，使用序列 ID
                        self.tweet_gen.github_ops.add_tweet(
                            new_tweet,
                            id=f"tweet_{tweet_count + 1}",
                            tweet_count=tweet_count + 1,
                            simulated_date=current_date.strftime('%Y-%m-%d'),
                            age=age
                        )
                else:
                    # 不发送到 Twitter 时使用序列 ID
                    self.tweet_gen.github_ops.add_tweet(
                        new_tweet,
                        id=f"tweet_{tweet_count + 1}",
                        tweet_count=tweet_count + 1,
                        simulated_date=current_date.strftime('%Y-%m-%d'),
                        age=age
                    )
                    print("推文生成但未发送到 Twitter (post_to_twitter=False)")
                
        except Exception as e:
            print(f"\n=== 模拟工作流出错 ===")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print("\n详细错误追踪:")
            traceback.print_exc()

def main():
    print("程序启动...")
    
    # 检查是否需要初始化仓库
    INIT_FLAG_FILE = ".initialized"
    
    # 初始化 GitHub 仓库结构
    github_ops = GithubOperations(is_production=False)
    
    # 只在第一次运行时初始化仓库
    if not os.path.exists(INIT_FLAG_FILE):
        try:
            print("首次运行，初始化仓库...")
            github_ops.initialize_repository()
            # 创建标记文件
            with open(INIT_FLAG_FILE, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            print(f"警告: 仓库初始化失败: {str(e)}")
    
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description='运行 Xavier 模拟')
    parser.add_argument('--tweets-per-year', type=int, default=96,
                      help='每年生成的推文数量')
    parser.add_argument('--digest-interval', type=int, default=4,
                      help='生成摘要的推文间隔')
    parser.add_argument('--provider', type=str, choices=['anthropic', 'openai', 'xai'],
                      default='xai', help='使用的 AI 提供商')
    parser.add_argument('--is-production', action='store_true',
                      help='是否在生产环境运行（默认为 False）')
    
    args = parser.parse_args()
    
    # AI 提供商映射
    provider_map = {
        'anthropic': AIProvider.ANTHROPIC,
        'openai': AIProvider.OPENAI,
        'xai': AIProvider.XAI
    }
    
    # 初始化工作流
    workflow = SimulationWorkflow(
        tweets_per_year=args.tweets_per_year,
        digest_interval=args.digest_interval,
        provider=provider_map[args.provider],
        is_production=args.is_production
    )
    
    # 运行工作流（目前只运行一次，可以取消注释 while True 实现环）
    while True:
        workflow.run()

if __name__ == "__main__":
    main() 