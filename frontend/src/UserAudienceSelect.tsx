import { useState } from "react";

import type { User } from "./types";

interface Props {
  users: User[];
  name: string;
  label: string;
  defaultValue?: string[];
  required?: boolean;
}

export default function UserAudienceSelect({
  users,
  name,
  label,
  defaultValue = [],
  required = false,
}: Props) {
  const [selected, setSelected] = useState<string[]>(defaultValue);
  const activeUsers = users.filter((user) => user.is_active);

  function selectUsers(nextUsers: User[]) {
    setSelected(nextUsers.map((user) => user.id));
  }

  function toggleUser(userId: string) {
    setSelected((current) =>
      current.includes(userId)
        ? current.filter((value) => value !== userId)
        : [...current, userId],
    );
  }

  return (
    <div className="full audience-field">
      <span className="field-label">{label}</span>
      <div className="audience-actions" aria-label={`${label} 빠른 선택`}>
        <button type="button" className="secondary" onClick={() => selectUsers(activeUsers)}>
          전체
        </button>
        {[1, 2, 3].map((grade) => (
          <button
            type="button"
            className="secondary"
            disabled={!activeUsers.some((user) => user.grade === grade)}
            key={grade}
            onClick={() => selectUsers(activeUsers.filter((user) => user.grade === grade))}
          >
            {grade}학년
          </button>
        ))}
        <button type="button" className="link-button" onClick={() => setSelected([])}>
          선택 해제
        </button>
      </div>
      <div className="audience-list">
        {activeUsers.length === 0 && <p className="muted">선택할 사용자가 없습니다.</p>}
        {activeUsers.map((user, index) => (
          <label className="audience-user" key={user.id}>
            <input
              type="checkbox"
              name={name}
              value={user.id}
              checked={selected.includes(user.id)}
              required={required && selected.length === 0 && index === 0}
              onChange={() => toggleUser(user.id)}
            />
            <span>
              <strong>{user.name}</strong>
              <small>{user.grade ? `${user.grade}학년` : "학년 없음"} · {user.email}</small>
            </span>
          </label>
        ))}
      </div>
      <small>{selected.length}명 선택됨 · 빠른 선택 후 개별 학생을 추가하거나 제외할 수 있습니다.</small>
    </div>
  );
}
