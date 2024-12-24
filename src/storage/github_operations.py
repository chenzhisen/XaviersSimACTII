import json
import base64
import requests
from datetime import datetime
from ..utils.config import Config
from github import Github
import re
from ..utils.path_utils import PathUtils
import urllib3
import ssl
import certifi
import time

class GithubOperations:
    def __init__(self, is_production=False):
        """初始化 GitHub 操作
        
        参数:
            is_production: 是否为生产环境
        """
        self.headers = {
            'Authorization': f'token {Config.GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 配置 SSL
        self.session = requests.Session()
        self.session.verify = certifi.where()
        
        # 配置重试
        retry = urllib3.util.Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        
        self.base_url = "https://api.github.com"
        self.repo_owner = Config.GITHUB_OWNER
        self.repo_name = Config.GITHUB_REPO
        
        # Define base directory based on environment
        self.base_dir = "prod" if is_production else "dev"
        self.data_dir = PathUtils.normalize_path("data", self.base_dir)
        PathUtils.ensure_dir(self.data_dir)
        
        # Define file paths
        self.ongoing_tweets_path = "ongoing_tweets.json"
        self.comments_path = "comments.json"
        self.story_digest_path = "digest_history.json"
        self.tech_advances_path = "tech_evolution.json"
        
        # 添加请求限制
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 最小请求间隔（秒）

    def _make_request(self, method, url, **kwargs):
        """发送 HTTP 请求并处理错误
        
        参数:
            method: HTTP 方法 ('get', 'put', 'post', 'delete')
            url: 请求 URL
            **kwargs: 其他请求参数
        """
        try:
            # 确保请求间隔
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last
                print(f"- 等待 {sleep_time:.2f} 秒以避免请求过快...")
                time.sleep(sleep_time)
            
            response = self.session.request(
                method,
                url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )
            self.last_request_time = time.time()
            response.raise_for_status()
            return response
            
        except requests.exceptions.SSLError as e:
            print(f"\n[github_operations.py:60] SSL 错误:")
            print(f"- URL: {url}")
            print(f"- 错误: {str(e)}")
            print("- 尝试使用备用 SSL 配置...")
            
            # 尝试使用不同的 SSL 配置
            try:
                context = ssl.create_default_context(cafile=certifi.where())
                context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
                session = requests.Session()
                session.verify = certifi.where()
                session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
                response = session.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=30,
                    **kwargs
                )
                self.last_request_time = time.time()
                return response
            except Exception as e2:
                print(f"- 备用配置也失败: {str(e2)}")
                time.sleep(5)  # 连续失败后等待更长时间
                raise
                
        except requests.exceptions.RequestException as e:
            print(f"\n[github_operations.py:85] 请求错误:")
            print(f"- URL: {url}")
            print(f"- 方法: {method.upper()}")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"- 响应状态: {e.response.status_code}")
                print(f"- 响应内容: {e.response.text}")
            raise

    def get_file_content(self, file_path):
        """获取文件内容"""
        try:
            # 定义延迟常量
            GET_DELAY = 0.1      # 100ms - 请求前延迟
            PARSE_DELAY = 0.05   # 50ms  - 解析前延迟
            ERROR_DELAY = 0.2    # 200ms - 错误后延迟
            
            time.sleep(GET_DELAY)  # 请求前等待
            
            full_path = PathUtils.normalize_path("data", self.base_dir, file_path)
            url_path = PathUtils.to_url_path(full_path)
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{url_path}"
            
            print(f"\n[github_operations.py:102] 正在请求文件:")
            print(f"- URL: {url}")
            print(f"- 文件路径: {full_path}")
            
            response = self._make_request('get', url)
            content_data = response.json()
            content = base64.b64decode(content_data['content']).decode('utf-8')
            
            try:
                time.sleep(PARSE_DELAY)  # JSON 解析前等待
                parsed_content = json.loads(content)
                print(f"[github_operations.py:111] 成功解析 {file_path}")
                return parsed_content, content_data['sha']
            except json.JSONDecodeError as e:
                print(f"[github_operations.py:114] JSON 解析错误: {str(e)}")
                time.sleep(ERROR_DELAY)  # 解析错误后等待
                return None, None
                
        except Exception as e:
            print(f"[github_operations.py:118] 读取文件错误:")
            print(f"- 文件: {file_path}")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            time.sleep(ERROR_DELAY)  # 请求错误后等待
            return None, None

    def update_file(self, file_path, content, commit_message, sha=None):
        """更新 GitHub 仓库中的文件"""
        try:
            # 定义延迟常量
            UPDATE_DELAY = 0.1      # 100ms - 更新前延迟
            RETRY_DELAY = 0.2       # 200ms - 重试前延迟
            
            time.sleep(UPDATE_DELAY)  # 更新前等待
            
            # 添加基础目录到路径
            full_path = f"data/{self.base_dir}/{file_path}"
            
            # 确保目录存在
            self.ensure_directory_exists(full_path)
            
            # 如果没有提供 SHA，先获取当前文件的 SHA
            if not sha:
                try:
                    current_file = self.get_file_content(file_path)
                    if current_file and len(current_file) == 2:  # 期望格式 (content, sha)
                        _, sha = current_file
                except:
                    time.sleep(RETRY_DELAY)  # 获取 SHA 失败后等待
                    # 文件可能不存在，这是正常的
                    pass
            
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}"
            print(f"\n[github_operations.py:89] 正在更新文件:")
            print(f"- URL: {url}")
            print(f"- 文件路径: {full_path}")
            print(f"- 仓库: {self.repo_owner}/{self.repo_name}")
            print(f"- SHA: {sha}")
            
            # 确保 content 是 JSON 字符串（如果是字典或列表）
            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=2)
            
            # 将内容编码为 base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('utf-8')
            
            data = {
                "message": commit_message,
                "content": content_base64
            }
            
            if sha:
                data["sha"] = sha
            
            print(f"[github_operations.py:109] 请求详情:")
            print(f"- 内容长度: {len(content_bytes)} 字节")
            print(f"- 提交信息: {commit_message}")
            
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"\n[github_operations.py:117] 更新文件失败:")
            print(f"- 文件: {file_path}")
            print(f"- URL: {url}")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            if hasattr(e, 'response') and e.response:
                print(f"- 响应内容: {e.response.text}")
            raise

    def _update_file_with_retry(self, file_path, content, message, sha=None, max_retries=3):
        """Helper method to update a file with retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.update_file(file_path, content, message, sha)
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Attempt {attempt + 1} failed, retrying...")
        return None

    def add_tweet(self, tweet, id=None, tweet_count=None, simulated_date=None, age=None):
        """Add a tweet to ongoing_tweets.json"""
        print(f"Adding tweet: {tweet}")
        try:
            # Handle ongoing tweets
            tweets, sha = self.get_file_content(self.ongoing_tweets_path)
            tweets = tweets or []
            
            # Clean up tweet content if it starts with labels
            if isinstance(tweet, dict) and 'content' in tweet:
                content = tweet['content']
                # Remove labels like "Setback:", "Update:", etc.
                content = re.sub(r'^(Setback|Update|Progress|Status):\s*', '', content)
                tweet['content'] = content
            
            # Add metadata to tweet
            tweet_with_metadata = {
                **tweet,
                "id": id,
                "tweet_count": tweet_count,
                "simulated_date": simulated_date,
                "age": age
            }
            
            # Add tweet if it doesn't already exist
            if not any(existing.get('id') == tweet.get('id') for existing in tweets):
                tweets.append(tweet_with_metadata)
                self._update_file_with_retry(
                    self.ongoing_tweets_path,
                    tweets,
                    f"Add tweet: {tweet.get('id', 'new')}",
                    sha
                )
            print(f"Successfully added tweet: {len(tweets)}")
        except Exception as e:
            print(f"Error saving ongoing tweets: {str(e)}")
            raise

    def add_comments(self, tweet_id, comments):
        all_comments, sha = self.get_file_content(self.comments_path)
        tweet_comments = next((item for item in all_comments if item["tweet_id"] == tweet_id), None)
        if tweet_comments:
            tweet_comments['comments'].extend(comments)
        else:
            all_comments.append({"tweet_id": tweet_id, "comments": comments})
        self.update_file(self.comments_path, all_comments, f"Add comments for tweet: {tweet_id}", sha)

        # Also update the story digest
        story_digest, digest_sha = self.get_file_content(self.story_digest_path)
        for comment in comments:
            story_digest.append({"tweet_id": tweet_id, "comment": comment})
        self.update_file(self.story_digest_path, story_digest, f"Update story digest with comments for tweet: {tweet_id}", digest_sha)

    def update_story_digest(self, new_tweets, new_comments, initial_content=None):
        """Update the story digest with new content"""
        try:
            # Fetch the existing digest history
            history, digest_sha = self.get_file_content(self.story_digest_path)
            if not isinstance(history, list):
                history = []
            
            if initial_content:
                # Add the new digest to history
                history.append(initial_content)
            
            # Store the updated history
            self.update_file(
                file_path=self.story_digest_path,
                content=history,
                commit_message=f"Update digest history with {len(new_tweets)} tweets and {len(new_comments)} comments",
                sha=digest_sha
            )
            print(f"Successfully updated digest history with {len(new_tweets)} tweets and {len(new_comments)} comments")
                
        except Exception as e:
            print(f"Error updating story digest: {str(e)}")
            raise

    def delete_file(self, file_path, commit_message, sha):
        """
        Delete a file from the GitHub repository
        """
        # Add base directory to path if it's not already included
        full_path = f"data/{self.base_dir}/{file_path}"
        
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{full_path}"
        print(f"Deleting file: {url}")
        data = {
            "message": commit_message,
            "sha": sha
        }
        response = requests.delete(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def ensure_directory_exists(self, path):
        """确��目录存在"""
        try:
            print(f"\n[github_operations.py:150] 检查目录是否存在: {path}")
            
            # 分解路径
            parts = path.split('/')
            current_path = ""
            
            for part in parts[:-1]:  # 不包括文件名
                current_path = f"{current_path}/{part}" if current_path else part
                
                try:
                    url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{current_path}"
                    print(f"- 检查路径: {url}")
                    
                    response = self._make_request('get', url)
                    response.raise_for_status()
                    print(f"- 目录已存在: {current_path}")
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        print(f"- 创建目录: {current_path}")
                        # 创建空的 .gitkeep 文件来创建目录
                        content = ""
                        content_bytes = content.encode('utf-8')
                        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
                        
                        data = {
                            "message": f"Create directory: {current_path}",
                            "content": content_base64,
                            "path": f"{current_path}/.gitkeep"
                        }
                        
                        create_url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{current_path}/.gitkeep"
                        response = self._make_request('put', create_url, json=data)
                        response.raise_for_status()
                        print(f"- 成功创建目录: {current_path}")
                    else:
                        raise
                    
        except Exception as e:
            print(f"[github_operations.py:185] 创建目录失败:")
            print(f"- 路径: {path}")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            raise

    def initialize_repository(self):
        """初始化仓库结构和文件"""
        try:
            print("\n[github_operations.py:200] 开始初始化仓库...")
            INIT_DELAY = 0.1        # 100ms
            FILE_INIT_DELAY = 0.1   # 100ms
            ERROR_DELAY = 0.2       # 200ms
            
            time.sleep(INIT_DELAY)  # 初始化前等待
            
            # 初始化文件结构
            initial_files = {
                'ongoing_tweets.json': [],
                'XaviersSim.json': {},
                'life_phases.json': {},
                'tech_evolution.json': {
                    'tech_trees': {},
                    'last_updated': datetime.now().isoformat()
                },
                'digest_history.json': []
            }
            
            for file_name, initial_content in initial_files.items():
                try:
                    print(f"\n- 初始化文件: {file_name}")
                    time.sleep(FILE_INIT_DELAY)  # 每个文件初始化前等待
                    self.update_file(
                        file_name,
                        initial_content,
                        f"Initialize {file_name}"
                    )
                    print(f"- 成功创建: {file_name}")
                except Exception as e:
                    print(f"- 警告: 创建 {file_name} 失败: {str(e)}")
                    time.sleep(ERROR_DELAY)  # 失败后等待
                    continue
                
            print("\n[github_operations.py:225] 仓库初始化完成")
            
        except Exception as e:
            print(f"\n[github_operations.py:228] 仓库初始化失败:")
            print(f"- 错误类型: {type(e).__name__}")
            print(f"- 错误信息: {str(e)}")
            raise

            raise
