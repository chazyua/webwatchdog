document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    function formatDate(dateObj) {
        try {
            let timestamp;
            if (typeof dateObj === 'object' && dateObj !== null) {
                if (dateObj.utc) {
                    timestamp = new Date(dateObj.utc);
                } else if (dateObj.timestamp) {
                    timestamp = new Date(dateObj.timestamp * 1000);
                } else {
                    return 'Unknown date';
                }
            } else if (typeof dateObj === 'string') {
                timestamp = new Date(dateObj);
            } else {
                return 'Unknown date';
            }

            if (isNaN(timestamp.getTime())) {
                return 'Unknown date';
            }

            return new Intl.DateTimeFormat('default', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true,
                timeZoneName: 'short'
            }).format(timestamp);
        } catch (error) {
            return 'Unknown date';
        }
    }

    function updateTimestamps() {
        document.querySelectorAll('.timestamp').forEach(element => {
            const utcTimestamp = element.dataset.utc;
            if (!utcTimestamp || element.textContent === 'Just now') return;

            try {
                const timestampData = JSON.parse(utcTimestamp);
                element.textContent = formatDate(timestampData);
            } catch (e) {
                element.textContent = formatDate(utcTimestamp);
            }
        });
    }

    // Update non-"Just now" timestamps initially
    updateTimestamps();

    // Handle website addition
    const addWebsiteForm = document.getElementById('addWebsiteForm');
    if (addWebsiteForm) {
        addWebsiteForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const url = document.getElementById('websiteUrl').value;

            try {
                const response = await fetch('/api/websites', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    const errorData = await response.json();
                    alert(errorData.error || 'Failed to add website');
                }
            } catch (error) {
                alert('Failed to add website');
            }
        });
    }

    // Handle website checking
    async function checkWebsite(button) {
        const websiteId = button.dataset.websiteId;
        const originalHtml = button.innerHTML;
        const card = button.closest('.website-card');

        button.disabled = true;
        button.innerHTML = '<i data-feather="loader" class="rotating"></i>';
        feather.replace();

        try {
            const response = await fetch(`/api/websites/${websiteId}/check`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();

                // Update status badge
                const statusBadge = card.querySelector('.status-badge');
                if (data.status === 'success') {
                    if (data.has_changed) {
                        statusBadge.innerHTML = '<i data-feather="alert-circle"></i>';
                        statusBadge.classList.add('has-changes');
                    } else {
                        statusBadge.innerHTML = '<i data-feather="check-circle"></i>';
                        statusBadge.classList.remove('has-changes');
                    }
                } else {
                    statusBadge.textContent = data.status;
                }
                statusBadge.className = `status-badge status-${data.status} me-2${data.has_changed ? ' has-changes' : ''}`;

                // Update timestamp
                if (data.last_checked) {
                    card.querySelectorAll('.timestamps .timestamp').forEach(timestamp => {
                        const container = timestamp.closest('.text-muted');
                        if (container && container.textContent.includes('Last checked:')) {
                            timestamp.dataset.utc = JSON.stringify(data.last_checked);
                            timestamp.textContent = 'Just now';
                        }
                    });
                }

                // Re-initialize Feather icons
                feather.replace();

                // Handle change detection UI
                updateChangeDetectionUI(card, data.has_changed);
            } else {
                const errorData = await response.json();
                alert(errorData.error || 'Failed to check website');
            }
        } catch (error) {
            alert('Error checking website. Please try again.');
        } finally {
            button.disabled = false;
            button.innerHTML = originalHtml;
            feather.replace();
        }
    }

    // Helper function to update change detection UI
    function updateChangeDetectionUI(card, hasChanged) {
        const mobileChangeDetected = card.querySelector('.change-detected.d-block');
        const desktopChangeDetected = card.querySelector('.change-detected.d-none');

        if (hasChanged) {
            if (!mobileChangeDetected) {
                const mobileMark = document.createElement('div');
                mobileMark.className = 'change-detected d-block d-md-none';
                mobileMark.textContent = 'Changes detected';
                card.querySelector('.website-info').appendChild(mobileMark);
            }
            if (!desktopChangeDetected) {
                const desktopMark = document.createElement('span');
                desktopMark.className = 'change-detected d-none d-md-inline-flex';
                desktopMark.textContent = 'Changes detected';
                card.querySelector('.card-title').after(desktopMark);
            }
        } else {
            if (mobileChangeDetected) mobileChangeDetected.remove();
            if (desktopChangeDetected) desktopChangeDetected.remove();
        }
    }

    // Handle individual website checking
    document.querySelectorAll('.check-website').forEach(button => {
        button.addEventListener('click', function() {
            checkWebsite(this);
        });
    });

    // Handle website deletion
    document.querySelectorAll('.delete-website').forEach(button => {
        button.addEventListener('click', async function() {
            const websiteId = this.dataset.websiteId;
            const card = this.closest('.website-card');

            try {
                const response = await fetch(`/api/websites/${websiteId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(-10px)';
                    setTimeout(() => card.remove(), 300);
                } else {
                    const errorData = await response.json();
                    alert(errorData.error || 'Failed to delete website');
                }
            } catch (error) {
                alert('Failed to delete website');
            }
        });
    });

    // Handle Check All functionality
    const checkAllButton = document.getElementById('checkAllWebsites');
    if (checkAllButton) {
        checkAllButton.addEventListener('click', async function() {
            this.disabled = true;
            this.innerHTML = '<i data-feather="loader" class="rotating"></i> Checking All...';
            feather.replace();

            const checkButtons = document.querySelectorAll('.check-website');
            for (const button of checkButtons) {
                await checkWebsite(button);
            }

            this.disabled = false;
            this.innerHTML = '<i data-feather="refresh-cw"></i> Check All';
            feather.replace();
        });
    }
});