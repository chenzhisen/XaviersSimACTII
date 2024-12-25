const { AICompletion } = require('../utils/ai_completion');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');

class DigestGenerator {
    constructor(client, model, digestInterval = 48, isProduction = false) {
        this.logger = new Logger('digest');
        this.ai = new AICompletion(client, model);
        this.digestInterval = digestInterval;
        this.isProduction = isProduction;

        // 文件路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };
    }

    async checkAndGenerateDigest(newTweets, currentAge, timestamp, totalTweets) {
        // 检查是否需要生成摘要
        if (totalTweets % this.digestInterval !== 0) {
            return null;
        }

        try {
            // 获取最近的推文
            const recentTweets = await this._getRecentTweets();
            
            // 生成摘要
            const digest = await this._generateDigest(recentTweets, currentAge);
            
            // 保存摘要
            await this._saveDigest(digest, currentAge, timestamp);

            return digest;
        } catch (error) {
            this.logger.error('Error generating digest', error);
            throw error;
        }
    }

    async _getRecentTweets() {
        const data = await fs.readFile(this.paths.mainFile, 'utf8');
        const storyData = JSON.parse(data);
        return storyData.story.tweets.slice(-this.digestInterval);
    }

    async _generateDigest(tweets, currentAge) {
        const prompt = this._buildDigestPrompt(tweets, currentAge);
        
        const response = await this.ai.getCompletion(
            'You are summarizing a period of life story.',
            prompt
        );

        return {
            content: response,
            timestamp: new Date().toISOString(),
            age: currentAge,
            tweetCount: tweets.length
        };
    }

    _buildDigestPrompt(tweets, currentAge) {
        return `Life Period Summary:
Age: ${currentAge}
Recent Events:
${tweets.map(t => t.text).join('\n')}

Create a concise summary that:
1. Captures key developments and changes
2. Highlights personal and professional growth
3. Notes significant relationships and events
4. Identifies emerging patterns and themes
5. Sets up future expectations

Guidelines:
- Focus on character development
- Include both achievements and challenges
- Note emotional and psychological growth
- Maintain story continuity
- Keep under 500 words

Write a natural, engaging summary that captures this period of life.`;
    }

    async _saveDigest(digest, currentAge, timestamp) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 添加新摘要到 story.digests
            storyData.story.digests.push({
                ...digest,
                age: currentAge,
                timestamp
            });

            // 更新统计信息
            storyData.stats.digestCount = storyData.story.digests.length;

            // 保存更新
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved new digest', {
                age: currentAge,
                timestamp
            });
        } catch (error) {
            this.logger.error('Error saving digest', error);
            throw error;
        }
    }
}

module.exports = { DigestGenerator }; 