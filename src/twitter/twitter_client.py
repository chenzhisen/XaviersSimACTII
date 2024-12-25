from requests_oauthlib import OAuth1Session
import os
import json
import sys

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

from src.utils.config import Config
import requests
from time import sleep
import time

class TwitterClientV2:
    def __init__(self):
        # 使用环境变量初始化 API 客户端
        self.consumer_key = Config.TWITTER_API_KEY
        self.consumer_secret = Config.TWITTER_API_SECRET
        self.access_token = Config.TWITTER_ACCESS_TOKEN
        self.access_token_secret = Config.TWITTER_ACCESS_TOKEN_SECRET
        self.bearer_token = Config.TWITTER_BEARER_TOKEN

        # 打印认证信息（调试用）
        print(f"Consumer Key: {self.consumer_key}")
        print(f"Consumer Secret: {self.consumer_secret}")
        print(f"Access Token: {self.access_token}")
        print(f"Access Token Secret: {self.access_token_secret}")

    def post_tweet(self, text):
        """发布推文
        
        Args:
            text (str): 推文内容
            
        Returns:
            str: 成功时返回推文ID，失败时返回None
        """
        payload = {"text": text}

        # 创建 OAuth1 会话
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # 发送请求
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
        )

        if response.status_code != 201:
            print(f"发推文失败: {response.status_code} {response.text}")
            return None

        # 解析并打印响应
        json_response = response.json()
        tweet_id = json_response.get("data", {}).get("id")
        print(f"推文已发布: {tweet_id}")
        return tweet_id

    def reply_to_tweet(self, text, tweet_id):
        """回复推文
        
        Args:
            text (str): 回复内容
            tweet_id (str): 要回复的推文ID
            
        Returns:
            str: 成功时返回回复的ID，失败时返回None
        """
        payload = {
            "text": text,
            "reply": {
                "in_reply_to_tweet_id": tweet_id
            }
        }

        # 创建 OAuth1 会话
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # 发送请求
        response = oauth.post(
            "https://api.twitter.com/2/tweets",
            json=payload,
        )

        if response.status_code != 201:
            print(f"回复失败: {response.status_code} {response.text}: {payload} ")
            return None

        # 解析并打印响应
        json_response = response.json()
        reply_id = json_response.get("data", {}).get("id")
        print(f"回复已发布: {reply_id}")
        return reply_id

    def get_replies(self, tweet_id):
        """获取推文的回复
        
        Args:
            tweet_id (str): 推文ID
            
        Returns:
            dict: 包含回复数据的字典，失败时返回None
        """
        # 构建查询参数
        query_params = {
            'query': f'conversation_id:{tweet_id}',
            'tweet.fields': 'in_reply_to_user_id,author_id,created_at,conversation_id'
        }
        print(f"查询参数: {query_params}")

        # 发送请求
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            headers=headers,
            params=query_params
        )
        
        if response.status_code != 200:
            raise Exception(f"请求失败: {response.status_code} {response.text}")
        
        return response.json()

    def get_user_tweets(self):
        """获取当前用户的所有推文
        
        Returns:
            list: 推文列表，失败时返回None
        """
        # 创建 OAuth1 会话
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        # 首先获取用户ID
        response = oauth.get("https://api.twitter.com/2/users/me")
        if response.status_code != 200:
            print(f"获取用户信息失败: {response.status_code} {response.text}")
            return None
            
        user_id = response.json()['data']['id']
        print(f"\n=== 用户信息 ===")
        print(f"用户ID: {user_id}")
     
        # 获取用户的推文
        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"  # 使用f-string正确格式化URL
        response = oauth.get(
            tweets_url,
            params={
                "max_results": 100,  # 每次请求最大数量
                "tweet.fields": "created_at,author_id"  # 添加更多字段
            }
        )

        print("\n=== API请求信息 ===")
        print(f"请求URL: {response.url}")
   
        if response.status_code != 200:
            print(f"获取推文失败: {response.status_code} {response.text}")
            return None

        print("\n=== 响应数据 ===")
        response_json = response.json()
        print(json.dumps(response_json, ensure_ascii=False, indent=2))
     
        if 'data' in response_json:
            print(f"\n找到 {len(response_json['data'])} 条推文")
            for i, tweet in enumerate(response_json['data'], 1):
                print(f"\n推文 {i}:")
                print(f"ID: {tweet.get('id', 'N/A')}")
                print(f"内容: {tweet.get('text', 'N/A')}")
                print(f"创建时间: {tweet.get('created_at', 'N/A')}")
                print("-" * 30)
        else:
            print("未找到推文数据")

        return response_json.get('data', [])

    def delete_tweet(self, tweet_id):
        """删除推文
        
        Args:
            tweet_id (str): 要删除的推文ID
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
        )

        response = oauth.delete(f"https://api.twitter.com/2/tweets/{tweet_id}")

        if response.status_code != 200:
            print(f"删除推文 {tweet_id} 失败: {response.status_code} {response.text}")
            return False

        print(f"成功删除推文: {tweet_id}")
        return True

    def delete_all_tweets(self):
        """删除所有推文（考虑基本版的速率限制）"""
        tweets = self.get_user_tweets()
        if not tweets:
            print("未找到推文或获取推文失败")
            return

        batch_size = 5  # 基本版：每15分钟5个请求
        for i in range(0, len(tweets), batch_size):
            batch = tweets[i:i + batch_size]
            print(f"\n处理第 {i//batch_size + 1} 批共 {(len(tweets) + batch_size - 1)//batch_size} 批")
            
            for tweet in batch:
                success = self.delete_tweet(tweet['id'])
                if success:
                    print(f"已删除推文 {tweet['id']}: {tweet.get('text', '')[:50]}...")
                else:
                    print(f"删除推文 {tweet['id']} 失败")
                time.sleep(2)  # 同一批次内的删除操作之间添加小延迟
            
            if i + batch_size < len(tweets):
                wait_time = 15 * 60  # 15分钟，单位为秒
                print(f"\n等待 {wait_time} 秒以重置速率限制...")
                time.sleep(wait_time)

    def get_latest_tweet(self):
        """获取当前用户的最新推文"""
        tweets = self.get_user_tweets()
        if not tweets:
            print("未找到推文或获取推文失败")
            return None

        # 返回最新的推文（数组第一个元素）
        return tweets[0]  # Twitter API返回的推文是按时间倒序排列的


# 示例用法
def main():
    twitter_client = TwitterClientV2()

    # 步骤1：发布推文
    tweet_id = twitter_client.post_tweet("这是一条测试推文 1 来自 XaviersSimACTII.")
    if not tweet_id:
        print("发布推文失败")
        return
    sleep(2)

    # 步骤2：回复推文
    reply_id = twitter_client.reply_to_tweet("这是对测试推文 1 的回复。", tweet_id)
    if not reply_id:
        print("发布回复失败")
        return
    sleep(2)

    # 获取第一条回复的ID
    first_reply_id = reply_id
    print(f"回复第一条回复: {first_reply_id}")
    twitter_client.reply_to_tweet("这是对评论的回复。", first_reply_id)

    # 步骤3：获取推文的回复
    replies = twitter_client.get_replies(reply_id)
    if not replies:
        print("未找到回复")
        return

    sleep(2)
    # 步骤4：回复特定评论
    if replies:
        first_reply_id = replies[0]['id']
        print(f"回复第一条回复: {first_reply_id}")
        twitter_client.reply_to_tweet("这是对评论的回复。", first_reply_id)

if __name__ == "__main__":
    main()