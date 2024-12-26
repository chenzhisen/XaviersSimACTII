import json
import os
import time
import re
from twitter_client import TwitterClientV2

class AutoTweeter:
    def __init__(self):
        self.client = TwitterClientV2()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
        data_dir = os.path.join(project_root, 'nodeSrc', 'data')
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        self.tweets_file = os.path.join(data_dir, 'tweets_public.json')
        self.sent_tweets_file = os.path.join(data_dir, 'sent_tweets.json')
        print(f"推文文件路径: {self.tweets_file}")
        print(f"已发送推文文件路径: {self.sent_tweets_file}")
        
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
                print(f"已创建空的已发送推文文件: {self.sent_tweets_file}")
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
                'sent_at': time.strftime('%Y-%m-%d %H:%M:%S')
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
            tweets = self.read_tweets()
            if not tweets:
                print("没有待发送的推文")
                return None

            # 获取第一条推文
            tweet = tweets[0]
            
            # 在推文内容后添加时间戳
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            tweet_content = f"{tweet['content']}\n\n{current_time}"
            
            # 检查是否是重复推文
            if self.is_duplicate_tweet(tweet_content):
                print(f"检测到重复推文，跳过: {tweet_content}")
                tweets.pop(0)
                self.save_tweets(tweets)
                return None

            try:
                # 发送推文
                tweet_id = self.client.post_tweet(tweet_content)
                
                # 如果发送成功（返回推文ID）
                if tweet_id and isinstance(tweet_id, str) and not tweet_id.startswith('Error'):
                    print(f"推文发送成功: {tweet_content}")
                    print(f"推文ID: {tweet_id}")
                    
                    # 保存已发送的推文
                    tweet['content'] = tweet_content  # 更新为带时间戳的内容
                    self.save_sent_tweet(tweet, tweet_id)
                    
                    # 从数组中删除第一条推文
                    tweets.pop(0)
                    
                    # 保存更新后的推文数组
                    if self.save_tweets(tweets):
                        print(f"剩余待发送推文数量: {len(tweets)}")
                        return {'id': tweet_id}
                    else:
                        print("保存更新后的推文数组失败")
                        return None
                
                # 如果是错误信息
                elif isinstance(tweet_id, str) and ('Error' in tweet_id or '403' in tweet_id):
                    print(f"发送失败: {tweet_id}")
                    if 'duplicate content' in tweet_id.lower():
                        print("检测到重复推文，删除并继续")
                        tweets.pop(0)
                        self.save_tweets(tweets)
                    return None
                
                print(f"未知的返回结果: {tweet_id}")
                return None
                
            except Exception as e:
                print(f"发送推文时出错: {str(e)}")
                if str(e).startswith('403'):
                    print("检测到重复推文错误，删除并继续")
                    tweets.pop(0)
                    self.save_tweets(tweets)
                return None

        except Exception as e:
            print(f"处理推文时出错: {str(e)}")
            return None

    def run(self, interval_seconds=300):  # 默认5分钟发送一次
        print(f"自动发推程序启动，间隔 {interval_seconds} 秒")
        while True:
            try:
                result = self.post_next_tweet()
                if result:
                    print(f"等待 {interval_seconds} 秒后发送下一条...")
                else:
                    print(f"没有新推文或发送失败，等待 {interval_seconds} 秒后重试...")
                
                time.sleep(interval_seconds)
            except Exception as e:
                print(f"运行出错: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟

    def _clean_tweet_content(self, tweet):
        """清理推文内容，去除前缀和时间戳"""
        # 获取推文内容
        text = tweet.get('content', '')
        
        # 去除TWEET数字前缀
        text = re.sub(r'^TWEET\d+\n', '', text)
        
        # 去除可能的时间戳格式
        time_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\d{2}:\d{2}',        # HH:MM
            r'上午|下午|晚上|凌晨',    # 时间段
            r'今天|明天|后天',        # 相对日期
            r'\d+天后',             # X天后
            r'\d+月\d+日',          # MM月DD日
            r'\d+年\d+月\d+日'      # YYYY年MM月DD日
        ]
        
        # 去除每个时间模式
        for pattern in time_patterns:
            text = re.sub(pattern, '', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

if __name__ == "__main__":
    tweeter = AutoTweeter()
    tweeter.run() 