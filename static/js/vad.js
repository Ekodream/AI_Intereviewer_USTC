/**
 * VAD (Voice Activity Detection) 模块
 * 基于 Web Audio API 的 RMS 音量检测
 */

class VADDetector {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.isListening = false;
        this.isSpeaking = false;
        this.animationFrameId = null;

        this.config = {
            silenceThreshold: 0.04,
            speechThreshold: 0.04,
            silenceDuration: 2000,
            minSpeechDuration: 1500,
            sampleRate: 16000
        };

        this.silenceTimer = null;
        this.speechStartTime = null;
        this.audioChunks = [];
        this.mediaRecorder = null;

        this.recordBtn = document.getElementById('record-btn');
        this.recordIconEl = document.getElementById('record-icon-i');
        this.statusIndicator = document.getElementById('vad-status-indicator');
        this.statusText = this.statusIndicator?.querySelector('.vad-status-text');

        this.onSpeechStart = null;
        this.onSpeechEnd = null;
        this.onError = null;

        this.bindEvents();
    }

    bindEvents() {
        if (this.recordBtn) {
            this.recordBtn.addEventListener('click', () => this.toggle());
        }
    }

    async toggle() {
        if (this.isListening) {
            await this.stop();
        } else {
            await this.start();
        }
    }

    async start() {
        if (this.isListening) return;

        try {
            this.updateStatus('requesting', '请求麦克风权限...');
            
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.config.sampleRate,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.config.sampleRate
            });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;
            this.analyser.smoothingTimeConstant = 0.3;
            source.connect(this.analyser);

            this.setupMediaRecorder();

            this.isListening = true;
            this.isSpeaking = false;
            this.updateStatus('listening', '监听中...');
            console.log('🎤 VAD 开始监听 (RMS)');

            this.detect();

        } catch (error) {
            console.error('VAD 启动失败:', error);
            this.updateStatus('error', '麦克风权限被拒绝');
            if (this.onError) this.onError(error);
        }
    }

    setupMediaRecorder() {
        const mimeType = this.getSupportedMimeType();
        this.mediaRecorder = new MediaRecorder(this.mediaStream, { mimeType });
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        };

        this.mediaRecorder.onstop = () => {
            this.processAudio();
        };
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

    detect() {
        if (!this.isListening || !this.analyser) return;

        const dataArray = new Float32Array(this.analyser.fftSize);
        this.analyser.getFloatTimeDomainData(dataArray);

        const rms = this.calculateRMS(dataArray);
        const now = Date.now();

        if (rms > this.config.speechThreshold) {
            if (!this.isSpeaking) {
                if (!this.speechStartTime) {
                    this.speechStartTime = now;
                } else if (now - this.speechStartTime >= this.config.minSpeechDuration) {
                    this.onSpeechDetected();
                }
            } else {
                this.silenceTimer = null;
            }
        } else if (rms < this.config.silenceThreshold && this.isSpeaking) {
            if (!this.silenceTimer) {
                this.silenceTimer = now;
            } else if (now - this.silenceTimer >= this.config.silenceDuration) {
                this.onSilenceDetected();
            }
        } else if (rms >= this.config.silenceThreshold && rms <= this.config.speechThreshold) {
            if (this.isSpeaking && !this.silenceTimer) {
                this.silenceTimer = now;
            }
        }

        this.animationFrameId = requestAnimationFrame(() => this.detect());
    }

    calculateRMS(dataArray) {
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i] * dataArray[i];
        }
        return Math.sqrt(sum / dataArray.length);
    }

    onSpeechDetected() {
        this.isSpeaking = true;
        this.speechStartTime = null;
        this.silenceTimer = null;
        
        console.log('🎯 检测到用户说话，打断 TTS...');
        
        // 1. 立即停止当前播放
        if (window.ttsPlayer) {
            console.log('⏹️ 调用 ttsPlayer.interrupt()');
            window.ttsPlayer.interrupt();
        } else {
            console.warn('⚠️ window.ttsPlayer 未定义');
        }
        
        // 2. 停止 AI 继续生成新的 TTS（关键！）
        if (window.chat && window.chat.abortController) {
            console.log('🚫 取消 AI 流式生成');
            window.chat.abortController.abort();
        }
        
        this.updateStatus('speaking', '说话中...');
        
        if (this.mediaRecorder && this.mediaRecorder.state === 'inactive') {
            this.audioChunks = [];
            this.mediaRecorder.start(100);
            console.log('🔴 开始录音');
        }

        if (this.onSpeechStart) {
            this.onSpeechStart();
        }
    }

    onSilenceDetected() {
        this.isSpeaking = false;
        this.silenceTimer = null;
        this.speechStartTime = null;

        this.updateStatus('processing', '识别中...');

        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
            console.log('⏹️ 停止录音，准备识别');
        }
    }

    async processAudio() {
        if (this.audioChunks.length === 0) {
            this.updateStatus('listening', '监听中...');
            return;
        }

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.audioChunks = [];

        window.app?.showLoading('正在识别语音...');

        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');

            const response = await fetch('/api/asr', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (result.status === 'ok' && result.text && result.text.trim()) {
                console.log('✅ 识别结果:', result.text);
                if (window.chat) {
                    window.chat.sendMessage(result.text);
                }
                if (this.onSpeechEnd) {
                    this.onSpeechEnd(result.text);
                }
            } else {
                console.log('⚠️ 未识别到有效内容');
            }
        } catch (error) {
            console.error('ASR 请求失败:', error);
            if (this.onError) {
                this.onError(error);
            }
        } finally {
            window.app?.hideLoading();
            if (this.isListening) {
                this.updateStatus('listening', '监听中...');
            }
        }
    }

    updateStatus(state, text) {
        if (this.statusIndicator) {
            this.statusIndicator.className = 'vad-status-badge';
            if (state) {
                this.statusIndicator.classList.add(state);
            }
        }
        if (this.statusText) {
            this.statusText.textContent = text;
        }

        if (this.recordBtn) {
            this.recordBtn.className = 'record-orb';
            if (state === 'listening') {
                this.recordBtn.classList.add('listening');
            } else if (state === 'speaking') {
                this.recordBtn.classList.add('speaking');
            } else if (state === 'processing') {
                this.recordBtn.classList.add('processing');
            }
        }

        if (this.recordIconEl) {
            if (state === 'speaking') {
                this.recordIconEl.className = 'fas fa-microphone';
            } else if (state === 'processing') {
                this.recordIconEl.className = 'fas fa-spinner fa-spin';
            } else if (state === 'listening') {
                this.recordIconEl.className = 'fas fa-microphone';
            } else {
                this.recordIconEl.className = 'fas fa-microphone';
            }
        }
    }

    async stop() {
        if (!this.isListening) return;

        this.isListening = false;
        this.isSpeaking = false;

        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }

        if (this.silenceTimer) {
            this.silenceTimer = null;
        }

        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.stop();
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }

        this.analyser = null;
        this.mediaRecorder = null;
        this.audioChunks = [];

        this.updateStatus('', '点击麦克风开始');
        console.log('🛑 VAD 停止监听');
    }

    setConfig(config) {
        this.config = { ...this.config, ...config };
    }
}

window.vadDetector = new VADDetector();
