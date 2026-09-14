import type { AnchorHTMLAttributes } from "react";

/**
 * 일반 문서 링크입니다. 클릭을 가로채지 않으므로 서버에서 새 HTML 문서를 받습니다.
 */
export function Link({
  href,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  return <a href={href} {...props} />;
}
