/**
 * 前端配置
 */

export const config = {
    // API 配置
    api: {
        baseURL: '',
        timeout: 30000,
    },
    
    // 音频配置
    audio: {
        sampleRate: 16000,
        channels: 1,
        
        // VAD 配置
        vad: {
            silenceThreshold: 0.03,
            speechThreshold: 0.03,
            silenceDurationMs: 1500,
            noSpeechTimeoutSeconds: 10,
        },
    },
    
    // 视频配置
    video: {
        width: 640,
        height: 480,
        frameRate: 30,
        videoBitRate: 1000000,
    },
    
    // 面试阶段名称
    interviewStages: {
        0: '开始',
        1: '自我介绍',
        2: '经历深挖',
        3: '基础知识',
        4: '代码',
        5: '科研动机',
        6: '科研潜力',
        7: '综合追问',
        8: '学生反问',
        9: '结束',
    },
    
    // 面试风格
    interviewStyles: {
        gentle: {
            name: '温和型',
            description: '以鼓励为主，营造轻松的面试氛围',
        },
        normal: {
            name: '正常型',
            description: '专业客观的提问方式，平衡难度和引导',
        },
        pressure: {
            name: '压力型',
            description: '较多追问和质疑，考验抗压能力',
        },
    },
    
    // 本地存储键名
    storageKeys: {
        sessionId: 'interview_session_id',
        settings: 'app_settings',
        history: 'chat_history',
    },
};

// 挂载到 window
if (typeof window !== 'undefined') {
    window.appConfig = config;
}

export default config;
