import { describe, expect, it } from "vitest";
import { createFormationPlan } from "./team-formation";
import type { User } from "@/types";

const people: User[] = [
  {
    id: "a",
    name: "가람",
    role: "MEMBER",
    department: "기획부",
    grade: "1학년",
    initials: "가",
  },
  {
    id: "b",
    name: "나래",
    role: "MEMBER",
    department: "홍보부",
    grade: "2학년",
    initials: "나",
  },
  {
    id: "c",
    name: "다온",
    role: "MEMBER",
    department: "홍보부",
    grade: "3학년",
    initials: "다",
  },
  {
    id: "d",
    name: "라온",
    role: "MEMBER",
    department: "체육부",
    grade: "1학년",
    initials: "라",
  },
];

describe("createFormationPlan", () => {
  it("선택한 모든 날짜에 참여자를 하루 조 개수만큼 나눈다", () => {
    const plan = createFormationPlan({
      people,
      teamsPerDay: 2,
      dates: ["2026-08-24", "2026-08-17", "2026-08-24"],
    });

    expect(plan.teams).toHaveLength(4);
    for (let dateIndex = 0; dateIndex < 2; dateIndex += 1) {
      const dayMembers = plan.teams
        .filter(team => team.dateIndex === dateIndex)
        .flatMap(team => team.members.map(member => member.id));
      expect(dayMembers.sort()).toEqual(["a", "b", "c", "d"]);
    }
    expect(plan.repeatableMemberIds).toEqual(
      expect.arrayContaining(["a", "b", "c", "d"])
    );
    expect(plan.teams[0].scheduleAt).toBe("2026-08-17T09:00");
  });

  it("회의에서 확정한 조별 시작 시간을 자동 편성에 사용한다", () => {
    const plan = createFormationPlan({
      people,
      teamsPerDay: 2,
      dates: ["2026-09-25"],
      requirements: [
        { name: "등교조", peopleCount: 2, roleDescription: "대여", startTime: "07:40", endTime: "08:30" },
        { name: "하교조", peopleCount: 2, roleDescription: "반납", startTime: "15:20", endTime: "16:20" },
      ],
    });
    expect(plan.teams.map(team => team.scheduleAt)).toEqual(["2026-09-25T07:40", "2026-09-25T15:20"]);
  });

  it("인원보다 조가 많으면 빈 조를 안내한다", () => {
    const plan = createFormationPlan({
      people: people.slice(0, 2),
      teamsPerDay: 3,
      dates: ["2026-08-17"],
    });

    expect(plan.teams).toHaveLength(3);
    expect(plan.warnings).toEqual([expect.stringContaining("비어 있어요")]);
  });
});
