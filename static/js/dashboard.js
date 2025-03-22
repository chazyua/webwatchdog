// Helper function to convert cron expression to readable days
function cronDaysToLabels(cronExpression) {
    if (!cronExpression) return [];
    
    // Parse the cron expression
    const parts = cronExpression.split(' ');
    if (parts.length !== 5) return [];
    
    const dayOfWeek = parts[4]; // Day of week (0-6, Sunday to Saturday)
    
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const selectedDays = [];
    
    // Handle special cases
    if (dayOfWeek === '*') {
        return dayNames; // All days selected
    }
    
    // Handle comma-separated values
    if (dayOfWeek.includes(',')) {
        const days = dayOfWeek.split(',');
        days.forEach(day => {
            const dayIndex = parseInt(day);
            if (!isNaN(dayIndex) && dayIndex >= 0 && dayIndex <= 6) {
                selectedDays.push(dayNames[dayIndex]);
            }
        });
        return selectedDays;
    }
    
    // Handle single day
    const dayIndex = parseInt(dayOfWeek);
    if (!isNaN(dayIndex) && dayIndex >= 0 && dayIndex <= 6) {
        return [dayNames[dayIndex]];
    }
    
    return [];
}

// Function to format cron schedule labels with day names
function formatCronScheduleLabels() {
    const scheduleElements = document.querySelectorAll('.cron-schedule');
    
    scheduleElements.forEach(element => {
        const cronExpression = element.textContent?.trim() || element.value;
        if (!cronExpression) return;
        
        const days = cronDaysToLabels(cronExpression);
        
        // Create day labels if they don't exist
        const daysContainer = document.createElement('div');
        daysContainer.className = 'days-container mt-1';
        
        days.forEach(day => {
            const daySpan = document.createElement('span');
            daySpan.className = 'badge bg-light text-dark me-1';
            daySpan.textContent = day;
            daysContainer.appendChild(daySpan);
        });
        
        // Add days container after the cron expression
        const parent = element.parentElement;
        
        // Check if days container already exists
        const existingDaysContainer = parent.querySelector('.days-container');
        if (existingDaysContainer) {
            parent.removeChild(existingDaysContainer);
        }
        
        // Add the new days container
        if (days.length > 0) {
            parent.appendChild(daysContainer);
        }
    });
}

// Function to initialize schedule toggles in sidebar
function initializeScheduleToggles() {
    const scheduleToggles = document.querySelectorAll('.schedule-toggle input[type="checkbox"]');
    
    scheduleToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const scheduleId = this.dataset.scheduleId;
            const scheduleFields = document.querySelectorAll(`.schedule-fields-${scheduleId}`);
            
            scheduleFields.forEach(field => {
                field.disabled = !this.checked;
                if (this.checked) {
                    field.classList.remove('opacity-50');
                } else {
                    field.classList.add('opacity-50');
                }
            });
        });
        
        // Initialize state
        toggle.dispatchEvent(new Event('change'));
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();
    
    // Process toast messages from HTML data element (direct approach)
    const toastDataElement = document.getElementById('toast-message-data');
    
    if (toastDataElement) {
        const message = toastDataElement.dataset.message;
        const type = toastDataElement.dataset.type || 'info';
        
        console.log("Found toast data in HTML:", message, type);
        
        if (message) {
            // Show toast with a slight delay
            window.setTimeout(function() {
                showToast(message, type);
                
                // Remove the data element to prevent showing again on page refresh
                toastDataElement.remove();
            }, 300); // Slight delay to ensure the toast system is ready
        }
    }
    
    // Set up scheduler debug modal data loading when opened
    const schedulerDebugModal = document.getElementById('schedulerDebugModal');
    if (schedulerDebugModal) {
        schedulerDebugModal.addEventListener('shown.bs.modal', function() {
            loadSchedulerDebugInfo();
        });
    }
    
    // Toast notification system
    // Make showToast function available globally for other pages
    window.showToast = function(message, type = 'info') {
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="toast-icon" data-feather="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'}"></i>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" aria-label="Close">×</button>
        `;
        
        // Add to DOM
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
            container.appendChild(toast);
        } else {
            toastContainer.appendChild(toast);
        }
        
        // Initialize Feather icons in the toast
        feather.replace();
        
        // Add show class after a brief delay (for animation)
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Set up auto-removal after exactly 4 seconds
        // This is the standard duration for all toasts in the application
        const removeTimeout = setTimeout(() => {
            removeToast(toast);
        }, 4000);
        
        // Set up manual close button
        const closeButton = toast.querySelector('.toast-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                clearTimeout(removeTimeout);
                removeToast(toast);
            });
        }
    }
    
    // Helper function to remove toast with animation
    function removeToast(toast) {
        toast.classList.remove('show');
        toast.classList.add('hiding');
        setTimeout(() => {
            toast.remove();
            
            // Check if toast container is empty and remove it if so
            const container = document.getElementById('toast-container');
            if (container && !container.hasChildNodes()) {
                container.remove();
            }
        }, 300); // Exact 300ms animation duration as specified
    }
    
    // This line is now redundant since we've made showToast global directly
    // window.showToast = showToast;
    
    // Get CSRF token for API requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    
    // Add CSRF token to all fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        // Only add the CSRF token to same-origin POST/DELETE/PUT requests
        if (
            (url.startsWith('/') || url.startsWith(window.location.origin)) && 
            (!options.method || ['POST', 'DELETE', 'PUT'].includes(options.method))
        ) {
            options = options || {};
            options.headers = options.headers || {};
            
            if (!options.headers['X-CSRFToken'] && !options.headers['x-csrftoken']) {
                options.headers['X-CSRFToken'] = csrfToken;
            }
        }
        
        return originalFetch(url, options);
    };
    
    // Create Telegram warning modal if it doesn't exist
    if (!document.getElementById('telegramWarningModal')) {
        const modalHTML = `
        <div class="modal fade" id="telegramWarningModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title"><i data-feather="alert-triangle" class="me-2"></i> Telegram Notifications Not Set Up</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p id="telegramWarningMessage"></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <a href="#" class="btn btn-primary" id="telegramSettingsLink">Go to Settings</a>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHTML;
        document.body.appendChild(modalContainer.firstElementChild);
    }
    
    // Initialize schedule toggles in sidebar
    initializeScheduleToggles();
    
    // Add day labels to cron schedules
    formatCronScheduleLabels();

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

            // Use US/Pacific timezone for displaying dates to maintain consistency with server
            // This ensures users see times in the same timezone as the scheduler
            return new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true,
                timeZone: 'America/Los_Angeles',
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
    
    // Function to show Telegram warning modal
    function showTelegramWarningModal(message, redirectUrl) {
        const modal = document.getElementById('telegramWarningModal');
        const messageEl = document.getElementById('telegramWarningMessage');
        const linkEl = document.getElementById('telegramSettingsLink');
        
        if (modal && messageEl && linkEl) {
            messageEl.textContent = message;
            linkEl.href = redirectUrl;
            
            // Initialize modal and show it
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            // Reinitialize Feather icons in the modal
            feather.replace();
        } else {
            // Fallback to alert if modal elements aren't found
            showToast(message, 'error');
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1000);
        }
    }

    // Handle website addition with smooth animation
    const addWebsiteForm = document.getElementById('addWebsiteForm');
    const addWebsiteModal = document.getElementById('addWebsiteModal');
    const websiteUrlInput = document.getElementById('websiteUrl');
    
    // Auto-focus the URL input when the modal is opened
    if (addWebsiteModal) {
        addWebsiteModal.addEventListener('shown.bs.modal', function() {
            if (websiteUrlInput) {
                websiteUrlInput.focus();
                // Clear any existing value
                websiteUrlInput.value = '';
            }
        });
    }
    
    if (addWebsiteForm && addWebsiteModal) {
        addWebsiteForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            let url = websiteUrlInput.value.trim();
            
            // Add https:// prefix if not present
            if (url && !url.startsWith('http://') && !url.startsWith('https://')) {
                url = 'https://' + url;
            }
            
            const submitButton = addWebsiteForm.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            
            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<i data-feather="loader" class="rotating"></i> Adding...';
            feather.replace();

            try {
                const response = await fetch('/api/websites', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                if (response.ok) {
                    const data = await response.json();
                    
                    // Hide the modal
                    const bsModal = bootstrap.Modal.getInstance(addWebsiteModal);
                    bsModal.hide();
                    
                    // Show success message
                    showToast('Website added successfully', 'success');
                    
                    // Create a new website card right away with animation
                    const newWebsite = {
                        id: data.id || crypto.randomUUID(),
                        url: data.url || url,
                        status: data.status || 'pending',
                        created_at: data.created_at || new Date().toISOString(),
                        last_checked: data.last_checked || null
                    };
                    
                    // Create a new website card immediately
                    createNewWebsiteCard(newWebsite);
                } else {
                    const errorData = await response.json();
                    showToast(errorData.error || 'Failed to add website', 'error');
                }
            } catch (error) {
                showToast('Failed to add website', 'error');
            } finally {
                // Reset form and button
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
                feather.replace();
                document.getElementById('websiteUrl').value = '';
            }
        });
    }
    
    // Function to create a new website card with animation
    function createNewWebsiteCard(website) {
        const dashboardContainer = document.querySelector('.website-cards-container');
        if (!dashboardContainer) {
            console.error("Dashboard container not found");
            return;
        }
        
        // Create column wrapper (matches dashboard.html structure)
        const colWrapper = document.createElement('div');
        colWrapper.className = 'col-12 mb-2';
        
        // Create the card element
        const cardElement = document.createElement('div');
        cardElement.className = 'card website-card new-card';
        cardElement.innerHTML = `
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="website-info">
                        <div class="d-flex align-items-center mb-2 mb-md-0">
                            <span class="status-badge status-${website.status || 'pending'} me-2">
                                ${website.status === 'success' ? '<i data-feather="check-circle"></i>' : website.status || 'pending'}
                            </span>
                            <h5 class="card-title text-truncate mb-0 me-2">${website.url.replace('https://', '')}</h5>
                        </div>
                        <div class="timestamps d-block d-md-none small">
                            <div class="text-muted">
                                Last checked: <span class="timestamp" data-utc='${JSON.stringify({utc: website.last_checked || null})}'>
                                    ${website.last_checked ? 'Just now' : 'Never'}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="d-flex align-items-start">
                        <div class="timestamps text-end me-3 d-none d-md-block">
                            <div class="text-muted">
                                Last checked: <span class="timestamp" data-utc='${JSON.stringify({utc: website.last_checked || null})}'>
                                    ${website.last_checked ? 'Just now' : 'Never'}
                                </span>
                            </div>
                        </div>
                        <div class="card-actions">
                            <a href="${website.url}" target="_blank" class="btn btn-sm btn-secondary">
                                <i data-feather="external-link"></i>
                            </a>
                            <button class="btn btn-sm btn-primary check-website" data-website-id="${website.id}">
                                <i data-feather="refresh-cw"></i>
                            </button>
                            <button class="btn btn-sm btn-danger delete-website" data-website-id="${website.id}">
                                <i data-feather="trash-2"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Add card to column wrapper
        colWrapper.appendChild(cardElement);
        
        // Set initial styles for animation
        colWrapper.style.opacity = '0';
        colWrapper.style.transform = 'translateY(20px)';
        
        // Add to DOM at the beginning of the list
        dashboardContainer.prepend(colWrapper);
        
        // Initialize feather icons
        feather.replace();
        
        // Add event listeners to the new card's buttons
        const checkButton = cardElement.querySelector('.check-website');
        if (checkButton) {
            checkButton.addEventListener('click', function() {
                checkWebsite(this);
            });
        }
        
        const deleteButton = cardElement.querySelector('.delete-website');
        if (deleteButton) {
            deleteButton.addEventListener('click', async function() {
                const websiteId = this.dataset.websiteId;
                const card = this.closest('.website-card');
                const cardWrapper = card.parentElement; // Get the column wrapper

                try {
                    const response = await fetch(`/api/websites/${websiteId}`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        cardWrapper.style.opacity = '0';
                        cardWrapper.style.transform = 'translateY(-10px)';
                        setTimeout(() => cardWrapper.remove(), 300); // 300ms animation as per our standards
                    } else {
                        const errorData = await response.json();
                        showToast(errorData.error || 'Failed to delete website', 'error');
                    }
                } catch (error) {
                    showToast('Failed to delete website', 'error');
                }
            });
        }
        
        // Trigger animation
        setTimeout(() => {
            colWrapper.style.opacity = '1';
            colWrapper.style.transform = 'translateY(0)';
        }, 10);
    }

    // Handle website checking
    async function checkWebsite(button) {
        const websiteId = button.dataset.websiteId;
        const originalHtml = button.innerHTML;
        const card = button.closest('.website-card');

        // Disable button and show processing state
        button.disabled = true;
        card.classList.add('processing');
        button.innerHTML = '<i data-feather="loader" class="rotating"></i>';
        feather.replace();

        try {
            const response = await fetch(`/api/websites/${websiteId}/check`, {
                method: 'POST'
            });

            if (response.ok) {
                const data = await response.json();
                
                // Show success toast
                if (data.has_changed) {
                    showToast('Website checked - Changes detected!', 'success');
                } else {
                    showToast('Website checked successfully', 'success');
                }

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
                
                // Apply highlight animation to show update
                card.classList.add('updated');
                setTimeout(() => {
                    card.classList.remove('updated');
                }, 2000); // Keep 2 seconds for website check animation as this is a special case
            } else {
                const errorData = await response.json();
                
                // Check if this is a Telegram chat ID warning
                if (errorData.type === 'warning' && errorData.error === 'Telegram chat ID not configured') {
                    // Show a modal with the warning and a link to settings
                    showTelegramWarningModal(errorData.message, errorData.redirect);
                } else {
                    // Standard error handling
                    showToast(errorData.error || 'Failed to check website', 'error');
                }
            }
        } catch (error) {
            showToast('Error checking website. Please try again.', 'error');
        } finally {
            // Reset the button and card state
            button.disabled = false;
            card.classList.remove('processing');
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
            const cardWrapper = card.parentElement; // Get the column wrapper

            try {
                const response = await fetch(`/api/websites/${websiteId}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    // Show success toast
                    showToast('Website deleted successfully', 'success');
                    
                    // Remove with animation
                    cardWrapper.style.opacity = '0';
                    cardWrapper.style.transform = 'translateY(-10px)';
                    setTimeout(() => cardWrapper.remove(), 300); // 300ms animation as per our standards
                } else {
                    const errorData = await response.json();
                    showToast(errorData.error || 'Failed to delete website', 'error');
                }
            } catch (error) {
                showToast('Failed to delete website', 'error');
            }
        });
    });

    // Handle Check All functionality with visual feedback
    const checkAllButton = document.getElementById('checkAllWebsites');
    if (checkAllButton) {
        checkAllButton.addEventListener('click', async function() {
            this.disabled = true;
            this.innerHTML = '<i data-feather="loader" class="rotating"></i>';
            feather.replace();
            
            // Visual feedback - add processing class sequentially to all website cards
            const allCards = document.querySelectorAll('.website-card');
            // Apply staggered animations to website cards
            allCards.forEach((card, index) => {
                setTimeout(() => {
                    card.classList.add('processing');
                    const checkButton = card.querySelector('.check-website');
                    if (checkButton) {
                        checkButton.disabled = true;
                        checkButton.innerHTML = '<i data-feather="loader" class="rotating"></i>';
                        feather.replace();
                    }
                }, index * 100); // 100ms delay between each card
            });

            try {
                // First check if user has configured Telegram chat ID
                const response = await fetch('/api/check-all', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    // If successful, get the data from the response
                    const data = await response.json();
                    
                    // Update each website card with new data
                    if (data.websites && Array.isArray(data.websites)) {
                        // Update each website's status with staggered animations
                        data.websites.forEach((websiteData, index) => {
                            // Add sequential timing to updates for visual effect
                            setTimeout(() => {
                                updateWebsiteCardWithData(websiteData);
                            }, index * 200); // 200ms delay between each card update
                        });
                    } else {
                        // Fallback to page reload if expected data format isn't received
                        window.location.reload();
                    }
                } else {
                    const errorData = await response.json();
                    
                    // Check if this is a Telegram chat ID warning
                    if (errorData.type === 'warning' && errorData.error === 'Telegram chat ID not configured') {
                        // Show a modal with the warning and a link to settings
                        showTelegramWarningModal(errorData.message, errorData.redirect);
                    } else {
                        // Standard error handling
                        showToast(errorData.error || 'Failed to check websites', 'error');
                    }
                }
            } catch (error) {
                showToast('Error checking websites. Please try again.', 'error');
            } finally {
                // Reset all website cards sequentially
                allCards.forEach((card, index) => {
                    setTimeout(() => {
                        card.classList.remove('processing');
                        const checkButton = card.querySelector('.check-website');
                        if (checkButton) {
                            checkButton.disabled = false;
                            checkButton.innerHTML = '<i data-feather="refresh-cw"></i>';
                            feather.replace();
                        }
                    }, index * 100); // 100ms delay between each card reset
                });
                
                // Reset the Check All button
                this.disabled = false;
                this.innerHTML = '<i data-feather="refresh-cw"></i>';
                feather.replace();
            }
        });
    }
    
    // We've removed the debug button from the top navigation as requested
    
    // Function to load scheduler debug info
    // Make loadSchedulerDebugInfo available globally
    window.loadSchedulerDebugInfo = async function() {
        try {
            const schedulerInfo = document.getElementById('scheduler-info');
            const userSchedules = document.getElementById('user-schedules');
            const schedulerJobs = document.getElementById('scheduler-jobs');
            
            if (!schedulerInfo || !userSchedules || !schedulerJobs) return;
            
            // Show loading indicators
            schedulerInfo.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading...</div>';
            userSchedules.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading...</div>';
            schedulerJobs.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading...</div>';
            
            // Fetch scheduler debug info
            const response = await fetch('/debug/scheduler');
            const data = await response.json();
            
            // Check for admin access denied
            if (response.status === 403) {
                // Show access denied message
                schedulerInfo.innerHTML = `<div class="alert alert-danger">${data.message || 'Access denied. Admin privileges required.'}</div>`;
                userSchedules.innerHTML = `<div class="alert alert-warning">You must be logged in as an admin user to access this feature.</div>`;
                schedulerJobs.innerHTML = '';
                
                // Hide refresh button
                const refreshBtn = document.getElementById('refreshSchedulerInfo');
                if (refreshBtn) {
                    refreshBtn.style.display = 'none';
                }
                return;
            }
            
            if (response.ok) {
                
                // Format scheduler info
                let schedulerHtml = `
                    <dl class="row mb-0">
                        <dt class="col-sm-4">Status:</dt>
                        <dd class="col-sm-8">${data.scheduler_info.running ? '<span class="text-success">Running</span>' : '<span class="text-danger">Stopped</span>'}</dd>
                        
                        <dt class="col-sm-4">Timezone:</dt>
                        <dd class="col-sm-8">${data.scheduler_info.timezone_name || data.scheduler_info.timezone}</dd>
                        
                        <dt class="col-sm-4">Server Time:</dt>
                        <dd class="col-sm-8">${data.scheduler_info.server_time}</dd>
                        
                        <dt class="col-sm-4">Pacific Time:</dt>
                        <dd class="col-sm-8">${data.scheduler_info.pacific_time || data.scheduler_info.scheduler_time}</dd>
                        
                        <dt class="col-sm-4">Scheduler Time:</dt>
                        <dd class="col-sm-8">${data.scheduler_info.scheduler_time}</dd>
                    </dl>
                `;
                schedulerInfo.innerHTML = schedulerHtml;
                
                // Format user schedules
                if (data.user_info.schedules.length === 0) {
                    userSchedules.innerHTML = '<div class="text-center text-muted">No schedules configured</div>';
                } else {
                    let schedulesHtml = '<ul class="list-group">';
                    data.user_info.schedules.forEach(schedule => {
                        schedulesHtml += `
                            <li class="list-group-item">
                                <strong>Schedule ${schedule.id}:</strong> ${schedule.cron}
                            </li>
                        `;
                    });
                    schedulesHtml += '</ul>';
                    userSchedules.innerHTML = schedulesHtml;
                }
                
                // Format jobs
                if (data.jobs.length === 0) {
                    schedulerJobs.innerHTML = '<div class="text-center text-muted">No jobs scheduled</div>';
                } else {
                    let jobsHtml = '<div class="table-responsive"><table class="table table-sm table-hover">';
                    jobsHtml += `
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Next Run Time</th>
                                <th>Trigger</th>
                            </tr>
                        </thead>
                        <tbody>
                    `;
                    
                    data.jobs.forEach(job => {
                        const isUserJob = job.is_user_job ? 'table-info' : '';
                        jobsHtml += `
                            <tr class="${isUserJob}">
                                <td>${job.name}</td>
                                <td>${job.next_run_time}</td>
                                <td>${job.trigger}</td>
                            </tr>
                        `;
                    });
                    
                    jobsHtml += '</tbody></table></div>';
                    schedulerJobs.innerHTML = jobsHtml;
                }
                
                // Add refresh button handler
                const refreshBtn = document.getElementById('refreshSchedulerInfo');
                if (refreshBtn) {
                    refreshBtn.addEventListener('click', loadSchedulerDebugInfo);
                }
                
            } else {
                const error = await response.json();
                schedulerInfo.innerHTML = `<div class="alert alert-danger">${error.message || 'Failed to load scheduler information'}</div>`;
                userSchedules.innerHTML = '';
                schedulerJobs.innerHTML = '';
            }
        } catch (error) {
            console.error('Error loading scheduler debug info:', error);
            const schedulerInfo = document.getElementById('scheduler-info');
            if (schedulerInfo) {
                schedulerInfo.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            }
        }
    }
    
    // Add click handler for the Run Scheduled Checks button
    const runScheduledChecksBtn = document.getElementById('runScheduledChecks');
    if (runScheduledChecksBtn) {
        runScheduledChecksBtn.addEventListener('click', async function() {
            try {
                // Disable button to prevent multiple clicks
                this.disabled = true;
                
                // Show loading state
                const originalHTML = this.innerHTML;
                this.innerHTML = '<i data-feather="loader" class="rotating"></i> Running...';
                feather.replace();
                
                // Visual feedback - add processing class to all website cards
                const allCards = document.querySelectorAll('.website-card');
                allCards.forEach((card, index) => {
                    setTimeout(() => {
                        card.classList.add('processing');
                    }, index * 50); // Staggered animation
                });
                
                // Call the debug endpoint to run scheduled checks
                const response = await fetch('/debug/run_checks_now', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showToast(data.message || 'Scheduled checks running', 'success');
                    
                    // Log debug info
                    console.log('Scheduled checks triggered:', data);
                    
                    // Refresh the page after 3 seconds to show updated results
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else if (response.status === 403) {
                    // Admin access denied
                    showToast(data.message || 'Access denied. Admin privileges required.', 'error');
                } else {
                    showToast(data.message || 'Failed to run scheduled checks', 'error');
                }
            } catch (error) {
                console.error('Error running scheduled checks:', error);
                showToast('Error: ' + error.message, 'error');
            } finally {
                // Reset button after 2 seconds regardless of outcome
                setTimeout(() => {
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                    feather.replace(); // Re-initialize the feather icons
                }, 2000);
                
                // Reset the cards
                allCards.forEach((card, index) => {
                    setTimeout(() => {
                        card.classList.remove('processing');
                    }, index * 50); // Staggered animation
                });
            }
        });
    }
    
    // Helper function to update a website card with new data
    function updateWebsiteCardWithData(websiteData) {
        if (!websiteData || !websiteData.id) return;
        
        const card = document.querySelector(`.website-card .check-website[data-website-id="${websiteData.id}"]`)?.closest('.website-card');
        if (!card) return;
        
        // Update status badge
        const statusBadge = card.querySelector('.status-badge');
        if (statusBadge) {
            if (websiteData.status === 'success') {
                if (websiteData.has_changed) {
                    statusBadge.innerHTML = '<i data-feather="alert-circle"></i>';
                    statusBadge.classList.add('has-changes');
                } else {
                    statusBadge.innerHTML = '<i data-feather="check-circle"></i>';
                    statusBadge.classList.remove('has-changes');
                }
            } else {
                statusBadge.textContent = websiteData.status || 'pending';
            }
            statusBadge.className = `status-badge status-${websiteData.status || 'pending'} me-2${websiteData.has_changed ? ' has-changes' : ''}`;
        }
        
        // Update timestamp
        if (websiteData.last_checked) {
            card.querySelectorAll('.timestamps .timestamp').forEach(timestamp => {
                const container = timestamp.closest('.text-muted');
                if (container && container.textContent.includes('Last checked:')) {
                    timestamp.dataset.utc = JSON.stringify(websiteData.last_checked);
                    timestamp.textContent = 'Just now';
                }
            });
        }
        
        // Handle change detection UI
        updateChangeDetectionUI(card, websiteData.has_changed);
        
        // Re-initialize Feather icons
        feather.replace();
        
        // Apply a highlight animation for 2 seconds as requested
        card.classList.add('updated');
        setTimeout(() => {
            card.classList.remove('updated');
        }, 2000); // Using 2 seconds for animation as requested
    }
});