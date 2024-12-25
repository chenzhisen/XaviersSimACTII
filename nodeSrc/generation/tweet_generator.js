const { AICompletion } = require('../utils/ai_completion');
const { GithubOperations } = require('../storage/github_operations');
const { Logger } = require('../utils/logger');
const fs = require('fs').promises;
const path = require('path');
const Introduction = require('../data/Introduction.json');
const tweetStorage = require('../utils/tweet_storage');

class TweetGenerator {
    constructor(client, model, isProduction = false) {
        this.logger = new Logger('tweet');
        this.ai = new AICompletion(client, model);
        this.githubOps = new GithubOperations(isProduction);
        this.isProduction = isProduction;

        // 文件路径配置
        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json'),
            backupDir: path.resolve(__dirname, '..', 'data', 'backups')
        };

        // 加载故事背景
        this.storyConfig = Introduction.story;
        this.protagonist = Introduction.protagonist;

        // 年龄和进度配置
        this.paceConfig = {
            tweetsPerYear: 48,
            scenesPerYear: 12,
            tweetsPerScene: 4
        };

        // 年龄限制配置
        this.ageConfig = {
            startAge: this.storyConfig.setting.startAge,
            endAge: this.storyConfig.setting.endAge,
            tweetsPerYear: this.paceConfig.tweetsPerYear
        };

        // 备份路径配置
        this.backupConfig = {
            dir: path.join(__dirname, '..', 'data', 'backups'),
            maxFiles: 5,  // 保留最近5个备份
            interval: 24 * 60 * 60 * 1000  // 24小时
        };
    }

    async generateTweetScene(lastDigest, currentAge, tweetCount) {
        try {
            // 每次生成前重新获取最新的系统提示
            const systemPrompt = await this._buildSystemPrompt();
            
            // 更新 AI 实例的系统提示
            this.ai.updateSystemPrompt(systemPrompt);

            const context = await this._prepareContext(lastDigest, currentAge, tweetCount);
            const prompt = this._buildStoryPrompt(context);

            // 直接获取生成的推文数组
            const tweets = await this.ai.getCompletion(
                'You are crafting a compelling life story through tweets.',
                prompt
            );

            // 保存新生成的推文获取更新后的信息
            const result = await this._saveTweets(tweets, currentAge);

            return result.tweets;
        } catch (error) {
            this.logger.error('Error generating tweet scene', error);
            throw error;
        }
    }

    async _buildSystemPrompt() {
        try {
            // 每次都重新读取最新的数据
            const data = JSON.parse(
                await fs.readFile(this.paths.mainFile, 'utf8')
            );
            
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
        } catch (error) {
            this.logger.error('Error building system prompt', error);
            throw error;
        }
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

    async _prepareContext(digest, currentAge, tweetCount) {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 获取最近的推文
            const recentTweets = storyData.story.tweets.slice(-5) || [];

            // 获��最新摘要
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
            // 使用新的存储工具保存推文
            const result = await tweetStorage.saveTweets(tweets, currentAge);
            if (!result.success) {
                throw new Error(result.error);
            }
            return result;
        } catch (error) {
            console.error('保存推文失败:', error);
            throw error;
        }
    }

    _updatePersonalStatus(storyData, currentAge) {
        const personal = storyData.personal;
        const romantic = personal.relationships.romantic;
        const familyLife = personal.family_life;

        // 根据年龄更新状态
        if (currentAge >= 27 && romantic.status === 'single') {
            // 27岁左右开始稳定的感情关系
            romantic.status = 'in_relationship';
            romantic.milestones.push({
                event: 'started_relationship',
                age: currentAge,
                timestamp: new Date().toISOString()
            });
        }

        if (currentAge >= 32 && !familyLife.marriage.isMarried) {
            // 32岁左右结婚
            familyLife.marriage.isMarried = true;
            familyLife.status = 'married';
            familyLife.marriage.date = new Date().toISOString();
            romantic.status = 'married';
        }

        if (currentAge >= 34 && !familyLife.children.hasChildren) {
            // 34岁左右有一个孩子
            familyLife.children.hasChildren = true;
            familyLife.children.count = 1;
            familyLife.children.milestones.push({
                event: 'first_child',
                age: currentAge,
                timestamp: new Date().toISOString()
            });
        }

        // 更新工作生活平衡
        if (currentAge >= 30) {
            personal.lifestyle.workLifeBalance.current = '逐步平衡';
        }
        if (currentAge >= 35) {
            personal.lifestyle.workLifeBalance.current = '重视家庭';
        }

        // 更新兴趣爱好
        if (currentAge >= 28 && !personal.lifestyle.interests.includes('亲子活动')) {
            personal.lifestyle.interests.push('亲子活动');
        }

        // 更新性格特点
        if (currentAge >= 30 && !personal.lifestyle.traits.includes('成熟稳重')) {
            personal.lifestyle.traits.push('成熟稳重');
        }

        // 记录重要的生活变化
        if (!storyData.story.keyPlotPoints) {
            storyData.story.keyPlotPoints = [];
        }

        // 检查并记录重要事件
        this._checkAndRecordLifeEvents(storyData, currentAge);
    }

    _checkAndRecordLifeEvents(storyData, currentAge) {
        const events = [
            {
                age: 27,
                type: 'relationship',
                title: '遇到人生伴侣',
                description: '在事业稳定发展时期，遇到了能够互相理解和支持的伴侣。'
            },
            {
                age: 32,
                type: 'marriage',
                title: '步入婚姻',
                description: '与相恋多年的伴侣共同开启人生的新篇章。'
            },
            {
                age: 34,
                type: 'family',
                title: '喜得贵子',
                description: '迎来人生的新角色，成为一名父亲。'
            }
        ];

        events.forEach(event => {
            if (currentAge >= event.age && 
                !storyData.story.keyPlotPoints.some(p => p.type === event.type)) {
                storyData.story.keyPlotPoints.push({
                    ...event,
                    timestamp: new Date().toISOString()
                });
            }
        });
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

            // 更新年龄阶段
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

    async _createBackup() {
        try {
            // 确保备份目录存在
            await fs.mkdir(this.backupConfig.dir, { recursive: true });

            // 生成备份文件名
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const backupPath = path.join(
                this.backupConfig.dir,
                `XaviersSim_${timestamp}.json`
            );

            // 复制当前文件作为备份
            await fs.copyFile(this.paths.mainFile, backupPath);

            // 清理旧备份
            await this._cleanupOldBackups();

            this.logger.info('Created story backup', { path: backupPath });
        } catch (error) {
            this.logger.error('Error creating backup', error);
            // 继续执行，备份失败不影响主流程
        }
    }

    async _cleanupOldBackups() {
        try {
            // 获取所有备份文件
            const files = await fs.readdir(this.backupConfig.dir);
            const backups = files
                .filter(f => f.startsWith('XaviersSim_'))
                .map(f => ({
                    name: f,
                    path: path.join(this.backupConfig.dir, f),
                    time: new Date(f.split('_')[1].split('.')[0].replace(/-/g, ':'))
                }))
                .sort((a, b) => b.time - a.time);  // 按时间降序排序

            // 删除超出数量限制的旧备份
            if (backups.length > this.backupConfig.maxFiles) {
                const oldBackups = backups.slice(this.backupConfig.maxFiles);
                for (const backup of oldBackups) {
                    await fs.unlink(backup.path);
                    this.logger.info('Deleted old backup', { path: backup.path });
                }
            }
        } catch (error) {
            this.logger.error('Error cleaning up old backups', error);
            // 继续执行，清理失败不影响主流程
        }
    }
}

module.exports = { TweetGenerator }; 