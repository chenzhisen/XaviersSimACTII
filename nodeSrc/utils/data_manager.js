const fs = require('fs').promises;
const path = require('path');
const { Logger } = require('./logger');

class DataManager {
    constructor(isProduction = false) {
        this.logger = new Logger('data');
        this.isProduction = isProduction;

        this.paths = {
            dataDir: path.resolve(__dirname, '..', 'data'),
            mainFile: path.resolve(__dirname, '..', 'data', 'XaviersSim.json'),
            backupDir: path.resolve(__dirname, '..', 'data', 'backups')
        };
    }

    async initialize() {
        try {
            // 确保目录存在
            await fs.mkdir(this.paths.dataDir, { recursive: true });
            await fs.mkdir(this.paths.backupDir, { recursive: true });

            // 检查主文件是否存在
            try {
                await fs.access(this.paths.mainFile);
            } catch {
                // 创建初始文件
                await this._createInitialFile();
            }

            return true;
        } catch (error) {
            this.logger.error('Initialization failed', error);
            throw error;
        }
    }

    async getData() {
        try {
            const data = await fs.readFile(this.paths.mainFile, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            this.logger.error('Error reading data', error);
            throw error;
        }
    }

    async saveData(data) {
        try {
            // 创建备份
            await this._createBackup();

            // 保存新数据
            await fs.writeFile(
                this.paths.mainFile,
                JSON.stringify(data, null, 2),
                'utf8'
            );

            this.logger.info('Data saved successfully');
            return true;
        } catch (error) {
            this.logger.error('Error saving data', error);
            throw error;
        }
    }

    async _createBackup() {
        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const backupPath = path.join(
                this.paths.backupDir,
                `XaviersSim_${timestamp}.json`
            );

            await fs.copyFile(this.paths.mainFile, backupPath);
            
            // 清理旧备份（保留最近10个）
            const backups = await fs.readdir(this.paths.backupDir);
            if (backups.length > 10) {
                const oldestBackup = backups.sort()[0];
                await fs.unlink(path.join(this.paths.backupDir, oldestBackup));
            }

            return true;
        } catch (error) {
            this.logger.error('Backup creation failed', error);
            return false;
        }
    }

    async _createInitialFile() {
        const initialData = require('../data/XaviersSim.json');
        await this.saveData(initialData);
        this.logger.info('Created initial data file');
    }
}

module.exports = { DataManager }; 