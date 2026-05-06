/**
 * 对话框管理器
 */

class DialogManager {
    constructor() {
        this.modalOverlay = null;
        this.modalTitle = null;
        this.modalBody = null;
        this.modalFooter = null;
        this.modalClose = null;
        
        // 延迟初始化，等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }
    
    /**
     * 初始化DOM元素
     */
    init() {
        this.modalOverlay = document.getElementById('modal-overlay');
        this.modalTitle = document.getElementById('modal-title');
        this.modalBody = document.getElementById('modal-body');
        this.modalFooter = document.getElementById('modal-footer');
        this.modalClose = document.getElementById('modal-close');
        
        if (this.modalOverlay && this.modalClose) {
            this.bindEvents();
            console.log('DialogManager 初始化成功');
        } else {
            // 静默处理，使用原生对话框作为降级方案
            console.info('DialogManager: 使用原生对话框模式');
        }
    }
    
    bindEvents() {
        this.modalClose.addEventListener('click', () => this.close());
        this.modalOverlay.addEventListener('click', (e) => {
            if (e.target === this.modalOverlay) {
                this.close();
            }
        });
    }
    
    /**
     * 显示确认对话框
     */
    showConfirm(title, message, onConfirm, onCancel, confirmText = '确认', cancelText = '取消') {
        // 优先尝试使用自定义模态对话框
        const customModal = this.findCustomModal();
        if (customModal) {
            this.showCustomConfirm(customModal, title, message, onConfirm, onCancel, confirmText, cancelText);
            return;
        }
        
        // 降级到全局modal
        if (this.modalOverlay) {
            this.showGlobalConfirm(title, message, onConfirm, onCancel, confirmText, cancelText);
            return;
        }
        
        // 最终降级到原生confirm
        console.info('使用原生confirm对话框');
        if (confirm(message)) {
            if (onConfirm) onConfirm();
        } else {
            if (onCancel) onCancel();
        }
    }
    
    /**
     * 查找可用的自定义模态对话框
     */
    findCustomModal() {
        // 查找所有可能的模态对话框
        const modalIds = ['settings-modal', 'chat-modal', 'move-history-modal', 'help-modal'];
        for (const id of modalIds) {
            const modal = document.getElementById(id);
            if (modal) {
                return { element: modal, id: id };
            }
        }
        return null;
    }
    
    /**
     * 显示自定义确认对话框
     */
    showCustomConfirm(modalInfo, title, message, onConfirm, onCancel, confirmText, cancelText) {
        // 创建一个临时的确认对话框
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.zIndex = '2000';
        
        overlay.innerHTML = `
            <div class="modal-dialog" style="max-width: 400px;">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body" style="padding: 20px; line-height: 1.6;">
                    ${message}
                </div>
                <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid #e0e0e0; display: flex; justify-content: flex-end; gap: 10px;">
                    <button class="btn-secondary" id="temp-dialog-cancel" style="padding: 8px 16px; border: none; border-radius: 6px; background: #f0f0f0; cursor: pointer; font-size: 14px;">${cancelText}</button>
                    <button class="btn-primary" id="temp-dialog-confirm" style="padding: 8px 16px; border: none; border-radius: 6px; background: #2f54eb; color: white; cursor: pointer; font-size: 14px;">${confirmText}</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 绑定事件
        overlay.querySelector('#temp-dialog-confirm').addEventListener('click', () => {
            overlay.remove();
            if (onConfirm) onConfirm();
        });
        
        overlay.querySelector('#temp-dialog-cancel').addEventListener('click', () => {
            overlay.remove();
            if (onCancel) onCancel();
        });
        
        // 点击背景关闭
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                if (onCancel) onCancel();
            }
        });
    }
    
    /**
     * 显示全局确认对话框
     */
    showGlobalConfirm(title, message, onConfirm, onCancel, confirmText, cancelText) {
        this.modalTitle.textContent = title;
        // 直接设置innerHTML，不进行额外包装
        this.modalBody.innerHTML = message;
        this.modalFooter.innerHTML = `
            <button class="btn-secondary" id="dialog-cancel">${cancelText}</button>
            <button class="btn-primary" id="dialog-confirm">${confirmText}</button>
        `;
        
        document.getElementById('dialog-confirm').addEventListener('click', () => {
            this.close();
            if (onConfirm) onConfirm();
        });
        
        document.getElementById('dialog-cancel').addEventListener('click', () => {
            this.close();
            if (onCancel) onCancel();
        });
        
        this.open();
    }
    
    /**
     * 显示信息对话框
     */
    showInfo(title, message, onClose) {
        // 优先尝试使用自定义模态对话框
        const customModal = this.findCustomModal();
        if (customModal) {
            this.showCustomInfo(customModal, title, message, onClose);
            return;
        }
        
        // 降级到全局modal
        if (this.modalOverlay) {
            this.showGlobalInfo(title, message, onClose);
            return;
        }
        
        // 最终降级到原生alert
        console.info('使用原生alert对话框');
        alert(message);
        if (onClose) onClose();
    }
    
    /**
     * 显示自定义信息对话框
     */
    showCustomInfo(modalInfo, title, message, onClose) {
        // 创建一个临时的信息对话框
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.zIndex = '2000';
        
        overlay.innerHTML = `
            <div class="modal-dialog" style="max-width: 400px;">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body" style="padding: 20px; line-height: 1.6;">
                    ${message}
                </div>
                <div class="modal-footer" style="padding: 16px 20px; border-top: 1px solid #e0e0e0; display: flex; justify-content: flex-end;">
                    <button class="btn-primary" id="temp-dialog-ok" style="padding: 8px 16px; border: none; border-radius: 6px; background: #2f54eb; color: white; cursor: pointer; font-size: 14px;">确定</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 绑定事件
        overlay.querySelector('#temp-dialog-ok').addEventListener('click', () => {
            overlay.remove();
            if (onClose) onClose();
        });
        
        // 点击背景关闭
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                if (onClose) onClose();
            }
        });
    }
    
    /**
     * 显示全局信息对话框
     */
    showGlobalInfo(title, message, onClose) {
        this.modalTitle.textContent = title;
        // 直接设置innerHTML，不进行额外包装
        this.modalBody.innerHTML = message;
        this.modalFooter.innerHTML = `
            <button class="btn-primary" id="dialog-ok">确定</button>
        `;
        
        document.getElementById('dialog-ok').addEventListener('click', () => {
            this.close();
            if (onClose) onClose();
        });
        
        this.open();
    }
    
    /**
     * 显示错误对话框
     */
    showError(message, onClose) {
        this.showInfo('错误', message, onClose);
    }
    
    /**
     * 显示自定义内容
     * @param {string} title - 对话框标题
     * @param {string} htmlContent - 自定义HTML内容
     * @param {string} footerHtml - 底部按钮HTML
     * @param {Object} callbacks - 回调函数对象
     * @param {Function} [callbacks.onMount] - 对话框挂载后的回调函数，接收modalBody参数
     */
    showCustom(title, htmlContent, footerHtml, callbacks = {}) {
        this.modalTitle.textContent = title;
        this.modalBody.innerHTML = htmlContent;
        this.modalFooter.innerHTML = footerHtml;
        
        // 执行回调绑定事件
        if (callbacks.onMount) {
            callbacks.onMount(this.modalBody);
        }
        
        this.open();
    }
    
    /**
     * 打开对话框
     */
    open() {
        if (this.modalOverlay) {
            this.modalOverlay.classList.remove('hidden');
        }
    }
    
    /**
     * 关闭对话框
     */
    close() {
        if (this.modalOverlay) {
            this.modalOverlay.classList.add('hidden');
        }
    }
}

// 全局实例
window.dialogManager = new DialogManager();
