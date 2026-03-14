/**
 * 流式 TTS 播放器 — Cybernetic Command
 * LLM 生成一句即播放一句
 */

class StreamingTTSPlayer {
    constructor() {
        this.audioQueue = [];
        this.isPlaying = false;
        this.isPaused = false;
        this.currentIndex = 0;
        this.totalCount = 0;
        this.audioElement = null;
        this.ttsStarted = false;  // 标记 TTS 是否已经开始

        this.statusEl = document.getElementById('tts-status');
        this.progressBar = document.getElementById('tts-progress-bar');
        this.playBtn = document.getElementById('tts-play');
        this.pauseBtn = document.getElementById('tts-pause');
        this.stopBtn = document.getElementById('tts-stop');

        this.bindEvents();
    }

    bindEvents() {
        if (this.playBtn) this.playBtn.addEventListener('click', () => this.play());
        if (this.pauseBtn) this.pauseBtn.addEventListener('click', () => this.pause());
        if (this.stopBtn) this.stopBtn.addEventListener('click', () => this.stop());
    }

    addAudio(base64Data, sentence = '') {
        this.audioQueue.push({
            base64: base64Data,
            sentence: sentence,
            index: this.totalCount
        });
        this.totalCount++;
        console.log(`🔊 添加音频 #${this.totalCount}: ${sentence.substring(0, 30)}...`);

        // 第一个音频添加时，关闭麦克风和超时计时器
        if (!this.ttsStarted && window.vadDetector) {
            console.log('⏸️ TTS 开始，关闭麦克风和超时计时器');
            window.vadDetector.pauseForTTSPlayback();
            this.ttsStarted = true;
        }

        if (!this.isPlaying && !this.isPaused) this.play();
        this.updateStatus();
    }

    play() {
        if (this.isPaused && this.audioElement) {
            this.audioElement.play();
            this.isPaused = false;
        } else if (!this.isPlaying && this.audioQueue.length > 0) {
            this.isPlaying = true;
            this.isPaused = false;
            this.playNext();
        }
        this.updateStatus();
    }

    playNext() {
        if (this.currentIndex >= this.audioQueue.length) {
            if (this.currentIndex >= this.totalCount) {
                this.isPlaying = false;
                this.updateStatus('播放完成');
                
                // TTS 全部播放完成，重新打开麦克风
                if (this.ttsStarted && window.vadDetector) {
                    console.log('▶️ TTS 播放完成，重新打开麦克风');
                    this.ttsStarted = false;
                    window.vadDetector.resumeAfterTTS();
                }
                return;
            }
            setTimeout(() => this.playNext(), 100);
            return;
        }

        const audioData = this.audioQueue[this.currentIndex];
        const audioSrc = `data:audio/mpeg;base64,${audioData.base64}`;

        this.audioElement = new Audio(audioSrc);

        this.audioElement.addEventListener('ended', () => {
            this.currentIndex++;
            this.updateProgress();
            this.playNext();
        });

        this.audioElement.addEventListener('error', (e) => {
            console.error('音频播放错误:', e);
            this.currentIndex++;
            this.playNext();
        });

        this.audioElement.play().then(() => {
            this.updateStatus(`播放中 (${this.currentIndex + 1}/${this.totalCount})`);
        }).catch(error => {
            console.error('播放失败:', error);
            this.updateStatus('点击播放按钮开始');
        });

        this.updateProgress();
    }

    pause() {
        if (this.isPlaying && this.audioElement && !this.isPaused) {
            this.audioElement.pause();
            this.isPaused = true;
            this.updateStatus('已暂停');
        }
    }

    stop() {
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement.currentTime = 0;
            this.audioElement = null;
        }
        this.isPlaying = false;
        this.isPaused = false;
        
        // 清空队列
        this.audioQueue = [];
        this.currentIndex = 0;
        this.totalCount = 0;
        this.ttsStarted = false;
        
        this.updateStatus('点击播放按钮开始');
        this.updateProgress();
    }

    interrupt() {
        console.log('⏹️ TTS 被用户打断');
        this.stop();
    }

    reset() {
        this.stop();
    }

    updateStatus(text) {
        if (this.statusEl) {
            this.statusEl.textContent = text || '';
        }
    }

    updateProgress() {
        if (!this.progressBar) return;
        if (this.totalCount === 0) {
            this.progressBar.style.width = '0%';
        } else {
            const percent = Math.round((this.currentIndex / this.totalCount) * 100);
            this.progressBar.style.width = `${percent}%`;
        }
    }
}

window.ttsPlayer = new StreamingTTSPlayer();
