/**
 * 阶段时间线管理器 - 管理面试阶段进度展示
 */

import { eventBus, Events } from '../../core/event-bus.js';
import { stateManager } from '../../core/state-manager.js';

export class PhaseTimeline {
    constructor() {
        // 十阶段面试流程
        this.phaseNames = [
            '开始',      // 0
            '自我介绍',   // 1
            '经历深挖',   // 2
            '基础知识',   // 3
            '代码',      // 4
            '科研动机',   // 5
            '科研潜力',   // 6
            '综合追问',   // 7
            '学生反问',   // 8
            '结束'       // 9
        ];
        
        this.currentPhase = 0;
    }
    
    /**
     * 初始化
     */
    init() {
        // 监听面试阶段变化事件
        eventBus.on(Events.INTERVIEW_STAGE_CHANGED, (data) => {
            this.update(data.newStage);
        });
    }
    
    /**
     * 更新阶段时间线
     */
    update(phase) {
        this.currentPhase = phase;
        
        const nodes = document.querySelectorAll('.phase-node');
        const lines = document.querySelectorAll('.phase-line');
        
        // 找到当前活跃的节点索引
        let activeIdx = Math.min(phase, nodes.length - 1);
        
        // 更新节点状态
        nodes.forEach((node, idx) => {
            node.classList.remove('completed', 'active');
            if (idx < activeIdx) {
                node.classList.add('completed');
            } else if (idx === activeIdx) {
                node.classList.add('active');
            }
        });
        
        // 更新连接线状态
        lines.forEach((line, idx) => {
            if (idx < activeIdx) {
                line.style.background = 'var(--neon-blue)';
                line.style.boxShadow = '0 0 6px rgba(0, 212, 255, 0.3)';
            } else {
                line.style.background = 'var(--text-muted)';
                line.style.boxShadow = 'none';
            }
        });
        
        // 更新沉浸模式阶段显示
        window.modeManager?.updateImmersivePhase(activeIdx);
    }
    
    /**
     * 重置时间线
     */
    reset() {
        this.currentPhase = 0;
        
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
        
        // 重置沉浸模式阶段显示
        window.modeManager?.updateImmersivePhase(0);
    }
    
    /**
     * 获取当前阶段
     */
    getCurrentPhase() {
        return this.currentPhase;
    }
    
    /**
     * 获取阶段名称
     */
    getPhaseName(phase) {
        return this.phaseNames[phase] || '未知';
    }
}

// 创建单例
export const phaseTimeline = new PhaseTimeline();

if (typeof window !== 'undefined') {
    window.phaseTimeline = phaseTimeline;
}

export default PhaseTimeline;
