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
        this.isProduction = isProduction;
        
        // 故事配置
        this.storyConfig = {
            protagonist: 'Xavier',
            startAge: 22,
            tweetsPerScene: 4,
            scenesPerDay: 3,
            maxTweetLength: 280
        };

        // 分片存储配置
        this.storageConfig = {
            tweetsPerFile: 1000,    // 每个文件存储1000条推文
            yearsPerEpoch: 10,      // 每10年为一个时期
            baseAge: 22             // 起始年龄
        };

        // 文件路径结构
        this.paths = {
            base: path.join(__dirname, '..', 'data', this.isProduction ? 'prod' : 'dev'),
            get summary() {
                return path.join(this.base, 'summary.json');  // 存储摘要信息
            },
            getEpochPath(epoch) {
                return path.join(this.base, `epoch_${epoch}.json`); // 分时期存储
            }
        };

        // 故事连贯性配置
        this.contextConfig = {
            recentTweets: 10,        // 最近的推文数量
            keyEventsToInclude: 5,   // 关键事件数量
            characterLimit: 8,        // 相关角色数量
            summaryLength: 500       // 背景摘要长度
        };

        // 初始化背景故事
        this.loadBackgroundStory();
    }

    async loadBackgroundStory() {
        try {
            // 加载摘要文件
            const summary = await this._loadOrCreateSummary();
            
            // 计算当前时期
            const currentEpoch = this._calculateEpoch(summary.currentAge);
            
            // 只加载最近的时期数据
            this.backgroundStory = await this._loadRecentEpochs(currentEpoch);
            
            console.log('Background loaded:', {
                currentAge: summary.currentAge,
                currentEpoch,
                loadedEpochs: Object.keys(this.backgroundStory).length
            });
        } catch (error) {
            this.logger.error('Error loading background', error);
            throw error;
        }
    }

    async _loadOrCreateSummary() {
        try {
            const data = await fs.readFile(this.paths.summary, 'utf8');
            return JSON.parse(data);
        } catch {
            const initial = {
                currentAge: this.storageConfig.baseAge,
                totalTweets: 0,
                epochs: [],
                keyPlotPoints: [],
                lastUpdate: new Date().toISOString()
            };
            await fs.writeFile(this.paths.summary, JSON.stringify(initial, null, 2));
            return initial;
        }
    }

    async _loadRecentEpochs(currentEpoch) {
        const epochs = {};
        
        // 只加载当前和前一个时期的数据
        for (let epoch = currentEpoch - 1; epoch <= currentEpoch; epoch++) {
            if (epoch >= 0) {
                try {
                    const path = this.paths.getEpochPath(epoch);
                    const data = await fs.readFile(path, 'utf8');
                    epochs[epoch] = JSON.parse(data);
                } catch {
                    epochs[epoch] = { tweets: [], metadata: {} };
                }
            }
        }
        
        return epochs;
    }

    _calculateEpoch(age) {
        return Math.floor((age - this.storageConfig.baseAge) / this.storageConfig.yearsPerEpoch);
    }

    async _saveToBackgroundStory(newTweets) {
        try {
            // 加载摘要
            const summary = await this._loadOrCreateSummary();
            
            // 计算时期
            const currentEpoch = this._calculateEpoch(newTweets[0].age);
            
            // 加载当前时期文件
            const epochPath = this.paths.getEpochPath(currentEpoch);
            let epochData;
            try {
                const data = await fs.readFile(epochPath, 'utf8');
                epochData = JSON.parse(data);
            } catch {
                epochData = {
                    tweets: [],
                    metadata: {
                        epoch: currentEpoch,
                        startAge: this.storageConfig.baseAge + (currentEpoch * this.storageConfig.yearsPerEpoch),
                        endAge: this.storageConfig.baseAge + ((currentEpoch + 1) * this.storageConfig.yearsPerEpoch),
                        plotPoints: []
                    }
                };
            }

            // 添加新推文
            epochData.tweets.push(...newTweets);
            
            // 更新摘要
            summary.currentAge = newTweets[newTweets.length - 1].age;
            summary.totalTweets += newTweets.length;
            
            // 提取关键情节点
            const plotPoints = this._extractPlotPoints(newTweets);
            if (plotPoints.length > 0) {
                epochData.metadata.plotPoints.push(...plotPoints);
                // 只保存重要的情节点到摘要
                summary.keyPlotPoints.push(...plotPoints.filter(p => 
                    p.text.includes('重要') || p.text.includes('转折')
                ));
            }

            // 保存文件
            await Promise.all([
                fs.writeFile(epochPath, JSON.stringify(epochData, null, 2)),
                fs.writeFile(this.paths.summary, JSON.stringify(summary, null, 2))
            ]);

            console.log('Story updated:', {
                epoch: currentEpoch,
                newTweets: newTweets.length,
                totalTweets: summary.totalTweets
            });
        } catch (error) {
            this.logger.error('Error saving story', error);
            throw error;
        }
    }

    _extractPlotPoints(tweets) {
        // 从新推文中提取关键情节点
        const plotPoints = [];
        const keywords = ['终于', '突然', '没想到', '重要', '决定', '原来'];
        
        tweets.forEach(tweet => {
            if (keywords.some(keyword => tweet.text.includes(keyword))) {
                plotPoints.push({
                    age: tweet.age,
                    point: tweet.text.slice(0, 50) + '...',
                    timestamp: tweet.timestamp
                });
            }
        });

        return plotPoints;
    }

    _buildScenePrompt(context) {
        return `Story Context:
Current Age: ${context.current_age}
Story Day: ${context.story_day}

Story Summary:
${context.story_summary}

Recent Key Events:
${context.key_events.map(e => `- Age ${e.age}: ${e.description}`).join('\n')}

Active Characters:
${Object.entries(context.characters)
    .map(([name, info]) => `- ${name}: ${info.role} (Last appeared: Age ${info.lastSeen})`)
    .join('\n')}

Recent Developments:
${context.recent_developments.map(t => t.text).join('\n')}

Latest Story Digest:
${context.latest_digest?.content || 'Story beginning...'}

Write a mini-scene as ${this.storyConfig.tweetsPerScene} connected tweets that:
1. Maintains story continuity with previous events
2. Develops established character relationships
3. Advances the overall narrative
4. Creates emotional engagement
5. Plants seeds for future developments

Format:
TWEET 1: [First tweet content]
TWEET 2: [Second tweet content]
TWEET 3: [Third tweet content]
TWEET 4: [Fourth tweet content]

Remember:
- Reference past events naturally
- Keep character personalities consistent
- Create anticipation for what comes next
- Use established relationships
- Stay true to the story's themes`;
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
                .filter(event => Math.abs(event.age - context.current_age) <= 0.5) // 选���半年内的事件
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
        // 获取当前时期
        const currentAge = this.storyConfig.startAge + 
            (tweetCount / (this.storyConfig.tweetsPerScene * this.storyConfig.scenesPerDay * 365));
        const currentEpoch = this._calculateEpoch(currentAge);

        // 1. 获取最近的故事发展
        const recentTweets = await this._getRecentTweets(currentEpoch);

        // 2. 获取关键情节点
        const keyEvents = await this._getKeyEvents(currentAge);

        // 3. 获取相关角色
        const relevantCharacters = this._getRelevantCharacters(recentTweets);

        // 4. 生成当前故事阶段摘要
        const storySummary = this._generatePhaseSummary(currentAge, recentTweets, keyEvents);

        return {
            current_age: currentAge,
            story_day: Math.floor(tweetCount / (this.storyConfig.tweetsPerScene * this.storyConfig.scenesPerDay)),
            recent_developments: recentTweets,
            key_events: keyEvents,
            characters: relevantCharacters,
            story_summary: storySummary,
            latest_digest: digest
        };
    }

    async _getRecentTweets(currentEpoch) {
        const tweets = [];
        
        // 从当前和前一个时期获取最近的推文
        for (let epoch = currentEpoch - 1; epoch <= currentEpoch; epoch++) {
            if (epoch >= 0 && this.backgroundStory[epoch]) {
                tweets.push(...this.backgroundStory[epoch].tweets);
            }
        }

        // 返回最近的N条推文
        return tweets
            .slice(-this.contextConfig.recentTweets)
            .map(t => ({
                text: t.text,
                age: t.age,
                timeGap: t.metadata.story_day
            }));
    }

    async _getKeyEvents(currentAge) {
        try {
            const summary = await this._loadOrCreateSummary();
            
            // 筛选关键事件
            return summary.keyPlotPoints
                .filter(event => event.age <= currentAge)  // 只包含当前年龄之前的事件
                .slice(-this.contextConfig.keyEventsToInclude)  // 取最近的几个关键事件
                .map(event => ({
                    description: event.point,
                    age: event.age,
                    impact: event.text.includes('重要') ? 'major' : 'minor'
                }));
        } catch (error) {
            this.logger.error('Error getting key events', error);
            return [];
        }
    }

    _generatePhaseSummary(currentAge, recentTweets, keyEvents) {
        // 生成当前阶段的故事摘要
        const ageBracket = Math.floor(currentAge / 5) * 5;
        const phaseDescription = this._getPhaseDescription(ageBracket);
        
        return `Current Life Phase (Age ${ageBracket}-${ageBracket + 5}):
${phaseDescription}

Recent Themes:
${this._extractThemes(recentTweets).join(', ')}

Key Developments:
${keyEvents.map(e => e.description).join('\n')}`;
    }

    _getPhaseDescription(ageBracket) {
        const phaseDescriptions = {
            20: "Early career and finding direction",
            25: "Career growth and relationship development",
            30: "Professional establishment and personal growth",
            35: "Mid-career challenges and life balance",
            // ... 其他年龄段描述
        };
        return phaseDescriptions[ageBracket] || "Continuing life journey";
    }

    _getRelevantCharacters(recentTweets) {
        const relevantCharacters = {};
        recentTweets.forEach(tweet => {
            Object.keys(this.storyBackground.characters).forEach(char => {
                if (tweet.text.includes(char)) {
                    relevantCharacters[char] = this.storyBackground.characters[char];
                }
            });
        });
        return relevantCharacters;
    }

    _extractThemes(recentTweets) {
        const themes = new Set();
        recentTweets.forEach(tweet => {
            const themesInTweet = tweet.text.match(/#(\w+Theme)/g) || [];
            themesInTweet.forEach(theme => themes.add(theme.slice(1)));
        });
        return Array.from(themes);
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