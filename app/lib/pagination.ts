// Provides page list helpers.
const DEFAULT_MAX_VISIBLE_PAGES = 6;

export type CompactPageItem = number | "ellipsis-left" | "ellipsis-right";

export function getCompactPageItems(
  currentPage: number,
  pageCount: number,
  maxVisiblePages = DEFAULT_MAX_VISIBLE_PAGES,
): CompactPageItem[] {
  if (pageCount <= maxVisiblePages) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const siblingCount = 1;
  const leftSibling = Math.max(currentPage - siblingCount, 2);
  const rightSibling = Math.min(currentPage + siblingCount, pageCount - 1);
  const showLeftEllipsis = leftSibling > 2;
  const showRightEllipsis = rightSibling < pageCount - 1;

  if (!showLeftEllipsis) {
    return [1, 2, 3, 4, 5, "ellipsis-right", pageCount];
  }

  if (!showRightEllipsis) {
    return [
      1,
      "ellipsis-left",
      pageCount - 4,
      pageCount - 3,
      pageCount - 2,
      pageCount - 1,
      pageCount,
    ];
  }

  return [
    1,
    "ellipsis-left",
    leftSibling,
    currentPage,
    rightSibling,
    "ellipsis-right",
    pageCount,
  ];
}
