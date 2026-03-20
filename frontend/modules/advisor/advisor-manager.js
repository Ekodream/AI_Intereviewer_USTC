/**
 * 导师搜索管理器 - 处理导师信息搜索和文档上传
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager } from '../../core/state-manager.js';
import { apiClient } from '../../core/api-client.js';

export class AdvisorManager {
    constructor() {
        this.searched = false;
        this.school = '';
        this.lab = '';
        this.name = '';
        this.info = null;
        this.searchInProgress = false;
        this.searchProgress = 0;
        this.searchProgressText = '';
        this.searchError = '';
        this.searchPayload = null;
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
        // 侧边栏搜索按钮
        const advisorSearchBtn = document.getElementById('advisor-search-btn');
        const advisorDeleteBtn = document.getElementById('advisor-delete-btn');
        const advisorNameInput = document.getElementById('advisor-name-input');
        
        if (advisorSearchBtn) {
            advisorSearchBtn.addEventListener('click', () => this.search('sidebar'));
        }
        if (advisorDeleteBtn) {
            advisorDeleteBtn.addEventListener('click', () => this.delete(true));
        }
        if (advisorNameInput) {
            advisorNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.search('sidebar');
            });
        }
        
        // 弹窗相关
        const modal = document.getElementById('advisor-modal');
        const modalCloseBtn = document.getElementById('advisor-modal-close');
        const modalSearchBtn = document.getElementById('modal-advisor-search-btn');
        const modalDeleteBtn = document.getElementById('modal-advisor-delete-btn');
        const modalNameInput = document.getElementById('modal-advisor-name');
        
        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', () => this.hideModal());
        }
        if (modalSearchBtn) {
            modalSearchBtn.addEventListener('click', () => this.search('modal'));
        }
        if (modalDeleteBtn) {
            modalDeleteBtn.addEventListener('click', () => this.delete(true));
        }
        if (modalNameInput) {
            modalNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.search('modal');
            });
        }
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target.id === 'advisor-modal') {
                    this.hideModal();
                }
            });
        }
        
        // 文档上传
        const docUploadBtn = document.getElementById('advisor-doc-upload-btn');
        const docInput = document.getElementById('advisor-doc-input');
        
        if (docUploadBtn && docInput) {
            docUploadBtn.addEventListener('click', () => docInput.click());
            docInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.uploadDocument(e.target.files[0]);
                }
            });
        }
    }
    
    /**
     * 加载导师状态
     */
    async loadStatus() {
        try {
            const data = await apiClient.get('/api/advisor/status');
            
            this.searched = !!data.searched;
            this.school = data.school || '';
            this.lab = data.lab || '';
            this.name = data.name || '';
            this.info = data.info || null;
            
            this.setInputValues({ school: this.school, lab: this.lab, name: this.name });
            this.updateUI();
            this.syncToStateManager();
        } catch (error) {
            console.error('加载导师状态失败:', error);
        }
    }
    
    /**
     * 搜索导师
     */
    async search(source = 'sidebar') {
        const { school, lab, name } = this.getInputValues(source);
        const customFields = document.getElementById('advisor-custom-fields');
        
        if (this.searchInProgress) return;
        
        if (!school && !name) {
            this.searchError = '请至少填写学校或导师姓名之一';
            this.renderSearchState();
            return;
        }
        
        this.setInputValues({ school, lab, name });
        this.searchPayload = { school, lab, name };
        this.searchError = '';
        this.searchInProgress = true;
        this.searchProgress = 20;
        this.searchProgressText = '正在联网检索导师信息...';
        if (customFields) customFields.style.display = 'none';
        this.renderSearchState();
        
        try {
            const formData = new FormData();
            formData.append('school', school);
            formData.append('lab', lab);
            formData.append('name', name);
            
            this.searchProgress = 50;
            this.searchProgressText = 'AI 正在分析导师信息...';
            this.renderSearchState();
            
            const data = await apiClient.upload('/api/advisor/search', formData);
            
            if (data.status !== 'ok') {
                throw new Error(data.message || '搜索失败');
            }
            
            this.searchProgress = 100;
            this.searchProgressText = '✅ 导师信息检索完成';
            
            this.searched = true;
            this.school = school;
            this.lab = lab;
            this.name = name;
            this.info = (typeof data.info === 'string') ? data.info : JSON.stringify(data.info);
            
            this.updateUI();
            this.renderSearchState();
            this.syncToStateManager();
        } catch (error) {
            console.error('导师检索失败:', error);
            this.searchError = `检索失败: ${error.message}`;
            if (customFields) customFields.style.display = 'block';
            this.renderSearchState();
        } finally {
            this.searchInProgress = false;
            this.renderSearchState();
        }
    }
    
    /**
     * 删除导师信息
     */
    async delete(showConfirm = true, switchToDefault = false) {
        const confirmMsg = switchToDefault
            ? '确定要清除导师信息并恢复为默认 AI 导师吗？'
            : '确定要清除导师信息吗？清除后可以重新搜索。';
        
        if (showConfirm && !confirm(confirmMsg)) return;
        
        try {
            const data = await apiClient.delete('/api/advisor');
            if (data.status === 'ok') {
                this.searched = false;
                this.school = '';
                this.lab = '';
                this.name = '';
                this.info = null;
                this.searchError = '';
                this.searchProgress = 0;
                this.searchProgressText = '';
                this.searchPayload = null;
                
                this.setInputValues({ school: '', lab: '', name: '' });
                this.updateUI();
                this.hideModal();
                this.syncToStateManager();
            }
        } catch (error) {
            console.error('清除导师信息失败:', error);
        }
    }
    
    /**
     * 上传导师文档
     */
    async uploadDocument(file) {
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
            formData.append('advisor_school', this.school || document.getElementById('advisor-school-input')?.value || '');
            formData.append('advisor_lab', this.lab || document.getElementById('advisor-lab-input')?.value || '');
            formData.append('advisor_name', this.name || document.getElementById('advisor-name-input')?.value || '');
            
            const data = await apiClient.upload('/api/advisor/document/upload', formData);
            
            if (data.status === 'ok') {
                if (progressFill) progressFill.style.width = '100%';
                if (progressText) progressText.textContent = '上传成功！';
                setTimeout(() => {
                    if (progressArea) progressArea.style.display = 'none';
                    this.loadDocuments();
                }, 1000);
            } else {
                throw new Error(data.message || '上传失败');
            }
        } catch (error) {
            console.error('文档上传失败:', error);
            alert(`文档上传失败: ${error.message}`);
            if (progressArea) progressArea.style.display = 'none';
        }
        
        const docInput = document.getElementById('advisor-doc-input');
        if (docInput) docInput.value = '';
    }
    
    /**
     * 加载导师文档列表
     */
    async loadDocuments() {
        try {
            const data = await apiClient.get('/api/advisor/document/list');
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
                    <button class="cyber-btn cyber-btn-danger cyber-btn-sm" onclick="advisorManager.deleteDocument('${doc.safe_filename}')" style="margin-left:auto;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载文档列表失败:', error);
        }
    }
    
    /**
     * 删除导师文档
     */
    async deleteDocument(filename) {
        if (!confirm('确定要删除这个文档吗？')) return;
        
        try {
            const data = await apiClient.delete(`/api/advisor/document/${filename}`);
            if (data.status === 'ok') {
                this.loadDocuments();
            } else {
                throw new Error(data.message || '删除失败');
            }
        } catch (error) {
            console.error('删除文档失败:', error);
            alert(`删除失败: ${error.message}`);
        }
    }
    
    /**
     * 同步到状态管理器
     */
    syncToStateManager() {
        stateManager.update({
            advisor: {
                name: this.name,
                school: this.school,
                info: this.info,
                isSearching: this.searchInProgress,
            }
        });
    }
    
    /**
     * 获取输入框值
     */
    getInputValues(source = 'sidebar') {
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
    
    /**
     * 设置输入框值
     */
    setInputValues(values = {}) {
        const { school = '', lab = '', name = '' } = values;
        
        const inputs = [
            { id: 'advisor-school-input', value: school },
            { id: 'advisor-lab-input', value: lab },
            { id: 'advisor-name-input', value: name },
            { id: 'modal-advisor-school', value: school },
            { id: 'modal-advisor-lab', value: lab },
            { id: 'modal-advisor-name', value: name },
        ];
        
        inputs.forEach(({ id, value }) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
        });
    }
    
    /**
     * 显示弹窗
     */
    showModal() {
        const modal = document.getElementById('advisor-modal');
        if (!modal) return;
        
        const school = this.searchPayload?.school || this.school || '';
        const lab = this.searchPayload?.lab || this.lab || '';
        const name = this.searchPayload?.name || this.name || '';
        this.setInputValues({ school, lab, name });
        
        modal.style.display = 'flex';
        this.renderSearchState();
    }
    
    /**
     * 隐藏弹窗
     */
    hideModal() {
        const modal = document.getElementById('advisor-modal');
        if (modal) modal.style.display = 'none';
    }
    
    /**
     * 渲染搜索状态
     */
    renderSearchState() {
        const elements = {
            sidebar: {
                progressArea: document.getElementById('advisor-progress'),
                progressFill: document.getElementById('advisor-progress-fill'),
                progressText: document.getElementById('advisor-progress-text'),
                errorArea: document.getElementById('advisor-error'),
                errorText: document.getElementById('advisor-error-text'),
                searchBtn: document.getElementById('advisor-search-btn'),
            },
            modal: {
                progressArea: document.getElementById('modal-advisor-progress'),
                progressFill: document.getElementById('modal-advisor-progress-fill'),
                progressText: document.getElementById('modal-advisor-progress-text'),
                errorArea: document.getElementById('modal-advisor-error'),
                errorText: document.getElementById('modal-advisor-error-text'),
                resultArea: document.getElementById('modal-advisor-result'),
                resultText: document.getElementById('modal-advisor-result-text'),
                searchBtn: document.getElementById('modal-advisor-search-btn'),
            }
        };
        
        const progressWidth = `${Math.max(0, Math.min(100, this.searchProgress || 0))}%`;
        
        ['sidebar', 'modal'].forEach(key => {
            const el = elements[key];
            
            if (this.searchInProgress) {
                if (el.progressArea) el.progressArea.style.display = 'block';
                if (el.progressFill) el.progressFill.style.width = progressWidth;
                if (el.progressText) el.progressText.textContent = this.searchProgressText || '正在检索...';
                if (el.errorArea) el.errorArea.style.display = 'none';
            } else {
                if (el.progressArea) el.progressArea.style.display = 'none';
            }
            
            if (el.searchBtn) el.searchBtn.disabled = this.searchInProgress;
            
            if (this.searchError) {
                if (el.errorArea) el.errorArea.style.display = 'block';
                if (el.errorText) el.errorText.textContent = this.searchError;
            } else {
                if (el.errorArea) el.errorArea.style.display = 'none';
            }
        });
        
        // 弹窗结果区域
        if (this.searched && this.info) {
            if (elements.modal.resultArea) elements.modal.resultArea.style.display = 'block';
            if (elements.modal.resultText) elements.modal.resultText.value = this.info;
        } else {
            if (elements.modal.resultArea) elements.modal.resultArea.style.display = 'none';
        }
    }
    
    /**
     * 更新 UI
     */
    updateUI() {
        const statusEl = document.getElementById('advisor-status');
        const customFields = document.getElementById('advisor-custom-fields');
        const searchedArea = document.getElementById('advisor-searched');
        const docsSection = document.getElementById('advisor-docs-section');
        const advisorMode = window.settingsManager?.settings?.advisor_mode || 'ai_default';
        
        if (advisorMode === 'ai_default') {
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--neon-cyan);">当前使用默认 AI 导师</p>';
            if (customFields) customFields.style.display = 'none';
            if (searchedArea) searchedArea.style.display = 'none';
            if (docsSection) docsSection.style.display = 'none';
            this.renderSearchState();
            return;
        }
        
        if (docsSection) docsSection.style.display = 'block';
        
        if (this.searched && this.info) {
            if (statusEl) statusEl.innerHTML = '<p class="hint-text" style="color: var(--success);">✅ 已加载自定义导师信息</p>';
            if (customFields) customFields.style.display = 'none';
            if (searchedArea) searchedArea.style.display = 'block';
            
            const displayName = document.getElementById('advisor-display-name');
            const displaySchool = document.getElementById('advisor-display-school');
            const displayLab = document.getElementById('advisor-display-lab');
            const resultTextbox = document.getElementById('advisor-result-textbox');
            
            if (displayName) displayName.textContent = this.name;
            if (displaySchool) displaySchool.textContent = this.school;
            if (displayLab) displayLab.textContent = this.lab;
            if (resultTextbox) resultTextbox.value = this.info;
            
            this.renderSearchState();
            this.loadDocuments();
            return;
        }
        
        if (statusEl) statusEl.innerHTML = '<p class="hint-text">填写导师信息后点击检索按钮</p>';
        if (customFields) customFields.style.display = 'block';
        if (searchedArea) searchedArea.style.display = 'none';
        this.renderSearchState();
        this.loadDocuments();
    }
    
    /**
     * 获取状态
     */
    isSearched() {
        return this.searched;
    }
    
    getInfo() {
        return this.info;
    }
}

// 创建单例
export const advisorManager = new AdvisorManager();

if (typeof window !== 'undefined') {
    window.advisorManager = advisorManager;
}

export default AdvisorManager;
