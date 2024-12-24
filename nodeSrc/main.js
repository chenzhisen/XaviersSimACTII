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
        const client = ''

        // 初始化生成器
        this.tweetGenerator = new TweetGenerator(client, aiConfig.model, isProduction);
        this.digestGenerator = new DigestGenerator(client, aiConfig.model, 12, isProduction);
        this.techGenerator = new TechEvolutionGenerator(client, aiConfig.model, isProduction);

        // 初始化状态
        this.currentAge = 22.0;
        this.tweetsPerYear = 96;
        this.daysPerTweet = 384 / this.tweetsPerYear;
    }

    async run() {
        try {
            this.logger.info('Starting simulation...');

            // 步骤 1: 获取当前状态
            console.log('Step 1: Getting current state...');
            const [ongoingTweets, tweetsByAge] = await this.tweetGenerator.getOngoingTweets();
            const tweetCount = ongoingTweets.length;
            console.log(`Found ${tweetCount} existing tweets`);

            // 步骤 2: 更新模拟状态
            console.log('Step 2: Updating simulation state...');
            const { currentDate, daysSinceStart } = this._updateSimulationState(ongoingTweets);
            console.log(`Current age: ${this.currentAge.toFixed(2)}, Days since start: ${daysSinceStart}`);

            // 步骤 3: 生成技术进化
            console.log('Step 3: Generating tech evolution...');
            const techEvolution = await this.techGenerator.generateTechEvolution();
            if (!techEvolution) {
                throw new Error('Failed to generate tech evolution');
            }
            console.log('Tech evolution generated successfully');

            // 步骤 4: 检查并生成摘要
            console.log('Step 4: Checking and generating digest...');
            const digest = await this.digestGenerator.checkAndGenerateDigest(
                ongoingTweets,
                this.currentAge,
                currentDate,
                tweetCount,
                techEvolution
            );
            console.log('Digest check completed');

            // 步骤 5: 生成新推文
            console.log('Step 5: Generating new tweet...');
            const tweet = await this.tweetGenerator.generateTweet(
                digest,
                this.currentAge,
                techEvolution,
                tweetCount
            );

            if (!tweet) {
                throw new Error('Failed to generate tweet');
            }
            console.log('New tweet generated');

            // 步骤 6: 保存推文
            console.log('Step 6: Saving tweet...');
            const success = await this.tweetGenerator.saveTweet(tweet);
            if (!success) {
                throw new Error('Failed to save tweet');
            }
            console.log('Tweet saved successfully');

            this.logger.info('Simulation completed successfully', {
                age: this.currentAge,
                tweetCount: tweetCount + 1
            });

            return { tweet, digest, techEvolution };

        } catch (error) {
            this.logger.error('Simulation failed', error);
            console.error('Error details:', {
                step: error.step,
                message: error.message,
                stack: error.stack
            });
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