/**
 * 面试模式管理器 - 管理标准/沉浸/测试模式
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager } from '../../core/state-manager.js';
import { apiClient } from '../../core/api-client.js';

export class ModeManager {
    constructor() {
        this.interviewMode = 'standard'; // standard | immersive | test
        this.testRoomId = null;
        this.testRoomInfo = null;
        
        // 沉浸模式观察器
        this._immersiveRecordObserver = null;
        this._immersiveStatusObserver = null;
    }
    
    /**
     * 初始化
     */
    init() {
        this.showModeSelector();
        this.selectMode('standard', false);
        this.bindEvents();
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        this.bindModeSelectorEvents();
        this.bindImmersiveEvents();
    }
    
    /**
     * 绑定模式选择器事件
     */
    bindModeSelectorEvents() {
        document.querySelectorAll('.mode-option').forEach((option) => {
            option.addEventListener('click', () => {
                const mode = option.getAttribute('data-mode');
                if (!mode) return;
                
                // 测试模式需要验证房间号
                if (mode === 'test') {
                    const roomId = document.getElementById('room-id-input').value.trim();
                    if (!roomId || roomId.length !== 6) {
                        alert('请输入6位房间号');
                        return;
                    }
                    this.joinTestRoom(roomId);
                    return;
                }
                
                option.classList.add('selecting');
                setTimeout(() => {
                    this.selectMode(mode, true);
                    this.hideModeSelector();
                }, 250);
            });
        });
    }
    
    /**
     * 绑定沉浸模式事件
     */
    bindImmersiveEvents() {
        const immersiveRecordBtn = document.getElementById('immersive-record-btn');
        if (immersiveRecordBtn) {
            immersiveRecordBtn.addEventListener('click', () => {
                document.getElementById('record-btn')?.click();
            });
        }
        
        const settingsToggle = document.getElementById('immersive-settings-toggle');
        if (settingsToggle) {
            settingsToggle.addEventListener('click', () => this.toggleImmersiveSettings());
        }
        
        const settingsClose = document.getElementById('immersive-settings-close');
        if (settingsClose) {
            settingsClose.addEventListener('click', () => this.closeImmersiveSettings());
        }
        
        // 沉浸模式 RAG 开关
        const immersiveRag = document.getElementById('immersive-enable-rag');
        if (immersiveRag) {
            immersiveRag.addEventListener('change', () => {
                const settings = window.settingsManager?.settings;
                if (settings) {
                    settings.enable_rag = immersiveRag.checked;
                    const enableRag = document.getElementById('enable-rag');
                    if (enableRag) enableRag.checked = immersiveRag.checked;
                    const ragSettings = document.getElementById('rag-settings');
                    if (ragSettings) ragSettings.style.display = immersiveRag.checked ? 'block' : 'none';
                    window.settingsManager?.saveSettings();
                }
            });
        }
        
        // 沉浸模式简历按钮
        const immersiveResumeBtn = document.getElementById('immersive-resume-btn');
        if (immersiveResumeBtn) {
            immersiveResumeBtn.addEventListener('click', () => {
                document.getElementById('resume-input')?.click();
                this.closeImmersiveSettings();
            });
        }
        
        // 沉浸模式导师按钮
        const immersiveAdvisorBtn = document.getElementById('immersive-advisor-btn');
        if (immersiveAdvisorBtn) {
            immersiveAdvisorBtn.addEventListener('click', () => {
                window.advisorManager?.showModal();
                this.closeImmersiveSettings();
            });
        }
        
        // 沉浸模式 IDE 按钮
        const immersiveIdeBtn = document.getElementById('immersive-ide-btn');
        if (immersiveIdeBtn) {
            immersiveIdeBtn.addEventListener('click', () => {
                window.chat?.showIDEPanel();
                this.closeImmersiveSettings();
            });
        }
        
        // 沉浸模式报告按钮
        const immersiveReportBtn = document.getElementById('immersive-report-btn');
        if (immersiveReportBtn) {
            immersiveReportBtn.addEventListener('click', () => {
                this.closeAllDrawers();
                document.getElementById('report-drawer')?.classList.add('show');
                document.getElementById('toggle-report-btn')?.classList.add('active');
                this.closeImmersiveSettings();
            });
        }
        
        // 沉浸模式新对话按钮
        const immersiveNewChatBtn = document.getElementById('immersive-new-chat-btn');
        if (immersiveNewChatBtn) {
            immersiveNewChatBtn.addEventListener('click', () => {
                if (!confirm('确定要开始新对话吗？当前对话历史将被清空。')) return;
                window.chat?.clearHistory();
                window.phaseTimeline?.reset();
                this.updateImmersiveMsgCount();
                this.updateImmersiveStatus('点击麦克风开始面试');
                this.closeImmersiveSettings();
            });
        }
        
        // 沉浸模式切换标准模式按钮
        const immersiveSwitchModeBtn = document.getElementById('immersive-switch-mode-btn');
        if (immersiveSwitchModeBtn) {
            immersiveSwitchModeBtn.addEventListener('click', () => {
                this.selectMode('standard', true);
                this.closeImmersiveSettings();
            });
        }
    }
    
    /**
     * 显示模式选择器
     */
    showModeSelector() {
        const selector = document.getElementById('mode-selector');
        if (selector) selector.classList.remove('hidden');
    }
    
    /**
     * 隐藏模式选择器
     */
    hideModeSelector() {
        const selector = document.getElementById('mode-selector');
        if (selector) selector.classList.add('hidden');
    }
    
    /**
     * 选择面试模式
     */
    selectMode(mode, save = true) {
        this.interviewMode = (mode === 'immersive') ? 'immersive' : 'standard';
        
        if (save) {
            localStorage.setItem('interviewMode', this.interviewMode);
        }
        
        document.body.classList.remove('standard-mode', 'immersive-mode');
        if (this.interviewMode === 'immersive') {
            this.switchToImmersiveMode();
        } else {
            this.switchToStandardMode();
        }
    }
    
    /**
     * 切换到标准模式
     */
    switchToStandardMode() {
        document.body.classList.add('standard-mode');
        
        const immersiveStage = document.getElementById('immersive-stage');
        if (immersiveStage) immersiveStage.classList.remove('active');
        
        const settingsToggle = document.getElementById('immersive-settings-toggle');
        if (settingsToggle) settingsToggle.classList.remove('visible');
        
        this.closeImmersiveSettings();
        
        const enableTts = document.getElementById('enable-tts');
        if (enableTts) enableTts.disabled = false;
    }
    
    /**
     * 切换到沉浸模式
     */
    switchToImmersiveMode() {
        document.body.classList.add('immersive-mode');
        
        const immersiveStage = document.getElementById('immersive-stage');
        if (immersiveStage) immersiveStage.classList.add('active');
        
        const settingsToggle = document.getElementById('immersive-settings-toggle');
        if (settingsToggle) settingsToggle.classList.add('visible');
        
        // 沉浸模式强制启用 TTS
        const settings = window.settingsManager?.settings;
        if (settings) {
            settings.enable_tts = true;
            const enableTts = document.getElementById('enable-tts');
            if (enableTts) {
                enableTts.checked = true;
                enableTts.disabled = true;
            }
            window.settingsManager?.saveSettings();
        }
        
        // 同步 UI 状态
        const immersiveRag = document.getElementById('immersive-enable-rag');
        if (immersiveRag && settings) immersiveRag.checked = settings.enable_rag;
        
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        if (immersiveEnableVideo && settings) immersiveEnableVideo.checked = settings.enable_video;
        
        window.resumeManager?.updateImmersiveBtn();
        this.updateImmersiveMsgCount();
        this.updateImmersivePhase(window.chat?.currentPhase || 0);
        this.syncImmersiveVoiceState();
    }
    
    /**
     * 加入测试房间
     */
    async joinTestRoom(roomId) {
        eventBus.emit(Events.LOADING_SHOW, '正在加入房间...');
        
        try {
            const data = await apiClient.post(`/api/student/join/${roomId}`);
            const room = data.room;
            
            // 应用房间配置
            if (window.settingsManager) {
                window.settingsManager.settings = room.config;
                await window.settingsManager.saveSettings();
            }
            
            // 标记为测试模式
            this.interviewMode = 'test';
            this.testRoomId = roomId;
            this.testRoomInfo = room;
            localStorage.setItem('testRoomId', roomId);
            localStorage.setItem('interviewMode', 'test');
            
            // 锁定设置
            window.settingsManager?.lockSettings();
            
            // 显示房间信息横幅
            this.showRoomInfoBanner(room);
            
            // 隐藏模式选择器
            this.hideModeSelector();
            
            eventBus.emit(Events.LOADING_HIDE);
            alert(`已成功加入房间 ${roomId}\n导师：${room.teacher_name}\n配置已锁定，开始面试吧！`);
        } catch (error) {
            eventBus.emit(Events.LOADING_HIDE);
            alert('加入房间失败：' + error.message);
        }
    }
    
    /**
     * 显示房间信息横幅
     */
    showRoomInfoBanner(room) {
        // 在侧边栏顶部显示锁定提示
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            const lockBanner = document.createElement('div');
            lockBanner.className = 'test-mode-banner';
            lockBanner.style.cssText = 'background: #f56565; color: #fff; padding: 12px; text-align: center; font-weight: 600; border-radius: 8px; margin-bottom: 16px;';
            lockBanner.innerHTML = '<i class="fas fa-lock"></i> 测试模式 - 配置已锁定';
            sidebar.insertBefore(lockBanner, sidebar.firstChild);
        }
        
        // 在顶部显示房间信息
        const commandBar = document.querySelector('.command-bar-center');
        if (commandBar) {
            const roomInfo = document.createElement('div');
            roomInfo.className = 'room-info-badge';
            roomInfo.style.cssText = 'background: rgba(99, 179, 237, 0.2); padding: 8px 16px; border-radius: 8px; color: #63b3ed; font-size: 14px;';
            roomInfo.innerHTML = `<i class="fas fa-door-open"></i> 房间 ${room.room_id} | 导师：${room.teacher_name}`;
            commandBar.appendChild(roomInfo);
        }
    }
    
    /**
     * 提交测试结果
     */
    async submitTestResult() {
        if (this.interviewMode !== 'test') return;
        
        try {
            await apiClient.post('/api/student/submit');
            console.log('✅ 测试结果已自动提交');
        } catch (error) {
            console.error('提交测试结果失败:', error);
        }
    }
    
    /**
     * 切换沉浸模式设置面板
     */
    toggleImmersiveSettings() {
        const settingsPanel = document.getElementById('immersive-settings-panel');
        if (!settingsPanel) return;
        
        if (settingsPanel.classList.contains('show')) {
            this.closeImmersiveSettings();
            return;
        }
        
        settingsPanel.classList.add('visible');
        requestAnimationFrame(() => {
            settingsPanel.classList.add('show');
        });
    }
    
    /**
     * 关闭沉浸模式设置面板
     */
    closeImmersiveSettings() {
        const settingsPanel = document.getElementById('immersive-settings-panel');
        if (!settingsPanel) return;
        
        settingsPanel.classList.remove('show');
        setTimeout(() => {
            if (!settingsPanel.classList.contains('show')) {
                settingsPanel.classList.remove('visible');
            }
        }, 350);
    }
    
    /**
     * 关闭所有抽屉面板
     */
    closeAllDrawers() {
        document.querySelectorAll('.side-drawer').forEach(d => d.classList.remove('show'));
        document.getElementById('toggle-rag-btn')?.classList.remove('active');
        document.getElementById('toggle-report-btn')?.classList.remove('active');
    }
    
    /**
     * 更新沉浸模式阶段显示
     */
    updateImmersivePhase(phase) {
        const phaseEl = document.getElementById('immersive-phase');
        if (!phaseEl) return;
        
        const phaseNames = ['开始', '自我介绍', '经历深挖', '基础知识', '代码', '科研动机', '科研潜力', '综合追问', '学生反问', '结束'];
        phaseEl.textContent = phaseNames[phase] || '面试中';
    }
    
    /**
     * 更新沉浸模式对话轮数
     */
    updateImmersiveMsgCount() {
        const countEl = document.getElementById('immersive-msg-count');
        if (!countEl || !window.chat) return;
        const rounds = Math.ceil(window.chat.history.length / 2);
        countEl.textContent = `${rounds} 轮对话`;
    }
    
    /**
     * 更新沉浸模式状态文字
     */
    updateImmersiveStatus(status) {
        const statusEl = document.getElementById('immersive-status');
        if (statusEl) statusEl.textContent = status;
    }
    
    /**
     * 显示沉浸模式 TTS 指示器
     */
    showImmersiveTTSIndicator() {
        document.getElementById('immersive-tts-indicator')?.classList.add('active');
    }
    
    /**
     * 隐藏沉浸模式 TTS 指示器
     */
    hideImmersiveTTSIndicator() {
        document.getElementById('immersive-tts-indicator')?.classList.remove('active');
    }
    
    /**
     * 同步沉浸模式语音状态
     */
    syncImmersiveVoiceState() {
        const mainRecordBtn = document.getElementById('record-btn');
        const mainStatusText = document.querySelector('#vad-status-indicator .vad-status-text');
        const immersiveBtn = document.getElementById('immersive-record-btn');
        const immersiveIcon = document.getElementById('immersive-record-icon');
        if (!mainRecordBtn || !immersiveBtn) return;
        
        const applyState = () => {
            immersiveBtn.className = 'immersive-mic-btn';
            
            const states = ['listening', 'speaking', 'processing', 'tts-playing'];
            let activeState = null;
            for (const state of states) {
                if (mainRecordBtn.classList.contains(state)) {
                    activeState = state;
                    immersiveBtn.classList.add(state);
                    break;
                }
            }
            
            if (immersiveIcon) {
                if (activeState === 'processing') {
                    immersiveIcon.className = 'fas fa-spinner fa-spin';
                } else {
                    immersiveIcon.className = 'fas fa-microphone';
                }
            }
            
            if (activeState === 'tts-playing') {
                this.showImmersiveTTSIndicator();
                this.updateImmersiveStatus('AI 正在回复...');
            } else {
                this.hideImmersiveTTSIndicator();
                const text = mainStatusText?.textContent?.trim();
                if (text) this.updateImmersiveStatus(text);
            }
        };
        
        applyState();
        
        if (this._immersiveRecordObserver) this._immersiveRecordObserver.disconnect();
        this._immersiveRecordObserver = new MutationObserver(applyState);
        this._immersiveRecordObserver.observe(mainRecordBtn, { attributes: true, attributeFilter: ['class'] });
        
        if (mainStatusText) {
            if (this._immersiveStatusObserver) this._immersiveStatusObserver.disconnect();
            this._immersiveStatusObserver = new MutationObserver(applyState);
            this._immersiveStatusObserver.observe(mainStatusText, { characterData: true, subtree: true, childList: true });
        }
    }
    
    /**
     * 是否为沉浸模式
     */
    isImmersiveMode() {
        return this.interviewMode === 'immersive';
    }
    
    /**
     * 是否为测试模式
     */
    isTestMode() {
        return this.interviewMode === 'test';
    }
    
    /**
     * 获取当前模式
     */
    getCurrentMode() {
        return this.interviewMode;
    }
}

// 创建单例
export const modeManager = new ModeManager();

if (typeof window !== 'undefined') {
    window.modeManager = modeManager;
}

export default ModeManager;
