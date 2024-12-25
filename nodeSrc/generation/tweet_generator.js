const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        
        // 故事配置
        this.storyConfig = {
            protagonist: 'Xavier',
            startAge: 22,
            tweetsPerScene: 4,     // 每个场景4条推文
            scenesPerDay: 3,       // 每天3个场景
            maxTweetLength: 280    // Twitter长度限制
        };

        // 加载背景故事
        this.loadBackgroundStory();
    }

    async loadBackgroundStory() {
        try {
            const filePath = path.join(__dirname, '..', 'data', 'XaviersSim.json');
            const data = await fs.readFile(filePath, 'utf8');
            this.backgroundStory = JSON.parse(data);
            
            // 提取关键信息
            this.storyBackground = {
                characters: this._extractCharacters(this.backgroundStory),
                locations: this._extractLocations(this.backgroundStory),
                events: this._extractEvents(this.backgroundStory),
                relationships: this._extractRelationships(this.backgroundStory)
            };

            console.log('Background story loaded:', {
                charactersCount: Object.keys(this.storyBackground.characters).length,
                locationsCount: this.storyBackground.locations.length,
                eventsCount: this.storyBackground.events.length
            });
        } catch (error) {
            this.logger.error('Error loading background story', error);
            throw error;
        }
    }

    async generateTweetScene(digest, currentAge, tweetCount) {
        try {
            const context = await this._prepareContext(digest, tweetCount);
            const prompt = this._buildScenePrompt(context);
            
            const response = await this.ai.getCompletion(
                'You are continuing Xavier\'s story from his previous adventures.',
                prompt
            );

            const tweets = this._parseTweets(response);
            
            return tweets.map((text, index) => ({
                id: `tweet_${Date.now()}_${index}`,
                text: text.slice(0, this.storyConfig.maxTweetLength),
                age: currentAge,
                timestamp: new Date().toISOString(),
                metadata: {
                    tweet_number: tweetCount + index + 1,
                    scene_number: Math.floor((tweetCount + index) / this.storyConfig.tweetsPerScene),
                    story_day: Math.floor((tweetCount + index) / (this.storyConfig.tweetsPerScene * this.storyConfig.scenesPerDay)),
                    has_digest: !!digest
                }
            }));

        } catch (error) {
            this.logger.error('Error generating tweet scene', error);
            throw error;
        }
    }

    _buildScenePrompt(context) {
        const relevantBackground = this._getRelevantBackground(context);

        return `Background Story Context:
${relevantBackground}

Current story context:
Character: Xavier, ${context.current_age} years old
Story progress: Day ${context.story_day}, Scene ${context.scene_number}

Recent story developments:
${context.recent_tweets.map(t => t.text).join('\n')}

Latest story summary:
${context.latest_digest?.content || 'Story beginning...'}

Write a mini-scene as ${this.storyConfig.tweetsPerScene} connected tweets. The scene should:
1. Continue naturally from Xavier's previous adventures
2. Reference established characters and relationships
3. Build on existing story elements
4. Create new developments and intrigue
5. Use appropriate hashtags

Format:
TWEET 1: [First tweet content]
TWEET 2: [Second tweet content]
TWEET 3: [Third tweet content]
TWEET 4: [Fourth tweet content]

Guidelines:
- Each tweet must be under 280 characters
- Maintain consistency with background story
- Reference previous relationships and events
- Create emotional resonance
- End with anticipation for next scene`;
    }

    _getRelevantBackground(context) {
        // 根据当前情境选择相关的背景信息
        const relevantChars = this._selectRelevantCharacters(context);
        const relevantEvents = this._selectRelevantEvents(context);
        
        return `Key Characters:
${Object.entries(relevantChars).map(([name, info]) => `- ${name}: ${info}`).join('\n')}

Important Past Events:
${relevantEvents.map(event => `- ${event}`).join('\n')}

Established Relationships:
${this._formatRelationships(relevantChars)}`;
    }

    // 辅助方法用于解析背景故事
    _extractCharacters(story) {
        // 从故事中提取人物信息
        const characters = {};
        // 实现提取逻辑
        return characters;
    }

    _extractLocations(story) {
        // 提取地点信息
        return [];
    }

    _extractEvents(story) {
        // 提取重要事件
        return [];
    }

    _extractRelationships(story) {
        // 提取人物关系
        return {};
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

    _parseTweets(response) {
        // 解析返回的文本为单独的推文
        const tweets = response
            .split(/TWEET \d+:\s+/)  // 按"TWEET N:"分割
            .filter(tweet => tweet.trim())  // 移除空白项
            .map(tweet => tweet.trim());    // 整理格式

        // 验证推文数量
        if (tweets.length !== this.storyConfig.tweetsPerScene) {
            this.logger.warn(`Expected ${this.storyConfig.tweetsPerScene} tweets, got ${tweets.length}`);
        }

        return tweets;
    }

    async _prepareContext(digest, tweetCount) {
        const [recentTweets, _] = await this.getOngoingTweets();
        const lastTweets = recentTweets.slice(-5);

        return {
            current_age: this.storyConfig.startAge + 
                (tweetCount / (this.storyConfig.tweetsPerScene * this.storyConfig.scenesPerDay * 365)),
            story_day: Math.floor(tweetCount / (this.storyConfig.tweetsPerScene * this.storyConfig.scenesPerDay)),
            scene_number: Math.floor(tweetCount / this.storyConfig.tweetsPerScene),
            latest_digest: digest,
            recent_tweets: lastTweets
        };
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

    async saveTweet(tweet) {
        try {
            return await this.githubOps.addTweet(tweet);
        } catch (error) {
            this.logger.error('Error saving tweet', error);
            return false;
        }
    }
}

module.exports = { TweetGenerator }; 