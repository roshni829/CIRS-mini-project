document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss flash messages after 4 seconds
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(function () {
                if (alert.parentNode) alert.remove();
            }, 300);
        }, 4000);
    });

    // Modal toggle
    var openModalBtn = document.getElementById('showSimilarModal');
    var modalOverlay = document.getElementById('similarModal');
    var closeModalBtns = document.querySelectorAll('.close-modal');

    if (openModalBtn && modalOverlay) {
        openModalBtn.addEventListener('click', function () {
            modalOverlay.classList.add('active');
        });
    }

    closeModalBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var modal = this.closest('.modal-overlay');
            if (modal) modal.classList.remove('active');
        });
    });

    // Close modal on overlay click
    if (modalOverlay) {
        modalOverlay.addEventListener('click', function (e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    }

    // Auto-show modal if the page was loaded with showModal flag
    if (modalOverlay && modalOverlay.classList.contains('active')) {
        // Already shown via server-rendered class
    }

    // ─── Live status polling every 10 seconds ────────────────────────────
    setInterval(function () {
        fetch('/api/my-complaints')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                data.complaints.forEach(function (c) {
                    var statusEl = document.getElementById('status-' + c.id);
                    var countEl = document.getElementById('count-' + c.id);
                    if (statusEl) statusEl.innerText = c.status;
                    if (countEl) countEl.innerText = c.affected_users;
                });
            })
            .catch(function (error) { console.log(error); });
    }, 10000);
});
