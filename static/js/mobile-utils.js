/**
 * 移动端工具函数模块
 * 提供移动端检测、音频解锁、触摸事件处理等功能
 */

const MobileUtils = {
    // 缓存检测结果
    _cache: {},

    /**
     * 检测是否为移动设备
     * @returns {boolean}
     */
    isMobile() {
        if (this._cache.isMobile !== undefined) {
            return this._cache.isMobile;
        }
        this._cache.isMobile = /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        return this._cache.isMobile;
    },

    /**
     * 检测是否为 iOS 设备
     * @returns {boolean}
     */
    isIOS() {
        if (this._cache.isIOS !== undefined) {
            return this._cache.isIOS;
        }
        this._cache.isIOS = /iPhone|iPad|iPod/i.test(navigator.userAgent) || 
            (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        return this._cache.isIOS;
    },

    /**
     * 检测是否为 Android 设备
     * @returns {boolean}
     */
    isAndroid() {
        if (this._cache.isAndroid !== undefined) {
            return this._cache.isAndroid;
        }
        this._cache.isAndroid = /Android/i.test(navigator.userAgent);
        return this._cache.isAndroid;
    },

    /**
     * 检测是否为触摸设备
     * @returns {boolean}
     */
    isTouchDevice() {
        if (this._cache.isTouchDevice !== undefined) {
            return this._cache.isTouchDevice;
        }
        this._cache.isTouchDevice = 'ontouchstart' in window || 
            navigator.maxTouchPoints > 0 || 
            navigator.msMaxTouchPoints > 0;
        return this._cache.isTouchDevice;
    },

    /**
     * 检测当前是否为横向模式
     * @returns {boolean}
     */
    isLandscape() {
        if (window.screen && window.screen.orientation) {
            return window.screen.orientation.type.includes('landscape');
        }
        return window.innerWidth > window.innerHeight;
    },

    /**
     * 监听屏幕方向变化
     * @param {Function} callback - 回调函数，参数为 isLandscape
     * @returns {Function} 取消监听函数
     */
    onOrientationChange(callback) {
        const handler = () => {
            callback(this.isLandscape());
        };

        if (window.screen && window.screen.orientation) {
            window.screen.orientation.addEventListener('change', handler);
            return () => window.screen.orientation.removeEventListener('change', handler);
        } else {
            window.addEventListener('orientationchange', handler);
            return () => window.removeEventListener('orientationchange', handler);
        }
    },

    /**
     * 获取安全区域内边距
     * @returns {Object} {top, right, bottom, left}
     */
    getSafeAreaInsets() {
        const computedStyle = getComputedStyle(document.documentElement);
        return {
            top: parseInt(computedStyle.getPropertyValue('--safe-area-inset-top') || '0', 10),
            right: parseInt(computedStyle.getPropertyValue('--safe-area-inset-right') || '0', 10),
            bottom: parseInt(computedStyle.getPropertyValue('--safe-area-inset-bottom') || '0', 10),
            left: parseInt(computedStyle.getPropertyValue('--safe-area-inset-left') || '0', 10),
        };
    },

    /**
     * 检测 MediaRecorder 支持情况
     * @returns {Object} {supported, mimeTypes}
     */
    checkMediaRecorderSupport() {
        if (!window.MediaRecorder) {
            return { supported: false, mimeTypes: [] };
        }

        const mimeTypes = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
            'audio/wav',
            'audio/mpeg'
        ];

        const supportedTypes = mimeTypes.filter(type => {
            try {
                return MediaRecorder.isTypeSupported(type);
            } catch (e) {
                return false;
            }
        });

        return {
            supported: supportedTypes.length > 0,
            mimeTypes: supportedTypes
        };
    },

    /**
     * 检测 Web Audio API 支持情况
     * @returns {boolean}
     */
    checkWebAudioSupport() {
        return !!(window.AudioContext || window.webkitAudioContext);
    },

    /**
     * 检测 getUserMedia 支持情况
     * @returns {boolean}
     */
    checkGetUserMediaSupport() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    },

    /**
     * 获取完整的功能支持报告
     * @returns {Object}
     */
    getFeatureSupport() {
        return {
            isMobile: this.isMobile(),
            isIOS: this.isIOS(),
            isAndroid: this.isAndroid(),
            isTouchDevice: this.isTouchDevice(),
            webAudio: this.checkWebAudioSupport(),
            getUserMedia: this.checkGetUserMediaSupport(),
            mediaRecorder: this.checkMediaRecorderSupport(),
        };
    },

    /**
     * 打印功能支持报告到控制台
     */
    logFeatureSupport() {
        const support = this.getFeatureSupport();
        console.log('📱 移动端功能支持报告:');
        console.table(support);
    }
};

/**
 * 音频解锁管理器
 * 处理移动端音频播放需要用户手势的问题
 */
const AudioUnlockManager = {
    _audioContext: null,
    _isUnlocked: false,
    _unlockPromise: null,
    _listeners: [],

    /**
     * 检查音频是否已解锁
     * @returns {boolean}
     */
    isUnlocked() {
        return this._isUnlocked;
    },

    /**
     * 获取或创建 AudioContext
     * @returns {AudioContext}
     */
    getAudioContext() {
        if (!this._audioContext) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                this._audioContext = new AudioContextClass();
            }
        }
        return this._audioContext;
    },

    /**
     * 尝试解锁音频
     * 在用户交互事件中调用此方法
     * @returns {Promise<boolean>}
     */
    async unlock() {
        if (this._isUnlocked) {
            return true;
        }

        // 如果已经有解锁进程在运行，返回该 Promise
        if (this._unlockPromise) {
            return this._unlockPromise;
        }

        this._unlockPromise = this._doUnlock();
        const result = await this._unlockPromise;
        this._unlockPromise = null;
        return result;
    },

    async _doUnlock() {
        try {
            // 方法1：恢复挂起的 AudioContext
            const ctx = this.getAudioContext();
            if (ctx && ctx.state === 'suspended') {
                await ctx.resume();
            }

            // 方法2：播放静音音频
            await this._playSilentAudio();

            // 方法3：创建并播放一个空的 AudioBuffer
            if (ctx) {
                const buffer = ctx.createBuffer(1, 1, 22050);
                const source = ctx.createBufferSource();
                source.buffer = buffer;
                source.connect(ctx.destination);
                source.start(0);
            }

            this._isUnlocked = true;
            console.log('🔓 音频已解锁');
            
            // 通知所有监听器
            this._listeners.forEach(cb => cb(true));
            
            return true;
        } catch (error) {
            console.warn('⚠️ 音频解锁失败:', error);
            return false;
        }
    },

    /**
     * 播放静音音频以解锁
     * @private
     */
    async _playSilentAudio() {
        return new Promise((resolve) => {
            const audio = new Audio();
            // 极短的静音 WAV 文件（44字节的最小有效WAV）
            audio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';
            audio.volume = 0.01;
            
            const playPromise = audio.play();
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        setTimeout(() => {
                            audio.pause();
                            resolve(true);
                        }, 10);
                    })
                    .catch(() => {
                        resolve(false);
                    });
            } else {
                resolve(true);
            }
        });
    },

    /**
     * 添加解锁状态变化监听器
     * @param {Function} callback
     */
    onUnlock(callback) {
        if (this._isUnlocked) {
            callback(true);
        } else {
            this._listeners.push(callback);
        }
    },

    /**
     * 设置全局用户交互监听
     * 在首次用户交互时自动尝试解锁音频
     */
    setupAutoUnlock() {
        const events = ['touchstart', 'touchend', 'click', 'keydown'];
        
        const handler = async () => {
            const unlocked = await this.unlock();
            if (unlocked) {
                // 解锁成功后移除所有监听器
                events.forEach(event => {
                    document.removeEventListener(event, handler, { capture: true });
                });
            }
        };

        events.forEach(event => {
            document.addEventListener(event, handler, { capture: true, passive: true });
        });
    }
};

/**
 * 触摸事件处理工具
 */
const TouchUtils = {
    /**
     * 添加触摸友好的点击事件
     * 解决移动端 300ms 延迟问题
     * @param {Element} element
     * @param {Function} callback
     * @param {Object} options
     */
    addTapListener(element, callback, options = {}) {
        const { threshold = 10, timeout = 200 } = options;
        let startX, startY, startTime;

        const onTouchStart = (e) => {
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            startTime = Date.now();
        };

        const onTouchEnd = (e) => {
            if (!startTime) return;

            const touch = e.changedTouches[0];
            const deltaX = Math.abs(touch.clientX - startX);
            const deltaY = Math.abs(touch.clientY - startY);
            const deltaTime = Date.now() - startTime;

            if (deltaX < threshold && deltaY < threshold && deltaTime < timeout) {
                e.preventDefault();
                callback(e);
            }

            startTime = null;
        };

        element.addEventListener('touchstart', onTouchStart, { passive: true });
        element.addEventListener('touchend', onTouchEnd, { passive: false });

        // 返回清理函数
        return () => {
            element.removeEventListener('touchstart', onTouchStart);
            element.removeEventListener('touchend', onTouchEnd);
        };
    },

    /**
     * 防止双击缩放
     * @param {Element} element
     */
    preventDoubleTapZoom(element) {
        let lastTap = 0;
        element.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTap < 300) {
                e.preventDefault();
            }
            lastTap = now;
        }, { passive: false });
    }
};

/**
 * 视口工具
 */
const ViewportUtils = {
    /**
     * 获取视口尺寸
     * @returns {Object} {width, height}
     */
    getSize() {
        return {
            width: window.innerWidth || document.documentElement.clientWidth,
            height: window.innerHeight || document.documentElement.clientHeight
        };
    },

    /**
     * 检测是否为小屏幕设备
     * @param {number} breakpoint - 断点宽度，默认 600px
     * @returns {boolean}
     */
    isSmallScreen(breakpoint = 600) {
        return this.getSize().width <= breakpoint;
    },

    /**
     * 监听视口尺寸变化
     * @param {Function} callback
     * @param {number} debounce - 防抖时间，默认 100ms
     * @returns {Function} 取消监听函数
     */
    onResize(callback, debounce = 100) {
        let timeoutId;
        const handler = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                callback(this.getSize());
            }, debounce);
        };

        window.addEventListener('resize', handler);
        return () => {
            clearTimeout(timeoutId);
            window.removeEventListener('resize', handler);
        };
    },

    /**
     * 锁定视口缩放（防止意外缩放）
     */
    lockScale() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
        }
    }
};

// 全局初始化
(function initMobileUtils() {
    // 在页面加载时设置音频自动解锁
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            AudioUnlockManager.setupAutoUnlock();
        });
    } else {
        AudioUnlockManager.setupAutoUnlock();
    }

    // 添加 CSS 变量用于安全区域
    if (CSS.supports('padding-bottom: env(safe-area-inset-bottom)')) {
        document.documentElement.style.setProperty('--safe-area-inset-top', 'env(safe-area-inset-top)');
        document.documentElement.style.setProperty('--safe-area-inset-right', 'env(safe-area-inset-right)');
        document.documentElement.style.setProperty('--safe-area-inset-bottom', 'env(safe-area-inset-bottom)');
        document.documentElement.style.setProperty('--safe-area-inset-left', 'env(safe-area-inset-left)');
    }

    // 打印功能支持报告（仅开发环境）
    if (MobileUtils.isMobile()) {
        console.log('📱 检测到移动设备');
        MobileUtils.logFeatureSupport();
    }
})();

// 导出到全局
window.MobileUtils = MobileUtils;
window.AudioUnlockManager = AudioUnlockManager;
window.TouchUtils = TouchUtils;
window.ViewportUtils = ViewportUtils;
