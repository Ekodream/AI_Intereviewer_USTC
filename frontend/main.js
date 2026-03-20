/**
 * AI Lab-InterReviewer — 模块化应用入口
 * 
 * 协调各功能模块的初始化和运行
 */

// 核心模块
import { eventBus, Events } from './core/event-bus.js';
import { stateManager } from './core/state-manager.js';
import { apiClient } from './core/api-client.js';
import { config } from './core/config.js';

// 设置模块
import { settingsManager } from './modules/settings/settings-manager.js';
import { sidebarManager } from './modules/settings/sidebar-manager.js';
import { drawerManager } from './modules/settings/drawer-manager.js';

// 简历模块
import { resumeManager } from './modules/resume/resume-manager.js';

// 导师模块
import { advisorManager } from './modules/advisor/advisor-manager.js';

// 面试模块
import { modeManager } from './modules/interview/mode-manager.js';
import { phaseTimeline } from './modules/interview/phase-timeline.js';
import { reportManager } from './modules/interview/report-manager.js';

/**
 * 应用主类
 */
class App {
    constructor() {
        this.initialized = false;
        
        // 加载遮罩
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingText = document.getElementById('loading-text');
        
        // 监听加载事件
        eventBus.on(Events.LOADING_SHOW, (message) => this.showLoading(message));
        eventBus.on(Events.LOADING_HIDE, () => this.hideLoading());
    }
    
    /**
     * 初始化应用
     */
    async init() {
        console.log('🚀 初始化 Cybernetic Command (模块化版本)...');
        
        try {
            // 初始化 API 客户端
            apiClient.init();
            
            // 初始化面试模式管理器（显示模式选择器）
            modeManager.init();
            
            // 初始化侧边栏和抽屉
            sidebarManager.init();
            drawerManager.init();
            
            // 初始化设置管理器
            await settingsManager.init();
            
            // 初始化简历管理器
            await resumeManager.init();
            
            // 初始化导师管理器
            await advisorManager.init();
            
            // 初始化阶段时间线
            phaseTimeline.init();
            
            // 初始化报告管理器
            reportManager.init();
            
            // 加载 RAG 历史
            await drawerManager.loadRagHistory();
            
            // 同步沉浸模式状态
            modeManager.syncImmersiveVoiceState();
            modeManager.updateImmersiveMsgCount();
            
            this.initialized = true;
            eventBus.emit(Events.APP_INITIALIZED);
            console.log('✅ 初始化完成');
            
        } catch (error) {
            console.error('❌ 初始化失败:', error);
            eventBus.emit(Events.APP_ERROR, error);
        }
    }
    
    /**
     * 显示加载遮罩
     */
    showLoading(text = '正在处理...') {
        if (this.loadingOverlay) this.loadingOverlay.classList.add('show');
        if (this.loadingText) this.loadingText.textContent = text;
    }
    
    /**
     * 隐藏加载遮罩
     */
    hideLoading() {
        if (this.loadingOverlay) this.loadingOverlay.classList.remove('show');
    }
    
    /**
     * 获取设置（向后兼容）
     */
    getSettings() {
        return settingsManager.getSettings();
    }
    
    /**
     * 更新阶段时间线（向后兼容）
     */
    updatePhaseTimeline(phase) {
        phaseTimeline.update(phase);
    }
    
    /**
     * 重置阶段时间线（向后兼容）
     */
    resetPhaseTimeline() {
        phaseTimeline.reset();
    }
    
    /**
     * 是否为沉浸模式（向后兼容）
     */
    isImmersiveMode() {
        return modeManager.isImmersiveMode();
    }
    
    /**
     * 更新沉浸模式对话数（向后兼容）
     */
    updateImmersiveMsgCount() {
        modeManager.updateImmersiveMsgCount();
    }
    
    /**
     * 关闭所有抽屉（向后兼容）
     */
    closeAllDrawers() {
        drawerManager.closeAll();
    }
    
    /**
     * 转义 HTML（工具函数）
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
    window.app.init();
});

// 导出
export default App;
