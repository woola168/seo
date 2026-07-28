export function formatSentimentRatio(ratio: number | null): string {
  return ratio === null ? "—" : `${ratio.toFixed(1)}:1.0`;
}
