/**
 * 报告管理器 - 处理面试报告生成和下载
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { apiClient } from '../../core/api-client.js';

export class ReportManager {
    constructor() {
        this.reportContent = '';
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
        // 下载 JSON
        document.getElementById('download-json')?.addEventListener('click', () => {
            window.location.href = '/api/report/download/json';
        });
        
        // 下载 TXT
        document.getElementById('download-txt')?.addEventListener('click', () => {
            window.location.href = '/api/report/download/txt';
        });
        
        // 生成报告
        document.getElementById('generate-report-btn')?.addEventListener('click', () => {
            this.generate();
        });
        
        // 下载 Markdown
        document.getElementById('download-report-md')?.addEventListener('click', () => {
            this.downloadMarkdown();
        });
    }
    
    /**
     * 生成报告（流式）
     */
    async generate() {
        const reportContent = document.getElementById('report-content');
        const reportDownload = document.getElementById('report-download');
        const generateBtn = document.getElementById('generate-report-btn');
        
        if (!reportContent) return;
        
        if (generateBtn) generateBtn.disabled = true;
        reportContent.textContent = '正在生成报告，请稍候...';
        this.reportContent = '';
        
        try {
            const sessionId = apiClient.getSessionId();
            const response = await fetch('/api/report/stream', {
                method: 'POST',
                headers: {
                    'X-Session-ID': sessionId,
                }
            });
            
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
                                if (window.modeManager?.isTestMode()) {
                                    await window.modeManager.submitTestResult();
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
    
    /**
     * 下载 Markdown 格式报告
     */
    downloadMarkdown() {
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
    
    /**
     * 清空报告
     */
    clear() {
        this.reportContent = '';
        const reportContent = document.getElementById('report-content');
        const reportDownload = document.getElementById('report-download');
        if (reportContent) reportContent.textContent = '';
        if (reportDownload) reportDownload.style.display = 'none';
    }
    
    /**
     * 获取报告内容
     */
    getContent() {
        return this.reportContent;
    }
}

// 创建单例
export const reportManager = new ReportManager();

if (typeof window !== 'undefined') {
    window.reportManager = reportManager;
}

export default ReportManager;
