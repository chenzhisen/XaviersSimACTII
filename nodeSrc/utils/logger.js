const winston = require('winston');
const { Config } = require('./config');

class Logger {
    constructor(component) {
        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.json()
            ),
            transports: [
                new winston.transports.Console(),
                new winston.transports.File({ 
                    filename: `logs/${component}.log`
                })
            ]
        });
    }

    info(message, meta = {}) {
        this.logger.info(message, meta);
    }

    error(message, error) {
        this.logger.error(message, {
            error: error.toString(),
            stack: error.stack
        });
    }

    debug(message, meta = {}) {
        this.logger.debug(message, meta);
    }

    warn(message, meta = {}) {
        this.logger.warn(message, meta);
    }
}

module.exports = { Logger }; 