const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 配置
        this.tweetsPerYear = 96;
        this.daysPerTweet = 384 / this.tweetsPerYear;
        this.maxTweetLength = 280;
    }

    async getOngoingTweets() {
        try {
            const [tweets, _] = await this.githubOps.getFileContent('ongoing_tweets.json');
            const ongoingTweets = tweets || [];
            const tweetsByAge = this._groupTweetsByAge(ongoingTweets);
            return [ongoingTweets, tweetsByAge];
        } catch (error) {
            this.logger.error('Error getting ongoing tweets', error);
            return [[], {}];
        }
    }

    async generateTweet(digest, currentAge, techEvolution, tweetCount) {
        try {
            const context = await this._prepareContext(digest, currentAge, techEvolution, tweetCount);
            const prompt = this._buildPrompt(context);
            
            const response = await this.ai.getCompletion(
                'You are Xavier, an AI system sharing insights on Twitter.',
                prompt
            );

            if (!response) {
                throw new Error('Failed to generate tweet content');
            }

            return {
                id: `tweet_${Date.now()}`,
                text: response.slice(0, this.maxTweetLength),
                age: currentAge,
                timestamp: new Date().toISOString(),
                metadata: {
                    tweet_number: tweetCount + 1,
                    has_digest: !!digest,
                    has_tech: !!techEvolution
                }
            };
        } catch (error) {
            this.logger.error('Error generating tweet', error);
            throw error;
        }
    }

    async saveTweet(tweet) {
        try {
            return await this.githubOps.addTweet(tweet);
        } catch (error) {
            this.logger.error('Error saving tweet', error);
            return false;
        }
    }

    _groupTweetsByAge(tweets) {
        const tweetsByAge = {};
        for (const tweet of tweets) {
            const age = tweet.age.toFixed(1);
            if (!tweetsByAge[age]) {
                tweetsByAge[age] = [];
            }
            tweetsByAge[age].push(tweet);
        }
        return tweetsByAge;
    }

    async _prepareContext(digest, currentAge, techEvolution, tweetCount) {
        const [recentTweets, _] = await this.getOngoingTweets();
        const lastTweets = recentTweets.slice(-5);

        return {
            current_age: currentAge,
            tweet_count: tweetCount,
            latest_digest: digest,
            tech_evolution: techEvolution,
            recent_tweets: lastTweets
        };
    }

    _buildPrompt(context) {
        return `Current age: ${context.current_age}
Tweet number: ${context.tweet_count + 1}
${context.latest_digest ? 'Recent digest available' : 'No recent digest'}
${context.tech_evolution ? 'Tech evolution data available' : 'No tech evolution data'}

Recent tweets:
${context.recent_tweets.map(t => t.text).join('\n')}

Generate a thoughtful and engaging tweet that continues Xavier's story.`;
    }
}

module.exports = { TweetGenerator }; 