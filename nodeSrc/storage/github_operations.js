const { Octokit } = require('@octokit/rest');
const { Config } = require('../utils/config');
const { Logger } = require('../utils/logger');

class GithubOperations {
    constructor(isProduction = false) {
        this.logger = new Logger('github');
        const config = Config.getStorageConfig();
        
        this.octokit = new Octokit({
            auth: config.githubToken
        });
        
        this.owner = config.githubOwner;
        this.repo = config.githubRepo;
        this.branch = isProduction ? 'main' : 'development';
    }

    async getFileContent(path) {
        try {
            const response = await this.octokit.repos.getContent({
                owner: this.owner,
                repo: this.repo,
                path: `data/${path}`,
                ref: this.branch
            });

            const content = Buffer.from(response.data.content, 'base64').toString();
            return [JSON.parse(content), response.data.sha];
        } catch (error) {
            if (error.status === 404) {
                return [null, null];
            }
            throw error;
        }
    }

    async updateFile(path, content, message, sha = null) {
        try {
            const params = {
                owner: this.owner,
                repo: this.repo,
                path: `data/${path}`,
                message,
                content: Buffer.from(JSON.stringify(content, null, 2)).toString('base64'),
                branch: this.branch
            };

            if (sha) {
                params.sha = sha;
            }

            await this.octokit.repos.createOrUpdateFileContents(params);
            return true;
        } catch (error) {
            this.logger.error(`Error updating file ${path}`, error);
            return false;
        }
    }

    async addTweet(tweet) {
        const [tweets, sha] = await this.getFileContent('ongoing_tweets.json');
        const updatedTweets = tweets ? [...tweets, tweet] : [tweet];
        return await this.updateFile(
            'ongoing_tweets.json',
            updatedTweets,
            `Add tweet ${tweet.id}`,
            sha
        );
    }
}

module.exports = { GithubOperations }; 