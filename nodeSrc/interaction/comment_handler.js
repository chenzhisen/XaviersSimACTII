const { TwitterApi } = require('twitter-api-v2');
const { AICompletion } = require('../utils/ai_completion');
const { Config } = require('../utils/config');
const { Logger } = require('../utils/logger');

class CommentHandler {
    constructor(client, model) {
        this.logger = new Logger('comments');
        this.ai = new AICompletion(client, model);
        
        const twitterConfig = Config.getTwitterConfig();
        this.twitter = new TwitterApi(twitterConfig.bearerToken);

        // 回复配置
        this.replyConfig = {
            maxRepliesPerTweet: 5,    // 每条推文最多回复数
            replyProbability: 0.7,    // 回复概率
            replyDelay: {             // 回复延迟（秒）
                min: 30,
                max: 300
            }
        };
    }

    async handleNewComments() {
        try {
            // 获取最近的推文
            const recentTweets = await this._getRecentTweets();
            
            for (const tweet of recentTweets) {
                // 获取新评论
                const comments = await this._getNewComments(tweet.id);
                
                // 处理每条评论
                for (const comment of comments) {
                    if (this._shouldReply(comment)) {
                        await this._generateAndSendReply(tweet, comment);
                    }
                }
            }
        } catch (error) {
            this.logger.error('Error handling comments', error);
        }
    }

    async _getRecentTweets() {
        // 获取自己最近的推文
        const tweets = await this.twitter.v2.userTimeline(Config.getTwitterConfig().userId, {
            max_results: 10,
            exclude: ['retweets', 'replies']
        });
        return tweets.data;
    }

    async _getNewComments(tweetId) {
        // 获取推文的评论
        const comments = await this.twitter.v2.search(
            `conversation_id:${tweetId} -from:${Config.getTwitterConfig().username}`,
            {
                'tweet.fields': ['author_id', 'created_at', 'text'],
                'user.fields': ['username', 'name'],
                max_results: 100
            }
        );
        return comments.data;
    }

    _shouldReply(comment) {
        // 决定是否回复
        return Math.random() < this.replyConfig.replyProbability &&
               !this._hasReplied(comment.id);
    }

    async _generateAndSendReply(originalTweet, comment) {
        try {
            const prompt = this._buildReplyPrompt(originalTweet, comment);
            
            const response = await this.ai.getCompletion(
                'You are engaging with your Twitter community naturally and authentically.',
                prompt
            );

            // 添加随机延迟
            const delay = Math.floor(
                Math.random() * 
                (this.replyConfig.replyDelay.max - this.replyConfig.replyDelay.min) + 
                this.replyConfig.replyDelay.min
            );
            
            await new Promise(resolve => setTimeout(resolve, delay * 1000));

            // 发送回复
            await this.twitter.v2.reply(
                response.slice(0, 280),
                comment.id
            );

            // 记录已回复
            await this._recordReply(comment.id);

        } catch (error) {
            this.logger.error('Error generating reply', error);
        }
    }

    _buildReplyPrompt(originalTweet, comment) {
        return `Context:
Original Tweet: ${originalTweet.text}
Comment: ${comment.text}

Generate a natural and engaging reply that:
1. Acknowledges the commenter's point
2. Adds value to the discussion
3. Maintains authentic voice
4. Encourages further engagement
5. Keeps a friendly and professional tone

Guidelines:
- Keep it concise (under 280 characters)
- Be authentic and personal
- Show appreciation for engagement
- Add insights when relevant
- Use emojis sparingly
- Maintain the tech founder voice

Write only the reply content, no additional formatting.`;
    }

    async _recordReply(commentId) {
        // 记录已回复的评论
        // 实现存储逻辑...
    }

    _hasReplied(commentId) {
        // 检查是否已回复
        // 实现检查逻辑...
        return false;
    }
}

module.exports = { CommentHandler }; 