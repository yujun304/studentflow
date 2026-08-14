# AGENTS.md

## Project Overview

StudentFlow는 중학생 학생회를 위한 폐쇄형 운영 플랫폼이다.

핵심 목표는 자유로운 소통과 유연한 업무 처리를 지원하면서, 공지·마감일·제출물·출석·회의 기록이 누락되지 않도록 관리하는 것이다.

## Tech Stack

Frontend:

* React
* Vite
* TypeScript
* PWA
* 반응형 UI

Backend:

* FastAPI
* Pydantic
* async/await
* REST API

Database:

* PostgreSQL

Authentication:

* JWT Access Token
* JWT Refresh Token
* 역할 및 담당 범위 기반 권한 검사

Storage:

* 비공개 클라우드 오브젝트 스토리지
* 권한 확인 후 업로드 및 다운로드 제공

Deployment:

* AWS 또는 로컬 서버
* HTTPS 필수

## Core Rules

* 웹소켓을 사용하지 않는다.
* PWA는 설치와 푸시 알림만 지원한다.
* 오프라인 저장, IndexedDB, Background Sync는 구현하지 않는다.
* 공개 회원가입은 제공하지 않는다.
* Redis, Celery, GraphQL, Firebase, Supabase를 임의로 추가하지 않는다.
* 기존 코드를 확인하지 않고 새 구조로 덮어쓰지 않는다.
* 비밀키와 인증정보를 코드에 하드코딩하지 않는다.

## User Roles

* MEMBER: 일반 임원
* DEPARTMENT_HEAD: 부장단
* EXECUTIVE_BOARD: 회장단
* TEACHER: 담당 선생님

프론트엔드에서 메뉴를 숨기는 것만으로 권한을 처리하지 않는다. 모든 보호 API에서 사용자 역할, 부서, 행사 담당 범위를 백엔드에서 검사한다.

## Main Features

* 개인 대시보드
* 행사 및 캠페인
* 업무 배정과 칸반 보드
* 파일 제출, 승인, 반려
* 조 편성
* 공지와 선착순 신청
* 날짜 및 시간 변경 요청
* 관리자 수동 출석 체크
* 회의록과 녹음 파일
* 댓글 Thread
* 빠른 메모와 개인 리마인더
* 기수 및 아카이브
* 앱 내부 알림과 PWA 푸시 알림

## UI Direction

Notion과 비슷한 미니멀한 분위기를 사용한다.

* 흰색과 연한 회색 중심
* 하나의 포인트 색상
* 얇은 테두리
* 충분한 여백
* 과도한 그림자와 애니메이션 금지
* 데스크톱과 모바일 모두 지원
* 최소 360px 화면 대응

Notion의 실제 코드나 디자인 자산을 복사하지 않는다.

## Development Process

작업 전 저장소 구조와 기존 코드를 먼저 분석한다.

한 번에 전체 기능을 구현하지 말고 작동 가능한 단위로 나누어 진행한다.

각 단계가 끝나면 다음 내용을 보고한다.

* 변경한 파일
* 구현한 기능
* 데이터베이스 변경
* 실행한 테스트
* 남은 문제
* 다음 작업

기존 기능을 삭제하거나 크게 변경할 경우 이유를 설명한다.
