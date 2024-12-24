const fs = require('fs').promises;
const path = require('path');
const { Config } = require('../utils/config');
const { Logger } = require('../utils/logger');
const { PathUtils } = require('../utils/path_utils');

class GithubOperations {
    constructor(isProduction = false) {
        this.logger = new Logger('github');
        
        // 本地数据目录
        this.localDataDir = path.join('data', isProduction ? 'prod' : 'dev');
    }

    async getFileContent(filePath) {
        try {
            const fullPath = path.join(this.localDataDir, filePath);
            try {
                const content = await fs.readFile(fullPath, 'utf-8');
                return [JSON.parse(content), null];
            } catch (error) {
                if (error.code === 'ENOENT') {
                    return [null, null];
                }
                throw error;
            }
        } catch (error) {
            this.logger.error(`Error reading file ${filePath}`, error);
            throw error;
        }
    }

    async updateFile(filePath, content, message) {
        try {
            const fullPath = path.join(this.localDataDir, filePath);
            await PathUtils.ensureDir(path.dirname(fullPath));
            await fs.writeFile(
                fullPath,
                JSON.stringify(content, null, 2),
                'utf-8'
            );
            this.logger.info(`Updated file ${filePath}: ${message}`);
            return true;
        } catch (error) {
            this.logger.error(`Error updating file ${filePath}`, error);
            return false;
        }
    }

    async addTweet(tweet) {
        const [tweets] = await this.getFileContent('ongoing_tweets.json');
        const updatedTweets = tweets ? [...tweets, tweet] : [tweet];
        return await this.updateFile(
            'ongoing_tweets.json',
            updatedTweets,
            `Add tweet ${tweet.id}`
        );
    }
}

module.exports = { GithubOperations }; 