/**
 * Lyon 2026 - Door to Door Canvassing App
 * Minimal JavaScript (HTMX handles most interactions)
 */

// ========== File Upload Enhancement ==========

/**
 * Initialize file upload drag and drop
 */
function initFileUpload() {
    const dropZones = document.querySelectorAll('.file-upload-zone');

    dropZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const content = zone.querySelector('.file-upload-content');
        const selected = zone.querySelector('.file-selected');
        const fileName = zone.querySelector('.file-name');

        if (!input) return;

        // Click to upload
        zone.addEventListener('click', (e) => {
            if (e.target !== input && !e.target.closest('.file-remove')) {
                input.click();
            }
        });

        // Drag over
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        // Drag leave
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });

        // Drop
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');

            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                updateFileName(e.dataTransfer.files[0].name);
            }
        });

        // File selected
        input.addEventListener('change', (e) => {
            if (e.target.files.length) {
                updateFileName(e.target.files[0].name);
            }
        });

        function updateFileName(name) {
            if (content) content.style.display = 'none';
            if (selected) selected.style.display = 'flex';
            if (fileName) fileName.textContent = name;
        }

        // Clear file button
        const removeBtn = zone.querySelector('.file-remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                input.value = '';
                if (content) content.style.display = 'flex';
                if (selected) selected.style.display = 'none';
            });
        }
    });
}

// ========== Voting Desk Toggle (Import Page) ==========

function initVotingDeskToggle() {
    const radios = document.querySelectorAll('input[name="desk_choice"]');
    const existingGroup = document.getElementById('existingDeskGroup');
    const newGroup = document.getElementById('newDeskGroup');
    const createNewDesk = document.getElementById('createNewDesk');

    if (!radios.length) return;

    radios.forEach(radio => {
        radio.addEventListener('change', () => {
            const isExisting = document.querySelector('input[value="existing"]').checked;
            if (existingGroup) existingGroup.style.display = isExisting ? 'block' : 'none';
            if (newGroup) newGroup.style.display = isExisting ? 'none' : 'block';
            if (createNewDesk) createNewDesk.value = isExisting ? '' : 'true';
        });
    });
}

// ========== Progress Bar Animation ==========

function animateProgressBars() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const bar = entry.target;
                const width = bar.dataset.width || bar.style.width;
                bar.style.width = '0%';
                requestAnimationFrame(() => {
                    bar.style.width = width;
                });
                observer.unobserve(bar);
            }
        });
    });

    document.querySelectorAll('.progress-fill').forEach(bar => {
        bar.dataset.width = bar.style.width;
        observer.observe(bar);
    });
}

// ========== Keyboard Shortcuts ==========

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Escape to close modals
        if (e.key === 'Escape') {
            const modalContainer = document.getElementById('modal-container');
            if (modalContainer) {
                modalContainer.innerHTML = '';
            }
        }

        // Ctrl+/ to focus search
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
    });
}

// ========== Initialize ==========

document.addEventListener('DOMContentLoaded', () => {
    initFileUpload();
    initVotingDeskToggle();
    animateProgressBars();
    initKeyboardShortcuts();
});

// Re-initialize after HTMX swaps
document.body.addEventListener('htmx:afterSwap', () => {
    animateProgressBars();
});
