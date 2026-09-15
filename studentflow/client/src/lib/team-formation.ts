import type { User } from "@/types";

export type TeamFormationPreview = {
  name: string;
  dateIndex: number;
  scheduleAt: string;
  leaderId: string;
  members: User[];
  requiredPeople?: number;
  roleDescription?: string;
};

export type TeamFormationPlan = {
  teams: TeamFormationPreview[];
  repeatableMemberIds: string[];
  warnings: string[];
};

function gradeNumber(grade: string) {
  const parsed = Number.parseInt(grade, 10);
  return Number.isNaN(parsed) ? 99 : parsed;
}

function scheduleAt(date: string, startTime?: string) {
  return `${date}T${startTime || "09:00"}`;
}

function dateLabel(value: string) {
  const [, month, day] = value.split("-").map(Number);
  return `${month}월 ${day}일`;
}

/** 선택한 날짜마다 모든 참여자를 한 번씩, 가능한 균등하게 배치한다. */
export function createFormationPlan(input: {
  people: User[];
  teamsPerDay: number;
  dates: string[];
  requirements?: Array<{
    name: string;
    peopleCount: number;
    roleDescription: string;
    startTime?: string;
    endTime?: string;
    operationDates?: string[];
  }>;
}): TeamFormationPlan {
  const people = [...input.people].sort(
    (left, right) =>
      gradeNumber(left.grade) - gradeNumber(right.grade) ||
      left.department.localeCompare(right.department, "ko") ||
      left.name.localeCompare(right.name, "ko")
  );
  const dates = Array.from(new Set(input.dates)).sort();
  if (!people.length || !dates.length) {
    return { teams: [], repeatableMemberIds: [], warnings: [] };
  }

  const requirements = input.requirements?.length ? input.requirements : undefined;
  const teams: TeamFormationPreview[] = [];
  const warnings: string[] = [];

  dates.forEach((date, dateIndex) => {
    const dayRequirements = requirements?.filter(
      requirement =>
        requirement.operationDates === undefined ||
        requirement.operationDates.includes(date)
    );
    const teamsPerDay = dayRequirements?.length ?? Math.max(1, Math.min(20, input.teamsPerDay));
    const dayTeams = Array.from({ length: teamsPerDay }, (_, teamIndex) => ({
      name:
        dates.length > 1
          ? `${dateLabel(date)} ${dayRequirements?.[teamIndex]?.name ?? `${teamIndex + 1}조`}`
          : (dayRequirements?.[teamIndex]?.name ?? `${teamIndex + 1}조`),
      dateIndex,
      scheduleAt: scheduleAt(date, dayRequirements?.[teamIndex]?.startTime),
      leaderId: "",
      members: [] as User[],
      requiredPeople: dayRequirements?.[teamIndex]?.peopleCount,
      roleDescription: dayRequirements?.[teamIndex]?.roleDescription,
    }));
    const rotatedPeople = people.map(
      (_, index) => people[(index + dateIndex) % people.length]
    );
    let personIndex = 0;
    dayTeams.forEach(team => {
      const capacity = team.requiredPeople ?? Math.ceil(rotatedPeople.length / teamsPerDay);
      team.members.push(...rotatedPeople.slice(personIndex, personIndex + capacity));
      personIndex += capacity;
    });
    dayTeams.forEach(team => {
      team.leaderId = team.members[0]?.id ?? "";
      if (!team.members.length) {
        warnings.push(
          `${team.name}이 비어 있어요. 학생을 추가하거나 하루 조 개수를 줄여 주세요.`
        );
      }
    });
    teams.push(...dayTeams);
  });

  return {
    teams,
    repeatableMemberIds:
      dates.length > 1 ? people.map(person => person.id) : [],
    warnings: Array.from(new Set(warnings)),
  };
}
