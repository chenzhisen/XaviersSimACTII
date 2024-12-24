const { Anthropic } = require('@anthropic-ai/sdk');
const { Config } = require('./utils/config');
const { Logger } = require('./utils/logger');
const { TweetGenerator } = require('./generation/tweet_generator');
const { DigestGenerator } = require('./generation/digest_generator');
const { TechEvolutionGenerator } = require('./generation/tech_evolution_generator');
const { AICompletion } = require('./utils/ai_completion');

class XavierSimulation {
    constructor(isProduction = false) {
        this.logger = new Logger('main');
        this.isProduction = isProduction;

        // 输出 AI 配置
        const aiConfig = Config.getAIConfig();
        // console.log('AI Config:', {
        //     apiKey: aiConfig.apiKey ? '***' + aiConfig.apiKey.slice(-4) : 'undefined',
        //     model: aiConfig.model,
        //     baseUrl: aiConfig.baseUrl
        // });

        // 初始化 AI 客户端
        const client = null
        // console.log('AI Client:', client);
        // console.log('AI Client messages:', client.messages);
        // 初始化生成器
        this.tweetGenerator = new TweetGenerator(client, aiConfig.model, isProduction);
        this.digestGenerator = new DigestGenerator(client, aiConfig.model, 12, isProduction);
        this.techGenerator = new TechEvolutionGenerator(client, aiConfig.model, isProduction);

        // 初始化状态
        this.currentAge = 22.0;  // 起始年龄
        this.tweetsPerYear = 96; // 每年推文数
        this.daysPerTweet = 384 / this.tweetsPerYear; // 每条推文间隔天数
    }

    async run() {
        try {
            this.logger.info('Starting simulation...');

            // 获取当前状态
            const [ongoingTweets, tweetsByAge] = await this.tweetGenerator.getOngoingTweets();
            const tweetCount = ongoingTweets.length;

            // 更新模拟状态
            const { currentDate, daysSinceStart } = this._updateSimulationState(ongoingTweets);

            // 生成技术进化
            const techEvolution = await this.techGenerator.generateTechEvolution();
            if (!techEvolution) {
                throw new Error('Failed to generate tech evolution');
            }

            // 检查并生成摘要
            const digest = await this.digestGenerator.checkAndGenerateDigest(
                ongoingTweets,
                this.currentAge,
                currentDate,
                tweetCount,
                techEvolution
            );

            // 生成新推文
            const tweet = await this.tweetGenerator.generateTweet(
                digest,
                this.currentAge,
                techEvolution,
                tweetCount
            );

            if (!tweet) {
                throw new Error('Failed to generate tweet');
            }

            // 保存推文
            const success = await this.tweetGenerator.saveTweet(tweet);
            if (!success) {
                throw new Error('Failed to save tweet');
            }

            this.logger.info('Simulation completed successfully', {
                age: this.currentAge,
                tweetCount: tweetCount + 1
            });

            return { tweet, digest, techEvolution };

        } catch (error) {
            this.logger.error('Simulation failed', error);
            throw error;
        }
    }

    _updateSimulationState(ongoingTweets) {
        const tweetCount = ongoingTweets.length;
        const daysSinceStart = tweetCount * this.daysPerTweet;
        const currentDate = new Date('2025-01-01');
        currentDate.setDate(currentDate.getDate() + daysSinceStart);
        
        this.currentAge = 22.0 + (daysSinceStart / 384);
        
        return { currentDate, daysSinceStart };
    }
}

module.exports = { XavierSimulation }; 