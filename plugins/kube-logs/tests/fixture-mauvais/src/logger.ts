import pino from "pino";
import winston from "winston";
// console.log("commenté : ne doit pas compter")
export const logger = pino({ level: "info" }, pino.destination("/var/log/app/app.log"));
export const legacy = winston.createLogger({ transports: [new winston.transports.File({ filename: "app.log" })] });
