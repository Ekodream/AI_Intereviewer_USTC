/**
 * 状态管理器 - 集中管理应用状态
 * 
 * 使用单一数据源模式，替代分散在各模块的全局状态。
 * 支持状态订阅和持久化。
 */

import { eventBus, Events } from './event-bus.js';

class StateManager {
    constructor() {
        // 初始状态
        this._state = {
            // 会话状态
            session: {
                id: null,
                createdAt: null,
                roomId: null,
            },
            
            // 面试状态
            interview: {
                currentStage: 0,
                style: 'normal',
                isStarted: false,
                isCompleted: false,
            },
            
            // 音频状态
            audio: {
                vadState: 'idle',      // idle | listening | speaking | processing | paused
                ttsState: 'idle',      // idle | playing | loading
                ttsQueueSize: 0,
                isMuted: false,
            },
            
            // 视频状态
            video: {
                isRecording: false,
                cameraReady: false,
                recordingDuration: 0,
            },
            
            // 对话状态
            chat: {
                history: [],
                messageCount: 0,
                isStreaming: false,
                lastMessageTime: null,
            },
            
            // 简历状态
            resume: {
                isUploaded: false,
                fileName: null,
                analysis: null,
            },
            
            // 导师信息
            advisor: {
                name: null,
                school: null,
                info: null,
                isSearching: false,
            },
            
            // 设置
            settings: {
                ttsEnabled: true,
                vadEnabled: true,
                ragEnabled: true,
                videoEnabled: false,
                compactMode: false,
            },
            
            // UI 状态
            ui: {
                isLoading: false,
                loadingMessage: '',
                currentPanel: null,
                sidebarOpen: false,
            },
        };
        
        // 状态变更订阅者
        this._subscribers = new Map();
        
        // 从本地存储恢复设置
        this._loadPersistedState();
    }
    
    /**
     * 获取当前状态
     * @param {string} [path] - 状态路径，如 'audio.vadState'
     * @returns {*} 状态值
     */
    get(path) {
        if (!path) {
            return { ...this._state };
        }
        
        return path.split('.').reduce((obj, key) => {
            return obj && obj[key] !== undefined ? obj[key] : undefined;
        }, this._state);
    }
    
    /**
     * 更新状态
     * @param {Object} updates - 状态更新对象
     * @param {Object} options - 选项
     * @param {boolean} options.silent - 是否静默更新（不触发事件）
     * @param {boolean} options.persist - 是否持久化到本地存储
     */
    update(updates, options = {}) {
        const { silent = false, persist = false } = options;
        const oldState = { ...this._state };
        
        // 深度合并更新
        this._deepMerge(this._state, updates);
        
        // 持久化
        if (persist) {
            this._persistState();
        }
        
        // 通知订阅者
        if (!silent) {
            this._notifySubscribers(updates, oldState);
        }
    }
    
    /**
     * 订阅状态变更
     * @param {string} path - 状态路径
     * @param {Function} callback - 回调函数
     * @returns {Function} 取消订阅函数
     */
    subscribe(path, callback) {
        if (!this._subscribers.has(path)) {
            this._subscribers.set(path, []);
        }
        this._subscribers.get(path).push(callback);
        
        // 返回取消订阅函数
        return () => {
            const subs = this._subscribers.get(path);
            if (subs) {
                const index = subs.indexOf(callback);
                if (index > -1) {
                    subs.splice(index, 1);
                }
            }
        };
    }
    
    /**
     * 重置状态到初始值
     * @param {string} [section] - 要重置的部分，如 'chat'
     */
    reset(section) {
        if (section) {
            const initialState = this._getInitialState(section);
            if (initialState) {
                this._state[section] = initialState;
            }
        } else {
            this._state = this._getInitialState();
        }
        
        this._notifySubscribers(this._state, {});
    }
    
    // ==================== 便捷方法 ====================
    
    /**
     * 更新 VAD 状态
     */
    setVADState(state) {
        this.update({ audio: { vadState: state } });
        eventBus.emit(`vad:${state}`);
    }
    
    /**
     * 更新 TTS 状态
     */
    setTTSState(state, queueSize = null) {
        const updates = { audio: { ttsState: state } };
        if (queueSize !== null) {
            updates.audio.ttsQueueSize = queueSize;
        }
        this.update(updates);
    }
    
    /**
     * 添加消息到历史
     */
    addMessage(role, content) {
        const history = [...this._state.chat.history];
        history.push({ role, content, timestamp: Date.now() });
        this.update({
            chat: {
                history,
                messageCount: history.length,
                lastMessageTime: Date.now(),
            }
        });
    }
    
    /**
     * 更新面试阶段
     */
    setInterviewStage(stage) {
        const oldStage = this._state.interview.currentStage;
        if (stage !== oldStage) {
            this.update({ interview: { currentStage: stage } });
            eventBus.emit(Events.INTERVIEW_STAGE_CHANGED, { oldStage, newStage: stage });
        }
    }
    
    /**
     * 更新设置
     */
    updateSettings(settings) {
        this.update({ settings }, { persist: true });
        eventBus.emit(Events.SETTINGS_CHANGED, settings);
    }
    
    // ==================== 私有方法 ====================
    
    _deepMerge(target, source) {
        for (const key in source) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                if (!target[key]) {
                    target[key] = {};
                }
                this._deepMerge(target[key], source[key]);
            } else {
                target[key] = source[key];
            }
        }
    }
    
    _notifySubscribers(updates, oldState) {
        // 通知所有匹配的订阅者
        for (const [path, callbacks] of this._subscribers) {
            const newValue = this.get(path);
            const oldValue = path.split('.').reduce((obj, key) => {
                return obj && obj[key] !== undefined ? obj[key] : undefined;
            }, oldState);
            
            if (JSON.stringify(newValue) !== JSON.stringify(oldValue)) {
                callbacks.forEach(cb => {
                    try {
                        cb(newValue, oldValue);
                    } catch (error) {
                        console.error(`Error in state subscriber for ${path}:`, error);
                    }
                });
            }
        }
    }
    
    _persistState() {
        try {
            const toPersist = {
                settings: this._state.settings,
            };
            localStorage.setItem('app_state', JSON.stringify(toPersist));
        } catch (error) {
            console.error('Error persisting state:', error);
        }
    }
    
    _loadPersistedState() {
        try {
            const saved = localStorage.getItem('app_state');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed.settings) {
                    this._deepMerge(this._state.settings, parsed.settings);
                }
            }
        } catch (error) {
            console.error('Error loading persisted state:', error);
        }
    }
    
    _getInitialState(section) {
        const initial = {
            session: { id: null, createdAt: null, roomId: null },
            interview: { currentStage: 0, style: 'normal', isStarted: false, isCompleted: false },
            audio: { vadState: 'idle', ttsState: 'idle', ttsQueueSize: 0, isMuted: false },
            video: { isRecording: false, cameraReady: false, recordingDuration: 0 },
            chat: { history: [], messageCount: 0, isStreaming: false, lastMessageTime: null },
            resume: { isUploaded: false, fileName: null, analysis: null },
            advisor: { name: null, school: null, info: null, isSearching: false },
            settings: { ttsEnabled: true, vadEnabled: true, ragEnabled: true, videoEnabled: false, compactMode: false },
            ui: { isLoading: false, loadingMessage: '', currentPanel: null, sidebarOpen: false },
        };
        
        return section ? initial[section] : initial;
    }
}

// 创建全局状态管理器实例
export const stateManager = new StateManager();

// 挂载到 window
if (typeof window !== 'undefined') {
    window.stateManager = stateManager;
}

export default StateManager;
