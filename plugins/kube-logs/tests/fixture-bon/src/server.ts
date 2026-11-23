import { logger } from "./logger";
// on ne logue jamais le password ici
export function fail(err: Error, tokenCount: number) {
  logger.error({ err }, "échec");
  logger.info({ count: tokenCount }, "jetons recalculés");
  const url = "http://example.org"; // une URL avec // ne casse pas le parsing
}
