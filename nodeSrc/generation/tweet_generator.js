const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');
const Introduction = require('../data/Introduction.json');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        this.isProduction = isProduction;
        
        // 加载故事背景
        this.storyConfig = Introduction.story;
        this.protagonist = Introduction.protagonist;

        // 年龄和进度配置
        this.paceConfig = {
            tweetsPerYear: 48,
            scenesPerYear: 12,
            tweetsPerScene: 4
        };

        // Windows 路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json')
        };

        // 年龄限制配置
        this.ageConfig = {
            startAge: this.storyConfig.setting.startAge,
            endAge: 72,
            tweetsPerYear: this.paceConfig.tweetsPerYear
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
                currentAge: Number(summary.metadata.currentAge.toFixed(2)),
                totalTweets: summary.story.tweets.length,
                lastDigest: summary.story.digests[summary.story.digests.length - 1]?.content || null,
                yearProgress: this._calculateYearProgress(summary.story.tweets.length)
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
        const tweetsPerYear = this.paceConfig.tweetsPerYear;
        return {
            year: Math.floor(tweetCount / tweetsPerYear),
            progress: ((tweetCount % tweetsPerYear) / tweetsPerYear * 100).toFixed(1)
        };
    }

    async generateTweetScene(digest, currentAge, tweetCount) {
        try {
            const context = await this._prepareContext(digest, currentAge, tweetCount);
            const prompt = this._buildStoryPrompt(context);
            
            // 直接获取生成的推文数组
            const tweets = await this.ai.getCompletion(
                'You are crafting a compelling life story through tweets.',
                prompt
            );
            
            // 保存新生成的推文并获取更新后的信息
            const result = await this._saveTweets(tweets, currentAge);
            
            return result.tweets;
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
            
            // 计算新的总推文数和年龄
            const totalTweets = storyData.story.tweets.length + tweets.length;
            const newAge = this._calculateAge(totalTweets);
            
            // 添加新推文到 story.tweets
            const newTweets = tweets.map(tweet => ({
                ...tweet,
                age: Number(newAge.toFixed(2)),
                timestamp: new Date().toISOString()
            }));
            
            storyData.story.tweets.push(...newTweets);
            
            // 更新统计信息
            storyData.stats.totalTweets = totalTweets;
            storyData.stats.yearProgress = this._calculateYearProgress(totalTweets).progress;
            
            // 更新元数据
            storyData.metadata.currentAge = Number(newAge.toFixed(2));
            storyData.metadata.lastUpdate = new Date().toISOString();
            storyData.metadata.currentPhase = this._getCurrentPhase(newAge);

            // 保存更新后的数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );
            
            this.logger.info('Saved new tweets', {
                count: tweets.length,
                currentAge: Number(newAge.toFixed(2)),
                totalTweets,
                newTweets: newTweets.length
            });

            return {
                tweets: newTweets,
                currentAge: newAge,
                totalTweets
            };
        } catch (error) {
            this.logger.error('Error saving tweets', error);
            throw error;
        }
    }

    _calculateAge(totalTweets) {
        if (totalTweets === 0) return this.ageConfig.startAge;
        
        const yearsPassed = totalTweets / this.paceConfig.tweetsPerYear;
        const newAge = this.ageConfig.startAge + yearsPassed;
        return Math.min(Number(newAge.toFixed(2)), this.ageConfig.endAge);
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
        return Object.entries(this.storyConfig.phases).find(
            ([_, phase]) => age >= phase.age[0] && age < phase.age[1]
        )[0];
    }

    _getPhaseContext(age) {
        const phase = this._getCurrentPhase(age);
        return {
            phase,
            focus: this.storyConfig.phases[phase].focus,
            themes: this.storyConfig.themes
        };
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