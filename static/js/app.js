/**
 * AI Lab-InterReviewer — Cybernetic Command
 * 主应用逻辑：初始化、设置管理、抽屉面板、报告生成
 */

class App {
    constructor() {
        this.settings = {
            prompt_choice: '正常型导师（默认）',
            system_prompt: '',
            enable_tts: true,
            auto_vad: true,
            enable_rag: true,
            rag_domain: 'cs ai',
            rag_top_k: 6,
            compact_mode: false,  // 精简对话模式
            enable_video: false,  // 视频录制
            advisor_mode: 'ai_default',
            advisor_school: '',
            advisor_lab: '',
            advisor_name: ''
        };

        this.presets = {};
        this.reportContent = '';
        this.resumeUploaded = false;
        this.resumeFileName = '';
        this.advisorSearched = false;
        this.advisorSchool = '';
        this.advisorLab = '';
        this.advisorName = '';
        this.advisorInfo = null;
        this.advisorSearchInProgress = false;
        this.advisorSearchProgress = 0;
        this.advisorSearchProgressText = '';
        this.advisorSearchError = '';
        this.advisorSearchPayload = null;
        this.interviewMode = 'standard';

        this.loadingOverlay = document.getElementById('loading-overlay');
        this.loadingText = document.getElementById('loading-text');

        this.init();
    }

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

    async init() {
        console.log('🚀 初始化 Cybernetic Command...');

        // Always start from mode selection screen.
        // User can pick standard/immersive each time after entering.
        this.showModeSelector();
        this.selectMode('standard', false);

        this.bindModeSelectorEvents();

        this.bindSidebarEvents();
        this.bindLandscapeQuickbarEvents(); // 横向模式快捷栏
        this.bindSettingsEvents();
        this.bindDrawerEvents();
        this.bindReportEvents();
        this.bindResumeEvents();
        this.bindAdvisorEvents();
        this.bindImmersiveEvents();
        
        // 设置全局音频解锁机制（移动端关键）
        this.setupGlobalAudioUnlock();

        await this.loadPresets();
        await this.loadSettings();
        await this.loadRagDomains();
        await this.loadRagHistory();
        await this.loadResumeStatus();
        await this.loadAdvisorStatus();

        this.syncImmersiveVoiceState();
        this.updateImmersiveMsgCount();

        console.log('✅ 初始化完成');
    }
    
    /**
     * 设置全局音频解锁机制
     * 移动端需要用户交互才能播放音频，在首次点击时解锁
     */
    setupGlobalAudioUnlock() {
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        if (!isMobile) {
            console.log('💻 桌面端无需全局音频解锁');
            return;
        }
        
        console.log('📱 设置移动端全局音频解锁机制');
        
        let audioUnlocked = false;
        
        const unlockHandler = async (event) => {
            if (audioUnlocked) return;
            
            console.log('🔐 检测到用户交互，尝试解锁音频...');
            
            // 解锁 TTS 音频
            if (window.ttsPlayer) {
                const success = await window.ttsPlayer.unlockAudio();
                if (success) {
                    audioUnlocked = true;
                    console.log('✅ 全局音频解锁成功');
                    
                    // 解锁成功后移除监听器
                    document.removeEventListener('touchstart', unlockHandler, { capture: true });
                    document.removeEventListener('touchend', unlockHandler, { capture: true });
                    document.removeEventListener('click', unlockHandler, { capture: true });
                }
            }
        };
        
        // 添加全局交互监听器
        document.addEventListener('touchstart', unlockHandler, { capture: true, passive: true });
        document.addEventListener('touchend', unlockHandler, { capture: true, passive: true });
        document.addEventListener('click', unlockHandler, { capture: true, passive: true });
    }

    /* ==================== Mode Management ==================== */
    showModeSelector() {
        const selector = document.getElementById('mode-selector');
        if (selector) selector.classList.remove('hidden');
    }

    hideModeSelector() {
        const selector = document.getElementById('mode-selector');
        if (selector) selector.classList.add('hidden');
    }

    async joinTestRoom(roomId) {
        this.showLoading('正在加入房间...');

        try {
            const response = await fetch(`/api/student/join/${roomId}`, {
                method: 'POST',
                headers: window.getApiHeaders()
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '加入房间失败');
            }

            const data = await response.json();
            const room = data.room;

            // 应用房间配置
            this.settings = room.config;
            await this.saveSettings();

            // 标记为测试模式
            this.interviewMode = 'test';
            this.testRoomId = roomId;
            this.testRoomInfo = room;
            localStorage.setItem('testRoomId', roomId);
            localStorage.setItem('interviewMode', 'test');

            // 锁定设置
            this.lockSettings();

            // 隐藏模式选择器
            this.hideModeSelector();

            // 显示房间信息
            this.showRoomInfo(room);

            this.hideLoading();
            alert(`已成功加入房间 ${roomId}\n导师：${room.teacher_name}\n配置已锁定，开始面试吧！`);

        } catch (error) {
            this.hideLoading();
            alert('加入房间失败：' + error.message);
        }
    }

    lockSettings() {
        // 禁用所有设置控件
        const controls = [
            'prompt-select', 'system-prompt', 'enable-tts', 'auto-vad',
            'enable-rag', 'rag-domain', 'rag-topk', 'compact-mode',
            'enable-video', 'advisor-mode'
        ];

        controls.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });

        // 在控制面板顶部显示锁定提示
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            const lockBanner = document.createElement('div');
            lockBanner.style.cssText = 'background: #f56565; color: #fff; padding: 12px; text-align: center; font-weight: 600; border-radius: 8px; margin-bottom: 16px;';
            lockBanner.innerHTML = '<i class="fas fa-lock"></i> 测试模式 - 配置已锁定';
            sidebar.insertBefore(lockBanner, sidebar.firstChild);
        }
    }

    showRoomInfo(room) {
        // 在顶部显示房间信息
        const commandBar = document.querySelector('.command-bar-center');
        if (commandBar) {
            const roomInfo = document.createElement('div');
            roomInfo.style.cssText = 'background: rgba(99, 179, 237, 0.2); padding: 8px 16px; border-radius: 8px; color: #63b3ed; font-size: 14px;';
            roomInfo.innerHTML = `<i class="fas fa-door-open"></i> 房间 ${room.room_id} | 导师：${room.teacher_name}`;
            commandBar.appendChild(roomInfo);
        }
    }

    async submitTestResult() {
        if (this.interviewMode !== 'test') return;

        try {
            const response = await fetch('/api/student/submit', {
                method: 'POST',
                headers: window.getApiHeaders()
            });

            if (response.ok) {
                console.log('✅ 测试结果已自动提交');
            }
        } catch (error) {
            console.error('提交测试结果失败:', error);
        }
    }

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

    switchToImmersiveMode() {
        document.body.classList.add('immersive-mode');

        const immersiveStage = document.getElementById('immersive-stage');
        if (immersiveStage) immersiveStage.classList.add('active');

        const settingsToggle = document.getElementById('immersive-settings-toggle');
        if (settingsToggle) settingsToggle.classList.add('visible');

        // Immersive mode enforces TTS on to keep pure voice flow.
        this.settings.enable_tts = true;
        const enableTts = document.getElementById('enable-tts');
        if (enableTts) {
            enableTts.checked = true;
            enableTts.disabled = true;
        }

        const immersiveRag = document.getElementById('immersive-enable-rag');
        if (immersiveRag) immersiveRag.checked = this.settings.enable_rag;

        // 同步视频开关状态
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        if (immersiveEnableVideo) immersiveEnableVideo.checked = this.settings.enable_video;

        this.updateImmersiveResumeBtn();
        this.updateImmersiveMsgCount();
        this.updateImmersivePhase(window.chat?.currentPhase || 0);
        this.syncImmersiveVoiceState();
        this.saveSettings();
    }

    isImmersiveMode() {
        return this.interviewMode === 'immersive';
    }

    /* ==================== Immersive Mode ==================== */
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

        const immersiveRag = document.getElementById('immersive-enable-rag');
        if (immersiveRag) {
            immersiveRag.addEventListener('change', () => {
                this.settings.enable_rag = immersiveRag.checked;
                const enableRag = document.getElementById('enable-rag');
                if (enableRag) enableRag.checked = immersiveRag.checked;
                const ragSettings = document.getElementById('rag-settings');
                if (ragSettings) ragSettings.style.display = immersiveRag.checked ? 'block' : 'none';
                this.saveSettings();
            });
        }

        const immersiveResumeBtn = document.getElementById('immersive-resume-btn');
        if (immersiveResumeBtn) {
            immersiveResumeBtn.addEventListener('click', () => {
                document.getElementById('resume-input')?.click();
                this.closeImmersiveSettings();
            });
        }

        const immersiveAdvisorBtn = document.getElementById('immersive-advisor-btn');
        if (immersiveAdvisorBtn) {
            immersiveAdvisorBtn.addEventListener('click', () => {
                this.showAdvisorModal();
                this.closeImmersiveSettings();
            });
        }

        // 沉浸模式导师文档按钮
        const immersiveAdvisorDocsBtn = document.getElementById('immersive-advisor-docs-btn');
        if (immersiveAdvisorDocsBtn) {
            immersiveAdvisorDocsBtn.addEventListener('click', () => {
                this.showAdvisorDocsModal();
                this.closeImmersiveSettings();
            });
        }

        const immersiveIdeBtn = document.getElementById('immersive-ide-btn');
        if (immersiveIdeBtn) {
            immersiveIdeBtn.addEventListener('click', () => {
                window.chat?.showIDEPanel();
                this.closeImmersiveSettings();
            });
        }

        const immersiveReportBtn = document.getElementById('immersive-report-btn');
        if (immersiveReportBtn) {
            immersiveReportBtn.addEventListener('click', () => {
                this.closeAllDrawers();
                document.getElementById('report-drawer')?.classList.add('show');
                document.getElementById('toggle-report-btn')?.classList.add('active');
                this.closeImmersiveSettings();
            });
        }

        const immersiveNewChatBtn = document.getElementById('immersive-new-chat-btn');
        if (immersiveNewChatBtn) {
            immersiveNewChatBtn.addEventListener('click', () => {
                if (!confirm('确定要开始新对话吗？当前对话历史将被清空。')) return;
                window.chat?.clearHistory();
                this.reportContent = '';
                const reportContent = document.getElementById('report-content');
                if (reportContent) reportContent.textContent = '';
                document.getElementById('report-download')?.style.setProperty('display', 'none');
                this.resetPhaseTimeline();
                this.updateImmersivePhase(0);
                this.updateImmersiveMsgCount();
                this.updateImmersiveStatus('点击麦克风开始面试');
                this.closeImmersiveSettings();
            });
        }

        const immersiveSwitchModeBtn = document.getElementById('immersive-switch-mode-btn');
        if (immersiveSwitchModeBtn) {
            immersiveSwitchModeBtn.addEventListener('click', () => {
                this.selectMode('standard', true);
                this.closeImmersiveSettings();
            });
        }
    }

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

    updateImmersiveResumeBtn() {
        const btn = document.getElementById('immersive-resume-btn');
        if (!btn) return;

        if (this.resumeUploaded) {
            btn.innerHTML = '<i class="fas fa-check"></i> 已上传';
            btn.classList.add('cyber-btn-success');
        } else {
            btn.innerHTML = '<i class="fas fa-upload"></i> 上传';
            btn.classList.remove('cyber-btn-success');
        }
    }

    updateImmersivePhase(phase) {
        const phaseEl = document.getElementById('immersive-phase');
        if (!phaseEl) return;

        const phaseNames = ['开始', '自我介绍', '经历深挖', '基础知识', '代码', '科研动机', '科研潜力', '综合追问', '学生反问', '结束'];
        phaseEl.textContent = phaseNames[phase] || '面试中';
    }

    updateImmersiveMsgCount() {
        const countEl = document.getElementById('immersive-msg-count');
        if (!countEl || !window.chat) return;
        const rounds = Math.ceil(window.chat.history.length / 2);
        countEl.textContent = `${rounds} 轮对话`;
    }

    updateImmersiveStatus(status) {
        const statusEl = document.getElementById('immersive-status');
        if (statusEl) statusEl.textContent = status;
    }

    showImmersiveTTSIndicator() {
        document.getElementById('immersive-tts-indicator')?.classList.add('active');
    }

    hideImmersiveTTSIndicator() {
        document.getElementById('immersive-tts-indicator')?.classList.remove('active');
    }

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

    /* ==================== Sidebar ==================== */
    bindSidebarEvents() {
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                if (window.innerWidth <= 900) {
                    sidebar.classList.toggle('show');
                } else {
                    sidebar.classList.toggle('hidden');
                }
                sidebarToggle.classList.toggle('active');
            });

            // 移动端点击主区域关闭侧边栏
            const mainStage = document.querySelector('.main-stage');
            if (mainStage) {
                mainStage.addEventListener('click', () => {
                    if (window.innerWidth <= 900) {
                        sidebar.classList.remove('show');
                        sidebarToggle.classList.remove('active');
                    }
                });
            }
        }

        // New chat
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                if (confirm('确定要开始新对话吗？当前对话历史将被清空。')) {
                    window.chat?.clearHistory();
                    this.reportContent = '';
                    const rc = document.getElementById('report-content');
                    if (rc) rc.textContent = '';
                    const rd = document.getElementById('report-download');
                    if (rd) rd.style.display = 'none';
                    // Reset phase timeline
                    this.resetPhaseTimeline();
                }
            });
        }

        const switchToImmersiveBtn = document.getElementById('switch-to-immersive-btn');
        if (switchToImmersiveBtn) {
            switchToImmersiveBtn.addEventListener('click', () => {
                this.selectMode('immersive', true);
                if (window.innerWidth <= 900 && sidebar) {
                    sidebar.classList.remove('show');
                    sidebarToggle?.classList.remove('active');
                }
            });
        }

        // Collapsible prompt
        const promptToggle = document.getElementById('prompt-toggle');
        const promptContent = document.getElementById('prompt-content');
        if (promptToggle && promptContent) {
            promptToggle.addEventListener('click', () => {
                promptToggle.classList.toggle('active');
                promptContent.classList.toggle('show');
            });
        }
    }

    /* ==================== Drawer Panels ==================== */
    bindDrawerEvents() {
        // RAG drawer
        const ragBtn = document.getElementById('toggle-rag-btn');
        const ragDrawer = document.getElementById('rag-drawer');
        const ragClose = document.getElementById('rag-close-btn');

        if (ragBtn && ragDrawer) {
            ragBtn.addEventListener('click', () => {
                const isOpen = ragDrawer.classList.contains('show');
                this.closeAllDrawers();
                if (!isOpen) {
                    ragDrawer.classList.add('show');
                    ragBtn.classList.add('active');
                    this.loadRagHistory();
                }
            });
        }
        if (ragClose) {
            ragClose.addEventListener('click', () => this.closeAllDrawers());
        }

        // Report drawer
        const reportBtn = document.getElementById('toggle-report-btn');
        const reportDrawer = document.getElementById('report-drawer');
        const reportClose = document.getElementById('report-close-btn');

        if (reportBtn && reportDrawer) {
            reportBtn.addEventListener('click', () => {
                const isOpen = reportDrawer.classList.contains('show');
                this.closeAllDrawers();
                if (!isOpen) {
                    reportDrawer.classList.add('show');
                    reportBtn.classList.add('active');
                }
            });
        }
        if (reportClose) {
            reportClose.addEventListener('click', () => this.closeAllDrawers());
        }
    }

    closeAllDrawers() {
        document.querySelectorAll('.side-drawer').forEach(d => d.classList.remove('show'));
        document.getElementById('toggle-rag-btn')?.classList.remove('active');
        document.getElementById('toggle-report-btn')?.classList.remove('active');
    }

    /* ==================== Landscape Quickbar ==================== */
    bindLandscapeQuickbarEvents() {
        const quickbar = document.getElementById('landscape-quickbar');
        const quickbarToggle = document.getElementById('quickbar-toggle');
        const quickbarMenu = document.getElementById('quickbar-menu');
        
        if (!quickbar || !quickbarToggle) return;
        
        // 快捷栏展开/收起切换
        quickbarToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            quickbar.classList.toggle('expanded');
        });
        
        // 点击外部关闭快捷栏
        document.addEventListener('click', (e) => {
            if (!quickbar.contains(e.target)) {
                quickbar.classList.remove('expanded');
            }
        });
        
        // 快捷栏按钮事件
        const qbSidebarToggle = document.getElementById('qb-sidebar-toggle');
        const qbNewChat = document.getElementById('qb-new-chat');
        const qbReport = document.getElementById('qb-report');
        const qbIde = document.getElementById('qb-ide');
        
        // 控制面板按钮
        if (qbSidebarToggle) {
            qbSidebarToggle.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    sidebar.classList.toggle('show');
                }
                quickbar.classList.remove('expanded');
            });
        }
        
        // 新对话按钮
        if (qbNewChat) {
            qbNewChat.addEventListener('click', () => {
                document.getElementById('new-chat-btn')?.click();
                quickbar.classList.remove('expanded');
            });
        }
        
        // 报告按钮
        if (qbReport) {
            qbReport.addEventListener('click', () => {
                document.getElementById('toggle-report-btn')?.click();
                quickbar.classList.remove('expanded');
            });
        }
        
        // IDE按钮
        if (qbIde) {
            qbIde.addEventListener('click', () => {
                document.getElementById('toggle-ide-btn')?.click();
                quickbar.classList.remove('expanded');
            });
        }
        
        // 监听方向变化，在切换到竖屏时收起快捷栏
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                quickbar.classList.remove('expanded');
            }, 100);
        });
        
        // 触摸优化：防止快速点击时触发双击缩放
        [quickbarToggle, qbSidebarToggle, qbNewChat, qbReport, qbIde].forEach(btn => {
            if (btn) {
                btn.style.touchAction = 'manipulation';
            }
        });
    }

    /* ==================== Settings ==================== */
    bindSettingsEvents() {
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

        const systemPrompt = document.getElementById('system-prompt');
        if (systemPrompt) {
            systemPrompt.addEventListener('change', () => {
                this.settings.system_prompt = systemPrompt.value;
                this.saveSettings();
            });
        }

        const enableTts = document.getElementById('enable-tts');
        if (enableTts) {
            enableTts.addEventListener('change', () => {
                this.settings.enable_tts = enableTts.checked;
                this.saveSettings();
            });
        }

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
            autoVad.addEventListener('change', () => {
                syncAutoVad(autoVad.checked);
            });
        }
        if (immersiveAutoVad) {
            immersiveAutoVad.addEventListener('change', () => {
                syncAutoVad(immersiveAutoVad.checked);
            });
        }

        const enableRag = document.getElementById('enable-rag');
        const ragSettings = document.getElementById('rag-settings');
        if (enableRag) {
            enableRag.addEventListener('change', () => {
                this.settings.enable_rag = enableRag.checked;
                if (ragSettings) ragSettings.style.display = enableRag.checked ? 'block' : 'none';
                const immersiveRag = document.getElementById('immersive-enable-rag');
                if (immersiveRag) immersiveRag.checked = enableRag.checked;
                this.saveSettings();
            });
        }

        const ragDomain = document.getElementById('rag-domain');
        if (ragDomain) {
            ragDomain.addEventListener('change', () => {
                this.settings.rag_domain = ragDomain.value;
                this.saveSettings();
            });
        }

        const ragTopk = document.getElementById('rag-topk');
        const topkValue = document.getElementById('topk-value');
        if (ragTopk) {
            ragTopk.addEventListener('input', () => {
                this.settings.rag_top_k = parseInt(ragTopk.value);
                if (topkValue) topkValue.textContent = ragTopk.value;
            });
            ragTopk.addEventListener('change', () => this.saveSettings());
        }

        // 精简模式开关
        const compactMode = document.getElementById('compact-mode');
        if (compactMode) {
            compactMode.addEventListener('change', () => {
                this.settings.compact_mode = compactMode.checked;
                this.saveSettings();
                // 通知聊天模块切换模式
                if (window.chat) {
                    window.chat.setCompactMode(compactMode.checked);
                }
            });
        }

        // 视频录制开关
        const enableVideo = document.getElementById('enable-video');
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        const syncVideoToggle = (enabled) => {
            this.settings.enable_video = enabled;
            if (enableVideo) enableVideo.checked = enabled;
            if (immersiveEnableVideo) immersiveEnableVideo.checked = enabled;
            this.toggleVideoPreview(enabled);
            this.saveSettings();
        };
        if (enableVideo) {
            enableVideo.addEventListener('change', () => {
                syncVideoToggle(enableVideo.checked);
            });
        }
        if (immersiveEnableVideo) {
            immersiveEnableVideo.addEventListener('change', () => {
                syncVideoToggle(immersiveEnableVideo.checked);
            });
        }

        const advisorMode = document.getElementById('advisor-mode');
        if (advisorMode) {
            advisorMode.addEventListener('change', async () => {
                this.settings.advisor_mode = advisorMode.value;
                const customFields = document.getElementById('advisor-custom-fields');
                if (customFields) {
                    customFields.style.display = advisorMode.value === 'custom' ? 'block' : 'none';
                }
                if (advisorMode.value === 'ai_default') {
                    // 切换到默认模式时，清除导师信息并切换模式
                    await this.deleteAdvisor(false, true);  // 不显示确认，切换到默认模式
                }
                this.saveSettings();
                this.updateAdvisorUI();
            });
        }
    }

    /* ==================== Report ==================== */
    bindReportEvents() {
        document.getElementById('download-json')?.addEventListener('click', () => {
            window.location.href = '/api/report/download/json';
        });
        document.getElementById('download-txt')?.addEventListener('click', () => {
            window.location.href = '/api/report/download/txt';
        });
        document.getElementById('generate-report-btn')?.addEventListener('click', () => {
            this.generateReport();
        });
        document.getElementById('download-report-md')?.addEventListener('click', () => {
            this.downloadReportMarkdown();
        });
    }

    /* ==================== Phase Timeline ==================== */
    updatePhaseTimeline(phase) {
        const nodes = document.querySelectorAll('.phase-node');
        const lines = document.querySelectorAll('.phase-line');

        // Ten-step interview flow: 0..9
        const phaseMap = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

        nodes.forEach((node, idx) => {
            const nodePhase = phaseMap[idx];
            node.classList.remove('completed', 'active');

            if (nodePhase < phase) {
                node.classList.add('completed');
            } else if (nodePhase === phase || (nodePhase === phaseMap[idx] && phase >= nodePhase && phase < (phaseMap[idx + 1] || 999))) {
                // Mark active for current phase or phases in between
            }
        });

        // More precise: find the active node
        let activeIdx = 0;
        for (let i = 0; i < phaseMap.length; i++) {
            if (phase >= phaseMap[i]) {
                activeIdx = i;
            }
        }

        nodes.forEach((node, idx) => {
            node.classList.remove('completed', 'active');
            if (idx < activeIdx) {
                node.classList.add('completed');
            } else if (idx === activeIdx) {
                node.classList.add('active');
            }
        });

        // Highlight lines
        lines.forEach((line, idx) => {
            if (idx < activeIdx) {
                line.style.background = 'var(--neon-blue)';
                line.style.boxShadow = '0 0 6px rgba(0, 212, 255, 0.3)';
            } else {
                line.style.background = 'var(--text-muted)';
                line.style.boxShadow = 'none';
            }
        });

        this.updateImmersivePhase(activeIdx);
    }

    resetPhaseTimeline() {
        const nodes = document.querySelectorAll('.phase-node');
        const lines = document.querySelectorAll('.phase-line');
        nodes.forEach((node, idx) => {
            node.classList.remove('completed', 'active');
            if (idx === 0) node.classList.add('active');
        });
        lines.forEach(line => {
            line.style.background = 'var(--text-muted)';
            line.style.boxShadow = 'none';
        });
    }

    /* ==================== Data Loading ==================== */
    async loadPresets() {
        try {
            const response = await fetch('/api/presets', { headers: window.getApiHeaders() });
            const data = await response.json();
            this.presets = data.prompts || {};
            this.settings.prompt_choice = this.normalizePromptChoice(this.settings.prompt_choice);
        } catch (error) {
            console.error('加载预设失败:', error);
        }
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/settings', { headers: window.getApiHeaders() });
            const data = await response.json();
            this.settings = { ...this.settings, ...data };
            this.settings.prompt_choice = this.normalizePromptChoice(this.settings.prompt_choice);
            this.updateSettingsUI();
        } catch (error) {
            console.error('加载设置失败:', error);
        }
    }

    async saveSettings() {
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: window.getApiHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify(this.settings)
            });
        } catch (error) {
            console.error('保存设置失败:', error);
        }
    }

    updateSettingsUI() {
        const promptSelect = document.getElementById('prompt-select');
        const systemPrompt = document.getElementById('system-prompt');
        const enableTts = document.getElementById('enable-tts');
        const enableRag = document.getElementById('enable-rag');
        const ragSettings = document.getElementById('rag-settings');
        const ragDomain = document.getElementById('rag-domain');
        const ragTopk = document.getElementById('rag-topk');
        const topkValue = document.getElementById('topk-value');
        const autoVad = document.getElementById('auto-vad');
        const immersiveAutoVad = document.getElementById('immersive-auto-vad');

        if (promptSelect) promptSelect.value = this.settings.prompt_choice;
        if (systemPrompt) systemPrompt.value = this.settings.system_prompt || this.presets[this.settings.prompt_choice] || '';
        if (enableTts) enableTts.checked = this.settings.enable_tts;
        if (enableRag) enableRag.checked = this.settings.enable_rag;
        if (autoVad) autoVad.checked = this.settings.auto_vad !== false;
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
        // 同步到聊天模块
        if (window.chat) {
            window.chat.setCompactMode(this.settings.compact_mode);
        }

        // 视频录制
        const enableVideo = document.getElementById('enable-video');
        const immersiveEnableVideo = document.getElementById('immersive-enable-video');
        if (enableVideo) enableVideo.checked = this.settings.enable_video;
        if (immersiveEnableVideo) immersiveEnableVideo.checked = this.settings.enable_video;
        // 同步视频预览状态
        this.toggleVideoPreview(this.settings.enable_video);

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
            const response = await fetch('/api/rag/domains', { headers: window.getApiHeaders() });
            const data = await response.json();
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
                    this.saveSettings();
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
            this.saveSettings();
        }
    }

    async loadRagHistory() {
        try {
            const response = await fetch('/api/rag/history', { headers: window.getApiHeaders() });
            const data = await response.json();
            const history = data.rag_history || [];
            const container = document.getElementById('rag-history');
            if (!container) return;

            if (history.length === 0) {
                container.innerHTML = '<div class="empty-state-mini"><i class="fas fa-search"></i><p>暂无检索记录</p></div>';
                return;
            }

            let html = `<p style="margin-bottom:12px;font-size:12px;color:var(--text-secondary);">共 <strong>${history.length}</strong> 条检索记录</p>`;
            const domainLabelMap = {
                'cs ai': '计算机与AI（CSAI）',
                'cs_ai': '计算机与AI（CSAI）',
                'math': '数学',
                'physics': '物理',
                'ee_info': '电子电气（EE）'
            };
            for (let i = history.length - 1; i >= 0; i--) {
                const item = history[i];
                const snippets = item.retrieved.split('\n').filter(s => s.trim());
                const preview = snippets.slice(0, 3).map((s, idx) =>
                    `<div class="rag-snippet"><b>片段 ${idx + 1}:</b> ${this.escapeHtml(s.substring(0, 200))}${s.length > 200 ? '...' : ''}</div>`
                ).join('');
                const domainLabel = domainLabelMap[item.domain] || item.domain;
                html += `
                    <div class="rag-card">
                        <div class="rag-query">Q: ${this.escapeHtml(item.query)}</div>
                        <div class="rag-content">${preview}</div>
                        <div class="rag-meta">领域: ${domainLabel} · Top-${item.top_k} · 共 ${snippets.length} 条片段</div>
                    </div>`;
            }
            container.innerHTML = html;
        } catch (error) {
            console.error('加载 RAG 历史失败:', error);
        }
    }

    /* ==================== Report Generation ==================== */
    async generateReport() {
        const reportContent = document.getElementById('report-content');
        const reportDownload = document.getElementById('report-download');
        const generateBtn = document.getElementById('generate-report-btn');
        if (!reportContent) return;

        if (generateBtn) generateBtn.disabled = true;
        reportContent.textContent = '正在生成报告，请稍候...';
        this.reportContent = '';

        try {
            const response = await fetch('/api/report/stream', { method: 'POST', headers: window.getApiHeaders() });
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'text') {
                                this.reportContent = data.content;
                                if (window.mdRenderer) {
                                    window.mdRenderer.renderTo(reportContent, this.reportContent);
                                } else {
                                    reportContent.textContent = this.reportContent;
                                }
                            } else if (data.type === 'done') {
                                if (reportDownload) reportDownload.style.display = 'block';
                                // 测试模式下自动提交结果
                                if (this.interviewMode === 'test') {
                                    await this.submitTestResult();
                                }
                            } else if (data.type === 'error') {
                                reportContent.textContent = `生成失败: ${data.message}`;
                            }
                        } catch (e) {
                            console.error('解析报告数据失败:', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('生成报告失败:', error);
            reportContent.textContent = `生成失败: ${error.message}`;
        } finally {
            if (generateBtn) generateBtn.disabled = false;
        }
    }

    downloadReportMarkdown() {
        if (!this.reportContent) {
            alert('没有报告内容可下载');
            return;
        }
        const blob = new Blob([this.reportContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `interview_report_${new Date().toISOString().slice(0, 10)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /* ==================== Resume ==================== */
    bindResumeEvents() {
        const resumeInput = document.getElementById('resume-input');
        const resumeUploadBtn = document.getElementById('resume-upload-btn');
        const resumeDeleteBtn = document.getElementById('resume-delete-btn');

        if (resumeUploadBtn && resumeInput) {
            resumeUploadBtn.addEventListener('click', () => resumeInput.click());
        }
        if (resumeInput) {
            resumeInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) await this.uploadResume(file);
                resumeInput.value = '';
            });
        }
        if (resumeDeleteBtn) {
            resumeDeleteBtn.addEventListener('click', () => this.deleteResume());
        }
    }

    async loadResumeStatus() {
        try {
            const response = await fetch('/api/resume/status', { headers: window.getApiHeaders() });
            const data = await response.json();
            this.resumeUploaded = data.uploaded;
            this.resumeFileName = data.file_name || '';
            this.updateResumeUI();
        } catch (error) {
            console.error('加载简历状态失败:', error);
        }
    }

    async uploadResume(file) {
        const uploadArea = document.getElementById('resume-upload-area');
        const progressArea = document.getElementById('resume-progress');
        const progressFill = document.getElementById('resume-progress-fill');
        const progressText = document.getElementById('resume-progress-text');

        if (uploadArea) uploadArea.style.display = 'none';
        if (progressArea) progressArea.style.display = 'block';
        if (progressFill) progressFill.style.width = '20%';
        if (progressText) progressText.textContent = '正在上传文件...';

        try {
            const formData = new FormData();
            formData.append('file', file);
            if (progressFill) progressFill.style.width = '40%';
            if (progressText) progressText.textContent = 'AI 正在分析简历（约 10-15 秒）...';

            const response = await fetch('/api/resume/upload', {
                method: 'POST',
                headers: window.getApiHeaders(),
                body: formData
            });
            const data = await response.json();

            if (data.status === 'ok') {
                if (progressFill) progressFill.style.width = '100%';
                if (progressText) progressText.textContent = '✅ 简历解析完成！';
                this.resumeUploaded = true;
                this.resumeFileName = data.file_name;
                setTimeout(() => this.updateResumeUI(), 1000);
            } else {
                throw new Error(data.message || '上传失败');
            }
        } catch (error) {
            console.error('简历上传失败:', error);
            if (progressText) progressText.textContent = `❌ 上传失败: ${error.message}`;
            setTimeout(() => this.updateResumeUI(), 3000);
        }
    }

    async deleteResume() {
        if (!confirm('确定要删除已上传的简历吗？')) return;
        try {
            const response = await fetch('/api/resume', { method: 'DELETE', headers: window.getApiHeaders() });
            const data = await response.json();
            if (data.status === 'ok') {
                this.resumeUploaded = false;
                this.resumeFileName = '';
                this.updateResumeUI();
            }
        } catch (error) {
            console.error('删除简历失败:', error);
        }
    }

    updateResumeUI() {
        const uploadArea = document.getElementById('resume-upload-area');
        const uploadedArea = document.getElementById('resume-uploaded');
        const progressArea = document.getElementById('resume-progress');
        const fileNameEl = document.getElementById('resume-file-name');
        const statusEl = document.getElementById('resume-status');

        if (progressArea) progressArea.style.display = 'none';

        if (this.resumeUploaded) {
            if (uploadArea) uploadArea.style.display = 'none';
            if (uploadedArea) uploadedArea.style.display = 'flex';
            if (fileNameEl) fileNameEl.textContent = this.resumeFileName;
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--success);">✅ 简历已上传，面试将个性化进行</p>';
        } else {
            if (uploadArea) uploadArea.style.display = 'block';
            if (uploadedArea) uploadedArea.style.display = 'none';
            if (statusEl) statusEl.innerHTML = '<p class="hint-text">上传 PDF 简历，AI 将更了解你</p>';
        }

        this.updateImmersiveResumeBtn();
    }

    /* ==================== Advisor Search ==================== */
    bindAdvisorEvents() {
        const advisorSearchBtn = document.getElementById('advisor-search-btn');
        const advisorDeleteBtn = document.getElementById('advisor-delete-btn');
        const advisorNameInput = document.getElementById('advisor-name-input');
        const modal = document.getElementById('advisor-modal');
        const modalCloseBtn = document.getElementById('advisor-modal-close');
        const modalSearchBtn = document.getElementById('modal-advisor-search-btn');
        const modalDeleteBtn = document.getElementById('modal-advisor-delete-btn');
        const modalNameInput = document.getElementById('modal-advisor-name');

        if (advisorSearchBtn) {
            advisorSearchBtn.addEventListener('click', () => this.searchAdvisor('sidebar'));
        }
        if (advisorDeleteBtn) {
            advisorDeleteBtn.addEventListener('click', () => this.deleteAdvisor(true));
        }
        if (advisorNameInput) {
            advisorNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.searchAdvisor('sidebar');
            });
        }

        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', () => this.hideAdvisorModal());
        }
        if (modalSearchBtn) {
            modalSearchBtn.addEventListener('click', () => this.searchAdvisor('modal'));
        }
        if (modalDeleteBtn) {
            modalDeleteBtn.addEventListener('click', () => this.deleteAdvisor(true));
        }
        if (modalNameInput) {
            modalNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.searchAdvisor('modal');
            });
        }
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'advisor-modal') {
                    this.hideAdvisorModal();
                }
            });
        }

        // 导师文档上传事件
        const docUploadBtn = document.getElementById('advisor-doc-upload-btn');
        const docInput = document.getElementById('advisor-doc-input');

        if (docUploadBtn && docInput) {
            docUploadBtn.addEventListener('click', () => docInput.click());
            docInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.uploadAdvisorDocument(e.target.files[0]);
                }
            });
        }

        // 导师文档模态框事件
        this.bindAdvisorDocsModalEvents();
    }

    /**
     * 绑定导师文档模态框事件
     */
    bindAdvisorDocsModalEvents() {
        const modal = document.getElementById('advisor-docs-modal');
        const closeBtn = document.getElementById('advisor-docs-modal-close');
        const uploadBtn = document.getElementById('modal-advisor-doc-upload-btn');
        const docInput = document.getElementById('modal-advisor-doc-input');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideAdvisorDocsModal());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'advisor-docs-modal') {
                    this.hideAdvisorDocsModal();
                }
            });
        }

        if (uploadBtn && docInput) {
            uploadBtn.addEventListener('click', () => docInput.click());
            docInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.uploadAdvisorDocumentModal(e.target.files[0]);
                }
            });
        }
    }

    /**
     * 显示导师文档模态框
     */
    showAdvisorDocsModal() {
        const modal = document.getElementById('advisor-docs-modal');
        if (modal) {
            modal.style.display = 'flex';
            this.loadAdvisorDocsModal();
        }
    }

    /**
     * 隐藏导师文档模态框
     */
    hideAdvisorDocsModal() {
        const modal = document.getElementById('advisor-docs-modal');
        if (modal) modal.style.display = 'none';
    }

    /**
     * 加载导师文档列表到模态框
     */
    async loadAdvisorDocsModal() {
        try {
            const response = await fetch('/api/advisor/document/list', {
                headers: window.getApiHeaders()
            });
            const data = await response.json();

            const docsList = document.getElementById('modal-advisor-docs-list-content');
            if (!docsList) return;

            if (!data.documents || data.documents.length === 0) {
                docsList.innerHTML = '<p class="hint-text">暂无文档</p>';
                return;
            }

            docsList.innerHTML = data.documents.map(doc => `
                <div class="resume-file-row" style="margin-top:8px;">
                    <i class="fas fa-file-pdf file-icon"></i>
                    <span class="file-name-text" title="${doc.filename}">${doc.filename}</span>
                    <button class="cyber-btn cyber-btn-danger cyber-btn-sm" onclick="app.deleteAdvisorDocumentModal('${doc.safe_filename}')" style="margin-left:auto;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载文档列表失败:', error);
        }
    }

    /**
     * 从模态框上传导师文档
     */
    async uploadAdvisorDocumentModal(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('只支持 PDF 文件格式');
            return;
        }

        const progressArea = document.getElementById('modal-advisor-doc-progress');
        const progressFill = document.getElementById('modal-advisor-doc-progress-fill');
        const progressText = document.getElementById('modal-advisor-doc-progress-text');

        try {
            if (progressArea) progressArea.style.display = 'block';
            if (progressText) progressText.textContent = '正在上传并索引文档...';
            if (progressFill) progressFill.style.width = '50%';

            const formData = new FormData();
            formData.append('file', file);

            // 添加导师信息
            const school = this.advisorSchool || document.getElementById('advisor-school-input')?.value || '';
            const lab = this.advisorLab || document.getElementById('advisor-lab-input')?.value || '';
            const name = this.advisorName || document.getElementById('advisor-name-input')?.value || '';

            formData.append('advisor_school', school);
            formData.append('advisor_lab', lab);
            formData.append('advisor_name', name);

            const response = await fetch('/api/advisor/document/upload', {
                method: 'POST',
                headers: window.getApiHeaders(),
                body: formData
            });

            const data = await response.json();

            if (data.status === 'ok') {
                if (progressFill) progressFill.style.width = '100%';
                if (progressText) progressText.textContent = '上传成功！';
                setTimeout(() => {
                    if (progressArea) progressArea.style.display = 'none';
                    this.loadAdvisorDocsModal();
                    // 同步更新侧边栏文档列表
                    this.loadAdvisorDocuments();
                }, 1000);
            } else {
                throw new Error(data.message || '上传失败');
            }
        } catch (error) {
            console.error('文档上传失败:', error);
            alert(`文档上传失败: ${error.message}`);
            if (progressArea) progressArea.style.display = 'none';
        }

        document.getElementById('modal-advisor-doc-input').value = '';
    }

    /**
     * 从模态框删除导师文档
     */
    async deleteAdvisorDocumentModal(filename) {
        if (!confirm('确定要删除这个文档吗？')) return;

        try {
            const response = await fetch(`/api/advisor/document/${filename}`, {
                method: 'DELETE',
                headers: window.getApiHeaders()
            });

            const data = await response.json();

            if (data.status === 'ok') {
                this.loadAdvisorDocsModal();
                // 同步更新侧边栏文档列表
                this.loadAdvisorDocuments();
            } else {
                throw new Error(data.message || '删除失败');
            }
        } catch (error) {
            console.error('删除文档失败:', error);
            alert(`删除失败: ${error.message}`);
        }
    }

    async loadAdvisorStatus() {
        try {
            const response = await fetch('/api/advisor/status', { headers: window.getApiHeaders() });
            const data = await response.json();

            this.settings.advisor_mode = data.mode || this.settings.advisor_mode || 'ai_default';
            this.settings.advisor_school = data.school || '';
            this.settings.advisor_lab = data.lab || '';
            this.settings.advisor_name = data.name || '';

            this.advisorSearched = !!data.searched;
            this.advisorSchool = data.school || '';
            this.advisorLab = data.lab || '';
            this.advisorName = data.name || '';
            this.advisorInfo = data.info || null;
            this.setAdvisorInputs({
                school: this.advisorSchool,
                lab: this.advisorLab,
                name: this.advisorName
            });

            this.updateSettingsUI();
            this.updateAdvisorUI();
        } catch (error) {
            console.error('加载导师状态失败:', error);
        }
    }

    getAdvisorInputValues(source = 'sidebar') {
        const useModal = source === 'modal';
        const schoolInput = document.getElementById(useModal ? 'modal-advisor-school' : 'advisor-school-input');
        const labInput = document.getElementById(useModal ? 'modal-advisor-lab' : 'advisor-lab-input');
        const nameInput = document.getElementById(useModal ? 'modal-advisor-name' : 'advisor-name-input');

        return {
            school: schoolInput?.value.trim() || '',
            lab: labInput?.value.trim() || '',
            name: nameInput?.value.trim() || ''
        };
    }

    setAdvisorInputs(values = {}) {
        const school = values.school || '';
        const lab = values.lab || '';
        const name = values.name || '';

        const sidebarSchool = document.getElementById('advisor-school-input');
        const sidebarLab = document.getElementById('advisor-lab-input');
        const sidebarName = document.getElementById('advisor-name-input');
        const modalSchool = document.getElementById('modal-advisor-school');
        const modalLab = document.getElementById('modal-advisor-lab');
        const modalName = document.getElementById('modal-advisor-name');

        if (sidebarSchool) sidebarSchool.value = school;
        if (sidebarLab) sidebarLab.value = lab;
        if (sidebarName) sidebarName.value = name;
        if (modalSchool) modalSchool.value = school;
        if (modalLab) modalLab.value = lab;
        if (modalName) modalName.value = name;
    }

    showAdvisorModal() {
        const modal = document.getElementById('advisor-modal');
        if (!modal) return;

        this.settings.advisor_mode = 'custom';
        this.updateSettingsUI();

        const school = this.advisorSearchPayload?.school || this.advisorSchool || this.settings.advisor_school || '';
        const lab = this.advisorSearchPayload?.lab || this.advisorLab || this.settings.advisor_lab || '';
        const name = this.advisorSearchPayload?.name || this.advisorName || this.settings.advisor_name || '';
        this.setAdvisorInputs({ school, lab, name });

        modal.style.display = 'flex';
        this.renderAdvisorSearchState();
    }

    hideAdvisorModal() {
        const modal = document.getElementById('advisor-modal');
        if (modal) modal.style.display = 'none';
    }

    renderAdvisorSearchState() {
        const sidebarProgressArea = document.getElementById('advisor-progress');
        const sidebarProgressFill = document.getElementById('advisor-progress-fill');
        const sidebarProgressText = document.getElementById('advisor-progress-text');
        const sidebarErrorArea = document.getElementById('advisor-error');
        const sidebarErrorText = document.getElementById('advisor-error-text');

        const modalProgressArea = document.getElementById('modal-advisor-progress');
        const modalProgressFill = document.getElementById('modal-advisor-progress-fill');
        const modalProgressText = document.getElementById('modal-advisor-progress-text');
        const modalErrorArea = document.getElementById('modal-advisor-error');
        const modalErrorText = document.getElementById('modal-advisor-error-text');
        const modalResultArea = document.getElementById('modal-advisor-result');
        const modalResultText = document.getElementById('modal-advisor-result-text');
        const sidebarSearchBtn = document.getElementById('advisor-search-btn');
        const modalSearchBtn = document.getElementById('modal-advisor-search-btn');

        const progressWidth = `${Math.max(0, Math.min(100, this.advisorSearchProgress || 0))}%`;

        if (this.advisorSearchInProgress) {
            if (sidebarProgressArea) sidebarProgressArea.style.display = 'block';
            if (sidebarProgressFill) sidebarProgressFill.style.width = progressWidth;
            if (sidebarProgressText) sidebarProgressText.textContent = this.advisorSearchProgressText || '正在检索导师信息...';
            if (sidebarErrorArea) sidebarErrorArea.style.display = 'none';

            if (modalProgressArea) modalProgressArea.style.display = 'block';
            if (modalProgressFill) modalProgressFill.style.width = progressWidth;
            if (modalProgressText) modalProgressText.textContent = this.advisorSearchProgressText || '正在检索导师信息...';
            if (modalErrorArea) modalErrorArea.style.display = 'none';
        } else {
            if (sidebarProgressArea) sidebarProgressArea.style.display = 'none';
            if (modalProgressArea) modalProgressArea.style.display = 'none';
        }

        if (sidebarSearchBtn) sidebarSearchBtn.disabled = this.advisorSearchInProgress;
        if (modalSearchBtn) modalSearchBtn.disabled = this.advisorSearchInProgress;

        if (this.advisorSearchError) {
            if (sidebarErrorArea) sidebarErrorArea.style.display = 'block';
            if (sidebarErrorText) sidebarErrorText.textContent = this.advisorSearchError;
            if (modalErrorArea) modalErrorArea.style.display = 'block';
            if (modalErrorText) modalErrorText.textContent = this.advisorSearchError;
        } else {
            if (sidebarErrorArea) sidebarErrorArea.style.display = 'none';
            if (modalErrorArea) modalErrorArea.style.display = 'none';
        }

        if (this.advisorSearched && this.advisorInfo) {
            if (modalResultArea) modalResultArea.style.display = 'block';
            if (modalResultText) modalResultText.value = this.advisorInfo;
        } else {
            if (modalResultArea) modalResultArea.style.display = 'none';
            if (modalResultText) modalResultText.value = '';
        }
    }

    async searchAdvisor(source = 'sidebar') {
        const { school, lab, name } = this.getAdvisorInputValues(source);
        const customFields = document.getElementById('advisor-custom-fields');

        if (this.advisorSearchInProgress) {
            return;
        }

        if (!school && !name) {
            this.advisorSearchError = '请至少填写学校或导师姓名之一';
            this.renderAdvisorSearchState();
            return;
        }

        this.setAdvisorInputs({ school, lab, name });
        this.advisorSearchPayload = { school, lab, name };
        this.advisorSearchError = '';
        this.advisorSearchInProgress = true;
        this.advisorSearchProgress = 20;
        this.advisorSearchProgressText = '正在联网检索导师信息...';
        if (customFields) customFields.style.display = 'none';
        this.renderAdvisorSearchState();

        try {
            const formData = new FormData();
            formData.append('school', school);
            formData.append('lab', lab);
            formData.append('name', name);

            this.advisorSearchProgress = 50;
            this.advisorSearchProgressText = 'AI 正在分析导师信息...';
            this.renderAdvisorSearchState();

            const response = await fetch('/api/advisor/search', {
                method: 'POST',
                headers: window.getApiHeaders(),
                body: formData
            });
            const data = await response.json();

            if (!response.ok || data.status !== 'ok') {
                throw new Error(data.message || '搜索失败');
            }

            this.advisorSearchProgress = 100;
            this.advisorSearchProgressText = '✅ 导师信息检索完成';

            this.settings.advisor_mode = 'custom';
            this.settings.advisor_school = school;
            this.settings.advisor_lab = lab;
            this.settings.advisor_name = name;

            this.advisorSearched = true;
            this.advisorSchool = school;
            this.advisorLab = lab;
            this.advisorName = name;
            this.advisorInfo = (typeof data.info === 'string') ? data.info : JSON.stringify(data.info);

            await this.saveSettings();
            this.updateAdvisorUI();
            this.renderAdvisorSearchState();
        } catch (error) {
            console.error('导师检索失败:', error);
            this.advisorSearchError = `检索失败: ${error.message}`;
            if (customFields) customFields.style.display = 'block';
            this.renderAdvisorSearchState();
        } finally {
            this.advisorSearchInProgress = false;
            this.renderAdvisorSearchState();
        }
    }

    async deleteAdvisor(showConfirm = true, switchToDefault = false) {
        // switchToDefault: true = 切换到默认 AI 导师模式，false = 保持自定义模式并显示搜索界面
        const confirmMsg = switchToDefault
            ? '确定要清除导师信息并恢复为默认 AI 导师吗？'
            : '确定要清除导师信息吗？清除后可以重新搜索。';
        if (showConfirm && !confirm(confirmMsg)) return;
        try {
            const response = await fetch('/api/advisor', { method: 'DELETE', headers: window.getApiHeaders() });
            const data = await response.json();
            if (data.status === 'ok') {
                // 只有在明确要求时才切换到默认模式
                if (switchToDefault) {
                    this.settings.advisor_mode = 'ai_default';
                }
                // 保持 advisor_mode = 'custom' 以便显示搜索界面（除非 switchToDefault）

                // 清除搜索结果相关状态
                this.settings.advisor_school = '';
                this.settings.advisor_lab = '';
                this.settings.advisor_name = '';

                this.advisorSearched = false;
                this.advisorSchool = '';
                this.advisorLab = '';
                this.advisorName = '';
                this.advisorInfo = null;
                this.advisorSearchError = '';
                this.advisorSearchProgress = 0;
                this.advisorSearchProgressText = '';
                this.advisorSearchPayload = null;

                this.setAdvisorInputs({ school: '', lab: '', name: '' });

                await this.saveSettings();
                this.updateSettingsUI();
                this.updateAdvisorUI();
                
                // 关闭可能打开的 modal
                this.hideAdvisorModal();
            }
        } catch (error) {
            console.error('清除导师信息失败:', error);
        }
    }

    updateAdvisorUI() {
        const statusEl = document.getElementById('advisor-status');
        const customFields = document.getElementById('advisor-custom-fields');
        const searchedArea = document.getElementById('advisor-searched');
        const advisorMode = document.getElementById('advisor-mode');
        const docsSection = document.getElementById('advisor-docs-section');

        if (advisorMode) advisorMode.value = this.settings.advisor_mode || 'ai_default';

        if (this.settings.advisor_mode === 'ai_default') {
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--neon-cyan);">当前使用默认 AI 导师</p>';
            if (customFields) customFields.style.display = 'none';
            if (searchedArea) searchedArea.style.display = 'none';
            if (docsSection) docsSection.style.display = 'none';
            this.renderAdvisorSearchState();
            return;
        }

        // 自定义导师模式：始终显示文档上传区域
        if (docsSection) docsSection.style.display = 'block';

        if (this.advisorSearched && this.advisorInfo) {
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--success);">✅ 已加载自定义导师信息，将作为提示词注入</p>';
            if (customFields) customFields.style.display = 'none';
            if (searchedArea) searchedArea.style.display = 'block';

            const displayName = document.getElementById('advisor-display-name');
            const displaySchool = document.getElementById('advisor-display-school');
            const displayLab = document.getElementById('advisor-display-lab');
            const resultTextbox = document.getElementById('advisor-result-textbox');

            if (displayName) displayName.textContent = this.advisorName;
            if (displaySchool) displaySchool.textContent = this.advisorSchool;
            if (displayLab) displayLab.textContent = this.advisorLab;
            if (resultTextbox) resultTextbox.value = this.advisorInfo;
            this.renderAdvisorSearchState();
            this.loadAdvisorDocuments();
            return;
        }

        if (statusEl) statusEl.innerHTML = '<p class="hint-text">填写导师信息后可直接上传文档，或点击检索按钮联网搜索</p>';
        if (customFields) customFields.style.display = 'block';
        if (searchedArea) searchedArea.style.display = 'none';
        this.renderAdvisorSearchState();
        this.loadAdvisorDocuments();
    }

    /* ==================== Advisor Documents ==================== */
    async uploadAdvisorDocument(file) {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            alert('只支持 PDF 文件格式');
            return;
        }

        const progressArea = document.getElementById('advisor-doc-progress');
        const progressFill = document.getElementById('advisor-doc-progress-fill');
        const progressText = document.getElementById('advisor-doc-progress-text');

        try {
            if (progressArea) progressArea.style.display = 'block';
            if (progressText) progressText.textContent = '正在上传并索引文档...';
            if (progressFill) progressFill.style.width = '50%';

            const formData = new FormData();
            formData.append('file', file);

            // 添加导师信息（从 session 或输入框获取）
            const school = this.advisorSchool || document.getElementById('advisor-school-input')?.value || '';
            const lab = this.advisorLab || document.getElementById('advisor-lab-input')?.value || '';
            const name = this.advisorName || document.getElementById('advisor-name-input')?.value || '';

            formData.append('advisor_school', school);
            formData.append('advisor_lab', lab);
            formData.append('advisor_name', name);

            const response = await fetch('/api/advisor/document/upload', {
                method: 'POST',
                headers: window.getApiHeaders(),
                body: formData
            });

            const data = await response.json();

            if (data.status === 'ok') {
                if (progressFill) progressFill.style.width = '100%';
                if (progressText) progressText.textContent = '上传成功！';
                setTimeout(() => {
                    if (progressArea) progressArea.style.display = 'none';
                    this.loadAdvisorDocuments();
                }, 1000);
            } else {
                throw new Error(data.message || '上传失败');
            }
        } catch (error) {
            console.error('文档上传失败:', error);
            alert(`文档上传失败: ${error.message}`);
            if (progressArea) progressArea.style.display = 'none';
        }

        document.getElementById('advisor-doc-input').value = '';
    }

    async loadAdvisorDocuments() {
        try {
            const response = await fetch('/api/advisor/document/list', {
                headers: window.getApiHeaders()
            });
            const data = await response.json();

            const docsList = document.getElementById('advisor-docs-list');
            if (!docsList) return;

            if (!data.documents || data.documents.length === 0) {
                docsList.innerHTML = '<p class="hint-text" style="margin-top:8px;">暂无文档</p>';
                return;
            }

            docsList.innerHTML = data.documents.map(doc => `
                <div class="resume-file-row" style="margin-top:8px;">
                    <i class="fas fa-file-pdf file-icon"></i>
                    <span class="file-name-text" title="${doc.filename}">${doc.filename}</span>
                    <button class="cyber-btn cyber-btn-danger cyber-btn-sm" onclick="app.deleteAdvisorDocument('${doc.safe_filename}')" style="margin-left:auto;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载文档列表失败:', error);
        }
    }

    async deleteAdvisorDocument(filename) {
        if (!confirm('确定要删除这个文档吗？')) return;

        try {
            const response = await fetch(`/api/advisor/document/${filename}`, {
                method: 'DELETE',
                headers: window.getApiHeaders()
            });

            const data = await response.json();

            if (data.status === 'ok') {
                this.loadAdvisorDocuments();
            } else {
                throw new Error(data.message || '删除失败');
            }
        } catch (error) {
            console.error('删除文档失败:', error);
            alert(`删除失败: ${error.message}`);
        }
    }

    /* ==================== Utilities ==================== */
    getSettings() {
        return this.settings;
    }

    /* ==================== Video Preview ==================== */
    toggleVideoPreview(enabled) {
        const container = document.getElementById('video-preview-container');
        const immersiveContainer = document.getElementById('immersive-video-container');
        if (enabled) {
            if (container) container.style.display = '';
            if (immersiveContainer) immersiveContainer.style.display = '';
            window.videoRecorder?.initCamera();
        } else {
            if (container) container.style.display = 'none';
            if (immersiveContainer) immersiveContainer.style.display = 'none';
            window.videoRecorder?.releaseCamera();
        }
    }

    showLoading(text = '正在处理...') {
        if (this.loadingOverlay) this.loadingOverlay.classList.add('show');
        if (this.loadingText) this.loadingText.textContent = text;
    }

    hideLoading() {
        if (this.loadingOverlay) this.loadingOverlay.classList.remove('show');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
