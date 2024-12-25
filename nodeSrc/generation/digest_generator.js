const { AICompletion } = require('../utils/ai_completion');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');
const chalk = require('chalk');

class DigestGenerator {
    constructor(client, model, digestInterval = 4, options = {}) {
        this.logger = new Logger('digest');
        this.ai = new AICompletion(client, model, options);
        this.digestInterval = digestInterval;
        this.isProduction = options.isProduction || false;

        // 文件路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };

        // 本地摘要模板
        this.digestTemplates = {
            early_career: [
                `在这段时间里，Xavier展现出了典型的创业初期特征。他专注于技术开发，不断挑战自我。与此同时，他也在学习平衡工作与生活，建立重要的人际关系。Debug猫的出现为他的创业生活增添了一份意外的惊喜，也象征着好运的开始。

这个阶段的关键发展包括：
1. 技术突破：成功解决了关键性能问题
2. 团队建设：开始组建核心团队
3. 个人成长：学会在压力下保持乐观
4. 人际关系：深化了重要的友情纽带

展望未来，Xavier需要继续保持这种积极的态度，同时更多关注团队建设和产品市场适配性。他的故事正在朝着一个有趣的方向发展。`,

                `这段时期是Xavier创业旅程的重要起点。他展现出了技术专家和创业者的双重特质，在解决技术难题的同时，也在探索创业之路。重要的是，他没有忘记生活中的其他方面，特别是与朋友们的珍贵情谊。

主要进展：
1. 产品开发：取得重要技术突破
2. 创业准备：初步建立团队框架
3. 生活平衡：保持工作与生活的平衡
4. 情感支持：维系重要的友情关系

未来展望：随着项目的推进，Xavier将面临更多挑战，但他已经展现出应对这些挑战的潜力。`
            ]
        };
    }

    async checkAndGenerateDigest(newTweets, currentAge, timestamp, totalTweets) {
        try {
            console.log(chalk.blue('Checking digest generation:', {
                totalTweets,
                interval: this.digestInterval
            }));

            // 获取最近的推文
            const recentTweets = await this._getRecentTweets();
            
            // 确保 recentTweets 是数组
            const validTweets = Array.isArray(recentTweets) ? recentTweets : [];
            
            // 生成摘要
            let digest;
            if (this.ai.options.useLocalSimulation) {
                console.log(chalk.yellow('Using local digest template'));
                digest = this._getLocalDigest(currentAge);
            } else {
                console.log(chalk.blue('Generating AI digest'));
                digest = await this._generateAIDigest(validTweets, currentAge);
            }

            // 保存摘要
            if (digest) {
                await this._saveDigest(digest, currentAge, timestamp);
                console.log(chalk.green('Digest generated and saved:', {
                    age: currentAge,
                    tweetCount: validTweets.length
                }));
            }

            return digest;
        } catch (error) {
            console.log(chalk.red('Error in digest generation:', error));
            throw error;
        }
    }

    async _getRecentTweets() {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
            return storyData.story?.tweets?.slice(-this.digestInterval) || [];
        } catch (error) {
            this.logger.error('Error getting recent tweets', error);
            return [];
        }
    }

    _getLocalDigest(currentAge) {
        // 选择合适的摘要模板
        const phase = this._getPhase(currentAge);
        const templates = this.digestTemplates[phase] || this.digestTemplates.early_career;
        const template = templates[Math.floor(Math.random() * templates.length)];

        return {
            content: template,
            timestamp: new Date().toISOString(),
            age: Number(currentAge.toFixed(2)),
            tweetCount: this.digestInterval
        };
    }

    async _generateAIDigest(tweets, currentAge) {
        try {
            const prompt = this._buildDigestPrompt(tweets, currentAge);
            const response = await this.ai.getCompletion(
                'You are crafting a story digest summarizing recent events.',
                prompt
            );

            return {
                content: response[0].text,
                timestamp: new Date().toISOString(),
                age: Number(currentAge.toFixed(2)),
                tweetCount: tweets.length
            };
        } catch (error) {
            console.log(chalk.red('Error generating AI digest:', error));
            console.log(chalk.yellow('Falling back to local digest template'));
            return this._getLocalDigest(currentAge);
        }
    }

    _calculateAge(totalTweets) {
        const tweetsPerYear = 48; // 每年48条推文
        const yearsPassed = totalTweets / tweetsPerYear;
        const startAge = 22;
        return Number((startAge + yearsPassed).toFixed(2));
    }

    _getPhase(age) {
        if (age < 32) return 'early_career';
        if (age < 42) return 'growth_phase';
        if (age < 52) return 'peak_phase';
        if (age < 62) return 'mature_phase';
        return 'wisdom_phase';
    }

    async _saveDigest(digest, currentAge, timestamp) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 添加新摘要到 story.digests
            storyData.story.digests.push({
                ...digest,
                age: Number(currentAge.toFixed(2)),
                timestamp
            });

            // 更新统计信息和年龄
            storyData.stats.digestCount = storyData.story.digests.length;
            storyData.metadata.currentAge = Number(currentAge.toFixed(2));

            // 保存更新
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved new digest', {
                age: Number(currentAge.toFixed(2)),
                timestamp
            });
        } catch (error) {
            this.logger.error('Error saving digest', error);
            throw error;
        }
    }
}

module.exports = { DigestGenerator }; 