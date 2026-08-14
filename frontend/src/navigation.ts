export const PAGE_PATHS = {
  dashboard: "/",
  login: "/login/",
  events: "/events/",
  tasks: "/tasks/",
  taskEditor: "/tasks/editor/",
  notices: "/notices/",
  noticeEditor: "/notices/editor/",
  reviews: "/reviews/",
  more: "/more/",
  admin: "/admin/",
} as const;

export type PageId =
  | "dashboard"
  | "login"
  | "events"
  | "tasks"
  | "task-editor"
  | "notices"
  | "notice-editor"
  | "reviews"
  | "more"
  | "admin";

const pageIds = new Set<PageId>([
  "dashboard",
  "login",
  "events",
  "tasks",
  "task-editor",
  "notices",
  "notice-editor",
  "reviews",
  "more",
  "admin",
]);

export function readPageId(): PageId {
  const page = document.body.dataset.page as PageId | undefined;
  return page && pageIds.has(page) ? page : "dashboard";
}

export function activeSection(page: PageId): Exclude<PageId, "login" | "task-editor" | "notice-editor"> {
  if (page === "task-editor") return "tasks";
  if (page === "notice-editor") return "notices";
  if (page === "login") return "dashboard";
  return page;
}
