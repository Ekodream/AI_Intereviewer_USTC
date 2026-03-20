/**
 * 抽屉面板管理器 - 管理 RAG 和报告抽屉面板
 */

import { apiClient } from '../../core/api-client.js';

export class DrawerManager {
    constructor() {
        this.activeDrawer = null;
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
        // RAG 抽屉
        const ragBtn = document.getElementById('toggle-rag-btn');
        const ragDrawer = document.getElementById('rag-drawer');
        const ragClose = document.getElementById('rag-close-btn');
        
        if (ragBtn && ragDrawer) {
            ragBtn.addEventListener('click', () => {
                const isOpen = ragDrawer.classList.contains('show');
                this.closeAll();
                if (!isOpen) {
                    ragDrawer.classList.add('show');
                    ragBtn.classList.add('active');
                    this.activeDrawer = 'rag';
                    this.loadRagHistory();
                }
            });
        }
        
        if (ragClose) {
            ragClose.addEventListener('click', () => this.closeAll());
        }
        
        // 报告抽屉
        const reportBtn = document.getElementById('toggle-report-btn');
        const reportDrawer = document.getElementById('report-drawer');
        const reportClose = document.getElementById('report-close-btn');
        
        if (reportBtn && reportDrawer) {
            reportBtn.addEventListener('click', () => {
                const isOpen = reportDrawer.classList.contains('show');
                this.closeAll();
                if (!isOpen) {
                    reportDrawer.classList.add('show');
                    reportBtn.classList.add('active');
                    this.activeDrawer = 'report';
                }
            });
        }
        
        if (reportClose) {
            reportClose.addEventListener('click', () => this.closeAll());
        }
    }
    
    /**
     * 关闭所有抽屉
     */
    closeAll() {
        document.querySelectorAll('.side-drawer').forEach(d => d.classList.remove('show'));
        document.getElementById('toggle-rag-btn')?.classList.remove('active');
        document.getElementById('toggle-report-btn')?.classList.remove('active');
        this.activeDrawer = null;
    }
    
    /**
     * 打开指定抽屉
     */
    open(drawer) {
        this.closeAll();
        
        if (drawer === 'rag') {
            document.getElementById('rag-drawer')?.classList.add('show');
            document.getElementById('toggle-rag-btn')?.classList.add('active');
            this.activeDrawer = 'rag';
            this.loadRagHistory();
        } else if (drawer === 'report') {
            document.getElementById('report-drawer')?.classList.add('show');
            document.getElementById('toggle-report-btn')?.classList.add('active');
            this.activeDrawer = 'report';
        }
    }
    
    /**
     * 加载 RAG 历史
     */
    async loadRagHistory() {
        try {
            const data = await apiClient.get('/api/rag/history');
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
    
    /**
     * 转义 HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 创建单例
export const drawerManager = new DrawerManager();

if (typeof window !== 'undefined') {
    window.drawerManager = drawerManager;
}

export default DrawerManager;
