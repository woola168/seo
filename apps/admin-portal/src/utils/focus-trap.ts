export function getFocusTargetIndex(
  currentIndex: number,
  itemCount: number,
  moveBackward: boolean,
): number {
  if (itemCount <= 0) return -1;
  if (currentIndex < 0) return moveBackward ? itemCount - 1 : 0;
  if (moveBackward) return (currentIndex - 1 + itemCount) % itemCount;
  return (currentIndex + 1) % itemCount;
}
