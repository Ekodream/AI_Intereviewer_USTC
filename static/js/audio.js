/**
 * 音频录制模块 — Cybernetic Command
 * 保留作为备用，主要功能已迁移到 vad.js
 */

class AudioRecorder {
    constructor() {
        console.log('ℹ️ 录音功能已迁移到 VAD 模块，请使用 window.vadDetector');
    }
}

window.audioRecorder = new AudioRecorder();
