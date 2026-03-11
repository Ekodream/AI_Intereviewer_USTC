/**
 * 音频录制模块 — Cybernetic Command
 * Web Audio API 录音，适配新 UI
 */

class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;

        this.recordBtn = document.getElementById('record-btn');
        this.recordIconEl = document.getElementById('record-icon-i');
        this.recordingIndicator = document.getElementById('recording-indicator');

        this.bindEvents();
    }

    bindEvents() {
        if (this.recordBtn) {
            this.recordBtn.addEventListener('click', () => this.toggleRecording());
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: this.getSupportedMimeType()
            });

            this.audioChunks = [];

            this.mediaRecorder.addEventListener('dataavailable', (event) => {
                if (event.data.size > 0) this.audioChunks.push(event.data);
            });

            this.mediaRecorder.addEventListener('stop', () => {
                this.processRecording();
            });

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateUI(true);
            console.log('🎤 开始录音');
        } catch (error) {
            console.error('无法访问麦克风:', error);
            alert('无法访问麦克风，请确保已授权浏览器访问麦克风权限。');
        }
    }

    async stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            this.updateUI(false);
            console.log('🛑 停止录音');
        }
    }

    async processRecording() {
        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        window.app?.showLoading('正在识别语音...');

        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.wav');

            const response = await fetch('/api/asr', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (result.status === 'ok' && result.text) {
                console.log('✅ 识别结果:', result.text);
                if (window.chat) window.chat.sendMessage(result.text);
            } else {
                alert('语音识别失败: ' + (result.message || '未识别到有效内容'));
            }
        } catch (error) {
            console.error('ASR 请求失败:', error);
            alert('语音识别请求失败，请检查网络连接。');
        } finally {
            window.app?.hideLoading();
        }
    }

    getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
            'audio/wav'
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) return type;
        }
        return 'audio/webm';
    }

    updateUI(recording) {
        if (this.recordBtn) {
            this.recordBtn.classList.toggle('recording', recording);
        }
        if (this.recordIconEl) {
            this.recordIconEl.className = recording ? 'fas fa-stop' : 'fas fa-microphone';
        }
        if (this.recordingIndicator) {
            this.recordingIndicator.classList.toggle('show', recording);
        }
    }
}

window.audioRecorder = new AudioRecorder();
