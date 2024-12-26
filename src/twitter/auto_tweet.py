import sys
import os
import time
import json
import argparse
from datetime import datetime
import re

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from twitter_client import TwitterClientV2
class AutoTweeter:
    def __init__(self, dry_run=True, is_production=False):
        self.dry_run = dry_run  # 是否实际发送推文
        self.client = TwitterClientV2()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        
        # 根据环境选择目录
        env_dir = 'prod' if is_production else 'dev'
        data_dir = os.path.join(project_root, 'nodeSrc', 'data', env_dir)
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        self.tweets_file = os.path.join(data_dir, 'tweets_public.json')
        self.sent_tweets_file = os.path.join(data_dir, 'sent_tweets.json')
        print(f"推文文件路径: {self.tweets_file}")
        print(f"已发送推文文件路径: {self.sent_tweets_file}")
        print(f"运行环境: {'生产环境' if is_production else '开发环境'}")
        print(f"运行模式: {'测试模式 (不实际发送)' if self.dry_run else '正式模式 (实际发送)'}")
        
        # 确保 sent_tweets_file 存在
        self._ensure_sent_tweets_file()
        
    def _ensure_sent_tweets_file(self):
        """确保已发送推文文件存在"""
        if not os.path.exists(self.sent_tweets_file):
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.sent_tweets_file), exist_ok=True)
                # 创建空的已发送推文文件
                with open(self.sent_tweets_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                print(f"创建空的已发送推文文件: {self.sent_tweets_file}")
            except Exception as e:
                print(f"创建已发送推文文件时出错: {str(e)}")

    def read_tweets(self):
        """读取推文文件"""
        try:
            if not os.path.exists(self.tweets_file):
                print(f"推文文件不存在: {self.tweets_file}")
                return []

            try:
                with open(self.tweets_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():  # 如果文件为空
                        return []
                    return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")
                return []
        except Exception as e:
            print(f"读取推文文件出错: {str(e)}")
            return []

    def save_tweets(self, tweets):
        """保存推文数组"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tweets_file), exist_ok=True)
            
            # 使用临时文件保存
            temp_file = self.tweets_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)
            
            # 重命名临时文件
            if os.path.exists(self.tweets_file):
                os.replace(temp_file, self.tweets_file)
            else:
                os.rename(temp_file, self.tweets_file)
            return True
        except Exception as e:
            print(f"保存推文文件出错: {str(e)}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False

    def is_duplicate_tweet(self, content):
        """检查是否是重复推文"""
        try:
            # 确保文件存在
            self._ensure_sent_tweets_file()
            
            with open(self.sent_tweets_file, 'r', encoding='utf-8') as f:
                sent_tweets = json.load(f)
                # 检查最近100条推文
                recent_contents = [t['content'] for t in sent_tweets[-100:]]
                return content in recent_contents
        except Exception as e:
            print(f"检查重复推文时出错: {str(e)}")
            return False

    def save_sent_tweet(self, tweet, tweet_id):
        """保存已发送的推文"""
        try:
            # 确保文件存在
            self._ensure_sent_tweets_file()
            
            try:
                with open(self.sent_tweets_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    sent_tweets = json.loads(content) if content.strip() else []
            except (json.JSONDecodeError, FileNotFoundError):
                sent_tweets = []

            sent_tweets.append({
                'id': tweet_id,
                'content': tweet['content'],
                'original_id': tweet.get('id'),
                'sent_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'age': tweet.get('age', None)  # 添加age字段
            })

            # 只保留最近1000条
            if len(sent_tweets) > 1000:
                sent_tweets = sent_tweets[-1000:]

            # 使用临时文件保存
            temp_file = self.sent_tweets_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(sent_tweets, f, ensure_ascii=False, indent=2)
            
            # 重命名临时文件
            if os.path.exists(self.sent_tweets_file):
                os.replace(temp_file, self.sent_tweets_file)
            else:
                os.rename(temp_file, self.sent_tweets_file)
            return True
        except Exception as e:
            print(f"保存已发送推文时出错: {str(e)}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False

    def post_next_tweet(self):
        """发送下一条推文"""
        try:
            # 读取待发送的推文
            tweets = self.read_tweets()
            if not tweets:
                print("没有待发送的推文")
                return None

            # 获取第一条推文
            tweet = tweets[0]
            
            # 清理内容
            clean_content = self._clean_tweet_content(tweet)

            if self.dry_run:
                # 如果是dry run模式，生成一个模拟的推文ID
                tweet_id = f"dry_run_{int(time.time())}_{hash(clean_content) % 10000}"
                print(f"[Dry Run] 模拟发送推文: {clean_content}")
                print(f"[Dry Run] 模拟推文ID: {tweet_id}")
            else:
                # 实际发送推文
                tweet_id = self.client.post_tweet(clean_content)
            
            if tweet_id and not tweet_id.startswith('Error'):
                # 保存发送成功的推文
                self.save_sent_tweet(tweet, tweet_id)
                
                # 从待发送列表中移除
                tweets.pop(0)
                self.save_tweets(tweets)
                
                print(f"{'[Dry Run] 模拟' if self.dry_run else ''} 成功发送推文: {clean_content}")
                return {'id': tweet_id}
            
            return None
        except Exception as e:
            print(f"发送推文时出错: {str(e)}")
            if str(e).startswith('403'):
                print("检测到重复推文错误，删除并继续")
                tweets.pop(0)
                self.save_tweets(tweets)
            return None

    def run(self, interval_seconds=30000):  # 默认5分钟发送一次
        print(f"自动发推程序启动")
        print(f"运行模式: {'测试模式 (不实际发送)' if self.dry_run else '正式模式 (实际发送)'}")
        
        try:
            result = self.post_next_tweet()
            if result:
                print("推文发送成功")
            else:
                print("没有新推文或发送失败")
            
        except Exception as e:
            print(f"运行出错: {str(e)}")
            return False
        
        return True

    def _clean_tweet_content(self, tweet):
        """清理推文内容，清理任何位置的TWEET1-4"""
        # 获取推文内容
        text = tweet.get('content', '')
        
        # 清理任何位置的TWEET1-4（包括前后的换行和空格）
        text = re.sub(r'[\n\s]*TWEET[1-4][\n\s]*', '', text)
        
        return text.strip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='自动发送推文程序')
    parser.add_argument('--prod', action='store_true', help='使用生产环境')
    parser.add_argument('--no-dry-run', action='store_true', help='实际发送推文（默认为测试模式）')
    args = parser.parse_args()
    
    tweeter = AutoTweeter(
        dry_run=not args.no_dry_run,
        is_production=args.prod
    )
    tweeter.run() 