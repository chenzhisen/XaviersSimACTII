const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class DigestGenerator {
    constructor(client, model, tweetsPerDigest = 12, isProduction = false) {
        this.logger = new Logger('digest');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 配置
        this.tweetsPerDigest = tweetsPerDigest;
        this.significantEventThreshold = 3;
    }

    async checkAndGenerateDigest(tweets, currentAge, currentDate, tweetCount, techEvolution) {
        try {
            const [currentDigest, sha] = await this.githubOps.getFileContent('digest.json');
            
            // 检查是否需要更新
            if (!this._shouldUpdateDigest(tweets, currentDigest)) {
                return currentDigest;
            }

            // 生成新的摘要
            const newDigest = await this._generateDigest(
                tweets,
                currentAge,
                currentDate,
                tweetCount,
                techEvolution
            );

            // 保存新摘要
            await this.githubOps.updateFile(
                'digest.json',
                newDigest,
                `Update digest at age ${currentAge.toFixed(1)}`
            );

            return newDigest;

        } catch (error) {
            this.logger.error('Error generating digest', error);
            throw error;
        }
    }

    _shouldUpdateDigest(tweets, currentDigest) {
        if (!currentDigest) return true;
        if (!tweets || tweets.length === 0) return false;

        const newTweetCount = tweets.length - (currentDigest.last_tweet_count || 0);
        if (newTweetCount >= this.tweetsPerDigest) return true;

        // 检查重要事件
        const significantEvents = this._countSignificantEvents(
            tweets.slice(-newTweetCount)
        );
        return significantEvents >= this.significantEventThreshold;
    }

    async _generateDigest(tweets, currentAge, currentDate, tweetCount, techEvolution) {
        const recentTweets = tweets.slice(-this.tweetsPerDigest);
        const prompt = this._buildPrompt(recentTweets, currentAge, currentDate, techEvolution);

        const response = await this.ai.getCompletion(
            'You are a story analysis system.',
            prompt
        );

        return {
            content: response,
            age: currentAge,
            date: currentDate.toISOString(),
            last_tweet_count: tweetCount,
            tech_state: techEvolution
        };
    }

    _buildPrompt(tweets, currentAge, currentDate, techEvolution) {
        return `Current story progress:
Age: ${currentAge}
Year: ${currentDate.getFullYear()}

Recent story developments:
${tweets.map(t => t.text).join('\n')}

Technology context:
${JSON.stringify(techEvolution, null, 2)}

Analyze the recent story developments and create a narrative digest that includes:
1. Story Summary: Key events and developments in Xavier's journey
2. Character Development: How Xavier is growing and changing
3. Relationships: Important connections and interactions
4. Technology Integration: How tech advances affect the story
5. Themes & Motifs: Recurring ideas and symbols
6. Future Setup: Potential story directions and upcoming developments

Format as a clear narrative structure that maintains story continuity.`;
    }

    _countSignificantEvents(tweets) {
        // 简单实现：包含特定关键词的推文数量
        const significantKeywords = [
            'announcement', 'breakthrough', 'discovery',
            'launch', 'milestone', 'partnership',
            'achievement', 'major', 'significant'
        ];

        return tweets.filter(tweet => 
            significantKeywords.some(keyword => 
                tweet.text.toLowerCase().includes(keyword)
            )
        ).length;
    }
}

module.exports = { DigestGenerator }; 