/**
 * VAD (Voice Activity Detection) 模块
 * 基于 Web Audio API 的 RMS 音量检测
 * 
 * 流程：
 * 1. 开始录音 → 启动超时计时器
 * 2. 静音 > 特定秒 → 结束录音 → TTS 开始 → 关闭麦克风 + 关闭超时计时器
 * 3. TTS 播放结束 → 开始录音 + 启动超时计时器
 * 4. 如此循环
 */

class VADDetector {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.isListening = false;
        this.isSpeaking = false;
        this.autoMonitoring = true;
        this.animationFrameId = null;

        this.config = {
            silenceThreshold: 0.03,
            speechThreshold: 0.03,
            silenceDuration: 1500,
            minSpeechDuration: 400,
            sampleRate: 16000,
            noSpeechTimeout: 10000  // 10秒无声音超时
        };

        this.silenceTimer = null;
        this.speechStartTime = null;
        this.audioChunks = [];
        this.mediaRecorder = null;
        this.listeningStartTime = null;
        this.hasSpoken = false;
        this.noSpeechTimeoutId = null;  // 超时计时器 ID
        this.skipProcessOnStop = false;

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
        // 如果 TTS 正在播放，强制打断并开始新的录音
        if (window.ttsPlayer && window.ttsPlayer.ttsStarted) {
            console.log('🎯 用户点击麦克风，强制打断 TTS');
            // 打断 TTS
            window.ttsPlayer.interrupt();
            // 等待一小段时间让 TTS 完全停止
            await new Promise(resolve => setTimeout(resolve, 100));
            // 开始新的录音
            await this.start();
            return;
        }
        
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
            this.skipProcessOnStop = false;

            // 同步启动视频录制
            if (window.videoRecorder && window.app?.settings?.enable_video) {
                window.videoRecorder.startRecording();
            }

            if (this.autoMonitoring) {
                this.updateStatus('listening', '监听中...');
                console.log('🎤 VAD 开始监听 (RMS)');

                // 启动超时计时器
                this.startNoSpeechTimeout();
                this.detect();
            } else {
                // 手动模式：点击后立即开始录音，再次点击结束
                this.audioChunks = [];
                this.isSpeaking = true;
                this.mediaRecorder.start(100);
                this.updateStatus('speaking', '手动录音中... 再次点击结束');
                console.log('🎙️ 手动模式开始录音');
            }

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
            if (this.skipProcessOnStop) {
                this.skipProcessOnStop = false;
                this.audioChunks = [];
                return;
            }
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

    startNoSpeechTimeout() {
        this.listeningStartTime = Date.now();
        this.hasSpoken = false;
        
        // 清除之前的计时器
        if (this.noSpeechTimeoutId) {
            clearTimeout(this.noSpeechTimeoutId);
        }
        
        console.log('⏱️ 启动超时计时器 (10秒)');
        this.noSpeechTimeoutId = setTimeout(() => {
            if (!this.hasSpoken && this.isListening) {
                console.log('⏰ 10秒无声音，自动推进面试');
                this.onNoSpeechTimeout();
            }
        }, this.config.noSpeechTimeout);
    }

    stopNoSpeechTimeout() {
        if (this.noSpeechTimeoutId) {
            clearTimeout(this.noSpeechTimeoutId);
            this.noSpeechTimeoutId = null;
            console.log('⏹️ 停止超时计时器');
        }
    }

    onSpeechDetected() {
        this.isSpeaking = true;
        this.speechStartTime = null;
        this.silenceTimer = null;
        this.hasSpoken = true;
        
        console.log('🎯 检测到用户说话');
        
        // 用户说话了，停止超时计时器
        this.stopNoSpeechTimeout();
        
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

    onNoSpeechTimeout() {
        console.log('⏰ 10秒无声音，自动推进面试');
        
        // 停止超时计时器
        this.stopNoSpeechTimeout();
        
        // 发送一个提示消息，让导师推进面试
        if (window.chat) {
            window.chat.sendMessage('（用户没有回答，请继续提问或推进面试）');
        }
    }

    async processAudio() {
        if (this.audioChunks.length === 0) {
            if (this.isListening && this.autoMonitoring) {
                this.updateStatus('listening', '监听中...');
                this.startNoSpeechTimeout();
            } else {
                this.updateStatus('', this.autoMonitoring ? '点击麦克风开始' : '手动模式：点击开始录音');
            }
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
                if (this.isListening && this.autoMonitoring) {
                    this.startNoSpeechTimeout();
                }
            }
        } catch (error) {
            console.error('ASR 请求失败:', error);
            if (this.onError) {
                this.onError(error);
            }
            if (this.isListening && this.autoMonitoring) {
                this.startNoSpeechTimeout();
            }
        } finally {
            window.app?.hideLoading();
            if (this.isListening) {
                this.updateStatus(this.autoMonitoring ? 'listening' : '', this.autoMonitoring ? '监听中...' : '手动模式：点击开始录音');
            } else {
                this.updateStatus('', this.autoMonitoring ? '点击麦克风开始' : '手动模式：点击开始录音');
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
            } else if (state === 'tts-playing') {
                this.recordBtn.classList.add('tts-playing');
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

    // TTS 开始时调用：关闭麦克风和超时计时器
    pauseForTTSPlayback() {
        if (!this.autoMonitoring) return;
        console.log('⏸️ TTS 开始播放，关闭麦克风和超时计时器');
        
        // 停止超时计时器
        this.stopNoSpeechTimeout();
        
        // 关闭麦克风
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        // 关闭 AudioContext
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        // 停止检测循环
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        this.analyser = null;
        this.isListening = false;
        this.isSpeaking = false;
        
        this.updateStatus('tts-playing', 'AI 说话中...');
    }

    // TTS 结束时调用：重新打开麦克风和超时计时器
    async resumeAfterTTS() {
        if (!this.autoMonitoring) return;
        console.log('▶️ TTS 播放结束，重新打开麦克风');
        
        // 重新启动
        await this.start();
    }

    async stop() {
        if (!this.isListening) return;

        this.isListening = false;
        this.isSpeaking = false;

        // 停止超时计时器
        this.stopNoSpeechTimeout();

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

        // 同步停止视频录制并上传
        if (window.videoRecorder && window.videoRecorder.isRecording) {
            const videoBlob = await window.videoRecorder.stopRecording();
            if (videoBlob && videoBlob.size > 0) {
                window.videoRecorder.uploadVideo(videoBlob);
            }
        }

        this.analyser = null;
        this.mediaRecorder = null;
        this.updateStatus('', this.autoMonitoring ? '点击麦克风开始' : '手动模式：点击开始录音');
        console.log('🛑 VAD 停止监听');
    }

    async setAutoMonitoring(enabled) {
        const next = !!enabled;
        if (this.autoMonitoring === next) {
            this.updateStatus('', this.autoMonitoring ? '点击麦克风开始' : '手动模式：点击开始录音');
            return;
        }

        this.autoMonitoring = next;
        if (this.isListening) {
            // 切换模式时先停止当前录音，避免状态混乱。
            await this.stop();
        }
        this.updateStatus('', this.autoMonitoring ? '点击麦克风开始' : '手动模式：点击开始录音');
    }

    setConfig(config) {
        this.config = { ...this.config, ...config };
    }
}

window.vadDetector = new VADDetector();
