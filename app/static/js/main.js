// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('PenVault application initialized');
    
    // Initialize all components
    initializeFlashMessages();
    initializeFormValidation();
    initializeTooltips();
    initializeReplyButtons();
    initializeThemeManager();
    initializeAccessibility();
    initializePerformanceOptimizations();
    initializeInteractiveElements();
});

// Enhanced flash message management with better accessibility
function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message, .alert');
    
    flashMessages.forEach(message => {
        // Add ARIA attributes for better accessibility
        message.setAttribute('role', 'alert');
        message.setAttribute('aria-live', 'polite');
        
        // Auto-hide with smooth animation
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            message.style.transition = 'all 0.3s ease-out';
            
            setTimeout(() => {
                message.style.display = 'none';
                // Announce removal for screen readers
                announceToScreenReader('Flash message dismissed');
            }, 300);
        }, 5000);
        
        // Add dismiss functionality
        const dismissBtn = message.querySelector('.btn-close, .close');
        if (dismissBtn) {
            dismissBtn.addEventListener('click', function() {
                message.style.opacity = '0';
                message.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    message.style.display = 'none';
                    announceToScreenReader('Flash message dismissed');
                }, 300);
            });
        }
    });
}

// Enhanced form validation with better UX
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            let firstInvalidField = null;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Add error message if not exists
                    if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('invalid-feedback')) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'invalid-feedback';
                        errorDiv.textContent = 'This field is required.';
                        field.parentNode.appendChild(errorDiv);
                    }
                    
                    if (!firstInvalidField) {
                        firstInvalidField = field;
                    }
                } else {
                    field.classList.remove('is-invalid');
                    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
                    if (errorDiv) {
                        errorDiv.remove();
                    }
                }
            });

            if (!isValid) {
                event.preventDefault();
                
                // Focus first invalid field
                if (firstInvalidField) {
                    firstInvalidField.focus();
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Show error toast
                showToast('Please fill in all required fields.', 'error');
                return false;
            }
            
            // Add loading state to form
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    validateField(this);
                }
            });
        });
    });
}

// Enhanced field validation
function validateField(field) {
    const value = field.value.trim();
    const isRequired = field.hasAttribute('required');
    
    if (isRequired && !value) {
        field.classList.add('is-invalid');
        showFieldError(field, 'This field is required.');
        return false;
    }
    
    // Email validation
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            field.classList.add('is-invalid');
            showFieldError(field, 'Please enter a valid email address.');
            return false;
        }
    }
    
    // Password validation
    if (field.type === 'password' && value) {
        if (value.length < 8) {
            field.classList.add('is-invalid');
            showFieldError(field, 'Password must be at least 8 characters long.');
            return false;
        }
    }
    
    field.classList.remove('is-invalid');
    removeFieldError(field);
    return true;
}

// Enhanced error display
function showFieldError(field, message) {
    removeFieldError(field);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    field.parentNode.appendChild(errorDiv);
}

function removeFieldError(field) {
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Enhanced tooltip initialization
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover focus',
            placement: 'top',
            animation: true
        });
    });
}

// Enhanced reply button functionality
function initializeReplyButtons() {
    document.querySelectorAll('.reply-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.getAttribute('data-comment-id');
            const replyForm = document.getElementById('replyForm' + commentId);
            
            if (replyForm) {
                const isVisible = replyForm.style.display !== 'none';
                
                // Hide all other reply forms first
                document.querySelectorAll('.reply-form').forEach(form => {
                    form.style.display = 'none';
                });
                
                // Toggle current form
                replyForm.style.display = isVisible ? 'none' : 'block';
                
                if (!isVisible) {
                    // Focus on textarea when showing
                    const textarea = replyForm.querySelector('textarea');
                    if (textarea) {
                        setTimeout(() => textarea.focus(), 100);
                    }
                    
                    // Announce for screen readers
                    announceToScreenReader('Reply form opened');
                }
            }
        });
    });
}

// Enhanced theme management
function initializeThemeManager() {
    const themeToggle = document.querySelector('[data-theme-toggle]');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
}

// Enhanced accessibility features
function initializeAccessibility() {
    // Skip to main content link
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = 'Skip to main content';
    skipLink.className = 'sr-only sr-only-focusable';
    skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 6px;
        z-index: 9999;
        padding: 8px 16px;
        background: #000;
        color: #fff;
        text-decoration: none;
        border-radius: 4px;
    `;
    
    skipLink.addEventListener('focus', function() {
        this.style.top = '6px';
    });
    
    skipLink.addEventListener('blur', function() {
        this.style.top = '-40px';
    });
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Enhanced keyboard navigation
    document.addEventListener('keydown', function(e) {
        // Escape key to close dropdowns and modals
        if (e.key === 'Escape') {
            const dropdowns = document.querySelectorAll('.dropdown-menu.show');
            dropdowns.forEach(dropdown => {
                const dropdownToggle = dropdown.previousElementSibling;
                if (dropdownToggle && dropdownToggle.classList.contains('dropdown-toggle')) {
                    dropdownToggle.click();
                }
            });
            
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const closeBtn = modal.querySelector('.btn-close, [data-bs-dismiss="modal"]');
                if (closeBtn) {
                    closeBtn.click();
                }
            });
        }
        
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="query"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
    });
}

// Enhanced performance optimizations
function initializePerformanceOptimizations() {
    // Lazy loading for images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
    
    // Debounced search
    const searchInput = document.querySelector('input[name="query"]');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Trigger search or autocomplete
                console.log('Searching for:', this.value);
            }, 300);
        });
    }
}

// Enhanced interactive elements
function initializeInteractiveElements() {
    // Add loading states to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            if (!this.classList.contains('disabled')) {
                this.classList.add('loading');
                setTimeout(() => this.classList.remove('loading'), 1000);
            }
        });
    });
    
    // Enhanced hover effects
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// Enhanced toast notification system
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    
    const icon = getToastIcon(type);
    const color = getToastColor(type);
    
    toast.innerHTML = `
        <div class="toast-content" style="display: flex; align-items: center; gap: 8px;">
            <i class="fas ${icon}" style="color: ${color};"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" style="position: absolute; top: 8px; right: 8px; background: none; border: none; color: #666; cursor: pointer;">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        padding: 16px;
        z-index: 9999;
        max-width: 300px;
        border-left: 4px solid ${color};
        animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    // Close button functionality
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    });
    
    // Auto-remove
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
    
    // Announce for screen readers
    announceToScreenReader(message);
}

// Enhanced toast utilities
function getToastIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

function getToastColor(type) {
    const colors = {
        success: '#27ae60',
        error: '#e74c3c',
        warning: '#f39c12',
        info: '#3498db'
    };
    return colors[type] || colors.info;
}

// Enhanced story interaction functions
function likeStory(storyId) {
    const likeButton = document.querySelector(`button[onclick="likeStory(${storyId})"]`);
    if (likeButton) {
        likeButton.classList.add('loading');
    }
    
    fetch(`/api/story/${storyId}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const likeButton = document.querySelector(`button[onclick="likeStory(${storyId})"]`);
            const likeCount = likeButton.querySelector('.like-count');
            if (likeCount) {
                const currentCount = parseInt(likeCount.textContent.match(/\d+/)[0]);
                likeCount.textContent = ` ${currentCount + 1}`;
            }
            showToast('Story liked successfully!', 'success');
        } else {
            showToast(data.message || 'Error liking story', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error liking story', 'error');
    })
    .finally(() => {
        if (likeButton) {
            likeButton.classList.remove('loading');
        }
    });
}

// Enhanced share functionality
function shareStory(storyId) {
    const url = window.location.origin + `/story/${storyId}`;
    const title = document.title;
    
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url,
            text: 'Check out this amazing story!'
        })
        .then(() => {
            showToast('Story shared successfully!', 'success');
        })
        .catch(error => {
            console.error('Error sharing:', error);
            copyToClipboard(url);
        });
    } else {
        copyToClipboard(url);
    }
}

// Enhanced clipboard functionality
function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => {
            showToast('Link copied to clipboard!', 'success');
        })
        .catch(error => {
            console.error('Error copying to clipboard:', error);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showToast('Link copied to clipboard!', 'success');
        });
}

// Enhanced reading list functionality
function addToReadingList(storyId) {
    const button = document.querySelector(`button[onclick="addToReadingList(${storyId})"]`);
    if (button) {
        button.classList.add('loading');
    }
    
    fetch(`/api/story/${storyId}/reading-list`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Added to reading list!', 'success');
            if (button) {
                button.textContent = 'Remove from Reading List';
                button.onclick = () => removeFromReadingList(storyId);
            }
        } else {
            showToast(data.message || 'Error adding to reading list', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error adding to reading list', 'error');
    })
    .finally(() => {
        if (button) {
            button.classList.remove('loading');
        }
    });
}

// Enhanced follow functionality
function followAuthor(authorId) {
    const followButton = document.querySelector(`button[onclick="followAuthor(${authorId})"]`);
    if (followButton) {
        followButton.classList.add('loading');
    }
    
    fetch(`/api/user/${authorId}/follow`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            followButton.textContent = 'Unfollow';
            followButton.onclick = () => unfollowAuthor(authorId);
            showToast('Author followed successfully!', 'success');
        } else {
            showToast(data.message || 'Error following author', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error following author', 'error');
    })
    .finally(() => {
        if (followButton) {
            followButton.classList.remove('loading');
        }
    });
}

// Enhanced unfollow functionality
function unfollowAuthor(authorId) {
    const followButton = document.querySelector(`button[onclick="unfollowAuthor(${authorId})"]`);
    if (followButton) {
        followButton.classList.add('loading');
    }
    
    fetch(`/api/user/${authorId}/unfollow`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            followButton.textContent = 'Follow';
            followButton.onclick = () => followAuthor(authorId);
            showToast('Author unfollowed successfully!', 'success');
        } else {
            showToast(data.message || 'Error unfollowing author', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error unfollowing author', 'error');
    })
    .finally(() => {
        if (followButton) {
            followButton.classList.remove('loading');
        }
    });
}

// Enhanced comment reply functionality
function replyToComment(commentId) {
    const commentElement = document.querySelector(`button[onclick="replyToComment(${commentId})"]`).closest('.comment');
    
    // Remove existing reply forms
    const existingForms = commentElement.querySelectorAll('.reply-form');
    existingForms.forEach(form => form.remove());
    
    const replyForm = document.createElement('form');
    replyForm.className = 'reply-form mt-3';
    replyForm.innerHTML = `
        <div class="mb-3">
            <textarea class="form-control" rows="3" placeholder="Write a reply..." required></textarea>
        </div>
        <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary btn-sm">
                <i class="fas fa-paper-plane me-1"></i>Reply
            </button>
            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="this.closest('.reply-form').remove()">
                <i class="fas fa-times me-1"></i>Cancel
            </button>
        </div>
    `;
    
    commentElement.appendChild(replyForm);
    
    // Focus on textarea
    const textarea = replyForm.querySelector('textarea');
    setTimeout(() => textarea.focus(), 100);
    
    replyForm.onsubmit = function(e) {
        e.preventDefault();
        const content = this.querySelector('textarea').value.trim();
        
        if (!content) {
            showToast('Please enter a reply', 'error');
            return;
        }
        
        const submitBtn = this.querySelector('button[type="submit"]');
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        
        fetch(`/api/comment/${commentId}/reply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ content }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Reply posted successfully!', 'success');
                location.reload();
            } else {
                showToast(data.message || 'Error posting reply', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error posting reply', 'error');
        })
        .finally(() => {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        });
    };
}

// Enhanced draft saving functionality
function saveDraft() {
    const form = document.querySelector('form');
    const formData = new FormData(form);
    const draftData = {};
    
    formData.forEach((value, key) => {
        draftData[key] = value;
    });
    
    localStorage.setItem('draft_' + Date.now(), JSON.stringify(draftData));
    showToast('Draft saved locally!', 'success');
}

// Enhanced accessibility announcements
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-label', 'Announcement');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
}

// Enhanced theme management
function setTheme(theme) {
    try {
        document.documentElement.setAttribute('data-theme', theme);
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
        
        // Announce theme change for screen readers
        announceToScreenReader(`Theme changed to ${theme} mode`);
        
        // If user is logged in, save preference to server
        if (typeof currentUser !== 'undefined' && currentUser) {
            fetch('/settings/theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme: theme })
            }).catch(error => console.error('Error saving theme:', error));
        }
    } catch (e) {
        console.error('Error setting theme:', e);
    }
}

// Enhanced CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
    
    .toast {
        animation: slideInRight 0.3s ease-out;
    }
    
    .loading {
        position: relative;
        pointer-events: none;
    }
    
    .loading::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 16px;
        height: 16px;
        margin: -8px 0 0 -8px;
        border: 2px solid transparent;
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    .is-invalid {
        border-color: #dc3545 !important;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25) !important;
    }
    
    .invalid-feedback {
        display: block;
        color: #dc3545;
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }
`;
document.head.appendChild(style);

// Export functions for global access
window.showToast = showToast;
window.likeStory = likeStory;
window.shareStory = shareStory;
window.addToReadingList = addToReadingList;
window.followAuthor = followAuthor;
window.unfollowAuthor = unfollowAuthor;
window.replyToComment = replyToComment;
window.saveDraft = saveDraft;
window.setTheme = setTheme;