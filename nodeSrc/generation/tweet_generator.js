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
            
            // 获取实际年龄
            const { totalTweets } = await this._getTweetsInfo();
            const currentAge = this._calculateAge(totalTweets);
            
            const personal = data.personal;
            const romantic = personal.relationships.romantic;
            const familyLife = personal.family_life;
            const lifestyle = personal.lifestyle;

            return `你是Xavier，一个${currentAge}岁的年轻科技创业者。作为$XVI Labs的创始人，你正在构建下一代去中心化AI基础设施。

个人背景：
1. 当前年龄：${currentAge}岁
2. 感情状态：${romantic.status === 'single' ? '单身' : '有恋人'}
3. 婚姻规划：计划在${familyLife.marriage.plans.timing}期间步入婚姻
4. 家庭观念：重视${familyLife.values.familyPriorities.join('、')}

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

            // 获取最新推文和评论
            const latestTweetAndReplies = await this._getLatestTweetAndReplies();
            
            // 从sent_tweets.json获取最近的推文和总推文数
            const { recentTweets, totalTweets } = await this._getTweetsInfo(5);

            // 获取最新摘要
            const latestDigest = storyData.story.digests.length > 0
                ? storyData.story.digests[storyData.story.digests.length - 1]
                : null;

            // 根据实际发送的推文数重新计算年龄和阶段
            const calculatedAge = this._calculateAge(totalTweets);
            const phase = this._calculatePhase(calculatedAge);

            // 根据评论调整故事发展
            const storyAdjustments = this._analyzeRepliesForStoryAdjustment(latestTweetAndReplies);

            return {
                current_age: calculatedAge,
                tweet_count: totalTweets,
                recent_tweets: recentTweets,
                latest_digest: latestDigest?.content || 'Starting a new chapter...',
                phase: phase,
                year_progress: this._calculateYearProgress(totalTweets),
                story_metadata: {
                    protagonist: storyData.metadata.protagonist,
                    current_phase: phase,
                    total_tweets: totalTweets
                },
                latest_interaction: latestTweetAndReplies,
                story_adjustments: storyAdjustments
            };
        } catch (error) {
            this.logger.error('Error preparing context', error);
            throw error;
        }
    }

    async _getTweetsInfo(recentCount = 5) {
        try {
            const sentTweetsPath = path.join(this.paths.dataDir, 'sent_tweets.json');
            
            // 检查文件是否存在
            try {
                await fs.access(sentTweetsPath);
            } catch {
                return { recentTweets: [], totalTweets: 0 };
            }

            // 读取sent_tweets.json
            const content = await fs.readFile(sentTweetsPath, 'utf8');
            if (!content.trim()) {
                return { recentTweets: [], totalTweets: 0 };
            }

            const sentTweets = JSON.parse(content);
            const totalTweets = sentTweets.length;
            
            // 获取最近的recentCount条推文
            const recentTweets = sentTweets.slice(-recentCount).map(tweet => ({
                text: tweet.content,
                id: tweet.id,
                timestamp: tweet.sent_at
            }));

            return { recentTweets, totalTweets };
        } catch (error) {
            this.logger.error('Error getting tweets info', error);
            return { recentTweets: [], totalTweets: 0 };
        }
    }

    async _getLatestTweetAndReplies() {
        try {
            // 读取最新推文
            const sentTweetsPath = path.join(this.paths.dataDir, 'sent_tweets.json');
            const repliesPath = path.join(this.paths.dataDir, 'tweet_replies.json');

            let latestTweet = null;
            let replies = [];

            // 获取最新推文
            if (await this._fileExists(sentTweetsPath)) {
                const sentTweetsData = await fs.readFile(sentTweetsPath, 'utf8');
                const sentTweets = JSON.parse(sentTweetsData);
                if (sentTweets.length > 0) {
                    latestTweet = sentTweets[sentTweets.length - 1];
                }
            }

            // 获取该推文的回复
            if (latestTweet && await this._fileExists(repliesPath)) {
                const repliesData = await fs.readFile(repliesPath, 'utf8');
                const allReplies = JSON.parse(repliesData);
                if (allReplies[latestTweet.id]) {
                    replies = allReplies[latestTweet.id].replies || [];
                }
            }

            return {
                tweet: latestTweet,
                replies: replies
            };
        } catch (error) {
            this.logger.error('Error getting latest tweet and replies', error);
            return { tweet: null, replies: [] };
        }
    }

    _analyzeRepliesForStoryAdjustment(latestTweetAndReplies) {
        if (!latestTweetAndReplies?.tweet || !latestTweetAndReplies?.replies?.length) {
            return null;
        }

        const replies = latestTweetAndReplies.replies;
        let adjustments = {
            suggestions: [],  // 存储每条评论的完整分析
            raw_suggestions: []  // 保存所有原始评论
        };

        // 分析所有回复
        const analyzedReplies = replies.map(reply => {
            // 过滤掉 @XaviersSimACTII
            const cleanContent = reply.content.replace(/@XaviersSimACTII/g, '').trim();
            
            const analysis = {
                content: cleanContent,  // 过滤后的内容
                created_at: reply.created_at,  // 评论时间
                author_id: reply.author_id,  // 评论者ID
                username: reply.username,  // 添加用户名字段
                analysis: {  // 评论分析结果
                    type: this._getSuggestionType(cleanContent),
                    impact: this._analyzeImpact(cleanContent),
                    mood: this._analyzeMood(cleanContent),
                    keywords: this._extractKeywords(cleanContent)
                }
            };

            // 计算评论的相关性分数
            analysis.relevanceScore = this._calculateRelevanceScore(analysis);

            return analysis;
        });

        // 按相关性分数排序并选取前3条
        const selectedReplies = analyzedReplies
            .sort((a, b) => b.relevanceScore - a.relevanceScore)
            .slice(0, 3);

        // 保存选中的评论
        adjustments.suggestions = selectedReplies;
        adjustments.raw_suggestions = selectedReplies.map(r => r.content);

        return adjustments;
    }

    _calculateRelevanceScore(analysis) {
        let score = 0;

        // 根据影响程度加分
        if (analysis.analysis.impact === 'high') score += 3;
        else if (analysis.analysis.impact === 'medium') score += 2;
        else score += 1;

        // 根据类型加分
        if (analysis.analysis.type.includes('TECH')) score += 2;  // 技术相关
        if (analysis.analysis.type.includes('CAREER')) score += 2;  // 职业发展
        if (analysis.analysis.type.includes('LIFE_EVENT')) score += 2;  // 重大生活事件
        if (analysis.analysis.type.includes('RELATIONSHIP')) score += 2;  // 人际关系

        // 根据关键词数量加分
        score += Math.min(analysis.analysis.keywords.length, 3);  // 最多加3分

        // 根据评论长度适当加分（避免过短的评论）
        const contentLength = analysis.content.length;
        if (contentLength > 50) score += 2;
        else if (contentLength > 20) score += 1;

        // 根据情绪倾向加分（优先选择积极或消极的评论，而不是中性的）
        if (analysis.analysis.mood !== 'neutral') score += 1;

        return score;
    }

    _getSuggestionType(content) {
        // 分析评论类型
        const types = [];
        
        if (this._containsAnyTechTerms(content)) {
            types.push('TECH');
        }
        if (this._containsRelationshipContext(content)) {
            types.push('RELATIONSHIP');
        }
        if (this._containsCareerContext(content)) {
            types.push('CAREER');
        }
        if (this._containsLifeEventContext(content)) {
            types.push('LIFE_EVENT');
        }

        return types.length > 0 ? types : ['GENERAL'];
    }

    _analyzeImpact(content) {
        // 分析评论的影响程度
        const impactWords = {
            high: ['必须', '一定要', '强烈建议', 'must', 'should', 'need to'],
            medium: ['建议', '可以', '不错', 'suggest', 'could', 'maybe'],
            low: ['或许', '可能', '试试', 'perhaps', 'might', 'try']
        };

        for (const [level, words] of Object.entries(impactWords)) {
            if (words.some(word => content.includes(word))) {
                return level;
            }
        }

        return 'medium';  // 默认中等影响
    }

    _extractKeywords(content) {
        // 提取关键词
        const keywords = [];
        
        // 技术相关
        if (content.includes('ai') || content.includes('人工智能')) keywords.push('AI');
        if (content.includes('研究') || content.includes('research')) keywords.push('RESEARCH');
        if (content.includes('项目') || content.includes('project')) keywords.push('PROJECT');
        
        // 人际关系
        if (content.includes('爱情') || content.includes('love')) keywords.push('LOVE');
        if (content.includes('家庭') || content.includes('family')) keywords.push('FAMILY');
        if (content.includes('朋友') || content.includes('friend')) keywords.push('FRIEND');
        
        // 职业发展
        if (content.includes('工作') || content.includes('work')) keywords.push('WORK');
        if (content.includes('创业') || content.includes('startup')) keywords.push('STARTUP');
        if (content.includes('公司') || content.includes('company')) keywords.push('COMPANY');
        
        // 生活变化
        if (content.includes('改变') || content.includes('change')) keywords.push('CHANGE');
        if (content.includes('冒险') || content.includes('adventure')) keywords.push('ADVENTURE');
        if (content.includes('旅行') || content.includes('travel')) keywords.push('TRAVEL');

        return keywords;
    }

    _containsAnyTechTerms(content) {
        // 检查是否包含技术相关内容
        return content.includes('ai') || 
               content.includes('技术') || 
               content.includes('研究') || 
               content.includes('开发') ||
               content.includes('项目') ||
               content.includes('学习') ||
               content.includes('tech') ||
               content.includes('research') ||
               content.includes('development') ||
               content.includes('coding');
    }

    _containsRelationshipContext(content) {
        // 检查是否涉及人际关系
        return content.includes('朋友') ||
               content.includes('家人') ||
               content.includes('关系') ||
               content.includes('感情') ||
               content.includes('相处') ||
               content.includes('friend') ||
               content.includes('family') ||
               content.includes('relationship') ||
               content.includes('love') ||
               content.includes('partner');
    }

    _containsCareerContext(content) {
        // 检查是否涉及职业发展
        return content.includes('工作') ||
               content.includes('职业') ||
               content.includes('事业') ||
               content.includes('发展') ||
               content.includes('晋升') ||
               content.includes('career') ||
               content.includes('job') ||
               content.includes('work') ||
               content.includes('promotion') ||
               content.includes('business');
    }

    _containsLifeEventContext(content) {
        // 检查是否涉及生活变化
        return content.includes('改变') ||
               content.includes('搬家') ||
               content.includes('旅行') ||
               content.includes('决定') ||
               content.includes('尝试') ||
               content.includes('change') ||
               content.includes('move') ||
               content.includes('travel') ||
               content.includes('decision') ||
               content.includes('try');
    }

    _analyzeMood(content) {
        // 这里只做简单的情绪判断，主要依靠 AI 理解完整语境
        if (content.includes('不') || 
            content.includes('别') || 
            content.includes('停') || 
            content.includes('don\'t') || 
            content.includes('stop') || 
            content.includes('no')) {
            return 'negative';
        }
        
        if (content.includes('要') || 
            content.includes('去') || 
            content.includes('试试') || 
            content.includes('可以') || 
            content.includes('should') || 
            content.includes('try') || 
            content.includes('can')) {
            return 'positive';
        }

        return 'neutral';
    }

    async _fileExists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
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
            // 读取当前数据
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            const storyData = JSON.parse(data);

            // 获取实际发送的推文总数
            const { totalTweets: sentTotalTweets } = await this._getTweetsInfo();

            // 检查是否达到年龄上限
            const calculatedAge = this._calculateAge(sentTotalTweets);
            if (calculatedAge >= this.storyConfig.setting.endAge) {
                this.logger.info('Story has reached end age, no more tweets will be saved');
                return {
                    tweets: [],
                    currentAge: this.storyConfig.setting.endAge,
                    totalTweets: sentTotalTweets
                };
            }

            // 计算新的总推文数和年龄
            const newTotalTweets = sentTotalTweets + tweets.length;
            const newAge = this._calculateAge(newTotalTweets);

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
            storyData.stats.totalTweets = newTotalTweets;
            storyData.stats.yearProgress = this._calculateYearProgress(newTotalTweets).progress;

            // 更新���据
            storyData.metadata.currentAge = Number(safeAge.toFixed(2));
            storyData.metadata.lastUpdate = new Date().toISOString();
            storyData.metadata.currentPhase = this._getCurrentPhase(safeAge);

            // 更新个人状态
            this._updatePersonalStatus(storyData, safeAge);

            // 保存更新后的数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(storyData, null, 2),
                'utf8'
            );

            this.logger.info('Saved new tweets', {
                count: tweets.length,
                currentAge: Number(safeAge.toFixed(2)),
                totalTweets: newTotalTweets,
                newTweets: newTweets.length
            });

            // 创建备份
            await this._createBackup();

            return {
                tweets: newTweets,
                currentAge: safeAge,
                totalTweets: newTotalTweets
            };
        } catch (error) {
            this.logger.error('Error saving tweets', error);
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
                title: '结婚',
                description: '与相恋多年的伴侣共同开启人生的新篇章。'
            },
            {
                age: 34,
                type: 'family',
                title: '喜得贵子',
                description: '迎来新角色，成为一名父亲。'
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
        const adjustments = context.story_adjustments;
        let prompt = '';
        
        // 获取评论者
        const commenters = new Set();  // 使用Set避免重复
        try {
            if (adjustments && adjustments.suggestions) {
                // 只获取被分析的评论者
                for (const suggestion of adjustments.suggestions) {
                    if (suggestion.username) {
                        commenters.add(`@${suggestion.username}`);
                    }
                }
            }
        } catch (error) {
            console.error('Error getting commenters:', error);
        }
        
        // 计算时间流逝
        const timeInfo = this._calculateTimeProgression(context.tweet_count);
        
        if (adjustments) {
            const suggestions = adjustments.suggestions.map(suggestion => {
                const { content, analysis } = suggestion;
                return `Comment: ${content}\nImpact: ${analysis.impact}\nType: ${analysis.type.join(', ')}\nKeywords: ${analysis.keywords.join(', ')}`;
            }).join('\n\n');

            prompt = `[HIGH PRIORITY: Respond to the following comments immediately]\n\n${suggestions}\n\nRequirements:\n1. Must take immediate action to respond to comments\n2. Comment suggestions take priority over original plot\n3. Let comments drive significant story changes\n\n`;
        }

        // 添加评论者@提示
        const commentersStr = Array.from(commenters).join(' ');
        if (commenters.size > 0) {
            prompt += `IMPORTANT NOTES:
1. Each tweet MUST start with ${commentersStr}
2. DO NOT mention (@) any other users
3. ONLY mention the users listed above\n\n`;
        }

        prompt += `Time Context:
- Current Season: ${timeInfo.season}
- Time Span: These 4 tweets will cover a week
- Time Note: Content should reflect seasonal changes and time progression\n\n`;

        prompt += `Recent Developments:\n${context.recent_tweets.map(t => `- ${t.text}`).join('\n')}\n\n`;
        prompt += `Current Progress:\n${context.latest_digest?.content || 'Starting a new chapter...'}\n\n`;
        prompt += `Writing Requirements:
1. Comment suggestions have highest priority
2. Must directly respond to comments
3. Let comments create major turning points
4. Content should show time progression
5. Consider seasonal elements
6. 4 tweets should tell a continuous and progressive story
7. DO NOT mention any users except those listed above\n\n`;

        prompt += `Format Requirements:
Please generate 4 tweets in the following format:

TWEET1
${commenters.size > 0 ? commentersStr + ' ' : ''}[First tweet content in English]

TWEET2
${commenters.size > 0 ? commentersStr + ' ' : ''}[Second tweet content in English]

TWEET3
${commenters.size > 0 ? commentersStr + ' ' : ''}[Third tweet content in English]

TWEET4
${commenters.size > 0 ? commentersStr + ' ' : ''}[Fourth tweet content in English]

Important Notes:
- Each tweet MUST start with ${commentersStr}
- DO NOT mention any other users
- Total length of each tweet (including @usernames) must not exceed 280 characters
- Directly respond to comment suggestions
- Describe specific actions and changes
- Show time continuity
- Do not include specific dates or times
- All tweet content must be in English`;

        return prompt;
    }

    _calculateTweetTimeSpans(timeInfo) {
        // 解析当前日期
        const currentDate = new Date(timeInfo.currentTime);
        const spans = [];
        let totalDays = 0;

        // 为每条推文生成时间跨度
        for (let i = 0; i < 4; i++) {
            const days = Math.floor(Math.random() * 2) + 1; // 1-2天
            totalDays += days;
            
            const tweetDate = new Date(currentDate);
            tweetDate.setDate(tweetDate.getDate() + totalDays);
            
            // 生成时间描述
            const timeDesc = this._generateTimeDescription(tweetDate, i === 0 ? '今天' : `${totalDays}天后`);
            spans.push(timeDesc);
        }

        return {
            spans,
            totalSpan: `${totalDays}天`
        };
    }

    _generateTimeDescription(date, timeOffset) {
        const hours = Math.floor(Math.random() * 24);
        const timeOfDay = hours < 6 ? '凌晨' :
                         hours < 12 ? '上午' :
                         hours < 18 ? '下午' : '晚上';
        
        return `${timeOffset}${timeOfDay}，${date.toLocaleDateString('zh-CN')}`;
    }

    _calculateTimeProgression(tweetCount) {
        // 基准时间：2024年
        const baseYear = 2024;
        const baseMonth = 1;
        
        // 计算时间流逝
        // 假设每4条推文代表一周的时间
        const weeksPassed = Math.floor(tweetCount / 4);
        const currentDate = new Date(baseYear, baseMonth - 1);
        currentDate.setDate(currentDate.getDate() + (weeksPassed * 7));
        
        // 获取季节
        const month = currentDate.getMonth() + 1;
        let season;
        if (month >= 3 && month <= 5) season = '春季';
        else if (month >= 6 && month <= 8) season = '夏季';
        else if (month >= 9 && month <= 11) season = '秋季';
        else season = '冬季';
        
        // 计算距离上一条推文的时间
        const daysPassed = Math.floor(Math.random() * 3) + 1;  // 1-3天
        const timePassedText = `${daysPassed}天`;
        
        return {
            currentTime: currentDate.toLocaleDateString('zh-CN'),
            season: season,
            timePassed: timePassedText
        };
    }

    _getPersonalContext(currentAge) {
        const data = require('../data/XaviersSim.json');
        const personal = data.personal;
        const romantic = personal.relationships.romantic;
        const familyLife = personal.family_life;
        const lifestyle = personal.lifestyle;

        let context = `
个人状态：
- ���情：${romantic.status === 'single' ? '单身' : '有恋人'}
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
                .sort((a, b) => b.time - a.time);  // 按时降序排序

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