const { TweetGenerator } = require('./generation/tweet_generator');
const { DigestGenerator } = require('./generation/digest_generator');
const { AICompletion } = require('./utils/ai_completion');
const { Logger } = require('./utils/logger');
const { Config } = require('./utils/config');

class XavierSimulation {
    constructor(isProduction = false) {
        this.logger = new Logger('simulation');
        this.isProduction = isProduction;

        // 初始化生成器
        this.tweetGenerator = new TweetGenerator(null, null, isProduction);
        this.digestGenerator = new DigestGenerator(null, null, 4, isProduction);

        // 运行配置
        this.config = {
            minInterval: 1 * 1000,     // 最小间隔5秒
            maxInterval: 1 * 1000,    // 最大间隔10秒
            isRunning: true
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
                const result = await this.runOnce();
                
                if (result.completed) {
                    this.logger.info('Story has completed');
                    this.stop();
                    break;
                }

                // 随机等待时间
                const waitTime = this._getRandomInterval();
                this.logger.info(`Waiting ${Math.floor(waitTime/1000)}s for next generation`);
                await new Promise(resolve => setTimeout(resolve, waitTime));
            } catch (error) {
                this.logger.error('Error in simulation loop', error);
                // 错误后等待3秒再继续
                await new Promise(resolve => setTimeout(resolve, 3000));
            }
        }
    }

    stop() {
        this.config.isRunning = false;
        this.logger.info('Stopping simulation');
    }

    async runOnce() {
        try {
            // 获取当前状态
            const summary = await this.tweetGenerator.getCurrentSummary();
            
            if (summary.isCompleted) {
                this.logger.info('Story has reached its end');
                return { completed: true };
            }

            // 生成新的推文场景
            const tweets = await this.tweetGenerator.generateTweetScene(
                summary.lastDigest,
                summary.currentAge,
                summary.totalTweets
            );

            // 确保 tweets 是数组
            const tweetsArray = tweets?.data?.new_tweets || [];
            if (!tweetsArray.length) {
                this.logger.warn('No tweets were generated');
                return { completed: false, tweets: [] };
            }

            this.logger.info('Generated new tweets', {
                count: tweetsArray.length,
                currentAge: summary.currentAge
            });

            return {
                completed: false,
                tweets: tweetsArray,
                summary: {
                    currentAge: summary.currentAge,
                    totalTweets: summary.totalTweets + tweetsArray.length
                }
            };
        } catch (error) {
            this.logger.error('Simulation error', error);
            throw error;
        }
    }

    _getRandomInterval() {
        return Math.floor(
            Math.random() * (this.config.maxInterval - this.config.minInterval) 
            + this.config.minInterval
        );
    }

    // 优雅关闭
    async gracefulShutdown() {
        this.logger.info('Graceful shutdown initiated');
        this.stop();
        // 等待当前操作完成
        await new Promise(resolve => setTimeout(resolve, 1000));
        this.logger.info('Simulation shutdown complete');
    }
}

// 处理进程信号
process.on('SIGINT', async () => {
    console.log('\nReceived SIGINT. Graceful shutdown...');
    const simulation = new XavierSimulation();
    await simulation.gracefulShutdown();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\nReceived SIGTERM. Graceful shutdown...');
    const simulation = new XavierSimulation();
    await simulation.gracefulShutdown();
    process.exit(0);
});

// 直接导出类
module.exports = XavierSimulation; 