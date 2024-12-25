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
            // 读取当前故事数据
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
            
            // 获取最近的推文
            const recentTweets = (storyData.tweets || []).slice(-5);
            
            // 计算当前阶段
            const phase = this._calculatePhase(currentAge);
            
            // 准备上下文
            return {
                current_age: currentAge,
                tweet_count: tweetCount,
                recent_tweets: recentTweets,
                latest_digest: digest,
                phase: phase,
                year_progress: this._calculateYearProgress(tweetCount),
                story_metadata: {
                    protagonist: this.storyConfig.protagonist.name,
                    current_phase: phase,
                    total_tweets: storyData.tweets?.length || 0
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
            // 读取现有数据
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);
            
            // 添加新推文
            storyData.tweets = storyData.tweets || [];
            storyData.tweets.push(...tweets.map(tweet => ({
                ...tweet,
                age: currentAge,
                timestamp: new Date().toISOString()
            })));
            
            // 更新元数据
            storyData.currentAge = currentAge;
            storyData.lastUpdate = new Date().toISOString();
            storyData.metadata.currentPhase = this._calculatePhase(currentAge);
            
            // 保存更新后的数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );
            
            this.logger.info('Saved new tweets', {
                count: tweets.length,
                currentAge
            });
        } catch (error) {
            this.logger.error('Error saving tweets', error);
            throw error;
        }
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

    _buildStoryPrompt(context, plotContext) {
        return `Story Context:
Age: ${context.current_age}
Life Phase: ${plotContext.currentPhase.focus}
Current Focus: ${plotContext.currentFocus}
Active Themes: ${plotContext.activeThemes.join(', ')}

Recent Story:
${context.recent_tweets.map(t => t.text).join('\n')}

Create a scene of 4 connected tweets that:
1. Advances the life story naturally
2. Shows character growth and insights
3. Reflects current life phase themes
4. Creates memorable moments
5. Maintains story continuity

Scene Structure:
TWEET 1: [Set the scene and mood]
TWEET 2: [Develop the situation]
TWEET 3: [Key moment or insight]
TWEET 4: [Resolution and future hint]

Writing Guidelines:
- Focus on personal growth and insights
- Show both successes and challenges
- Include technical and financial elements
- Create authentic character voice
- Build towards larger story arcs`;
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

    // ... 其他必要方法 ...
}

module.exports = { TweetGenerator }; 