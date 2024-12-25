import sys
import os
import time
import json
from datetime import datetime
from twitter_client import TwitterClientV2

# 添加项目根目录到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

class TweetFetcher:
    def __init__(self):
        """初始化推特获取器"""
        self.client = TwitterClientV2()
        self.data_dir = "twitter_data"
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """确保数据保存目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"创建数据目录: {self.data_dir}")

    def _get_timestamp(self):
        """获取当前时间戳字符串"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _get_iso_timestamp(self):
        """获取ISO格式的时间戳"""
        return datetime.now().isoformat()

    def save_tweet_and_replies(self, tweet_data, replies_data):
        """将推特及其回复保存到本地文件
        
        Args:
            tweet_data (dict): 推特数据
            replies_data (list): 回复数据列表
        """
        timestamp = self._get_timestamp()
        tweet_id = tweet_data['id']
        
        # 构建文件名：tweet_ID_时间戳.json
        filename = os.path.join(self.data_dir, f"tweet_{tweet_id}_{timestamp}.json")
        
        # 准备保存的数据，使用更规范的格式
        data = {
            "metadata": {
                "version": "1.0",
                "fetch_time": self._get_iso_timestamp(),
                "tweet_id": tweet_id,
                "reply_count": len(replies_data)
            },
            "tweet": {
                "id": tweet_data['id'],
                "text": tweet_data.get('text', ''),
                "created_at": tweet_data.get('created_at', ''),
                "author_id": tweet_data.get('author_id', ''),
                "raw_data": tweet_data  # 保存完整的原始数据
            },
            "replies": [
                {
                    "id": reply.get('id', ''),
                    "text": reply.get('text', ''),
                    "created_at": reply.get('created_at', ''),
                    "author_id": reply.get('author_id', ''),
                    "in_reply_to_user_id": reply.get('in_reply_to_user_id', ''),
                    "raw_data": reply  # 保存完整的原始数据
                }
                for reply in replies_data
            ]
        }
        
        # 保存到文件，确保JSON格式化
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存推特及回复到文件: {filename}")
        
        # 同时更新最新数据的软链接
        latest_link = os.path.join(self.data_dir, f"latest_tweet_{tweet_id}.json")
        if os.path.exists(latest_link):
            try:
                os.remove(latest_link)
            except Exception:
                pass
        try:
            os.symlink(filename, latest_link)
            print(f"已更新最新数据链接: {latest_link}")
        except Exception as e:
            print(f"创建软链接失败: {e}")

    def fetch_and_save_latest_tweet(self):
        """获取最新推特及其回复并保存"""
        try:
            # 获取最新推特
            latest_tweet = self.client.get_latest_tweet()
            if not latest_tweet:
                print("未找到最新推特")
                return

            tweet_id = latest_tweet['id']
            print(f"\n获取到最新推特，ID: {tweet_id}")
            print(f"推特内容: {latest_tweet.get('text', '无内容')}")

            # 获取推特的回复
            replies = self.client.get_replies(tweet_id)
            replies_data = replies.get('data', []) if replies else []
            
            if replies_data:
                print(f"找到 {len(replies_data)} 条回复")
            else:
                print("未找到回复")

            # 保存推特及回复
            self.save_tweet_and_replies(latest_tweet, replies_data)

        except Exception as e:
            print(f"获取推特时发生错误: {str(e)}")
            # 记录错误到日志文件
            error_log = os.path.join(self.data_dir, "error_log.json")
            try:
                with open(error_log, 'a', encoding='utf-8') as f:
                    error_data = {
                        "timestamp": self._get_iso_timestamp(),
                        "error": str(e)
                    }
                    f.write(json.dumps(error_data, ensure_ascii=False) + "\n")
            except Exception as log_error:
                print(f"记录错误日志失败: {log_error}")

def main():
    """主函数"""
    fetcher = TweetFetcher()
    interval = 3600  # 每小时执行一次
    
    print("启动推特获取器...")
    print(f"数据将保存在目录: {os.path.abspath(fetcher.data_dir)}")
    print(f"获取间隔: {interval} 秒")
    
    while True:
        try:
            print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            print("开始获取最新推特...")
            fetcher.fetch_and_save_latest_tweet()
            
        except Exception as e:
            print(f"发生错误: {str(e)}")
            
        print(f"等待 {interval} 秒后进行下一次获取...")
        time.sleep(interval)

if __name__ == "__main__":
    main() 