import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { activeSection, PAGE_PATHS } from "./navigation";

describe("StudentFlow MPA navigation", () => {
  it("uses distinct document paths for primary pages", () => {
    const paths = [PAGE_PATHS.dashboard, PAGE_PATHS.events, PAGE_PATHS.tasks, PAGE_PATHS.notices, PAGE_PATHS.more];
    expect(new Set(paths).size).toBe(paths.length);
    expect(PAGE_PATHS.tasks).toBe("/tasks/");
  });

  it("keeps editor documents in their parent navigation section", () => {
    expect(activeSection("task-editor")).toBe("tasks");
    expect(activeSection("notice-editor")).toBe("notices");
  });
});
