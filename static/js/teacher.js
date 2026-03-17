/**
 * AI Lab-InterReviewer - 导师端逻辑
 */

class TeacherApp {
    constructor() {
        this.rooms = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadRooms();
    }

    bindEvents() {
        document.getElementById('create-room-btn').addEventListener('click', () => this.createRoom());
        document.getElementById('refresh-rooms-btn').addEventListener('click', () => this.loadRooms());
    }

    async createRoom() {
        const teacherName = document.getElementById('teacher-name').value.trim();
        if (!teacherName) {
            alert('请输入导师姓名');
            return;
        }

        const config = {
            prompt_choice: document.getElementById('prompt-choice').value,
            system_prompt: '',
            enable_tts: document.getElementById('enable-tts').checked,
            auto_vad: document.getElementById('auto-vad').checked,
            enable_rag: document.getElementById('enable-rag').checked,
            enable_video: document.getElementById('enable-video').checked,
            require_resume: document.getElementById('require-resume').checked,
            rag_domain: 'cs ai',
            rag_top_k: 6,
            compact_mode: false,
            advisor_mode: 'ai_default'
        };

        this.showLoading('正在创建房间...');

        try {
            const response = await fetch('/api/teacher/room/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ teacher_name: teacherName, config })
            });

            const data = await response.json();

            if (data.status === 'ok') {
                alert(`房间创建成功！\n房间号：${data.room_id}\n请将此房间号告知学生`);
                this.loadRooms();
            } else {
                alert('创建失败：' + (data.detail || '未知错误'));
            }
        } catch (error) {
            alert('创建失败：' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async loadRooms() {
        try {
            const response = await fetch('/api/teacher/rooms');
            const data = await response.json();
            this.rooms = data.rooms || [];
            this.renderRooms();
        } catch (error) {
            console.error('加载房间列表失败:', error);
        }
    }

    renderRooms() {
        const container = document.getElementById('rooms-container');

        if (this.rooms.length === 0) {
            container.innerHTML = '<p class="hint-text">暂无房间</p>';
            return;
        }

        container.innerHTML = this.rooms.map(room => `
            <div class="room-card" style="background: rgba(45, 55, 72, 0.6); padding: 20px; border-radius: 8px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div style="font-size: 32px; font-weight: 700; color: #63b3ed; margin-bottom: 8px;">
                            ${room.room_id}
                        </div>
                        <div style="color: #a0aec0; margin-bottom: 4px;">
                            <i class="fas fa-user"></i> ${room.teacher_name}
                        </div>
                        <div style="color: #718096; font-size: 14px;">
                            创建时间：${new Date(room.created_at).toLocaleString('zh-CN')}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="background: ${room.status === 'active' ? '#48bb78' : '#718096'}; padding: 4px 12px; border-radius: 12px; font-size: 12px;">
                            ${room.status === 'active' ? '进行中' : '已关闭'}
                        </span>
                    </div>
                </div>
                <div style="margin-top: 16px; display: flex; gap: 8px;">
                    <button class="cyber-btn cyber-btn-sm" onclick="teacherApp.viewResults('${room.room_id}')">
                        <i class="fas fa-chart-line"></i> 查看结果
                    </button>
                    ${room.status === 'active' ? `
                        <button class="cyber-btn cyber-btn-danger cyber-btn-sm" onclick="teacherApp.closeRoom('${room.room_id}')">
                            <i class="fas fa-times-circle"></i> 关闭房间
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    async closeRoom(roomId) {
        if (!confirm(`确定要关闭房间 ${roomId} 吗？关闭后学生将无法加入。`)) {
            return;
        }

        try {
            const response = await fetch(`/api/teacher/room/${roomId}/close`, {
                method: 'PUT'
            });

            const data = await response.json();
            if (data.status === 'ok') {
                alert('房间已关闭');
                this.loadRooms();
            }
        } catch (error) {
            alert('关闭失败：' + error.message);
        }
    }

    async viewResults(roomId) {
        this.showLoading('正在加载学生结果...');

        try {
            const response = await fetch(`/api/teacher/room/${roomId}/results`);
            const data = await response.json();
            const results = data.results || [];

            this.hideLoading();

            if (results.length === 0) {
                alert('暂无学生参与此房间');
                return;
            }

            this.showResultsModal(roomId, results);
        } catch (error) {
            this.hideLoading();
            alert('加载失败：' + error.message);
        }
    }

    showResultsModal(roomId, results) {
        const modal = document.createElement('div');
        modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 9999;';

        modal.innerHTML = `
            <div style="background: #1a202c; padding: 32px; border-radius: 12px; max-width: 800px; max-height: 80vh; overflow-y: auto; width: 90%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <h2 style="color: #fff; margin: 0;">房间 ${roomId} - 学生结果</h2>
                    <button onclick="this.closest('div[style*=fixed]').remove()" style="background: none; border: none; color: #fff; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="color: #a0aec0;">
                    ${results.map(r => {
                        const meta = r.metadata || {};
                        return `
                            <div style="background: rgba(45, 55, 72, 0.6); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                                <div style="font-weight: 600; color: #63b3ed; margin-bottom: 8px;">
                                    学生 ID: ${r.session_id.substring(0, 8)}...
                                </div>
                                ${meta.end_time ? `<div>完成时间: ${new Date(meta.end_time).toLocaleString('zh-CN')}</div>` : ''}
                                ${meta.total_turns ? `<div>对话轮数: ${meta.total_turns}</div>` : ''}
                                <div style="margin-top: 12px;">
                                    <button class="cyber-btn cyber-btn-sm" onclick="teacherApp.downloadStudentData('${roomId}', '${r.session_id}', 'conversation')">
                                        <i class="fas fa-download"></i> 对话记录
                                    </button>
                                    <button class="cyber-btn cyber-btn-sm" onclick="teacherApp.downloadStudentData('${roomId}', '${r.session_id}', 'report')">
                                        <i class="fas fa-download"></i> AI报告
                                    </button>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    async downloadStudentData(roomId, sessionId, type) {
        try {
            const response = await fetch(`/api/teacher/room/${roomId}/student/${sessionId}`);
            const data = await response.json();

            let content, filename;
            if (type === 'conversation') {
                content = JSON.stringify(data.conversation || [], null, 2);
                filename = `conversation_${sessionId.substring(0, 8)}.json`;
            } else if (type === 'report') {
                content = data.report || '暂无报告';
                filename = `report_${sessionId.substring(0, 8)}.md`;
            }

            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            alert('下载失败：' + error.message);
        }
    }

    showLoading(text) {
        document.getElementById('loading-text').textContent = text;
        document.getElementById('loading-overlay').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

const teacherApp = new TeacherApp();

