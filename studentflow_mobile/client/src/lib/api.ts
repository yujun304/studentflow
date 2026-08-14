/** StudentFlow | 학기 운영 보드: 실제 API 전환 지점은 이 파일에 모읍니다 */
const wait = (ms = 450) => new Promise((resolve) => window.setTimeout(resolve, ms));
/** 데모는 브라우저 메모리에서만 동작합니다. 실제 서버 연결 시 이 객체의 메서드만 교체하세요. */
export const studentflowApi = { auth: { async signIn() { await wait(500); return { ok: true } as const; } }, tasks: { async save() { await wait(); return { ok: true } as const; } }, attendance: { async save() { await wait(650); return { ok: true } as const; } } };
