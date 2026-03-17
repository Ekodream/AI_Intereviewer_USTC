/**
 * 视频录制模块 — Cybernetic Command
 * 摄像头视频流获取与录制，与音频录制同步
 */

class VideoRecorder {
    constructor() {
        this.videoStream = null;
        this.mediaRecorder = null;
        this.videoChunks = [];
        this.isRecording = false;
        this.cameraReady = false;

        this.previewEl = document.getElementById('video-preview');
        this.immersivePreviewEl = document.getElementById('immersive-video-preview');
        this.statusEl = document.getElementById('video-rec-status');
        this.containerEl = document.getElementById('video-preview-container');
        this.immersiveContainerEl = document.getElementById('immersive-video-container');
        this.recDotEl = document.getElementById('immersive-video-rec-dot');
    }

    /**
     * 初始化摄像头（仅视频轨道，音频由 VAD 独立管理）
     */
    async initCamera() {
        if (this.cameraReady && this.videoStream) return this.videoStream;

        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: false
            });

            // 设置预览
            if (this.previewEl) {
                this.previewEl.srcObject = this.videoStream;
            }
            if (this.immersivePreviewEl) {
                this.immersivePreviewEl.srcObject = this.videoStream;
            }

            this.cameraReady = true;
            console.log('📹 摄像头已初始化');
            return this.videoStream;
        } catch (error) {
            console.error('📹 无法访问摄像头:', error);
            this.cameraReady = false;
            return null;
        }
    }

    /**
     * 开始视频录制
     */
    async startRecording() {
        if (this.isRecording) return;

        // 确保摄像头已初始化
        if (!this.cameraReady || !this.videoStream) {
            const stream = await this.initCamera();
            if (!stream) {
                console.warn('📹 摄像头未就绪，跳过视频录制');
                return;
            }
        }

        try {
            const mimeType = this.getSupportedVideoMimeType();
            this.mediaRecorder = new MediaRecorder(this.videoStream, {
                mimeType,
                videoBitsPerSecond: 1000000 // 1 Mbps
            });

            this.videoChunks = [];

            this.mediaRecorder.addEventListener('dataavailable', (event) => {
                if (event.data.size > 0) {
                    this.videoChunks.push(event.data);
                }
            });

            this.mediaRecorder.start(1000); // 每秒一个 chunk
            this.isRecording = true;
            this.updateUI(true);
            console.log('📹 开始视频录制');
        } catch (error) {
            console.error('📹 视频录制启动失败:', error);
        }
    }

    /**
     * 停止视频录制
     * @returns {Promise<Blob|null>} 录制的视频 Blob
     */
    stopRecording() {
        return new Promise((resolve) => {
            if (!this.mediaRecorder || !this.isRecording) {
                resolve(null);
                return;
            }

            this.mediaRecorder.addEventListener('stop', () => {
                const blob = this.getRecordedBlob();
                this.isRecording = false;
                this.updateUI(false);
                console.log('📹 停止视频录制，大小:', blob ? `${(blob.size / 1024).toFixed(1)}KB` : '0');
                resolve(blob);
            }, { once: true });

            this.mediaRecorder.stop();
        });
    }

    /**
     * 获取录制的视频 Blob
     */
    getRecordedBlob() {
        if (this.videoChunks.length === 0) return null;
        return new Blob(this.videoChunks, { type: 'video/webm' });
    }

    /**
     * 上传视频到后端
     */
    async uploadVideo(blob) {
        if (!blob || blob.size === 0) return null;

        try {
            const formData = new FormData();
            formData.append('file', blob, 'interview_video.webm');

            const response = await fetch('/api/video/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (result.status === 'ok') {
                console.log('📹 视频上传成功:', result.filename);
            } else {
                console.error('📹 视频上传失败:', result.message);
            }
            return result;
        } catch (error) {
            console.error('📹 视频上传请求失败:', error);
            return null;
        }
    }

    /**
     * 释放摄像头资源
     */
    releaseCamera() {
        if (this.isRecording) {
            // 强制停止录制（不等待 Promise）
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                this.mediaRecorder.stop();
            }
            this.isRecording = false;
        }

        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }

        if (this.previewEl) {
            this.previewEl.srcObject = null;
        }
        if (this.immersivePreviewEl) {
            this.immersivePreviewEl.srcObject = null;
        }

        this.cameraReady = false;
        this.mediaRecorder = null;
        this.videoChunks = [];
        this.updateUI(false);
        console.log('📹 摄像头已释放');
    }

    /**
     * 更新录制状态 UI
     */
    updateUI(recording) {
        // 标准模式状态指示
        if (this.statusEl) {
            if (recording) {
                this.statusEl.classList.add('active');
                this.statusEl.textContent = 'REC';
            } else {
                this.statusEl.classList.remove('active');
                this.statusEl.textContent = '';
            }
        }

        // 沉浸式模式录制红点
        if (this.recDotEl) {
            if (recording) {
                this.recDotEl.classList.add('active');
            } else {
                this.recDotEl.classList.remove('active');
            }
        }
    }

    /**
     * 获取浏览器支持的视频 MIME 类型
     */
    getSupportedVideoMimeType() {
        const types = [
            'video/webm;codecs=vp9',
            'video/webm;codecs=vp8',
            'video/webm',
            'video/mp4'
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) return type;
        }
        return 'video/webm';
    }
}

window.videoRecorder = new VideoRecorder();
