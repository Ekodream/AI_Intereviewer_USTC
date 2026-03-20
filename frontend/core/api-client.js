/**
 * API 客户端 - 封装后端 API 调用
 * 
 * 统一管理所有 API 请求，提供错误处理和请求拦截。
 */

import { eventBus, Events } from './event-bus.js';

class APIClient {
    constructor(baseURL = '') {
        this._baseURL = baseURL;
        this._sessionId = null;
    }
    
    /**
     * 设置会话 ID
     */
    setSessionId(sessionId) {
        this._sessionId = sessionId;
    }
    
    /**
     * 获取会话 ID
     */
    getSessionId() {
        return this._sessionId;
    }
    
    /**
     * 发送 GET 请求
     */
    async get(endpoint, params = {}) {
        const url = new URL(this._baseURL + endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });
        
        return this._fetch(url.toString(), { method: 'GET' });
    }
    
    /**
     * 发送 POST 请求
     */
    async post(endpoint, data = {}, options = {}) {
        const { isFormData = false } = options;
        
        const fetchOptions = {
            method: 'POST',
        };
        
        if (isFormData) {
            fetchOptions.body = data;
        } else {
            fetchOptions.headers = { 'Content-Type': 'application/json' };
            fetchOptions.body = JSON.stringify(data);
        }
        
        return this._fetch(this._baseURL + endpoint, fetchOptions);
    }
    
    /**
     * 发送 DELETE 请求
     */
    async delete(endpoint, params = {}) {
        const url = new URL(this._baseURL + endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                url.searchParams.append(key, value);
            }
        });
        
        return this._fetch(url.toString(), { method: 'DELETE' });
    }
    
    /**
     * 发送流式请求
     */
    async *streamPost(endpoint, data = {}) {
        const response = await fetch(this._baseURL + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const text = decoder.decode(value, { stream: true });
                const lines = text.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        
                        try {
                            yield JSON.parse(data);
                        } catch {
                            yield { text: data };
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }
    
    // ==================== 具体 API 方法 ====================
    
    /**
     * 发送对话消息（流式）
     */
    async *chat(message, options = {}) {
        const {
            history = [],
            systemPrompt = '',
            settings = {},
            ttsEnabled = true,
        } = options;
        
        yield* this.streamPost('/api/chat', {
            session_id: this._sessionId,
            message,
            history,
            system_prompt: systemPrompt,
            settings,
            tts_enabled: ttsEnabled,
        });
    }
    
    /**
     * 语音识别
     */
    async transcribeAudio(audioBlob) {
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');
        if (this._sessionId) {
            formData.append('session_id', this._sessionId);
        }
        
        return this.post('/api/asr', formData, { isFormData: true });
    }
    
    /**
     * 上传简历
     */
    async uploadResume(file) {
        const formData = new FormData();
        formData.append('file', file);
        if (this._sessionId) {
            formData.append('session_id', this._sessionId);
        }
        
        return this.post('/api/resume/upload', formData, { isFormData: true });
    }
    
    /**
     * 搜索导师信息
     */
    async searchAdvisor(name, school = '') {
        return this.post('/api/advisor/search', {
            session_id: this._sessionId,
            name,
            school,
        });
    }
    
    /**
     * 获取对话历史
     */
    async getHistory() {
        return this.get('/api/history', { session_id: this._sessionId });
    }
    
    /**
     * 清空对话历史
     */
    async clearHistory() {
        return this.delete('/api/history', { session_id: this._sessionId });
    }
    
    /**
     * 生成报告
     */
    async *generateReport() {
        yield* this.streamPost('/api/report/generate', {
            session_id: this._sessionId,
        });
    }
    
    /**
     * 上传视频
     */
    async uploadVideo(videoBlob, filename) {
        const formData = new FormData();
        formData.append('file', videoBlob, filename);
        if (this._sessionId) {
            formData.append('session_id', this._sessionId);
        }
        
        return this.post('/api/video/upload', formData, { isFormData: true });
    }
    
    // ==================== 私有方法 ====================
    
    async _fetch(url, options) {
        try {
            const response = await fetch(url, options);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return response.json();
        } catch (error) {
            eventBus.emit(Events.APP_ERROR, { source: 'api', error });
            throw error;
        }
    }
}

// 创建全局 API 客户端实例
export const apiClient = new APIClient();

// 挂载到 window
if (typeof window !== 'undefined') {
    window.apiClient = apiClient;
}

export default APIClient;
