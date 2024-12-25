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
            protagonist: {
                name: 'Xavier',
                identity: '程序员/创业者/$XVI创始人',
                startAge: 22,
                endAge: 72
            },
            yearlyPace: {
                tweetsPerYear: 48,
                scenesPerYear: 12,
                tweetsPerScene: 4
            }
        };

        // Windows 路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };

        // 年龄限制配置
        this.ageConfig = {
            startAge: 22,
            endAge: 72,
            tweetsPerYear: 48
        };
    }

    async getCurrentSummary() {
        try {
            // 确保数据目录存在
            await fs.mkdir(this.paths.dataDir, { recursive: true });
            
            let summary;
            try {
                // 尝试读取现有数据
                const data = await fs.readFile(this.paths.mainFile, 'utf8');
                summary = JSON.parse(data);
            } catch (error) {
                if (error.code === 'ENOENT') {
                    // 文件不存在，创建新数据
                    summary = await this._initializeSummary();
                } else {
                    this.logger.error('Error reading file', error);
                    throw error;
                }
            }

            // 检查是否达到年龄上限
            if (summary.currentAge >= this.ageConfig.endAge) {
                this.logger.info('Story has reached end age', {
                    currentAge: summary.currentAge,
                    endAge: this.ageConfig.endAge
                });
                return {
                    ...summary,
                    isCompleted: true
                };
            }

            return {
                currentAge: summary.currentAge || this.storyConfig.protagonist.startAge,
                totalTweets: summary.tweets?.length || 0,
                lastDigest: summary.lastDigest || null,
                yearProgress: this._calculateYearProgress(summary.tweets?.length || 0)
            };
        } catch (error) {
            this.logger.error('Error getting current summary', error);
            throw error;
        }
    }

    async _initializeSummary() {
        const initialData = {
            currentAge: this.storyConfig.protagonist.startAge,
            tweets: [],
            lastDigest: null,
            lastUpdate: new Date().toISOString(),
            metadata: {
                protagonist: this.storyConfig.protagonist.name,
                startAge: this.storyConfig.protagonist.startAge,
                currentPhase: 'early_career'
            }
        };

        try {
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(initialData, null, 2),
                'utf8'
            );
            
            this.logger.info('Initialized new story file', {
                path: this.paths.mainFile
            });

            return initialData;
        } catch (error) {
            this.logger.error('Error initializing story file', error);
            throw error;
        }
    }

    _calculateYearProgress(tweetCount) {
        const tweetsPerYear = this.storyConfig.yearlyPace.tweetsPerYear;
        return {
            year: Math.floor(tweetCount / tweetsPerYear),
            progress: ((tweetCount % tweetsPerYear) / tweetsPerYear * 100).toFixed(1)
        };
    }

    async generateTweetScene(digest, currentAge, tweetCount) {
        try {
            const context = await this._prepareContext(digest, currentAge, tweetCount);
            const prompt = this._buildStoryPrompt(context);
            
            const response = await this.ai.getCompletion(
                'You are crafting a compelling life story through tweets.',
                prompt
            );

            const tweets = this._parseTweets(response);
            
            // 保存新生成的推文
            await this._saveTweets(tweets, currentAge);
            
            return tweets;
        } catch (error) {
            this.logger.error('Error generating story scene', error);
            throw error;
        }
    }

    async _prepareContext(digest, currentAge, tweetCount) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
                        
            // 获取最近的推文
            const recentTweets = storyData.story.tweets.slice(-5) || [];
            
            // 获取最新摘要
            const latestDigest = storyData.story.digests.length > 0 
                ? storyData.story.digests[storyData.story.digests.length - 1]
                : null;

            // 计算当前阶段
            const phase = this._calculatePhase(currentAge);
            
            return {
                current_age: currentAge,
                tweet_count: tweetCount,
                recent_tweets: recentTweets,
                latest_digest: latestDigest?.content || 'Starting a new chapter...',
                phase: phase,
                year_progress: this._calculateYearProgress(tweetCount),
                story_metadata: {
                    protagonist: storyData.metadata.protagonist,
                    current_phase: phase,
                    total_tweets: storyData.stats.totalTweets
                }
            };
        } catch (error) {
            this.logger.error('Error preparing context', error);
            throw error;
        }
    }

    _calculatePhase(age) {
        if (age < 32) return 'early_career';
        if (age < 42) return 'growth_phase';
        if (age < 52) return 'peak_phase';
        if (age < 62) return 'mature_phase';
        return 'wisdom_phase';
    }

    async _saveTweets(tweets, currentAge) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
            
            // 添加新推文到 story.tweets
            const newTweets = tweets.map(tweet => ({
                ...tweet,
                age: currentAge,
                timestamp: new Date().toISOString()
            }));
            
            storyData.story.tweets.push(...newTweets);
            
            // 更新统计信息
            storyData.stats.totalTweets = storyData.story.tweets.length;
            storyData.stats.yearProgress = this._calculateYearProgress(storyData.stats.totalTweets).progress;
            
            // 计算新年龄
            const newAge = this._calculateAge(storyData.stats.totalTweets);
            
            // 更新元数据
            storyData.metadata.currentAge = newAge;
            storyData.metadata.lastUpdate = new Date().toISOString();
            storyData.metadata.currentPhase = this._calculatePhase(newAge);

            // 保存更新后的数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );
            
            this.logger.info('Saved new tweets', {
                count: tweets.length,
                currentAge: newAge,
                totalTweets: storyData.stats.totalTweets
            });

            return true;
        } catch (error) {
            this.logger.error('Error saving tweets', error);
            throw error;
        }
    }

    _calculateAge(totalTweets) {
        const yearsPassed = totalTweets / this.ageConfig.tweetsPerYear;
        const newAge = Number((this.ageConfig.startAge + yearsPassed).toFixed(2));
        
        // 确保不超过结束年龄
        return Math.min(newAge, this.ageConfig.endAge);
    }

    _parseTweets(response) {
        // 解析生成的推文
        const tweets = response.split('TWEET').slice(1);
        return tweets.map(tweet => {
            const text = tweet.split('\n')
                .filter(line => line.trim())
                .join('\n')
                .replace(/^\d+:\s*/, '')
                .trim();
            
            return {
                text,
                id: `tweet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            };
        });
    }

    _buildStoryPrompt(context) {
        return `Story Context:
Age: ${context.current_age}
Phase: ${context.phase}
Progress: Year ${context.year_progress.year}, ${context.year_progress.progress}% complete
Total Tweets: ${context.story_metadata.total_tweets}

Recent Story:
${context.recent_tweets.map(t => t.text).join('\n\n')}

Latest Summary:
${context.latest_digest?.content || 'Starting a new chapter...'}

Create a scene of 4 connected tweets that:
1. Reflects the current life phase (${context.phase})
2. Shows character growth and experiences
3. Includes both work and personal life
4. Creates engaging moments
5. Maintains story continuity

Scene Guidelines:
- Balance tech/crypto with personal growth
- Show both successes and challenges
- Include relationships and interactions
- Create memorable moments
- Build towards future developments

Format:
TWEET 1: [Set the scene/situation]
TWEET 2: [Develop the story/interaction]
TWEET 3: [Key moment or insight]
TWEET 4: [Resolution and future hint]

Remember:
- Keep each tweet under 280 characters
- Use natural, conversational tone
- Include occasional #hashtags
- Reference $XVI when relevant
- Show both professional and personal growth`;
    }

    _getCurrentPhase(age) {
        return Object.values(this.storyConfig.lifePhases).find(
            phase => age >= phase.age[0] && age < phase.age[1]
        );
    }

    _getPlotContext(context) {
        const currentPhase = this._getCurrentPhase(context.current_age);
        const yearProgress = (context.tweet_count % 48) / 48;

        // 选择当前主题
        const activeThemes = this._selectThemes(currentPhase, yearProgress);
        
        return {
            currentPhase,
            currentFocus: this._selectFocus(currentPhase, yearProgress),
            plotType: this._selectPlotType(yearProgress),
            activeThemes
        };
    }

    async _updateStoryProgress(tweets, currentAge) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 更新年龄和阶段
            storyData.currentAge = currentAge;
            storyData.metadata.currentPhase = this._calculatePhase(currentAge);

            // 添加关键情节点
            const keyMoments = this._identifyKeyMoments(tweets);
            if (keyMoments.length > 0) {
                storyData.keyPlotPoints = storyData.keyPlotPoints || [];
                storyData.keyPlotPoints.push(...keyMoments.map(moment => ({
                    ...moment,
                    age: currentAge,
                    timestamp: new Date().toISOString()
                })));
            }

            // 保存更新
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            return storyData;
        } catch (error) {
            this.logger.error('Error updating story progress', error);
            throw error;
        }
    }

    _identifyKeyMoments(tweets) {
        // 识别关键情节（基于关键词和内容分析）
        const keywordPatterns = {
            milestone: /(突破|里程碑|成功|实现)/,
            relationship: /(爱情|友情|团队|伙伴)/,
            challenge: /(困难|挑战|问题|危机)/,
            growth: /(成长|学习|进步|改变)/,
            achievement: /(完成|达成|获得|赢得)/
        };

        return tweets
            .filter(tweet => {
                // 检查是否包含关键词
                return Object.values(keywordPatterns).some(pattern => 
                    pattern.test(tweet.text)
                );
            })
            .map(tweet => ({
                type: this._getKeyMomentType(tweet.text, keywordPatterns),
                content: tweet.text,
                id: tweet.id
            }));
    }

    _getKeyMomentType(text, patterns) {
        for (const [type, pattern] of Object.entries(patterns)) {
            if (pattern.test(text)) return type;
        }
        return 'general';
    }

    async _backupStoryData() {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const backupPath = path.join(
                this.paths.dataDir,
                'backups',
                `story_${timestamp}.json`
            );

            // 确保备份目录存在
            await fs.mkdir(path.dirname(backupPath), { recursive: true });

            // 复制当前数据文件
            await fs.copyFile(this.paths.mainFile, backupPath);

            this.logger.info('Created story backup', { path: backupPath });
        } catch (error) {
            this.logger.error('Error creating backup', error);
            // 继续执行，备份失败不影响主流程
        }
    }
}

module.exports = { TweetGenerator }; 