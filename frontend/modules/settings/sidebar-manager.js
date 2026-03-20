/**
 * 侧边栏管理器 - 管理侧边栏的展开/收起和事件
 */

export class SidebarManager {
    constructor() {
        this.isOpen = false;
    }
    
    /**
     * 初始化
     */
    init() {
        this.bindEvents();
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
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
                this.isOpen = !this.isOpen;
            });
            
            // 移动端点击主区域关闭侧边栏
            const mainStage = document.querySelector('.main-stage');
            if (mainStage) {
                mainStage.addEventListener('click', () => {
                    if (window.innerWidth <= 900) {
                        sidebar.classList.remove('show');
                        sidebarToggle.classList.remove('active');
                        this.isOpen = false;
                    }
                });
            }
        }
        
        // 新对话按钮
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                if (confirm('确定要开始新对话吗？当前对话历史将被清空。')) {
                    window.chat?.clearHistory();
                    window.reportManager?.clear();
                    window.phaseTimeline?.reset();
                }
            });
        }
        
        // 切换沉浸模式按钮
        const switchToImmersiveBtn = document.getElementById('switch-to-immersive-btn');
        if (switchToImmersiveBtn && sidebar) {
            switchToImmersiveBtn.addEventListener('click', () => {
                window.modeManager?.selectMode('immersive', true);
                if (window.innerWidth <= 900) {
                    sidebar.classList.remove('show');
                    document.getElementById('sidebar-toggle')?.classList.remove('active');
                }
            });
        }
        
        // 可折叠提示词区域
        const promptToggle = document.getElementById('prompt-toggle');
        const promptContent = document.getElementById('prompt-content');
        if (promptToggle && promptContent) {
            promptToggle.addEventListener('click', () => {
                promptToggle.classList.toggle('active');
                promptContent.classList.toggle('show');
            });
        }
    }
    
    /**
     * 打开侧边栏
     */
    open() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        
        if (sidebar) {
            if (window.innerWidth <= 900) {
                sidebar.classList.add('show');
            } else {
                sidebar.classList.remove('hidden');
            }
        }
        if (sidebarToggle) sidebarToggle.classList.add('active');
        this.isOpen = true;
    }
    
    /**
     * 关闭侧边栏
     */
    close() {
        const sidebar = document.getElementById('sidebar');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        
        if (sidebar) {
            sidebar.classList.remove('show');
            sidebar.classList.add('hidden');
        }
        if (sidebarToggle) sidebarToggle.classList.remove('active');
        this.isOpen = false;
    }
    
    /**
     * 切换侧边栏
     */
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
}

// 创建单例
export const sidebarManager = new SidebarManager();

if (typeof window !== 'undefined') {
    window.sidebarManager = sidebarManager;
}

export default SidebarManager;
