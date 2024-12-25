const fs = require('fs').promises;
const path = require('path');
const moment = require('moment');

class TweetStorage {
    constructor() {
        this.baseDir = path.join(process.cwd(), 'data', 'tweets');
        this.storageFile = path.join(this.baseDir, 'all_tweets.json');
        this.init();
    }

    async init() {
        try {
            await fs.mkdir(this.baseDir, { recursive: true });
            // 初始化存储文件
            if (!await this._fileExists(this.storageFile)) {
                await fs.writeFile(this.storageFile, JSON.stringify({
                    metadata: {
                        created_at: moment().toISOString(),
                        last_updated: moment().toISOString(),
                        total_tweets: 0
                    },
                    tweets: []
                }, null, 2), 'utf8');
            }
        } catch (error) {
            console.error('初始化存储失败:', error);
        }
    }

    async _fileExists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    async saveTweets(tweets, age) {
        try {
            // 读取现有数据
            let data = { tweets: [] };
            try {
                const content = await fs.readFile(this.storageFile, 'utf8');
                data = JSON.parse(content);
            } catch (error) {
                console.log('读取文件失败，使用新的数据结构');
            }

            // 准备新的推文数据
            const timestamp = moment().format('YYYYMMDD_HHmmss');
            const newTweets = tweets.map(tweet => ({
                id: `tweet_${timestamp}_${Math.random().toString(36).substr(2, 9)}`,
                content: tweet,
                age: age,
                created_at: moment().toISOString(),
                metadata: {
                    age: age,
                    timestamp: timestamp
                }
            }));

            // 添加新推文
            data.tweets.push(...newTweets);

            // 更新元数据
            data.metadata = {
                created_at: data.metadata?.created_at || moment().toISOString(),
                last_updated: moment().toISOString(),
                total_tweets: data.tweets.length
            };

            // 保存更新后的数据
            await fs.writeFile(
                this.storageFile,
                JSON.stringify(data, null, 2),
                'utf8'
            );

            console.log(`已保存 ${newTweets.length} 条新推文，总计 ${data.tweets.length} 条`);

            return {
                success: true,
                data: {
                    new_tweets: newTweets,
                    total_tweets: data.tweets.length
                }
            };
        } catch (error) {
            console.error('保存推文失败:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getLatestTweets(age = null, limit = 10) {
        try {
            const content = await fs.readFile(this.storageFile, 'utf8');
            const data = JSON.parse(content);

            let tweets = data.tweets;
            if (age !== null) {
                tweets = tweets.filter(t => t.age === age);
            }

            // 返回最新的 n 条推文
            return tweets.slice(-limit);
        } catch (error) {
            console.error('获取推文失败:', error);
            return [];
        }
    }

    async getTweetsByAge(age) {
        try {
            const content = await fs.readFile(this.storageFile, 'utf8');
            const data = JSON.parse(content);
            return data.tweets.filter(t => t.age === age);
        } catch (error) {
            console.error('获取推文失败:', error);
            return [];
        }
    }

    async getAllTweets() {
        try {
            const content = await fs.readFile(this.storageFile, 'utf8');
            return JSON.parse(content);
        } catch (error) {
            console.error('获取所有推文失败:', error);
            return { tweets: [] };
        }
    }
}

module.exports = new TweetStorage(); 