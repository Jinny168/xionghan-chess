/**
 * 云服务接入：登录 + 备份/恢复。
 *
 * SDK 走 CDN 延迟加载（单文件应用无构建步骤），只在用户打开「云同步」时才拉取，
 * 不影响首屏与离线游玩。endpoint / publishableKey 由服务端注入的 __CLOUD_CONFIG__ 提供，
 * 前端不硬编码任何环境地址。
 */

const SDK_SRC = 'https://cdn.jsdelivr.net/npm/@tencent-ai/workbuddy-cloud-sdk@dev/lib/index.global.js';

let sdkPromise = null;
let clientPromise = null;

export function cloudConfigured() {
  return Boolean(window.__CLOUD_CONFIG__ && window.__CLOUD_CONFIG__.endpoint);
}

function loadSdk() {
  if (window.WorkBuddyCloud) return Promise.resolve(window.WorkBuddyCloud);
  if (!sdkPromise) {
    sdkPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = SDK_SRC;
      script.async = true;
      script.onload = () => (window.WorkBuddyCloud ? resolve(window.WorkBuddyCloud) : reject(new Error('sdk-missing')));
      script.onerror = () => reject(new Error('sdk-load-failed'));
      document.head.append(script);
    });
  }
  return sdkPromise;
}

export async function getCloud() {
  if (!cloudConfigured()) throw new Error('cloud-not-configured');
  if (!clientPromise) {
    clientPromise = (async () => {
      const sdk = await loadSdk();
      const cfg = window.__CLOUD_CONFIG__;
      return sdk.createWorkBuddyCloud({
        endpoint: cfg.endpoint,
        oauthRelayBaseUrl: cfg.oauthRelayBaseUrl,
        publishableKey: cfg.publishableKey,
      });
    })();
    clientPromise.catch(() => { clientPromise = null; });
  }
  return clientPromise;
}

export async function currentSession() {
  const cloud = await getCloud();
  const { data, error } = await cloud.auth.getSession();
  if (error) throw error;
  return data || null;
}

export async function sendCode(email) {
  const cloud = await getCloud();
  const { data, error } = await cloud.auth.sendOtp({ email });
  if (error) throw error;
  return data;
}

export async function verifyCode({ email, verificationId, isExistingUser, token }) {
  const cloud = await getCloud();
  const { data, error } = await cloud.auth.verifyOtp({ email, verificationId, isExistingUser, token });
  if (error) throw error;
  return data;
}

export async function signOut() {
  const cloud = await getCloud();
  const { error } = await cloud.auth.signOut();
  if (error) throw error;
}

export async function pullState() {
  const cloud = await getCloud();
  const { data, error } = await cloud.database
    .from('sync_state')
    .select('payload, updated_at')
    .maybeSingle();
  if (error) throw error;
  return data || null;
}

export async function pushState(payload) {
  const cloud = await getCloud();
  const { data, error } = await cloud.database
    .from('sync_state')
    .upsert({ payload, updated_at: new Date().toISOString() }, { onConflict: 'owner_id' })
    .select('updated_at')
    .maybeSingle();
  if (error) throw error;
  return data;
}
