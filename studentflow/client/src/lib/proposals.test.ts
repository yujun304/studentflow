import { describe, expect, it } from "vitest";
import { categoryLabel, isProposalCompleted, proposalIdFromPath, statusLabel } from "./proposals";

describe("proposal UI contracts", () => {
  it("offers only the four feedback categories", () => {
    expect(Object.values(categoryLabel)).toEqual(["좋은 점", "걱정되는 점", "바꾸고 싶은 점", "새로운 아이디어"]);
  });
  it("shows discussion, re-review, and confirmed states", () => {
    expect(statusLabel).toEqual({ DISCUSSING: "의견 수렴 중", RE_REVIEW: "재검토 중", CONFIRMED: "확정" });
  });
  it("reads proposal detail ids without accepting unrelated routes", () => {
    expect(proposalIdFromPath("/proposals/abc-123")).toBe("abc-123");
    expect(proposalIdFromPath("/proposals/abc-123/")).toBe("abc-123");
    expect(proposalIdFromPath("/community/abc-123")).toBeNull();
  });
});

describe("proposal completion", () => {
  it("treats only terminal workflow stages as completed", () => {
    expect(isProposalCompleted({ planning_stage: "APPROVED" })).toBe(false);
    expect(isProposalCompleted({ planning_stage: "ASSIGNING_TEAMS" })).toBe(false);
    expect(isProposalCompleted({ planning_stage: "SCHEDULED" })).toBe(true);
    expect(isProposalCompleted({ planning_stage: "REJECTED" })).toBe(true);
  });
});
