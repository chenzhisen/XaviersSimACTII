import random

class AutoTweet:
    async def post_next_tweet(self):
        try:
            # 读取待发送的推文
            tweets = await self.read_tweets()
            if not tweets:
                return None

            # 获取第一条推文
            tweet = tweets[0]
            
            # 去掉TWEET前缀
            content = tweet['text']
            if content.startswith('TWEET'):
                content = content.split('\n', 1)[1].strip()
            
            # 根据内容生成相关表情
            random_emoji = self._generate_content_related_emoji(content)
            content = f"{content} {random_emoji}"

            # 发送推文
            result = await self.post_tweet(content)
            if result:
                # 保存发送成功的推文
                await self.save_sent_tweet(result)
                
                # 从待发送列表中移除
                tweets.pop(0)
                await self.save_tweets(tweets)
                
                return result
            
            return None
        except Exception as e:
            self.logger.error(f"Error posting next tweet: {str(e)}")
            return None

    def _generate_content_related_emoji(self, content):
        """根据内容生成相关表情"""
        # 表情主题分类
        emoji_themes = {
            'tech': ['🤖', '💻', '📱', '💡', '🚀', '⚡', '🔧', '🌐', '📊', '🎮'],
            'work': ['💼', '📈', '💪', '🎯', '✨', '📚', '💡', '🔥', '⭐', '🎨'],
            'life': ['😊', '🌟', '🎉', '💫', '🌈', '☕', '🍀', '🌺', '🎵', '🎭'],
            'think': ['🤔', '💭', '🧐', '🎯', '📝', '💡', '🔍', '📚', '💫', '⭐'],
            'happy': ['😄', '🎉', '✨', '🌟', '💫', '🎵', '🌈', '🎨', '🦋', '🌺'],
            'nature': ['🌱', '🌿', '🍃', '🌸', '🌺', '🦋', '🌊', '🌍', '☀️', '🌙'],
            'create': ['🎨', '✨', '💡', '🚀', '🔧', '📝', '💻', '🎮', '🎭', '🌟'],
            'learn': ['📚', '💡', '🎯', '💪', '🤔', '💭', '🔍', '✨', '⭐', '🌟']
        }

        # 关键词映射到主题
        theme_keywords = {
            'tech': ['ai', '人工智能', '技术', '编程', '开发', '项目', '代码', '研究', '创新'],
            'work': ['工作', '会议', '团队', '项目', '公司', '创业', '合作', '效率', '进展'],
            'life': ['生活', '日常', '休息', '放松', '享受', '快乐', '心情', '感受'],
            'think': ['思考', '想法', '计划', '决定', '观点', '发现', '理解', '认为'],
            'happy': ['开心', '高兴', '激动', '兴奋', '期待', '喜欢', '热爱', '享受'],
            'nature': ['自然', '天气', '季节', '风景', '环境', '花', '树', '海'],
            'create': ['创造', '设计', '制作', '开发', '构建', '写作', '艺术', '创意'],
            'learn': ['学习', '研究', '探索', '了解', '知识', '经验', '成长', '提升']
        }

        # 识别内容主题
        content_lower = content.lower()
        matched_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                matched_themes.append(theme)
        
        # 如果没有匹配到主题，使用默认主题
        if not matched_themes:
            matched_themes = ['think', 'life']
        
        # 从匹配的主题中随机选择一个
        selected_theme = random.choice(matched_themes)
        
        # 从选中主题的表情中随机选择1-2个
        num_emojis = random.randint(1, 2)
        selected_emojis = random.sample(emoji_themes[selected_theme], num_emojis)
        
        return ' '.join(selected_emojis) 