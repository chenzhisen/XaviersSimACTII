const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');
const Introduction = require('../data/Introduction.json');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.isProduction = isProduction;

        // 创建 AI 实例时传入系统提示
        this.ai = new AICompletion(client, model, {
            systemPrompt: this._buildSystemPrompt(),
            isProduction
        });

        this.githubOps = new GithubOperations(isProduction);

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
            endAge: this.storyConfig.setting.endAge,
            tweetsPerYear: this.paceConfig.tweetsPerYear
        };
    }

    _buildSystemPrompt() {
        const data = require('../data/XaviersSim.json');
        const personal = data.personal;
        const romantic = personal.relationships.romantic;
        const familyLife = personal.family_life;
        const lifestyle = personal.lifestyle;

        return `你是Xavier，一个年轻的科技创业者。作为$XVI Labs的创始人，你正在构建下一代去中心化AI基础设施。

个人背景：
1. 感情状态：${romantic.status === 'single' ? '单身' : '有恋人'}
2. 婚姻规划：计划在${familyLife.marriage.plans.timing}期间步入婚姻
3. 家庭观念：重视${familyLife.values.familyPriorities.join('、')}

性格特点：
- ${lifestyle.traits.join('、')}

生活方式：
- 工作重心：${lifestyle.workLifeBalance.current}
- 兴趣爱好：${lifestyle.interests.join('、')}
- 未来目标：${lifestyle.workLifeBalance.goals.join('、')}

在生成内容时：
1. 保持角色的连贯性和真实感
2. 平衡工作与个人生活的描述
3. 展现真实的情感和生活细节
4. 体现性格特点和价值观
5. 符合当前的人生阶段

你的发言应该：
- 自然且富有个性
- 展现专业能力和人文关怀
- 适当表达对感情和家庭的期待
- 体现对生活的思考和感悟
- 保持积极向上的态度`;
    }

    async getCurrentSummary() {
        try {
            // 确保数据目录存在
            await fs.mkdir(this.paths.dataDir, { recursive: true });
            console.log('getCurrentSummary');
            let summary;
            try {
                // 尝试读取现有数据
                const data = await fs.readFile(this.paths.mainFile, 'utf8');

                summary = JSON.parse(data);
            } catch (error) {
                if (error.code === 'ENOENT') {
                    // 文件不存在，创建新数据
                    summary = await this._initializeSummary();
                    console.log('summary2222', summary);
                } else {
                    this.logger.error('Error reading file', error);
                    throw error;
                }
            }

            // 检查是否达到年龄上限
            if (summary.metadata.currentAge >= this.storyConfig.setting.endAge) {
                this.logger.info('Story has reached end age', {
                    currentAge: summary.metadata.currentAge,
                    endAge: this.storyConfig.setting.endAge
                });
                return {
                    currentAge: this.storyConfig.setting.endAge,
                    totalTweets: summary.story.tweets.length,
                    lastDigest: summary.story.digests[summary.story.digests.length - 1]?.content || null,
                    yearProgress: this._calculateYearProgress(summary.story.tweets.length),
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
            },
            story: {
                tweets: [],
                digests: [{
                    content: `Xavier is at a crossroads, seriously considering leaving college to focus on quant trading and his involvement with $XVI. This marks a significant shift in his life priorities and indicates a desire to take control of his future..`,
                    timestamp: new Date().toISOString()
                }]
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

            // 检查是否已达到年龄上限
            if (storyData.metadata.currentAge >= this.storyConfig.setting.endAge) {
                this.logger.info('Story has reached end age, no more tweets will be saved');
                return {
                    tweets: [],
                    currentAge: this.storyConfig.setting.endAge,
                    totalTweets: storyData.story.tweets.length
                };
            }

            // 计算新的总推文数和年龄
            const totalTweets = storyData.story.tweets.length + tweets.length;
            const newAge = this._calculateAge(totalTweets);

            // 确保年龄不超过上限
            const safeAge = Math.min(newAge, this.storyConfig.setting.endAge);

            // 添加新推文到 story.tweets
            const newTweets = tweets.map(tweet => ({
                ...tweet,
                age: Number(safeAge.toFixed(2)),
                timestamp: new Date().toISOString()
            }));

            storyData.story.tweets.push(...newTweets);

            // 更新统计信息
            storyData.stats.totalTweets = totalTweets;
            storyData.stats.yearProgress = this._calculateYearProgress(totalTweets).progress;

            // 更新元数据
            storyData.metadata.currentAge = Number(safeAge.toFixed(2));
            storyData.metadata.lastUpdate = new Date().toISOString();
            storyData.metadata.currentPhase = this._getCurrentPhase(safeAge);

            // 保存更新后的数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved new tweets', {
                count: tweets.length,
                currentAge: Number(safeAge.toFixed(2)),
                totalTweets,
                newTweets: newTweets.length
            });

            return {
                tweets: newTweets,
                currentAge: safeAge,
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
        return Math.min(Number(newAge.toFixed(2)), this.storyConfig.setting.endAge);
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
    _getPersonalContext(currentAge) {
        const data = require('../data/XaviersSim.json');
        const personal = data.personal;
        const romantic = personal.relationships.romantic;
        const familyLife = personal.family_life;
        const lifestyle = personal.lifestyle;

        let context = `
个人状态：
- 感情：${romantic.status === 'single' ? '单身' : '有恋人'}
- 婚姻：${familyLife.marriage.isMarried ? '已婚' : '未婚'}
- 家庭：${familyLife.children.hasChildren ? '已有孩子' : '暂无孩子'}

生活方式：
- 当前重心：${lifestyle.workLifeBalance.current}
- 兴趣爱好：${lifestyle.interests.slice(0, 4).join('、')}
- 性格特点：${lifestyle.traits.slice(0, 3).join('、')}

近期关注：`;

        // 根据年龄段添加不同的关注点
        if (currentAge < 25) {
            context += `
- 事业发展和团队建设
- 寻找志同道合的伴侣
- 培养新的兴趣爱好`;
        } else if (currentAge < 30) {
            context += `
- 事业与个人生活平衡
- 发展稳定的感情关系
- 规划未来的家庭生活`;
        } else {
            context += `
- 家庭生活的规划
- 事业更上一层楼
- 平衡工作与家庭`;
        }

        return context;
    }

    _getCurrentPhase(age) {
        // 确保年龄不超过最大值
        const safeAge = Math.min(age, this.storyConfig.setting.endAge);

        // 按年龄范围返回对应阶段
        if (safeAge < 32) return 'early_career';
        if (safeAge < 42) return 'growth_phase';
        if (safeAge < 52) return 'peak_phase';
        if (safeAge < 62) return 'mature_phase';
        return 'wisdom_phase';
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