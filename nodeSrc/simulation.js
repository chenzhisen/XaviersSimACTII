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
        this.digestGenerator = new DigestGenerator(client, aiConfig.model, 4, isProduction);

        // 运行配置
        this.config = {
            minInterval: 5 * 1000,    // 最小间隔5秒
            maxInterval: 10 * 1000,   // 最大间隔10秒
            maxTweetsPerDay: 48,      // 每天最大推文数
            tweetsPerScene: 4,        // 每个场景4条推文
            scenesPerBatch: 3,        // 每批3个场景
            isRunning: false
        };
    }

    async start() {
        if (this.config.isRunning) {
            this.logger.warn('Simulation is already running');
            return;
        }

        this.config.isRunning = true;
        this.logger.info('Starting continuous simulation');

        while (this.config.isRunning) {
            try {
                await this.runOnce();
                
                // 随机等待时间
                const waitTime = this._getRandomInterval();
                this.logger.info(`Waiting ${Math.floor(waitTime/1000)}s for next generation`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            } catch (error) {
                this.logger.error('Error in simulation loop', error);
                await new Promise(resolve => setTimeout(resolve, 30000)); // 错误后等待30秒
            }
        }
    }

    stop() {
        this.config.isRunning = false;
        this.logger.info('Stopping simulation');
    }

    async runOnce() {
        try {
            this.logger.info('Starting story generation');

            // 获取当前状态
            const summary = await this.tweetGenerator.getCurrentSummary();
            
            // 检查是否已完成
            if (summary.isCompleted) {
                this.logger.info('Story has completed', {
                    finalAge: summary.currentAge,
                    totalTweets: summary.totalTweets
                });
                this.stop();
                return null;
            }

            // 检查每日限额
            if (!this._checkDailyLimit(summary.totalTweets)) {
                this.logger.info('Daily tweet limit reached, waiting for next day');
                await new Promise(resolve => setTimeout(resolve, this._getTimeToNextDay()));
                return;
            }

            // 生成多个场景
            let allTweets = [];
            for (let i = 0; i < this.config.scenesPerBatch; i++) {
                const tweets = await this.tweetGenerator.generateTweetScene(
                    summary.lastDigest,
                    summary.currentAge,
                    summary.totalTweets + allTweets.length
                );
                allTweets = [...allTweets, ...tweets];

                // 短暂暂停，避免生成太快
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            // 检查是否需要生成摘要
            const digest = await this.digestGenerator.checkAndGenerateDigest(
                allTweets,
                summary.currentAge,
                new Date(),
                summary.totalTweets + allTweets.length
            );

            this.logger.info('Story generation completed', {
                newTweets: allTweets.length,
                hasDigest: !!digest,
                currentAge: summary.currentAge
            });

            return {
                tweets: allTweets,
                digest,
                currentAge: summary.currentAge
            };

        } catch (error) {
            this.logger.error('Story generation failed', error);
            throw error;
        }
    }

    _getRandomInterval() {
        return Math.floor(
            Math.random() * (this.config.maxInterval - this.config.minInterval) 
            + this.config.minInterval
        );
    }

    _checkDailyLimit(totalTweets) {
        const today = new Date().toISOString().split('T')[0];
        const dayStart = new Date(today).getTime();
        const tweetsToday = totalTweets % this.config.maxTweetsPerDay;
        return tweetsToday < this.config.maxTweetsPerDay;
    }

    _getTimeToNextDay() {
        const now = new Date();
        const tomorrow = new Date(now);
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        return tomorrow.getTime() - now.getTime();
    }
}

module.exports = XavierSimulation; 