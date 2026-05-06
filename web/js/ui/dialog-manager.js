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
            console.warn('DialogManager: 模态对话框DOM元素未找到');
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
        if (!this.modalOverlay) {
            console.warn('DialogManager未初始化，使用原生confirm');
            if (confirm(message)) {
                if (onConfirm) onConfirm();
            } else {
                if (onCancel) onCancel();
            }
            return;
        }
        
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
        if (!this.modalOverlay) {
            console.warn('DialogManager未初始化，使用原生alert');
            alert(message);
            if (onClose) onClose();
            return;
        }
        
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
