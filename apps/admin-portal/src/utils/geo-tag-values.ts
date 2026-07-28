export function parseGeoTagValues(value: string): string[] {
  return value
    .split(/[\r\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function mergeGeoTagValues(
  current: readonly string[],
  value: string,
  maxTags?: number,
): string[] {
  const merged = Array.from(new Set([...current, ...parseGeoTagValues(value)]));
  return maxTags === undefined ? merged : merged.slice(0, Math.max(0, maxTags));
}
