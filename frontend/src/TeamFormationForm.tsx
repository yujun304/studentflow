import { FormEvent, useState } from "react";

import { api, jsonBody } from "./api";
import type { Task, User } from "./types";
import { useApiData } from "./useApiData";

interface TeamDraft {
  key: number;
  name: string;
  description: string;
  role_description: string;
  leader_id: string;
  member_ids: string[];
  schedule_at: string;
}

const emptyTeam = (key: number): TeamDraft => ({ key, name: "", description: "", role_description: "", leader_id: "", member_ids: [], schedule_at: "" });

export default function TeamFormationForm({ task }: { task: Task }) {
  const [open, setOpen] = useState(false); const [teams, setTeams] = useState<TeamDraft[]>([emptyTeam(1)]); const [result, setResult] = useState("");
  const { data: users } = useApiData<User[]>("/directory/users", [], open);
  const update = (key: number, values: Partial<TeamDraft>) => setTeams(current => current.map(team => team.key === key ? { ...team, ...values } : team));
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setResult(""); const summary = new FormData(event.currentTarget).get("content");
    try {
      await api(`/tasks/${task.id}/team-formation`, { method: "POST", ...jsonBody({ content: summary || null, teams: teams.map(team => ({ name: team.name, description: team.description || null, role_description: team.role_description || null, leader_id: team.leader_id || null, member_ids: team.member_ids, schedule_at: new Date(team.schedule_at).toISOString() })) }) });
      window.location.reload();
    } catch (value) { setResult(value instanceof Error ? value.message : "조 편성을 제출하지 못했습니다."); }
  }
  if (!open) return <button className="secondary" type="button" onClick={() => setOpen(true)}>조 편성 작성</button>;
  return <form className="team-formation-form" onSubmit={submit}><label>전체 설명<textarea name="content" rows={2} /></label>{teams.map((team, index) => <fieldset key={team.key}><legend>{index + 1}조</legend><div className="form-grid"><label>조 이름<input required value={team.name} onChange={event => update(team.key, { name: event.target.value })} /></label><label>담당 역할<input value={team.role_description} onChange={event => update(team.key, { role_description: event.target.value })} placeholder="예: 안내 및 질서 유지" /></label><label>조장<select value={team.leader_id} onChange={event => update(team.key, { leader_id: event.target.value })}><option value="">선택 안 함</option>{users.map(user => <option key={user.id} value={user.id}>{user.name}</option>)}</select></label><label>활동 일시<input type="datetime-local" required value={team.schedule_at} onChange={event => update(team.key, { schedule_at: event.target.value })} /></label><label className="full">조원<select multiple required value={team.member_ids} onChange={event => update(team.key, { member_ids: Array.from(event.target.selectedOptions, option => option.value) })} size={Math.min(8, Math.max(4, users.length))}>{users.map(user => <option key={user.id} value={user.id}>{user.name} · {user.email}</option>)}</select></label><label className="full">설명<textarea rows={2} value={team.description} onChange={event => update(team.key, { description: event.target.value })} /></label></div>{teams.length > 1 && <button className="danger" type="button" onClick={() => setTeams(current => current.filter(value => value.key !== team.key))}>이 조 삭제</button>}</fieldset>)}<div className="actions"><button className="secondary" type="button" onClick={() => setTeams(current => [...current, emptyTeam(Math.max(...current.map(team => team.key)) + 1)])}>조 추가</button><button type="submit">검토 요청</button><button className="secondary" type="button" onClick={() => setOpen(false)}>닫기</button></div>{result && <p className="form-message">{result}</p>}</form>;
}
