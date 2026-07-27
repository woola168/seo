export function parseGeoTagValues(value: string): string[] {
  return value
    .split(/[\r\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}
