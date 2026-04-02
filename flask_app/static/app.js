// =============================================================================
// InventoryPro — JavaScript
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initThemeToggle();
    initFlashMessages();
    initDeleteConfirmations();
    initCountUp();
    initNotificationCount();
});

// =============================================================================
// Sidebar Toggle
// =============================================================================

function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleBtn = document.getElementById('sidebarToggle');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (!sidebar) return;

    // Mobile menu
    if (mobileBtn) {
        mobileBtn.addEventListener('click', () => {
            sidebar.classList.add('open');
            overlay.classList.add('active');
        });
    }

    // Close sidebar
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }

    // Desktop toggle
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-collapsed');
        });
    }
}

// =============================================================================
// Theme Toggle
// =============================================================================

function initThemeToggle() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    const html = document.documentElement;
    const saved = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', saved);
    updateThemeIcon(btn, saved);

    btn.addEventListener('click', () => {
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(btn, next);
    });
}

function updateThemeIcon(btn, theme) {
    const icon = btn.querySelector('i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
    }
}

// =============================================================================
// Flash Messages Auto-dismiss
// =============================================================================

function initFlashMessages() {
    const messages = document.querySelectorAll('[data-auto-dismiss]');
    messages.forEach((msg, i) => {
        setTimeout(() => {
            msg.style.transition = 'all 0.4s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(40px)';
            setTimeout(() => msg.remove(), 400);
        }, 4000 + (i * 500));
    });
}

// =============================================================================
// Delete Confirmations
// =============================================================================

function initDeleteConfirmations() {
    document.querySelectorAll('[data-confirm]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const message = form.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

// =============================================================================
// Count-up animation for stats
// =============================================================================

function initCountUp() {
    const counters = document.querySelectorAll('[data-count]');
    counters.forEach(el => {
        const target = parseFloat(el.getAttribute('data-count'));
        const prefix = el.getAttribute('data-prefix') || '';
        const suffix = el.getAttribute('data-suffix') || '';
        const isDecimal = el.hasAttribute('data-decimal');
        const duration = 1200;
        const startTime = performance.now();

        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = target * eased;

            if (isDecimal) {
                el.textContent = prefix + current.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + suffix;
            } else {
                el.textContent = prefix + Math.round(current).toLocaleString() + suffix;
            }

            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }

        requestAnimationFrame(update);
    });
}

// =============================================================================
// Notification count (low stock)
// =============================================================================

function initNotificationCount() {
    const badge = document.getElementById('notifCount');
    if (!badge) return;

    // Count low stock items from data attribute or DOM
    const lowStockItems = document.querySelectorAll('.alert-item');
    const count = lowStockItems.length;
    badge.textContent = count;

    if (count === 0) {
        badge.style.display = 'none';
    }
}

// =============================================================================
// Utility: Confirm delete modal
// =============================================================================

function showDeleteModal(formId) {
    const form = document.getElementById(formId);
    if (form && confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
        form.submit();
    }
}
