/**
 * 简历管理器 - 处理简历上传和状态管理
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager } from '../../core/state-manager.js';
import { apiClient } from '../../core/api-client.js';

export class ResumeManager {
    constructor() {
        this.uploaded = false;
        this.fileName = '';
    }
    
    /**
     * 初始化
     */
    async init() {
        await this.loadStatus();
        this.bindEvents();
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        const resumeInput = document.getElementById('resume-input');
        const resumeUploadBtn = document.getElementById('resume-upload-btn');
        const resumeDeleteBtn = document.getElementById('resume-delete-btn');
        
        if (resumeUploadBtn && resumeInput) {
            resumeUploadBtn.addEventListener('click', () => resumeInput.click());
        }
        
        if (resumeInput) {
            resumeInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) await this.upload(file);
                resumeInput.value = '';
            });
        }
        
        if (resumeDeleteBtn) {
            resumeDeleteBtn.addEventListener('click', () => this.delete());
        }
    }
    
    /**
     * 加载简历状态
     */
    async loadStatus() {
        try {
            const data = await apiClient.get('/api/resume/status');
            this.uploaded = data.uploaded;
            this.fileName = data.file_name || '';
            this.updateUI();
            this.syncToStateManager();
        } catch (error) {
            console.error('加载简历状态失败:', error);
        }
    }
    
    /**
     * 上传简历
     */
    async upload(file) {
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
            
            const data = await apiClient.upload('/api/resume/upload', formData);
            
            if (data.status === 'ok') {
                if (progressFill) progressFill.style.width = '100%';
                if (progressText) progressText.textContent = '✅ 简历解析完成！';
                this.uploaded = true;
                this.fileName = data.file_name;
                this.syncToStateManager();
                setTimeout(() => this.updateUI(), 1000);
            } else {
                throw new Error(data.message || '上传失败');
            }
        } catch (error) {
            console.error('简历上传失败:', error);
            if (progressText) progressText.textContent = `❌ 上传失败: ${error.message}`;
            setTimeout(() => this.updateUI(), 3000);
        }
    }
    
    /**
     * 删除简历
     */
    async delete() {
        if (!confirm('确定要删除已上传的简历吗？')) return;
        
        try {
            const data = await apiClient.delete('/api/resume');
            if (data.status === 'ok') {
                this.uploaded = false;
                this.fileName = '';
                this.updateUI();
                this.syncToStateManager();
            }
        } catch (error) {
            console.error('删除简历失败:', error);
        }
    }
    
    /**
     * 同步到状态管理器
     */
    syncToStateManager() {
        stateManager.update({
            resume: {
                isUploaded: this.uploaded,
                fileName: this.fileName,
            }
        });
    }
    
    /**
     * 更新 UI
     */
    updateUI() {
        const uploadArea = document.getElementById('resume-upload-area');
        const uploadedArea = document.getElementById('resume-uploaded');
        const progressArea = document.getElementById('resume-progress');
        const fileNameEl = document.getElementById('resume-file-name');
        const statusEl = document.getElementById('resume-status');
        
        if (progressArea) progressArea.style.display = 'none';
        
        if (this.uploaded) {
            if (uploadArea) uploadArea.style.display = 'none';
            if (uploadedArea) uploadedArea.style.display = 'flex';
            if (fileNameEl) fileNameEl.textContent = this.fileName;
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--success);">✅ 简历已上传，面试将个性化进行</p>';
        } else {
            if (uploadArea) uploadArea.style.display = 'block';
            if (uploadedArea) uploadedArea.style.display = 'none';
            if (statusEl) statusEl.innerHTML = '<p class="hint-text">上传 PDF 简历，AI 将更了解你</p>';
        }
        
        // 更新沉浸模式按钮
        this.updateImmersiveBtn();
    }
    
    /**
     * 更新沉浸模式的简历按钮
     */
    updateImmersiveBtn() {
        const btn = document.getElementById('immersive-resume-btn');
        if (!btn) return;
        
        if (this.uploaded) {
            btn.innerHTML = '<i class="fas fa-check"></i> 已上传';
            btn.classList.add('cyber-btn-success');
        } else {
            btn.innerHTML = '<i class="fas fa-upload"></i> 上传';
            btn.classList.remove('cyber-btn-success');
        }
    }
    
    /**
     * 获取状态
     */
    isUploaded() {
        return this.uploaded;
    }
    
    getFileName() {
        return this.fileName;
    }
}

// 创建单例
export const resumeManager = new ResumeManager();

if (typeof window !== 'undefined') {
    window.resumeManager = resumeManager;
}

export default ResumeManager;
