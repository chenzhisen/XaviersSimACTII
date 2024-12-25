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
        const characters = {
            'Xavier': {
                role: '主角',
                traits: ['富有创造力', '对AI充满热情', '追求技术创新'],
                background: '年轻的程序员和创业者'
            }
        };

        try {
            // 从推文中提取人物信息
            story.tweets.forEach(tweet => {
                // 提取@提及的人物
                const mentions = tweet.text.match(/@(\w+)/g) || [];
                mentions.forEach(mention => {
                    const name = mention.slice(1);
                    if (!characters[name]) {
                        characters[name] = {
                            role: '故事人物',
                            firstMention: tweet.age,
                            interactions: []
                        };
                    }
                    characters[name].interactions.push({
                        age: tweet.age,
                        context: tweet.text
                    });
                });

                // 提取引用的对话
                const dialogues = tweet.text.match(/'([^']*)'|"([^"]*)"/g) || [];
                if (dialogues.length > 0) {
                    dialogues.forEach(dialogue => {
                        // 分析对话可能涉及的人物
                        const speakerMatch = tweet.text.match(/(\w+)[:：]/);
                        if (speakerMatch && !characters[speakerMatch[1]]) {
                            characters[speakerMatch[1]] = {
                                role: '对话者',
                                firstMention: tweet.age,
                                dialogues: []
                            };
                        }
                    });
                }
            });

            return characters;
        } catch (error) {
            this.logger.error('Error extracting characters', error);
            return characters;  // 返回基本角色信息
        }
    }

    _extractLocations(story) {
        const locations = new Set();
        
        try {
            story.tweets.forEach(tweet => {
                // 提取位置标签
                const locationTags = tweet.text.match(/#(\w+Location|\w+Place|\w+地|\w+区)/g) || [];
                locationTags.forEach(tag => locations.add(tag.slice(1)));

                // 提取常见地点词
                const locationWords = tweet.text.match(/在([\u4e00-\u9fa5]+[区街路店园院])/g) || [];
                locationWords.forEach(loc => locations.add(loc.slice(1)));
            });

            return Array.from(locations);
        } catch (error) {
            this.logger.error('Error extracting locations', error);
            return [];
        }
    }

    _extractEvents(story) {
        const events = [];
        
        try {
            let currentEvent = null;
            let eventTweets = [];

            story.tweets.forEach(tweet => {
                // 检测重要事件的开始
                const isNewEvent = tweet.text.includes('重要') || 
                                 tweet.text.includes('突破') ||
                                 tweet.text.includes('终于') ||
                                 tweet.text.match(/#[\u4e00-\u9fa5]*事件/);

                if (isNewEvent) {
                    // 保存前一个事件
                    if (currentEvent) {
                        events.push({
                            title: currentEvent,
                            age: eventTweets[0].age,
                            tweets: eventTweets.map(t => t.text)
                        });
                    }
                    
                    // 开始新事件
                    currentEvent = tweet.text.slice(0, 50);
                    eventTweets = [tweet];
                } else if (currentEvent) {
                    eventTweets.push(tweet);
                }
            });

            return events;
        } catch (error) {
            this.logger.error('Error extracting events', error);
            return [];
        }
    }

    _extractRelationships(story) {
        const relationships = {};
        
        try {
            const characters = Object.keys(this._extractCharacters(story));
            
            characters.forEach(char => {
                relationships[char] = {
                    friends: new Set(),
                    mentions: new Set(),
                    interactions: []
                };
            });

            story.tweets.forEach(tweet => {
                // 分析提及的人物关系
                characters.forEach(char => {
                    if (tweet.text.includes(char)) {
                        // 寻找关系词
                        const relationWords = ['朋友', '同事', '伙伴', '搭档', '师兄', '师妹'];
                        relationWords.forEach(word => {
                            if (tweet.text.includes(`${char}${word}`)) {
                                relationships[char].friends.add(
                                    tweet.text.match(new RegExp(`([\u4e00-\u9fa5]+)${word}`))[1]
                                );
                            }
                        });

                        // 记录互动
                        relationships[char].interactions.push({
                            age: tweet.age,
                            context: tweet.text
                        });
                    }
                });
            });

            // 转换Set为数组
            Object.keys(relationships).forEach(char => {
                relationships[char].friends = Array.from(relationships[char].friends);
                relationships[char].mentions = Array.from(relationships[char].mentions);
            });

            return relationships;
        } catch (error) {
            this.logger.error('Error extracting relationships', error);
            return {};
        }
    }

    _selectRelevantCharacters(context) {
        // 根据当前情境选择相关角色
        const relevantChars = {};
        const recentTweets = context.recent_tweets || [];
        
        try {
            // 从最近的推文中提取相关人物
            recentTweets.forEach(tweet => {
                Object.keys(this.storyBackground.characters).forEach(char => {
                    if (tweet.text.includes(char)) {
                        relevantChars[char] = this.storyBackground.characters[char];
                    }
                });
            });

            return relevantChars;
        } catch (error) {
            this.logger.error('Error selecting relevant characters', error);
            return {};
        }
    }

    _selectRelevantEvents(context) {
        // 选择与当前情境相关的事件
        try {
            return this.storyBackground.events
                .filter(event => Math.abs(event.age - context.current_age) <= 0.5) // 选择半年内的事件
                .map(event => event.title);
        } catch (error) {
            this.logger.error('Error selecting relevant events', error);
            return [];
        }
    }

    _formatRelationships(characters) {
        // 格式化人物关系
        try {
            return Object.entries(characters)
                .map(([name, info]) => {
                    const relations = this.storyBackground.relationships[name];
                    if (!relations) return '';
                    
                    const friends = relations.friends.join(', ');
                    return `${name} -> ${friends ? `朋友: ${friends}` : '暂无密切关系'}`;
                })
                .filter(Boolean)
                .join('\n');
        } catch (error) {
            this.logger.error('Error formatting relationships', error);
            return '';
        }
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