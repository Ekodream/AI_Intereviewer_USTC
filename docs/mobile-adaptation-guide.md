# AI InterReviewer 移动端适配指南

> 本文档记录项目的移动端适配架构设计、已知问题解决方案、测试标准和维护指南。

## 目录

1. [适配架构概述](#适配架构概述)
2. [核心模块说明](#核心模块说明)
3. [已知兼容性问题与解决方案](#已知兼容性问题与解决方案)
4. [测试标准](#测试标准)
5. [维护指南](#维护指南)

---

## 适配架构概述

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    移动端适配层                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ mobile-utils│  │   config    │  │     style.css       │  │
│  │    .js      │  │    .js      │  │  (响应式/触摸/横向)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│  ┌──────┴────────────────┴─────────────────────┴──────────┐  │
│  │                    应用层                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │tts-stream│  │   vad    │  │  video   │              │  │
│  │  │   .js    │  │   .js    │  │recorder.js│              │  │
│  │  └──────────┘  └──────────┘  └──────────┘              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 关键文件

| 文件 | 职责 |
|------|------|
| `static/js/mobile-utils.js` | 移动端工具函数（设备检测、音频解锁、触摸工具） |
| `frontend/core/config.js` | 移动端配置参数（阈值、尺寸、断点） |
| `static/js/tts-stream.js` | TTS 音频播放（含移动端 AudioContext 方案） |
| `static/js/vad.js` | 语音活动检测（含移动端优化） |
| `static/css/style.css` | 响应式布局、横向模式、触摸优化 |
| `static/index.html` | 移动端 meta 标签 |

---

## 核心模块说明

### 1. MobileUtils 工具模块

**位置**: `static/js/mobile-utils.js`

提供四个主要对象：

```javascript
// 设备检测
MobileUtils.isMobile()      // 是否移动端
MobileUtils.isIOS()         // 是否 iOS
MobileUtils.isAndroid()     // 是否 Android
MobileUtils.isLandscape()   // 是否横向模式

// 音频解锁管理
AudioUnlockManager.unlock()         // 解锁音频播放
AudioUnlockManager.setupAutoUnlock() // 自动解锁设置

// 触摸工具
TouchUtils.isTouchDevice()          // 是否触摸设备
TouchUtils.addTouchFeedback(el)     // 添加触摸反馈

// 视口工具
ViewportUtils.getSafeAreaInsets()   // 获取安全区域
ViewportUtils.lockOrientation()     // 锁定方向
```

### 2. 音频解锁机制

移动浏览器要求音频播放必须由用户手势触发。解决方案：

```javascript
// 在用户首次交互时解锁
document.addEventListener('click', async () => {
    await AudioUnlockManager.unlock();
}, { once: true });

// 解锁过程
1. 创建 AudioContext
2. 创建并播放静音 buffer
3. 标记为已解锁
```

### 3. TTS 移动端播放

**位置**: `static/js/tts-stream.js`

移动端使用 AudioContext + decodeAudioData 方式：

```javascript
// 播放流程
1. 检查音频是否已解锁
2. 恢复挂起的 AudioContext
3. 使用 decodeAudioData 解码音频
4. 创建 BufferSource 播放
5. 失败时自动重试（最多 3 次）
```

### 4. VAD 移动端优化

**位置**: `static/js/vad.js`

- 移动端使用略高的检测阈值（0.04 vs 0.03）
- 启动时自动恢复挂起的 AudioContext
- 添加移动端友好的错误提示

### 5. CSS 响应式设计

**位置**: `static/css/style.css`

关键媒体查询：

```css
/* 横向模式 */
@media (orientation: landscape) and (max-height: 500px)

/* 触摸设备 */
@media (pointer: coarse)

/* 响应式断点 */
@media (max-width: 600px)   /* 手机 */
@media (max-width: 900px)   /* 平板 */
@media (max-width: 1200px)  /* 桌面 */

/* 安全区域 */
@supports (padding-bottom: env(safe-area-inset-bottom))
```

---

## 已知兼容性问题与解决方案

### 问题 1: iOS Safari 音频无法自动播放

**现象**: TTS 音频在 iOS Safari 上无法播放  
**原因**: iOS 要求音频播放必须由用户手势直接触发  
**解决方案**:
1. 使用 `AudioUnlockManager` 在用户首次交互时解锁
2. 使用 AudioContext + AudioBuffer 方式播放
3. 提供重试机制

**相关代码**: `static/js/tts-stream.js` - `unlockAudio()`, `playWithAudioContext()`

---

### 问题 2: AudioContext 挂起状态

**现象**: 录音或 VAD 功能不工作  
**原因**: 移动端 AudioContext 创建后默认处于 suspended 状态  
**解决方案**:
```javascript
if (this.audioContext.state === 'suspended') {
    await this.audioContext.resume();
}
```

**相关代码**: `static/js/vad.js` - `start()` 方法

---

### 问题 3: 横向模式布局问题

**现象**: 横屏时 UI 元素重叠或显示不完整  
**原因**: 横向模式高度有限，原布局未针对优化  
**解决方案**:
```css
@media (orientation: landscape) and (max-height: 500px) {
    .command-bar { flex-direction: row; gap: 8px; }
    .immersive-mic-btn { width: 60px; height: 60px; }
}
```

**相关代码**: `static/css/style.css` - 横向模式媒体查询

---

### 问题 4: 触摸目标过小

**现象**: 按钮难以点击  
**原因**: 默认尺寸未达到 WCAG 2.1 触摸目标标准（44x44px）  
**解决方案**:
```css
@media (pointer: coarse) {
    .cyber-btn { min-height: 44px; min-width: 44px; }
    .record-orb { width: 56px; height: 56px; }
}
```

**相关代码**: `static/css/style.css` - 触摸设备媒体查询

---

### 问题 5: 刘海屏/安全区域

**现象**: 内容被刘海或底部指示条遮挡  
**原因**: 未处理 safe-area-inset  
**解决方案**:
```html
<meta name="viewport" content="viewport-fit=cover">
```
```css
@supports (padding-bottom: env(safe-area-inset-bottom)) {
    .input-dock {
        padding-bottom: max(16px, env(safe-area-inset-bottom));
    }
}
```

**相关代码**: `static/index.html`, `static/css/style.css`

---

### 问题 6: MediaRecorder 兼容性

**现象**: 某些浏览器不支持 MediaRecorder  
**解决方案**: 使用 `MobileUtils.checkMediaRecorderSupport()` 检测支持情况

**支持情况**:
| 浏览器 | audio/webm | audio/mp4 | audio/wav |
|--------|------------|-----------|-----------|
| Chrome Android | ✓ | ✗ | ✗ |
| Safari iOS 14.3+ | ✗ | ✓ | ✗ |
| Firefox Android | ✓ | ✗ | ✗ |

---

## 测试标准

### 测试设备清单

**必须测试**:
- [ ] iPhone 12+ (iOS 15+) - Safari
- [ ] iPhone SE - Safari（小屏测试）
- [ ] Android 手机 (Android 10+) - Chrome
- [ ] iPad - Safari（平板横向）

**建议测试**:
- [ ] Android 平板 - Chrome
- [ ] Samsung Internet Browser
- [ ] Firefox Mobile

### 测试检查项

#### 音频功能
- [ ] TTS 首次播放正常
- [ ] TTS 连续播放正常
- [ ] 语音录制正常
- [ ] VAD 检测正常
- [ ] 静音后恢复播放正常

#### 布局功能
- [ ] 纵向模式布局正确
- [ ] 横向模式布局正确
- [ ] 方向切换无异常
- [ ] 刘海屏安全区域正确

#### 交互功能
- [ ] 所有按钮可点击（目标 44px+）
- [ ] 滚动流畅
- [ ] 触摸反馈正常
- [ ] 无误触问题

### 自动化测试命令

```bash
# 运行移动端相关单元测试
pytest tests/ -k "mobile" -v

# 使用 Playwright 进行设备模拟测试
npx playwright test --project=mobile
```

---

## 维护指南

### 新增移动端功能检查清单

添加新功能时，确保：

1. **音频相关**
   - [ ] 使用 `AudioUnlockManager` 解锁
   - [ ] 处理 AudioContext suspended 状态
   - [ ] 添加错误处理和重试

2. **UI 相关**
   - [ ] 触摸目标 >= 44x44px
   - [ ] 添加横向模式适配
   - [ ] 考虑安全区域

3. **测试相关**
   - [ ] 真机测试（不仅是模拟器）
   - [ ] 测试横向/纵向切换

### 配置参数

移动端配置集中在 `frontend/core/config.js`:

```javascript
mobile: {
    touchTargetSize: 44,        // 触摸目标最小尺寸
    touchTargetSpacing: 8,      // 触摸目标最小间距
    audioUnlockRequired: true,  // 是否需要音频解锁
    vadThresholds: {
        silenceThreshold: 0.04, // 移动端静音阈值
        speechThreshold: 0.04,  // 移动端语音阈值
    },
    breakpoints: {              // 响应式断点
        mobile: 600,
        tablet: 900,
        desktop: 1200,
    },
    tts: {
        maxRetries: 3,          // 播放重试次数
        retryDelay: 100,        // 重试延迟(ms)
        useAudioContext: true,  // 使用 AudioContext 播放
    },
},
```

### 调试技巧

1. **远程调试 iOS Safari**
   - Mac: Safari > 开发 > [设备名]
   - 需要开启 iPhone 的 Web 检查器

2. **远程调试 Android Chrome**
   - 访问 `chrome://inspect`
   - 开启 USB 调试

3. **模拟移动端**
   - Chrome DevTools > Toggle device toolbar
   - 注意：模拟器无法完全复现真机行为

### 常见问题排查

| 问题 | 排查步骤 |
|------|---------|
| 音频不播放 | 1. 检查控制台错误 2. 确认音频已解锁 3. 检查 AudioContext 状态 |
| 布局错乱 | 1. 检查视口 meta 2. 检查媒体查询 3. 检查安全区域 |
| 触摸不响应 | 1. 检查元素尺寸 2. 检查 z-index 3. 检查事件绑定 |

---

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0 | 2024-01 | 初始版本，完成基础移动端适配 |

---

## 相关文档

- [移动端适配开发规范](../.qoder/rules/mobile-adaptation.md)
- [项目 README](../README.md)
- [部署文档](../DEPLOYMENT.md)
