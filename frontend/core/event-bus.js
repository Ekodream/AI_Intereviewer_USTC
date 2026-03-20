/**
 * 事件总线 - 解耦模块间通信
 * 
 * 使用发布-订阅模式替代全局 window 对象的直接调用，
 * 解决 vad.js 和 tts-stream.js 之间的循环依赖问题。
 */

class EventBus {
    constructor() {
        this._events = new Map();
        this._onceEvents = new Map();
    }
    
    /**
     * 订阅事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     * @returns {Function} 取消订阅的函数
     */
    on(event, callback) {
        if (!this._events.has(event)) {
            this._events.set(event, []);
        }
        this._events.get(event).push(callback);
        
        // 返回取消订阅函数
        return () => this.off(event, callback);
    }
    
    /**
     * 订阅一次性事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    once(event, callback) {
        const wrapper = (...args) => {
            this.off(event, wrapper);
            callback.apply(this, args);
        };
        this.on(event, wrapper);
    }
    
    /**
     * 取消订阅
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        const callbacks = this._events.get(event);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }
    
    /**
     * 发布事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     */
    emit(event, data) {
        const callbacks = this._events.get(event);
        if (callbacks) {
            callbacks.forEach(cb => {
                try {
                    cb(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    /**
     * 清除指定事件的所有订阅
     * @param {string} event - 事件名称
     */
    clear(event) {
        if (event) {
            this._events.delete(event);
        } else {
            this._events.clear();
        }
    }
    
    /**
     * 获取事件的订阅者数量
     * @param {string} event - 事件名称
     * @returns {number} 订阅者数量
     */
    listenerCount(event) {
        const callbacks = this._events.get(event);
        return callbacks ? callbacks.length : 0;
    }
}

// 预定义事件常量
export const Events = {
    // ==================== 音频事件 ====================
    // VAD 相关
    VAD_STARTED: 'vad:started',           // VAD 开始监听
    VAD_STOPPED: 'vad:stopped',           // VAD 停止监听
    VAD_PAUSED: 'vad:paused',             // VAD 暂停（TTS 播放时）
    VAD_RESUMED: 'vad:resumed',           // VAD 恢复
    VAD_SPEECH_START: 'vad:speech_start', // 检测到说话开始
    VAD_SPEECH_END: 'vad:speech_end',     // 检测到说话结束
    VAD_SILENCE_TIMEOUT: 'vad:silence_timeout', // 静音超时
    
    // TTS 相关
    TTS_STARTED: 'tts:started',           // TTS 开始播放
    TTS_ENDED: 'tts:ended',               // TTS 播放完成
    TTS_INTERRUPTED: 'tts:interrupted',   // TTS 被中断
    TTS_QUEUE_UPDATED: 'tts:queue_updated', // TTS 队列更新
    TTS_ERROR: 'tts:error',               // TTS 错误
    
    // 音频录制
    AUDIO_RECORDING_START: 'audio:recording_start',
    AUDIO_RECORDING_STOP: 'audio:recording_stop',
    AUDIO_DATA_READY: 'audio:data_ready', // 音频数据就绪（发送 ASR）
    
    // ASR 相关
    ASR_STARTED: 'asr:started',           // ASR 开始识别
    ASR_COMPLETED: 'asr:completed',       // ASR 识别完成
    ASR_ERROR: 'asr:error',               // ASR 错误
    
    // ==================== 视频事件 ====================
    VIDEO_RECORDING_START: 'video:recording_start',
    VIDEO_RECORDING_STOP: 'video:recording_stop',
    VIDEO_UPLOADED: 'video:uploaded',
    CAMERA_READY: 'camera:ready',
    CAMERA_ERROR: 'camera:error',
    
    // ==================== 对话事件 ====================
    MESSAGE_SENDING: 'message:sending',   // 消息发送中
    MESSAGE_SENT: 'message:sent',         // 消息已发送
    MESSAGE_RECEIVED: 'message:received', // 收到消息
    MESSAGE_STREAM_START: 'message:stream_start', // 流式消息开始
    MESSAGE_STREAM_CHUNK: 'message:stream_chunk', // 流式消息片段
    MESSAGE_STREAM_END: 'message:stream_end',     // 流式消息结束
    
    // ==================== 面试事件 ====================
    INTERVIEW_STARTED: 'interview:started',
    INTERVIEW_STAGE_CHANGED: 'interview:stage_changed',
    INTERVIEW_COMPLETED: 'interview:completed',
    INTERVIEW_ERROR: 'interview:error',
    
    // ==================== UI 事件 ====================
    LOADING_SHOW: 'ui:loading_show',
    LOADING_HIDE: 'ui:loading_hide',
    TOAST_SHOW: 'ui:toast_show',
    MODAL_OPEN: 'ui:modal_open',
    MODAL_CLOSE: 'ui:modal_close',
    SETTINGS_CHANGED: 'ui:settings_changed',
    
    // ==================== 应用事件 ====================
    APP_INITIALIZED: 'app:initialized',
    APP_ERROR: 'app:error',
    SESSION_CREATED: 'session:created',
    SESSION_EXPIRED: 'session:expired',
};

// 创建全局事件总线实例
export const eventBus = new EventBus();

// 也挂载到 window 上，便于非模块脚本使用
if (typeof window !== 'undefined') {
    window.eventBus = eventBus;
    window.Events = Events;
}

export default EventBus;
