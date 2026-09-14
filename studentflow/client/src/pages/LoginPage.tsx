/** StudentFlow | 교내 구성원이 바로 로그인하는 단순한 진입 화면 */
import { useState } from "react";
import { LockKeyhole } from "lucide-react";
import { useApp } from "@/contexts/AppContext";
import { nextDocumentPath } from "@/lib/document-path";
import { Button, TextInput } from "@/components/primitives";
import ThemeToggle from "@/components/ThemeToggle";

export default function LoginPage() {
  const { signIn } = useApp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim()) return setError("아이디 또는 이메일을 입력해 주세요.");
    if (!password) return setError("비밀번호를 입력해 주세요.");
    setError("");
    setLoading(true);
    const ok = await signIn(email, password);
    setLoading(false);
    if (ok) window.location.assign(nextDocumentPath());
    else setError("아이디 또는 비밀번호가 올바르지 않습니다.");
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="bg-white">
        <div className="mx-auto flex h-16 max-w-[1040px] items-center justify-between px-5 sm:px-8">
          <div>
            <p className="text-base font-bold text-slate-900">StudentFlow</p>
            <p className="text-[11px] text-slate-500">학생회 운영 시스템</p>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-[1040px] px-5 py-16 sm:px-8 sm:py-24">
        <div className="w-full max-w-[380px]">
          <p className="mb-2 text-sm text-slate-500">2026학년도 2학기</p>
          <h1 className="text-2xl font-bold text-slate-900">로그인</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            학교에서 안내받은 계정을 입력해 주세요.
          </p>

          <form
            className="mt-9 grid gap-5"
            onSubmit={handleSubmit}
            noValidate
          >
            <TextInput
              label="아이디 또는 이메일"
              value={email}
              onChange={event => setEmail(event.target.value)}
              error={error}
              autoComplete="username"
              required
            />
            <TextInput
              label="비밀번호"
              type="password"
              value={password}
              onChange={event => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
            <Button
              type="submit"
              size="lg"
              className="mt-2 w-full"
              disabled={loading}
            >
              {loading ? "로그인하는 중…" : "로그인"}
            </Button>
          </form>

          <p className="mt-8 flex gap-2 text-xs leading-5 text-slate-500">
            <LockKeyhole size={15} className="mt-0.5 shrink-0" />
            계정 문의는 담당 선생님에게 해주세요.
          </p>
        </div>
      </main>
    </div>
  );
}
