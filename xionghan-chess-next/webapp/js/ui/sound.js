/**
 * 音效：全部用 WebAudio 现场合成，不加载任何音频文件。
 * 这样首屏体积为 0，也没有素材授权问题。
 */

let ctx = null;
let enabled = true;
let volume = 0.55;

// 背景音乐：全部现场合成，五声音阶的稀疏拨弦 + 低音铺底
let musicOn = false;
let musicWanted = false;
let musicVolume = 0.35;
let musicGain = null;
let musicPad = null;
let musicTimer = null;
const PENTATONIC = [0, 3, 5, 7, 10];

function ensure() {
  if (!ctx) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function tone({ freq = 440, type = 'sine', duration = 0.12, gain = 0.2, slide = 0, delay = 0 }) {
  const audio = ensure();
  if (!audio) return;
  const t0 = audio.currentTime + delay;
  const osc = audio.createOscillator();
  const amp = audio.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t0);
  if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(40, freq + slide), t0 + duration);
  amp.gain.setValueAtTime(0.0001, t0);
  amp.gain.exponentialRampToValueAtTime(gain * volume, t0 + 0.008);
  amp.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
  osc.connect(amp).connect(audio.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

function noise({ duration = 0.08, gain = 0.12, delay = 0, filter = 1200 }) {
  const audio = ensure();
  if (!audio) return;
  const length = Math.max(1, Math.floor(audio.sampleRate * duration));
  const buffer = audio.createBuffer(1, length, audio.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i += 1) {
    data[i] = (Math.random() * 2 - 1) * (1 - i / length) ** 2;
  }
  const src = audio.createBufferSource();
  src.buffer = buffer;
  const biquad = audio.createBiquadFilter();
  biquad.type = 'lowpass';
  biquad.frequency.value = filter;
  const amp = audio.createGain();
  amp.gain.value = gain * volume;
  src.connect(biquad).connect(amp).connect(audio.destination);
  src.start(audio.currentTime + delay);
}

const sounds = {
  select() {
    tone({ freq: 760, type: 'sine', duration: 0.07, gain: 0.1 });
  },
  move() {
    tone({ freq: 190, type: 'sine', duration: 0.11, gain: 0.24, slide: -70 });
    noise({ duration: 0.06, gain: 0.1, filter: 900 });
  },
  capture() {
    tone({ freq: 320, type: 'triangle', duration: 0.09, gain: 0.2, slide: -180 });
    noise({ duration: 0.12, gain: 0.16, filter: 1600, delay: 0.01 });
  },
  check() {
    tone({ freq: 620, type: 'triangle', duration: 0.16, gain: 0.18 });
    tone({ freq: 930, type: 'triangle', duration: 0.14, gain: 0.12, delay: 0.09 });
  },
  win() {
    [523, 659, 784, 1046].forEach((freq, i) => {
      tone({ freq, type: 'sine', duration: 0.24, gain: 0.16, delay: i * 0.1 });
    });
  },
  lose() {
    [392, 330, 262].forEach((freq, i) => {
      tone({ freq, type: 'sine', duration: 0.3, gain: 0.16, delay: i * 0.13 });
    });
  },
  click() {
    tone({ freq: 520, type: 'square', duration: 0.035, gain: 0.06 });
  },
  undo() {
    tone({ freq: 300, type: 'sine', duration: 0.12, gain: 0.14, slide: 120 });
  },
};

export function play(name) {
  if (!enabled) return;
  const fn = sounds[name];
  if (!fn) return;
  try {
    fn();
  } catch {
    /* 音频不可用时静默降级 */
  }
}

function scheduleMusicNote() {
  if (!musicOn || !ctx || !musicGain) return;
  const t0 = ctx.currentTime + 0.06;
  const step = PENTATONIC[Math.floor(Math.random() * PENTATONIC.length)];
  const octave = Math.random() < 0.3 ? 2 : 1;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.value = 220 * Math.pow(2, step / 12) * octave;
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(0.32, t0 + 0.03);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 2.4);
  osc.connect(gain).connect(musicGain);
  osc.start(t0);
  osc.stop(t0 + 2.5);
}

export function startMusic() {
  if (musicOn || musicVolume <= 0) return;
  const audio = ensure();
  if (!audio) return;
  musicOn = true;
  musicGain = audio.createGain();
  musicGain.gain.value = musicVolume * 0.14;
  musicGain.connect(audio.destination);

  musicPad = audio.createOscillator();
  const padGain = audio.createGain();
  musicPad.type = 'sine';
  musicPad.frequency.value = 110;
  padGain.gain.value = 0.45;
  musicPad.connect(padGain).connect(musicGain);
  musicPad.start();

  scheduleMusicNote();
  musicTimer = setInterval(scheduleMusicNote, 2600);
}

export function stopMusic() {
  musicOn = false;
  if (musicTimer) {
    clearInterval(musicTimer);
    musicTimer = null;
  }
  try { musicPad && musicPad.stop(); } catch { /* 忽略 */ }
  musicPad = null;
  if (musicGain) {
    try { musicGain.disconnect(); } catch { /* 忽略 */ }
    musicGain = null;
  }
}

export function setMusicEnabled(value) {
  musicWanted = Boolean(value);
  if (musicWanted) startMusic();
  else stopMusic();
}

export function isMusicEnabled() {
  return musicOn;
}

export function setMusicVolume(value) {
  musicVolume = Math.max(0, Math.min(1, value));
  if (musicGain) musicGain.gain.value = musicVolume * 0.14;
}

export function setSoundEnabled(value) {
  enabled = value;
}

export function isSoundEnabled() {
  return enabled;
}

export function setVolume(value) {
  volume = Math.max(0, Math.min(1, value));
}

/** 浏览器要求首次交互后才能播放音频。 */
export function unlock() {
  ensure();
  // 浏览器要求先有用户手势才能出声：偏好里开着音乐时，首次交互再起
  if (musicWanted && !musicOn) startMusic();
}
