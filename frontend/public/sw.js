self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));

// 오프라인 캐시는 사용하지 않는다. 푸시 동작은 다음 단계에서 이 파일에 추가한다.
self.addEventListener("push", () => {});

