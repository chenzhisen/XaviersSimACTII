const OpenAI = require('openai');
const { Logger } = require('./logger');
const { Config } = require('./config');

class AICompletion {
    constructor(client, model) {
        this.model = model;
        this.client = client;

        // 模拟回复模板
        this.mockResponses = {
            // 工作场景
            work: [
                `TWEET 1: 凌晨3点，第108次修改代码。这个bug太难找了，但我知道答案就在眼前。泡一杯咖啡，继续战斗。#coding #startup

TWEET 2: 等等！突然发现一个有趣的pattern，如果把这个算法改成递归...手有点抖，这可能是个突破口！

TWEET 3: 成功了！！！重构后性能提升300%。看着终端里的测试全部通过，这感觉比喝了十杯咖啡还让人兴奋！

TWEET 4: 有人说创业是场马拉松，但对我来说，每一个这样的时刻都让这段旅程值得。明天继续，$XVI的未来就在代码中。`
            ],

            // 生活趣事
            life: [
                `TWEET 1: 今天遇到一个超可爱的场景！楼下咖啡店的猫咪趴在我笔记本上，死活不让我写代码。😂 #CatLife

TWEET 2: 它对着屏幕上的光标又抓又挠，搞得我哭笑不得。最后只能一只手撸猫，一只手敲代码。多任务处理能力++

TWEET 3: 结果！这个小家伙居然帮我发现了一个bug！它踩键盘时触发了一个边界情况。谁说猫不懂编程？😅

TWEET 4: 决定给它取名"Debug"，以后就是我们团队的首席测试喵了。投资人说要有好运气，也许这就是了？🐱 #StartupLife`
            ],

            // 感情故事
            romance: [
                `TWEET 1: 难得休息，约会去咖啡店。她看着我调试代码，突然问："为什么你写代码时总是在笑？" #Love

TWEET 2: 愣住了。原来在解决技术难题时，我会不自觉地微笑。她说这是她最喜欢我的时刻，因为看起来很快乐。

TWEET 3: "但是我更希望你能多陪陪我。"她说。是啊，这几个月太忙了，亏欠了很多。有时候追逐梦想，却忘了身边人。

TWEET 4: 决定从今天起，每周抽一天完全属于她。再忙的创业，也要记得生活和爱情。平衡很重要。#WorkLifeBalance`
            ],

            // 生活感悟
            reflection: [
                `TWEET 1: 清晨跑步时看到日出，突然想到很多。创业三年，经历过太多起起落落，但从未放弃。

TWEET 2: 昨天一个早期用户给我发消息，说因为用了我们的产品，他的生活变得更好了。那一刻，所有熬夜都值得。

TWEET 3: 路过以前经常写代码的咖啡店，现在已经搬进了新办公室。生活总是在不经意间，悄悄地向前。

TWEET 4: 也许成功不是登上顶峰，而是在路上时仍保持热爱。继续做一个快乐的创造者。 #生活感悟 #创业日记`
            ],

            // 友情日常
            friendship: [
                `TWEET 1: 老友聚会，他们笑称我是"成功人士"。其实他们不知道，最成功的是这些年友情始终如一。

TWEET 2: 还记得当年挤在出租屋写代码，大家轮流给我送饭。现在我请他们吃饭，他们却说："能不能换回那时的盒饭？"

TWEET 3: 朋友说我变了，变得更忙了。但有一点永远不会变，就是遇到困难时第一个想到的还是他们。

TWEET 4: 真正的财富是那些在你还一无所有时，就愿意陪你疯狂的人。#Friendship #感恩`
            ]
        };
    }

    async getCompletion(systemPrompt, userPrompt, options = {}) {
        console.log('Generating mock response for prompt:', userPrompt);

        // 根据prompt内容选择合适的模拟回复
        let response;
        
        // 随机选择生活或工作场景
        const sceneTypes = ['work', 'life', 'romance', 'reflection', 'friendship'];
        const sceneType = sceneTypes[Math.floor(Math.random() * sceneTypes.length)];
        
        response = this._getRandomResponse(sceneType);

        // 模拟API延迟
        await new Promise(resolve => setTimeout(resolve, 1000));

        return response;
    }

    _getRandomResponse(type) {
        const responses = this.mockResponses[type];
        return responses[Math.floor(Math.random() * responses.length)];
    }
}

module.exports = { AICompletion }; 