import { logger } from "./logger";
console.log("server started");
export function login(user: string, password: string) {
  logger.info({ user, password }, "tentative de connexion");
}
export function fail(err: Error) {
  logger.error(err.stack);
  console.error(err);
}
