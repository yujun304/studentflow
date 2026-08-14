import { api, jsonBody } from "@/lib/api";

type PushConfig = { enabled: boolean; public_key: string | null };
export type PushState = "loading" | "unsupported" | "unconfigured" | "denied" | "available" | "enabled";

function applicationServerKey(value: string): Uint8Array {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  const decoded = atob((value + padding).replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(new ArrayBuffer(decoded.length));
  for (let index = 0; index < decoded.length; index += 1) bytes[index] = decoded.charCodeAt(index);
  return bytes;
}

async function registration() {
  const existing = await navigator.serviceWorker.getRegistration();
  return existing ?? navigator.serviceWorker.register("/sw.js");
}

export async function getPushState(): Promise<PushState> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) return "unsupported";
  const config = await api<PushConfig>("/push/config");
  if (!config.enabled || !config.public_key) return "unconfigured";
  if (Notification.permission === "denied") return "denied";
  const current = await (await registration()).pushManager.getSubscription();
  return current ? "enabled" : "available";
}

export async function enablePush(): Promise<void> {
  const config = await api<PushConfig>("/push/config");
  if (!config.enabled || !config.public_key) throw new Error("푸시 알림 키가 설정되지 않았습니다.");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("알림 권한이 허용되지 않았습니다.");
  const worker = await registration();
  const subscription =
    (await worker.pushManager.getSubscription()) ??
    (await worker.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: applicationServerKey(config.public_key),
    }));
  const serialized = subscription.toJSON();
  if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys.auth) {
    throw new Error("브라우저 구독 정보를 만들지 못했습니다.");
  }
  await api("/push-subscriptions", {
    method: "POST",
    ...jsonBody({
      endpoint: serialized.endpoint,
      p256dh: serialized.keys.p256dh,
      auth: serialized.keys.auth,
    }),
  });
}

export async function disablePush(): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  const worker = await navigator.serviceWorker.getRegistration();
  const subscription = await worker?.pushManager.getSubscription();
  if (!subscription) return;
  await api("/push-subscriptions", {
    method: "DELETE",
    ...jsonBody({ endpoint: subscription.endpoint }),
  });
  await subscription.unsubscribe();
}
