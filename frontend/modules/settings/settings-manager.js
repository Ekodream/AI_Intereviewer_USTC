/**
 * 设置管理器 - 统一管理应用设置
 * 
 * 负责加载、保存、同步设置状态
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager } from '../../core/state-manager.js';
import { apiClient } from '../../core/api-client.js';

export class SettingsManager {
    constructor() {
        this.settings = {
            prompt_choice: '正常型导师（默认）',
            system_prompt: '',
            enable_tts: true,
            auto_vad: true,
            enable_rag: true,
            rag_domain: 'cs ai',
            rag_top_k: 6,
            compact_mode: false,
            enable_video: false,
            advisor_mode: 'ai_default',
            advisor_school: '',
            advisor_lab: '',
            advisor_name: ''
        };
        
        this.presets = {};
    }
    
    /**
     * 初始化设置管理器
     */
    async init() {
        await this.loadPresets();
        await this.loadSettings();
        await this.loadRagDomains();
        this.bindEvents();
    }
    
    /**
     * 标准化提示选择
     */
    normalizePromptChoice(choice) {
        const aliases = {
            '温和型': '温和型导师',
            '正常型（默认）': '正常型导师（默认）',
            '正常型导师': '正常型导师（默认）',
            '压力型': '压力型导师',
            '压力型导师': '压力型导师'
        };
        const legacyRole = '面试' + '官';
        const normalizedInput = (choice || '').replaceAll(legacyRole, '导师');
        const normalized = aliases[normalizedInput] || normalizedInput;
        if (normalized && this.presets[normalized]) return normalized;
        return '正常型导师（默认）';
    }
    
    /**
     * 加载预设提示词
     */
    async loadPresets() {
        try {
            const data = await apiClient.get('/api/presets');
            this.presets = data.prompts || {};
            this.settings.prompt_choice = this.normalizePromptChoice(this.settings.prompt_choice);
        } catch (error) {
            console.error('加载预设失败:', error);
        }
    }
    
    /**
     * 加载设置
     */
    async loadSettings() {
        try {
            const data = await apiClient.get('/api/settings');
            this.settings = { ...this.settings, ...data };
            this.settings.prompt_choice = this.normalizePromptChoice(this.settings.prompt_choice);
            this.updateUI();
            this.syncToStateManager();
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }
    
    /**
     * 保存设置
     */
    async saveSettings() {
        try {
            await apiClient.post('/api/settings', this.settings);
            this.syncToStateManager();
        } catch (error) {
            console.error('保存设置失败:', error);
        }
    }
    
    /**
     * 同步设置到状态管理器
     */
    syncToStateManager() {
        stateManager.update({
            settings: {
                ttsEnabled: this.settings.enable_tts,
                vadEnabled: this.settings.auto_vad,
                ragEnabled: this.settings.enable_rag,
                videoEnabled: this.settings.enable_video,
                compactMode: this.settings.compact_mode,
            }
        });
    }
    
    /**
     * 加载 RAG 领域
     */
    async loadRagDomains() {
        const fallbackDomains = ['cs ai', 'math', 'physics', 'ee_info'];
        const aliasMap = { 'cs_ai': 'cs ai', 'cs-ai': 'cs ai' };
        const domainLabelMap = {
            'cs ai': '计算机与AI（CSAI）',
            'cs_ai': '计算机与AI（CSAI）',
            'math': '数学',
            'physics': '物理',
            'ee_info': '电子电气（EE）'
        };
        try {
            const data = await apiClient.get('/api/rag/domains');
            const domains = (data.domains || fallbackDomains)
                .map((d) => aliasMap[d] || d)
                .filter((d, idx, arr) => d && arr.indexOf(d) === idx);
            const ragDomain = document.getElementById('rag-domain');
            
            if (ragDomain && domains.length > 0) {
                ragDomain.innerHTML = domains.map(d =>
                    `<option value="${d}">${domainLabelMap[d] || d}</option>`
                ).join('');
                
                if (domains.includes(this.settings.rag_domain)) {
                    ragDomain.value = this.settings.rag_domain;
                } else {
                    this.settings.rag_domain = domains.includes('cs ai') ? 'cs ai' : domains[0];
                    ragDomain.value = this.settings.rag_domain;
                    await this.saveSettings();
                }
            }
        } catch (error) {
            console.error('加载 RAG 领域失败:', error);
            const ragDomain = document.getElementById('rag-domain');
            if (!ragDomain) return;

            ragDomain.innerHTML = fallbackDomains.map(d =>
                `<option value="${d}">${domainLabelMap[d] || d}</option>`
            ).join('');

            const normalized = aliasMap[this.settings.rag_domain] || this.settings.rag_domain;
            this.settings.rag_domain = fallbackDomains.includes(normalized) ? normalized : 'cs ai';
            ragDomain.value = this.settings.rag_domain;
            await this.saveSettings();
        }
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 提示词选择
        const promptSelect = document.getElementById('prompt-select');
        if (promptSelect) {
            promptSelect.addEventListener('change', () => {
                const choice = promptSelect.value;
                this.settings.prompt_choice = choice;
                if (choice !== '自定义' && this.presets[choice]) {
                    this.settings.system_prompt = this.presets[choice];
                    const pa = document.getElementById('system-prompt');
                    if (pa) pa.value = this.settings.system_prompt;
                }
                this.saveSettings();
            });
        }
        
        // 系统提示词
        const systemPrompt = document.getElementById('system-prompt');
        if (systemPrompt) {
            systemPrompt.addEventListener('change', () => {
                this.settings.system_prompt = systemPrompt.value;
                this.saveSettings();
            });
        }
        
        // TTS 开关
        const enableTts = document.getElementById('enable-tts');
        if (enableTts) {
            enableTts.addEventListener('change', () => {
                this.settings.enable_tts = enableTts.checked;
                this.saveSettings();
            });
        }
        
        // VAD 开关
        this._bindVadToggle();
        
        // RAG 开关
        this._bindRagToggle();
        
        // 精简模式
        const compactMode = document.getElementById('compact-mode');
        if (compactMode) {
            compactMode.addEventListener('change', () => {
                this.settings.compact_mode = compactMode.checked;
                this.saveSettings();
                eventBus.emit(Events.SETTINGS_CHANGED, { compactMode: compactMode.checked });
            });
        }
        
        // 视频录制
        this._bindVideoToggle();
        
        // 导师模式
        this._bindAdvisorMode();
    }
    
    _bindVadToggle() {
        const autoVad = document.getElementById('auto-vad');
        const immersiveAutoVad = document.getElementById('immersive-auto-vad');
        
        const syncAutoVad = (enabled) => {
            this.settings.auto_vad = enabled;
            if (autoVad) autoVad.checked = enabled;
            if (immersiveAutoVad) immersiveAutoVad.checked = enabled;
            if (window.vadDetector?.setAutoMonitoring) {
                window.vadDetector.setAutoMonitoring(enabled);
            }
            this.saveSettings();
        };
        
        if (autoVad) {
            autoVad.addEventListener('change', () => syncAutoVad(autoVad.checked));
        }
        if (immersiveAutoVad) {
            immersiveAutoVad.addEventListener('change', () => syncAutoVad(immersiveAutoVad.checked));
        }
    }
    
    _bindRagToggle() {
        const enableRag = document.getElementById('enable-rag');
        const ragSettings = document.getElementById('rag-settings');
        const ragDomain = document.getElementById('rag-domain');
        const ragTopk = document.getElementById('rag-topk');
        const topkValue = document.getElementById('topk-value');
        
        if (enableRag) {
            enableRag.addEventListener('change', () => {
                this.settings.enable_rag = enableRag.checked;
                if (ragSettings) ragSettings.style.display = enableRag.checked ? 'block' : 'none';
                const immersiveRag = document.getElementById('immersive-enable-rag');
                if (immersiveRag) immersiveRag.checked = enableRag.checked;
                this.saveSettings();
            });
        }
        
        if (ragDomain) {
            ragDomain.addEventListener('change', () => {
                this.settings.rag_domain = ragDomain.value;
                this.saveSettings();
            });
        }
        
        if (ragTopk) {
            ragTopk.addEventListener('input', () => {
                this.settings.rag_top_k = parseInt(ragTopk.value);
                if (topkValue) topkValue.textContent = ragTopk.value;
            });
            ragTopk.addEventListener('change', () => this.saveSettings());
        }
    }
    
    _bindVideoToggle() {
        const enableVideo = document.getElementById('enable-video');
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        
        const syncVideoToggle = (enabled) => {
            this.settings.enable_video = enabled;
            if (enableVideo) enableVideo.checked = enabled;
            if (immersiveEnableVideo) immersiveEnableVideo.checked = enabled;
            eventBus.emit(Events.SETTINGS_CHANGED, { videoEnabled: enabled });
            this.saveSettings();
        };
        
        if (enableVideo) {
            enableVideo.addEventListener('change', () => syncVideoToggle(enableVideo.checked));
        }
        if (immersiveEnableVideo) {
            immersiveEnableVideo.addEventListener('change', () => syncVideoToggle(immersiveEnableVideo.checked));
        }
    }
    
    _bindAdvisorMode() {
        const advisorMode = document.getElementById('advisor-mode');
        if (advisorMode) {
            advisorMode.addEventListener('change', async () => {
                this.settings.advisor_mode = advisorMode.value;
                const customFields = document.getElementById('advisor-custom-fields');
                if (customFields) {
                    customFields.style.display = advisorMode.value === 'custom' ? 'block' : 'none';
                }
                await this.saveSettings();
                eventBus.emit(Events.SETTINGS_CHANGED, { advisorMode: advisorMode.value });
            });
        }
    }
    
    /**
     * 更新 UI
     */
    updateUI() {
        const promptSelect = document.getElementById('prompt-select');
        const systemPrompt = document.getElementById('system-prompt');
        const enableTts = document.getElementById('enable-tts');
        const autoVad = document.getElementById('auto-vad');
        const enableRag = document.getElementById('enable-rag');
        const ragSettings = document.getElementById('rag-settings');
        const ragDomain = document.getElementById('rag-domain');
        const ragTopk = document.getElementById('rag-topk');
        const topkValue = document.getElementById('topk-value');
        const immersiveAutoVad = document.getElementById('immersive-auto-vad');
        
        if (promptSelect) promptSelect.value = this.settings.prompt_choice;
        if (systemPrompt) systemPrompt.value = this.settings.system_prompt || this.presets[this.settings.prompt_choice] || '';
        if (enableTts) enableTts.checked = this.settings.enable_tts;
        if (autoVad) autoVad.checked = this.settings.auto_vad !== false;
        if (enableRag) enableRag.checked = this.settings.enable_rag;
        if (ragSettings) ragSettings.style.display = this.settings.enable_rag ? 'block' : 'none';
        if (ragDomain) ragDomain.value = this.settings.rag_domain;
        if (ragTopk) ragTopk.value = this.settings.rag_top_k;
        if (topkValue) topkValue.textContent = this.settings.rag_top_k;
        
        const immersiveRag = document.getElementById('immersive-enable-rag');
        if (immersiveRag) immersiveRag.checked = this.settings.enable_rag;
        if (immersiveAutoVad) immersiveAutoVad.checked = this.settings.auto_vad !== false;
        
        if (window.vadDetector?.setAutoMonitoring) {
            window.vadDetector.setAutoMonitoring(this.settings.auto_vad !== false);
        }
        
        // 精简模式
        const compactMode = document.getElementById('compact-mode');
        if (compactMode) compactMode.checked = this.settings.compact_mode;
        
        // 视频录制
        const enableVideo = document.getElementById('enable-video');
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        if (enableVideo) enableVideo.checked = this.settings.enable_video;
        if (immersiveEnableVideo) immersiveEnableVideo.checked = this.settings.enable_video;
        
        // 导师模式
        const advisorMode = document.getElementById('advisor-mode');
        const advisorCustomFields = document.getElementById('advisor-custom-fields');
        const advisorSchoolInput = document.getElementById('advisor-school-input');
        const advisorLabInput = document.getElementById('advisor-lab-input');
        const advisorNameInput = document.getElementById('advisor-name-input');
        
        if (advisorMode) advisorMode.value = this.settings.advisor_mode || 'ai_default';
        if (advisorCustomFields) {
            advisorCustomFields.style.display = (this.settings.advisor_mode === 'custom') ? 'block' : 'none';
        }
        if (advisorSchoolInput) advisorSchoolInput.value = this.settings.advisor_school || '';
        if (advisorLabInput) advisorLabInput.value = this.settings.advisor_lab || '';
        if (advisorNameInput) advisorNameInput.value = this.settings.advisor_name || '';
    }
    
    /**
     * 获取当前设置
     */
    getSettings() {
        return { ...this.settings };
    }
    
    /**
     * 锁定设置（测试模式）
     */
    lockSettings() {
        const controls = [
            'prompt-select', 'system-prompt', 'enable-tts', 'auto-vad',
            'enable-rag', 'rag-domain', 'rag-topk', 'compact-mode',
            'enable-video', 'advisor-mode'
        ];
        
        controls.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });
    }
    
    /**
     * 解锁设置
     */
    unlockSettings() {
        const controls = [
            'prompt-select', 'system-prompt', 'enable-tts', 'auto-vad',
            'enable-rag', 'rag-domain', 'rag-topk', 'compact-mode',
            'enable-video', 'advisor-mode'
        ];
        
        controls.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = false;
        });
    }
}

// 创建单例
export const settingsManager = new SettingsManager();

// 挂载到 window
if (typeof window !== 'undefined') {
    window.settingsManager = settingsManager;
}

export default SettingsManager;
