const { TweetGenerator } = require('./generation/tweet_generator');
const { DigestGenerator } = require('./generation/digest_generator');
const { AICompletion } = require('./utils/ai_completion');
const { Logger } = require('./utils/logger');
const { Config } = require('./utils/config');
const path = require('path');
const fs = require('fs');
const fsPromises = require('fs/promises');

class XavierSimulation {
    constructor(isProduction = false) {
        console.log('XavierSimulation constructor',isProduction);
        this.logger = new Logger('simulation');
        this.isProduction = isProduction;
        this.envDir = isProduction ? 'prod' : 'dev';
        this.dataDir = path.join(__dirname, 'data', this.envDir);
        
        // 确保目录存在
        if (!fs.existsSync(this.dataDir)) {
            fs.mkdirSync(this.dataDir, { recursive: true });
        }

        // 初始化生成器，不传入客户端，让 AICompletion 自己初始化
        this.tweetGenerator = new TweetGenerator(null, null, isProduction);
        console.log("isProduction isProductionisProductionisProduction",isProduction);
        this.digestGenerator = new DigestGenerator(null, null, 4, {isProduction:isProduction});

        // 运行配置
        this.config = {
            minInterval: 1 * 1000,    // 最小间隔1秒
            maxInterval: 2 * 1000,    // 最大间隔2秒
            maxTweetsPerDay: 4800,    // 每天最大推文数
            tweetsPerScene: 4,        // 每个场景4条推文
            scenesPerBatch: 1,        // 1个场景
            isRunning: false
        };

        // 加载故事配置
        this.storyConfig = require('./data/Introduction.json').story;
    }

    async saveTweetsToPublic(tweets) {
        try {
            // 保存到tweets_public.json（覆盖方式）
            const publicFilePath = path.join(this.dataDir, 'tweets_public.json');
            
            // 直接写入新数据（覆盖）
            fs.writeFileSync(publicFilePath, JSON.stringify(tweets, null, 2));
            
            console.log('Successfully saved tweets to public file (overwrite mode)');
        } catch (error) {
            console.error('Error saving tweets to public:', error);
            throw error;
        }
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
                await new Promise(resolve => setTimeout(resolve, 3000)); // 错误后等待30秒
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
       //     console.log('summary',summary);
            // 检查是否完成
            if (summary.isCompleted || summary.currentAge >= this.storyConfig.setting.endAge) {
                this.logger.info('Story has completed', {
                    finalAge: summary.currentAge,
                    totalTweets: summary.totalTweets,
                    endAge: this.storyConfig.setting.endAge
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

            // 检查剩余推文数量是否足够一个完整批次
            const remainingTweets = this.config.maxTweetsPerDay - (summary.totalTweets % this.config.maxTweetsPerDay);
            if (remainingTweets < this.config.tweetsPerScene * this.config.scenesPerBatch) {
                this.logger.info('Not enough remaining tweets for a full batch', {
                    remainingTweets,
                    requiredTweets: this.config.tweetsPerScene * this.config.scenesPerBatch
                });
                await new Promise(resolve => setTimeout(resolve, this._getTimeToNextDay()));
                return;
            }

            // 生成固定数量的场景（3个场景，共12条推文）
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

            // 将所有生成的推文保存到tweets_public.json
            const publicTweets = allTweets.map(tweet => ({
                id: tweet.id || `tweet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                content: (tweet.text || tweet.content).replace(/^TWEET[1-4]\n/, ''),
                created_at: tweet.timestamp || new Date().toISOString(),
                age: tweet.age || Number(summary.currentAge.toFixed(2))
            }));

            // 直接保存新推文（覆盖模式）
            await this.saveTweetsToPublic(publicTweets);

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
            console.log("10s后继续");
            await new Promise(resolve => setTimeout(resolve, 10*1000));
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