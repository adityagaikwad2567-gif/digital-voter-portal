/* Digital Voter Services Portal - Main JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // ─── Auto-dismiss flash messages ──────────────────────
    const flashMessages = document.querySelectorAll('.flash-messages .alert');
    flashMessages.forEach(function(msg) {
        setTimeout(function() {
            msg.style.transition = 'opacity 0.5s';
            msg.style.opacity = '0';
            setTimeout(function() { msg.remove(); }, 500);
        }, 5000);
    });

    // ─── Candidate selection for voting ───────────────────
    const candidateCards = document.querySelectorAll('.candidate-select-card');
    candidateCards.forEach(function(card) {
        card.addEventListener('click', function() {
            // Remove selection from all
            candidateCards.forEach(c => c.classList.remove('selected'));
            // Select this one
            this.classList.add('selected');
            const radio = this.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    });

    // ─── Form step navigation ─────────────────────────────
    const stepForms = document.querySelectorAll('.step-form');
    stepForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let valid = true;
            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    field.classList.add('is-invalid');
                    valid = false;
                } else {
                    field.classList.remove('is-invalid');
                }
            });
            if (!valid) {
                e.preventDefault();
                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) firstInvalid.focus();
            }
        });
    });

    // ─── Print voter card ─────────────────────────────────
    const printBtn = document.getElementById('printCard');
    if (printBtn) {
        printBtn.addEventListener('click', function() {
            window.print();
        });
    }

    // ─── Download voter card as image ─────────────────────
    const downloadBtn = document.getElementById('downloadCard');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            alert('Demo card download feature. In production, this would generate a PDF/image.');
        });
    }

    // ─── Confirmation dialogs ─────────────────────────────
    const confirmForms = document.querySelectorAll('form[data-confirm]');
    confirmForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm(this.dataset.confirm || 'Are you sure?')) {
                e.preventDefault();
            }
        });
    });

    // ─── Vote confirmation ────────────────────────────────
    const voteConfirmForm = document.getElementById('voteConfirmForm');
    if (voteConfirmForm) {
        voteConfirmForm.addEventListener('submit', function(e) {
            if (!confirm('WARNING: Once submitted, your vote cannot be changed. Are you sure?')) {
                e.preventDefault();
            }
        });
    }

    // ─── Search tabs ──────────────────────────────────────
    const searchTabs = document.querySelectorAll('.search-tab-btn');
    searchTabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            const target = this.dataset.target;
            document.querySelectorAll('.search-tab-content').forEach(content => {
                content.style.display = 'none';
            });
            document.getElementById(target).style.display = 'block';
            searchTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // ─── Admin sidebar toggle for mobile ──────────────────
    const sidebarToggle = document.getElementById('sidebarToggle');
    const adminSidebar = document.querySelector('.admin-sidebar');
    if (sidebarToggle && adminSidebar) {
        sidebarToggle.addEventListener('click', function() {
            adminSidebar.classList.toggle('d-none');
        });
    }

    // ─── Language selector ────────────────────────────────
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
        langSelect.addEventListener('change', function() {
            document.cookie = `lang=${this.value};path=/;max-age=31536000`;
            location.reload();
        });
    }

    // ─── Chart initialization helpers ─────────────────────
    const chartColors = {
        primary: '#1a3a6b',
        primaryLight: '#2c5299',
        accent: '#e8a838',
        success: '#28a745',
        danger: '#dc3545',
        info: '#17a2b8',
        purple: '#6f42c1',
        pink: '#e83e8c'
    };

    window.chartColors = chartColors;
});
