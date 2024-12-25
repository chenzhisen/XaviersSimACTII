const { Logger } = require('./logger');

class AICompletion {
    constructor(client, model) {
        this.logger = new Logger('ai');
        this.client = client;
        this.model = model;
    }

    async getCompletion(systemPrompt, userPrompt) {
        try {
            // 模拟 AI 生成
            const scenes = [
                this._generateScene('工作场景'),
                this._generateScene('生活场景'),
                this._generateScene('社交场景')
            ];

            // 将场景转换为推文格式
            const tweets = scenes.flatMap(scene => scene.map((text, index) => ({
                text,
                id: `tweet_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
            })));

            return tweets;
        } catch (error) {
            this.logger.error('AI completion failed', error);
            throw error;
        }
    }

    _generateScene(type) {
        const templates = {
            '工作场景': [
                [
                    "1: 凌晨3点，第108次修改代码。这个bug太难找了，但我知道答案就在眼前。泡一杯咖啡，继续战斗。#coding #startup",
                    "2: 等等！突然发现一个有趣的pattern，如果把这个算法改成递归...手有点抖，这可能是个突破口！",
                    "3: 成功了！！！重构后性能提升300%。看着终端里的测试全部通过，这感觉比喝了十杯咖啡还让人兴奋！",
                    "4: 有人说创业是场马拉松，但对我来说，每一个这样的时刻都让这段旅程值得。明天继续，$XVI的未来就在代码中。"
                ]
            ],
            '生活场景': [
                [
                    "1: 今天遇到一个超可爱的场景！楼下咖啡店的猫咪趴在我笔记本上，死活不让我写代码。😂 #CatLife",
                    "2: 它对着屏幕上的光标又抓又挠，搞得我哭笑不得。最后只能一只手撸猫，一只手敲代码。多任务处理能力++",
                    "3: 结果！这个小家伙居然帮我发现了一个bug！它踩键盘时触发了一个边界情况。谁说猫不懂编程？😅",
                    "4: 决定给它取名\"Debug\"，以后就是我们团队的首席测试喵了。投资人说要有好运气，也许这就是了？🐱 #StartupLife"
                ]
            ],
            '社交场景': [
                [
                    "1: 老友聚会，他们笑称我是\"成功人士\"。其实他们不知道，最成功的是这些年友情始终如一。",
                    "2: 还记得当年挤在出租屋写代码，大家轮流给我送饭。现在我请他们吃饭，他们却说：\"能不能换回那时的盒饭？\"",
                    "3: 朋友说我变了，变得更忙了。但有一点永远不会变，就是遇到困难时第一个想到的还是他们。",
                    "4: 真正的财富是那些在你还一无所有时，就愿意陪你疯狂的人。#Friendship #感恩"
                ]
            ]
        };

        return templates[type][0];
    }
}

module.exports = { AICompletion }; 