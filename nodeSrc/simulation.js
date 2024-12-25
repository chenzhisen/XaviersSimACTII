const { TweetGenerator } = require('./generation/tweet_generator');
const { DigestGenerator } = require('./generation/digest_generator');
const { AICompletion } = require('./utils/ai_completion');
const { Logger } = require('./utils/logger');
const { Config } = require('./utils/config');

class XavierSimulation {
    constructor(isProduction = false) {
        this.logger = new Logger('simulation');
        this.isProduction = isProduction;

        // 初始化 AI 客户端
        const aiConfig = Config.getAIConfig();
        const client = new AICompletion(null, aiConfig.model);

        // 初始化生成器
        this.tweetGenerator = new TweetGenerator(client, aiConfig.model, isProduction);
        this.digestGenerator = new DigestGenerator(client, aiConfig.model, 12, isProduction);
    }

    async run() {
        try {
            this.logger.info('Starting story generation');

            // 获取当前状态
            const summary = await this.tweetGenerator.getCurrentSummary();
            
            // 生成新的场景
            const tweets = await this.tweetGenerator.generateTweetScene(
                summary.lastDigest,
                summary.currentAge,
                summary.totalTweets
            );

            // 检查是否需要生成摘要
            const digest = await this.digestGenerator.checkAndGenerateDigest(
                tweets,
                summary.currentAge,
                new Date(),
                summary.totalTweets + tweets.length
            );

            this.logger.info('Story generation completed', {
                newTweets: tweets.length,
                hasDigest: !!digest,
                currentAge: summary.currentAge
            });

            return {
                tweets,
                digest,
                currentAge: summary.currentAge
            };

        } catch (error) {
            this.logger.error('Story generation failed', error);
            throw error;
        }
    }
}

module.exports = XavierSimulation; 