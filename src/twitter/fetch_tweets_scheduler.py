import sys
import os
import time
import json
from datetime import datetime

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from src.twitter.twitter_client import TwitterClientV2

class TweetFetcher:
    def __init__(self):
        """初始化推特获取器"""
        self.client = TwitterClientV2()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        data_dir = os.path.join(project_root, 'nodeSrc', 'data')
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        self.sent_tweets_file = os.path.join(data_dir, 'sent_tweets.json')
        self.replies_file = os.path.join(data_dir, 'tweet_replies.json')
        print(f"已发送推文文件路径: {self.sent_tweets_file}")
        print(f"推文回复文件路径: {self.replies_file}")

    def get_latest_tweet_id(self):
        """获取最后一条推文的ID和完整信息"""
        try:
            if not os.path.exists(self.sent_tweets_file):
                print(f"已发送推文文件不存在: {self.sent_tweets_file}")
                return None, None

            with open(self.sent_tweets_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    print("已发送推文文件为空")
                    return None, None
                
                sent_tweets = json.loads(content)
                if not sent_tweets:
                    print("没有已发送的推文")
                    return None, None
                
                latest_tweet = sent_tweets[-1]
                return latest_tweet.get('id'), latest_tweet
        except Exception as e:
            print(f"获取最后一条推文ID时出错: {str(e)}")
            return None, None

    def save_replies(self, tweet_id, tweet_data, replies):
        """保存推文和回复"""
        try:
            # 读取现有数据
            existing_data = {}
            if os.path.exists(self.replies_file):
                try:
                    with open(self.replies_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            existing_data = json.loads(content)
                except:
                    pass

            # 更新推文数据
            if tweet_id not in existing_data:
                existing_data[tweet_id] = {
                    'tweet': {
                        'id': tweet_data.get('id'),
                        'content': tweet_data.get('content'),
                        'original_id': tweet_data.get('original_id'),
                        'sent_at': tweet_data.get('sent_at'),
                        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
                    },
                    'replies': []
                }
            
            # 添加新回复，避免重复
            existing_ids = {r['id'] for r in existing_data[tweet_id]['replies']}
            for reply in replies:
                if reply['id'] not in existing_ids:
                    reply_data = {
                        'id': reply['id'],
                        'author_id': reply.get('author_id'),
                        'content': reply.get('text'),
                        'created_at': reply.get('created_at'),
                        'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    existing_data[tweet_id]['replies'].append(reply_data)

            # 使用临时文件保存
            temp_file = self.replies_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            # 重命名临时文件
            if os.path.exists(self.replies_file):
                os.replace(temp_file, self.replies_file)
            else:
                os.rename(temp_file, self.replies_file)
            
            print(f"已保存推文 {tweet_id} 及其回复，共 {len(existing_data[tweet_id]['replies'])} 条回复")
            return True
        except Exception as e:
            print(f"保存推文和回复时出错: {str(e)}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False

    def fetch_and_save_replies(self):
        """获取并保存最新推文的回复"""
        try:
            # 获取最新推文ID和完整信息
            tweet_id, latest_tweet = self.get_latest_tweet_id()
            if not tweet_id or not latest_tweet:
                print("无法获取最新推文信息")
                return False

            # 获取回复
            print(f"正在获取推文 {tweet_id} 的回复...")
            replies_response = self.client.get_replies(tweet_id)
            
            if not replies_response or 'data' not in replies_response:
                print("没有找到新的回复")
                return False

            # 获取回复数据
            replies = replies_response.get('data', [])
            if not replies:
                print("没有找到新的回复")
                return False

            print(f"找到 {len(replies)} 条回复")
            
            # 保存推文和回复
            return self.save_replies(tweet_id, latest_tweet, replies)

        except Exception as e:
            print(f"获取和保存回复时出错: {str(e)}")
            return False

    def run(self, interval_seconds=300):  # 默认5分钟获取一次
        print(f"推文回复获取程序启动，间隔 {interval_seconds} 秒")
        while True:
            try:
                if self.fetch_and_save_replies():
                    print(f"等待 {interval_seconds} 秒后获取下一批回复...")
                else:
                    print(f"没有新回复或获取失败，等待 {interval_seconds} 秒后重试...")
                
                time.sleep(interval_seconds)
            except Exception as e:
                print(f"运行出错: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟

if __name__ == "__main__":
    fetcher = TweetFetcher()
    fetcher.run() 