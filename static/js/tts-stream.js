/**
 * 流式 TTS 播放器 — Cybernetic Command
 * LLM 生成一句即播放一句
 * 
 * 移动端兼容性说明：
 * - iOS Safari/Android Chrome 需要用户手势触发音频播放
 * - 使用 AudioContext + AudioBuffer 方式播放更可靠
 * - 实现重试机制应对播放失败
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
        
        // 移动端兼容性配置
        this.isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        this.isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent);
        this.audioContext = null;
        this.isAudioUnlocked = false;
        this.maxRetries = 3;
        this.retryDelay = 100;
        
        // 当前正在播放的 AudioBufferSourceNode
        this.currentSource = null;
        
        // 播放失败回调
        this.playbackFailedCallback = null;
        // 首次播放失败标记（用于只提示一次）
        this.hasShownUnlockHint = false;

        this.statusEl = document.getElementById('tts-status');
        this.progressBar = document.getElementById('tts-progress-bar');
        this.playBtn = document.getElementById('tts-play');
        this.pauseBtn = document.getElementById('tts-pause');
        this.stopBtn = document.getElementById('tts-stop');

        this.bindEvents();
        this.setupAudioUnlock();
        
        // 移动端打印调试信息
        if (this.isMobile) {
            console.log('📱 TTS 移动端模式已启用, iOS:', this.isIOS);
        }
    }

    bindEvents() {
        if (this.playBtn) this.playBtn.addEventListener('click', () => this.play());
        if (this.pauseBtn) this.pauseBtn.addEventListener('click', () => this.pause());
        if (this.stopBtn) this.stopBtn.addEventListener('click', () => this.stop());
    }
    
    /**
     * 设置音频解锁机制
     * 移动端需要用户手势才能播放音频
     */
    setupAudioUnlock() {
        const unlockEvents = ['touchstart', 'touchend', 'click', 'keydown'];
        
        const unlockHandler = async () => {
            if (this.isAudioUnlocked) return;
            
            try {
                // 创建 AudioContext
                await this.getOrCreateAudioContext();
                
                // 尝试恢复挂起的 AudioContext
                if (this.audioContext && this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                }
                
                // 播放一个静音缓冲区来解锁
                if (this.audioContext) {
                    const buffer = this.audioContext.createBuffer(1, 1, 22050);
                    const source = this.audioContext.createBufferSource();
                    source.buffer = buffer;
                    source.connect(this.audioContext.destination);
                    source.start(0);
                }
                
                // 同时尝试播放一个静音 Audio 元素
                const silentAudio = new Audio();
                silentAudio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
                silentAudio.volume = 0.01;
                await silentAudio.play().catch(() => {});
                silentAudio.pause();
                
                this.isAudioUnlocked = true;
                console.log('🔓 TTS 音频已解锁');
                
                // 解锁成功后移除监听器
                unlockEvents.forEach(event => {
                    document.removeEventListener(event, unlockHandler, { capture: true });
                });
            } catch (error) {
                console.warn('⚠️ TTS 音频解锁失败:', error);
            }
        };
        
        // 添加解锁事件监听
        unlockEvents.forEach(event => {
            document.addEventListener(event, unlockHandler, { capture: true, passive: true });
        });
    }
    
    /**
     * 获取或创建 AudioContext
     */
    async getOrCreateAudioContext() {
        if (!this.audioContext) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                this.audioContext = new AudioContextClass();
                console.log('🔊 AudioContext 已创建, 初始状态:', this.audioContext.state);
                
                // 监控 AudioContext 状态变化
                this.audioContext.onstatechange = () => {
                    console.log('🔊 AudioContext 状态变化:', this.audioContext.state);
                };
            }
        }
        
        // 确保 AudioContext 处于运行状态
        if (this.audioContext && this.audioContext.state === 'suspended') {
            try {
                await this.audioContext.resume();
                console.log('✅ AudioContext 已恢复, 当前状态:', this.audioContext.state);
            } catch (e) {
                console.warn('⚠️ AudioContext resume 失败:', e);
            }
        }
        
        return this.audioContext;
    }
    
    /**
     * 手动解锁音频（供外部调用）
     * 应在用户交互事件中调用此方法
     */
    async unlockAudio() {
        if (this.isAudioUnlocked) {
            console.log('🔓 TTS 音频已经解锁');
            return true;
        }
        
        try {
            console.log('🔐 尝试手动解锁 TTS 音频...');
            
            // 创建 AudioContext
            await this.getOrCreateAudioContext();
            
            // 尝试恢复挂起的 AudioContext
            if (this.audioContext && this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // 播放静音缓冲区来解锁
            if (this.audioContext && this.audioContext.state === 'running') {
                const buffer = this.audioContext.createBuffer(1, 1, 22050);
                const source = this.audioContext.createBufferSource();
                source.buffer = buffer;
                source.connect(this.audioContext.destination);
                source.start(0);
            }
            
            // 同时尝试播放静音 Audio 元素（双保险）
            const silentAudio = new Audio();
            silentAudio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
            silentAudio.volume = 0.01;
            await silentAudio.play().catch(() => {});
            silentAudio.pause();
            
            this.isAudioUnlocked = true;
            this.hasShownUnlockHint = false;  // 重置提示标记
            console.log('🔓 TTS 音频手动解锁成功');
            return true;
        } catch (error) {
            console.warn('⚠️ TTS 音频手动解锁失败:', error);
            return false;
        }
    }
    
    /**
     * 检查音频是否就绪
     */
    isReady() {
        const ready = this.isAudioUnlocked && 
                      this.audioContext && 
                      this.audioContext.state === 'running';
        return ready;
    }
    
    /**
     * 设置播放失败回调
     */
    onPlaybackFailed(callback) {
        this.playbackFailedCallback = callback;
    }
    
    /**
     * 通知播放失败
     */
    notifyPlaybackFailed(reason) {
        console.warn('⚠️ TTS 播放失败:', reason);
        
        // 移动端首次失败时显示提示
        if (this.isMobile && !this.hasShownUnlockHint) {
            this.hasShownUnlockHint = true;
            this.updateStatus('请点击屏幕启用音频');
            
            if (this.playbackFailedCallback) {
                this.playbackFailedCallback(reason);
            }
        }
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

    async playNext() {
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
        
        // 移动端：在播放前确保 AudioContext 已创建并尝试解锁
        if (this.isMobile) {
            // 尝试创建/恢复 AudioContext
            await this.getOrCreateAudioContext();
            
            // 检查 AudioContext 状态
            if (this.audioContext && this.audioContext.state === 'running') {
                console.log('📱 移动端使用 AudioContext 播放');
                this.playWithAudioContext(audioData);
            } else {
                // AudioContext 未就绪，尝试使用 Audio 元素
                console.log('📱 AudioContext 未就绪 (state:', this.audioContext?.state, '), 尝试 Audio 元素');
                this.playWithAudioElement(audioData);
            }
        } else {
            // 桌面端使用标准 Audio 元素
            this.playWithAudioElement(audioData);
        }
    }
    
    /**
     * 使用 AudioContext 播放音频（移动端更可靠）
     */
    async playWithAudioContext(audioData) {
        try {
            // 关键：确保 AudioContext 处于运行状态
            const ctx = await this.getOrCreateAudioContext();
            
            if (!ctx) {
                console.warn('⚠️ 无法创建 AudioContext，回退到 Audio 元素');
                this.playWithAudioElement(audioData);
                return;
            }
            
            // 检查 AudioContext 状态
            if (ctx.state !== 'running') {
                console.warn('⚠️ AudioContext 状态不是 running:', ctx.state);
                
                if (ctx.state === 'suspended') {
                    console.log('🔄 尝试恢复 AudioContext...');
                    try {
                        await ctx.resume();
                        console.log('✅ AudioContext 恢复成功, 状态:', ctx.state);
                    } catch (resumeError) {
                        console.warn('⚠️ AudioContext 恢复失败:', resumeError);
                    }
                }
                
                // 再次检查，如果仍然不是 running，回退到 Audio 元素
                if (ctx.state !== 'running') {
                    console.warn('⚠️ AudioContext 仍未就绪，回退到 Audio 元素');
                    this.notifyPlaybackFailed('AudioContext 未就绪');
                    this.playWithAudioElement(audioData);
                    return;
                }
            }
            
            // 解码 base64 为 ArrayBuffer
            const binaryString = atob(audioData.base64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // 解码音频数据
            const audioBuffer = await ctx.decodeAudioData(bytes.buffer.slice(0));
            
            // 创建并播放
            this.currentSource = ctx.createBufferSource();
            this.currentSource.buffer = audioBuffer;
            this.currentSource.connect(ctx.destination);
            
            this.currentSource.onended = () => {
                this.currentSource = null;
                this.currentIndex++;
                this.updateProgress();
                this.playNext();
            };
            
            this.currentSource.start(0);
            this.isAudioUnlocked = true;  // 成功播放后标记为已解锁
            this.updateStatus(`播放中 (${this.currentIndex + 1}/${this.totalCount})`);
            this.updateProgress();
            console.log('🔊 AudioContext 播放开始:', audioData.sentence?.substring(0, 20));
            
        } catch (error) {
            console.error('❌ AudioContext 播放失败，回退到 Audio 元素:', error);
            // 回退到标准 Audio 元素
            this.playWithAudioElement(audioData);
        }
    }
    
    /**
     * 使用标准 Audio 元素播放（带重试机制）
     */
    async playWithAudioElement(audioData, retryCount = 0) {
        const audioSrc = `data:audio/mpeg;base64,${audioData.base64}`;
        this.audioElement = new Audio(audioSrc);
        
        // iOS Safari 需要设置这些属性
        if (this.isIOS) {
            this.audioElement.playsInline = true;
            this.audioElement.setAttribute('playsinline', '');
            this.audioElement.setAttribute('webkit-playsinline', '');
        }

        this.audioElement.addEventListener('ended', () => {
            this.currentIndex++;
            this.updateProgress();
            this.playNext();
        });

        this.audioElement.addEventListener('error', (e) => {
            console.error('❌ Audio 元素播放错误:', e);
            
            // 移动端重试机制
            if (this.isMobile && retryCount < this.maxRetries) {
                console.log(`🔄 重试播放 (${retryCount + 1}/${this.maxRetries})...`);
                setTimeout(() => {
                    this.playWithAudioElement(audioData, retryCount + 1);
                }, this.retryDelay * (retryCount + 1));
                return;
            }
            
            this.currentIndex++;
            this.playNext();
        });

        try {
            await this.audioElement.play();
            this.isAudioUnlocked = true;  // 成功播放后标记为已解锁
            this.updateStatus(`播放中 (${this.currentIndex + 1}/${this.totalCount})`);
            console.log('🔊 Audio 元素播放开始:', audioData.sentence?.substring(0, 20));
        } catch (error) {
            console.error('❌ Audio 元素播放失败:', error.name, error.message);
            
            // 移动端播放失败时的处理
            if (this.isMobile) {
                if (error.name === 'NotAllowedError') {
                    // 自动播放被阻止，需要用户交互
                    this.notifyPlaybackFailed('需要用户交互才能播放音频');
                    
                    if (!this.isAudioUnlocked) {
                        this.updateStatus('请点击屏幕启用音频');
                        return;  // 不重试，等待用户交互
                    }
                }
                
                // 其他错误进行重试
                if (retryCount < this.maxRetries) {
                    console.log(`🔄 重试播放 (${retryCount + 1}/${this.maxRetries})...`);
                    setTimeout(() => {
                        this.playWithAudioElement(audioData, retryCount + 1);
                    }, this.retryDelay * (retryCount + 1));
                    return;
                }
            } else {
                // 桌面端重试
                if (retryCount < this.maxRetries) {
                    setTimeout(() => {
                        this.playWithAudioElement(audioData, retryCount + 1);
                    }, this.retryDelay * (retryCount + 1));
                    return;
                }
            }
            
            // 所有重试都失败，跳到下一个
            this.currentIndex++;
            this.playNext();
        }

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
        // 停止 AudioContext 源
        if (this.currentSource) {
            try {
                this.currentSource.stop();
            } catch (e) {
                // 忽略已经停止的源
            }
            this.currentSource = null;
        }
        
        // 停止 Audio 元素
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
        
        // 如果 TTS 已开始，通知 VAD 可以重新开始
        if (this.ttsStarted && window.vadDetector) {
            this.ttsStarted = false;
            // 用户主动打断时不自动开始录音，由用户决定
        }
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
