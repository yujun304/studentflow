# StudentFlow

중학생 학생회를 위한 폐쇄형 운영 플랫폼입니다. 현재 MVP는 사용자·부서·기수, 쿠키 기반 JWT 인증, 개인 대시보드, 행사, 업무·제출, 조 편성·통합 달력, 공지·선착순 신청, 출석 체크리스트와 운영 센터를 제공합니다.

운영 센터에서는 회의 결정사항을 담당자·마감일·실제 업무에 연결하고, 행사 당일 진행표를 관리하며, 비공개 학교 지도 이미지 위에 학생별 활동 위치를 배정할 수 있습니다. 현재 기수의 시행착오와 체크리스트는 공개 인수인계 문서로 남아 다음 기수에서 조회할 수 있습니다.

## 기술 스택

- Frontend: React, Vite MPA, TypeScript
- Backend: FastAPI, Pydantic, SQLAlchemy async, Alembic
- Database: PostgreSQL
- Storage: 권한 검사를 거치는 비공개 로컬 파일시스템
- Authentication: HttpOnly Access/Refresh JWT 쿠키와 CSRF 방어

## 구조

```text
frontend/       화면별 HTML 엔트리를 가진 React MPA 웹 애플리케이션
backend/app/    FastAPI API, 모델, 도메인 라우터
backend/alembic 데이터베이스 마이그레이션
backend/tests/  백엔드 테스트
```

이 프로젝트는 중학생 포트폴리오에서 흐름을 따라가기 쉽도록 Python 백엔드를 중심으로 구성했습니다. `app/api`의 각 파일은 HTTP 요청을 받고, `app/models/entities.py`는 데이터 구조를 정의하며, `app/core`는 인증·DB·파일처럼 여러 기능이 함께 쓰는 코드만 담습니다. React는 서버 데이터를 보여주고 입력을 전달하는 얇은 화면 계층으로 제한했습니다.

프론트엔드는 React Router 기반 SPA가 아닙니다. 대시보드, 로그인, 행사, 업무, 공지,
검토, 관리 화면마다 별도의 `index.html`을 빌드하며 메뉴 이동 시 브라우저가 새 HTML
문서를 요청합니다. React는 각 문서 안에서 폼, 달력, 칸반 같은 상호작용을 처리합니다.
서버 데이터는 작은 `useApiData` 훅으로 불러오고, 저장이 끝나면 현재 문서를 다시
불러옵니다. 별도의 전역 상태 관리나 클라이언트 캐시는 사용하지 않습니다.

## 로컬 실행

1. `.env.example`을 `.env`로 복사하고 `JWT_SECRET`을 안전한 값으로 변경합니다.
2. PostgreSQL을 실행합니다: `docker compose up -d postgres`
3. 백엔드 의존성과 DB를 준비합니다.

```powershell
Set-Location backend
uv sync
uv run alembic upgrade head
uv run python -m app.bootstrap --email teacher@example.com --name "담당 선생님" --password "change-me-now"
uv run uvicorn app.main:app --reload
```

4. 프론트엔드를 실행합니다.

```powershell
Set-Location frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다. 운영 환경에서는 프론트와 API를 동일한 HTTPS 사이트의 리버스 프록시 뒤에 배치하는 구성을 권장합니다.

전체 로컬 서버 구성은 `.env`를 준비한 뒤 `docker compose up -d --build`로 실행하며 기본 주소는 `http://localhost:8081`입니다. 포트를 바꾸려면 `COMPOSE_FRONTEND_PORT`와 `COMPOSE_FRONTEND_ORIGIN`을 같은 주소로 설정합니다. 외부에 공개할 때는 앞단 리버스 프록시에 TLS 인증서를 설정하고 `COMPOSE_COOKIE_SECURE=true`로 변경합니다. PostgreSQL과 업로드 파일은 각각 영구 Docker 볼륨에 보관합니다.

### 기능 검사 예시 데이터

개발 환경에서 실제 튜토리얼과 삭제 기능을 검사하려면 실행 중인 backend에 예시 데이터를 보강합니다. 같은 명령을 다시 실행해도 동일한 제목과 계정을 중복 생성하지 않으며, 기존 데이터는 삭제하지 않습니다.

```powershell
docker compose exec -T backend uv run --no-sync python -m app.bootstrap --demo
```

- 로그인: `demo-teacher@studentflow.example.com`
- 비밀번호: `studentflow-demo`
- 전체 흐름: 메뉴의 `체험 안내`에서 제안 → 교사 승인 → 조 편성 → 포스터 제출 순서로 검사
- 삭제 검사: `[삭제 기능 검사] 독립 업무`, `[삭제 기능 검사] 독립 행사`, `[삭제 기능 검사] 독립 공지`

제출물이나 조 편성 결과가 연결된 업무는 기록 보호를 위해 삭제되지 않습니다. 삭제 전용 예시는 의존 기록이 없는 상태로 생성됩니다.

## Docker가 쓰이는 곳

Docker는 애플리케이션 기능을 구현하는 도구가 아니라, 개발자 컴퓨터마다 다른 설치 환경을 같은 실행 환경으로 맞추는 데 사용합니다. Docker Compose로 다음 세 컨테이너를 함께 관리합니다.

| 컨테이너 | 역할 | 호스트 공개 여부 |
|---|---|---|
| `postgres` | PostgreSQL 16 데이터베이스 | 개발 편의를 위해 `5432` 공개 |
| `backend` | Alembic 마이그레이션 실행 후 FastAPI 시작 | 직접 공개하지 않음 |
| `frontend` | React 정적 파일 제공 및 API 프록시 | `8081` 공개 |

구체적인 사용처는 다음과 같습니다.

1. **PostgreSQL 실행**: PC에 DB를 직접 설치하지 않고 동일한 16 버전을 실행합니다.
2. **백엔드 환경 고정**: Python 3.12와 `uv.lock`에 기록된 버전으로 FastAPI 이미지를 만듭니다.
3. **DB 마이그레이션 자동 적용**: backend 시작 시 `alembic upgrade head`를 실행한 뒤 API 서버를 시작합니다.
4. **프론트엔드 빌드**: Node 22에서 TypeScript와 React를 빌드하고, 최종 이미지에는 Nginx와 결과 파일만 넣습니다.
5. **리버스 프록시**: Nginx가 브라우저의 `/api/` 요청을 내부 네트워크의 `backend:8000`으로 전달합니다. 프론트와 API가 같은 Origin을 사용해 쿠키와 CSRF 설정도 단순해집니다.
6. **시작 순서 관리**: PostgreSQL healthcheck 성공 후 backend를 시작합니다.
7. **데이터 보존**: `studentflow_postgres`에는 DB를, `studentflow_uploads`에는 파일을 저장해 컨테이너를 다시 만들어도 데이터가 유지됩니다.
8. **한 명령 실행**: `docker compose up -d --build`로 세 서비스를 빌드하고 실행합니다.

React 상태 관리, FastAPI 권한 검사, 업무·공지·출석 규칙은 일반 애플리케이션 코드이며 Docker가 처리하지 않습니다. Docker Compose는 현재 로컬 실행과 단일 서버 배포용이고 Kubernetes 같은 다중 서버 오케스트레이션은 사용하지 않습니다.

## 환경 변수

- `DATABASE_URL`: asyncpg PostgreSQL 주소
- `JWT_SECRET`: 최소 32자의 임의 비밀값
- `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS`: 토큰 수명
- `COOKIE_SECURE`: HTTPS 운영 환경에서는 `true`
- `FRONTEND_ORIGIN`: 허용할 정확한 프론트엔드 Origin
- `COMPOSE_FRONTEND_ORIGIN`, `COMPOSE_FRONTEND_PORT`: Docker Compose 프론트엔드 Origin과 호스트 포트
- `COMPOSE_COOKIE_SECURE`: Compose의 HTTPS 쿠키 여부. localhost는 `false`, HTTPS 배포는 `true`
- `STORAGE_ROOT`: 웹 루트 밖의 업로드 저장 경로
- `STORAGE_BACKEND`: 현재는 `local`, 후속 S3 구현을 위한 설정 계약은 예약됨
- `MAX_UPLOAD_BYTES`: 업로드 최대 바이트
- `DEFAULT_TIMEZONE`: 기본 `Asia/Seoul`
- `PROPOSAL_AI_ENABLED`: `true`일 때 회의 녹음 자동 처리를 활성화
- `PROPOSAL_AI_API_KEY`: 서버에서만 사용하는 OpenAI API 키. 프론트엔드에는 전달하지 않음
- `PROPOSAL_TRANSCRIPTION_MODEL`, `PROPOSAL_TRANSCRIPTION_LANGUAGE`: 음성 전사 모델(기본 `whisper-1`)과 언어
- `PROPOSAL_AI_MODEL`: 회의 녹취를 기존 계획서 JSON 구조로 정리할 모델
- `PROPOSAL_AI_TIMEOUT_SECONDS`, `PROPOSAL_TRANSCRIPT_MAX_CHARS`: 외부 API 제한 시간과 처리할 최대 녹취 길이

회의 녹음 자동 처리는 서버가 업로드 파일을 Whisper 전사 API로 보내고, 전사문과 기존 간이
기획서를 LLM의 엄격한 JSON 스키마 출력으로 정리한 다음 기존 행사 계획서 필드에 채웁니다.
자동 처리를 사용하지 않거나 API 설정이 없을 때도 기존 수동 녹취·회의 정리 흐름은 유지됩니다.

## 보안 구조

Access Token과 Refresh Token은 JavaScript에서 읽을 수 없는 HttpOnly 쿠키로 전달됩니다. 모든 상태 변경 요청은 별도의 CSRF 토큰과 Origin 검사를 통과해야 합니다. JWT의 역할만 신뢰하지 않고 API 요청마다 현재 사용자, 활성 상태, 역할, 부서 및 기수를 DB에서 확인합니다. 파일 경로는 공개하지 않으며 API의 접근 권한 검사 후 스트리밍합니다.

## 테스트와 빌드

```powershell
Set-Location backend
uv run ruff check app tests alembic
uv run pytest tests
Set-Location ..\frontend
npm test
npm run build
```

## 후속 범위

조 편성·통합 달력, 출석 체크리스트, 회의록, 빠른 메모, 결정 카드, 행사 운영표, 학교 지도 위치 배정과 기수 인수인계 API는 동작합니다. 빠른 메모는 대시보드에서 사용자별로 작성·조회·삭제할 수 있습니다. 댓글 Thread, 저장 항목과 감사 로그 조회 등 아직 준비되지 않은 API는 인증과 기본 권한을 확인한 뒤 `501 feature_not_ready`를 반환합니다. 프로젝트 범위를 단순화하기 위해 채팅 기능은 제거했습니다.

PWA manifest와 서비스 워커 등록은 제공하지만 오프라인 저장은 하지 않습니다. IndexedDB와 Background Sync도 사용하지 않습니다. 실제 푸시 발송과 S3 저장소 구현은 다음 단계로 남겨두었습니다.
