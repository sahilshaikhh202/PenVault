// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Flash message auto-hide
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 300);
        }, 3000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });

            if (!isValid) {
                event.preventDefault();
            }
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Dark mode toggle logic
    const themeToggleBtn = document.querySelector('.theme-toggle');
    const body = document.body;
    const darkModeClass = 'dark-mode';
    const darkIconClass = 'fa-moon';
    const lightIconClass = 'fa-sun';

    // Helper to update icon
    function updateThemeIcon(isDark) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('i');
        if (icon) {
            icon.classList.remove(isDark ? lightIconClass : darkIconClass);
            icon.classList.add(isDark ? darkIconClass : lightIconClass);
        }
    }

    // Set theme from localStorage or system
    function setInitialTheme() {
        let theme = localStorage.getItem('theme');
        if (!theme) {
            // Use system preference if not set
            theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        if (theme === 'dark') {
            body.classList.add(darkModeClass);
            updateThemeIcon(true);
        } else {
            body.classList.remove(darkModeClass);
            updateThemeIcon(false);
        }
    }

    setInitialTheme();

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const isDark = !body.classList.contains(darkModeClass);
            if (isDark) {
                body.classList.add(darkModeClass);
                localStorage.setItem('theme', 'dark');
            } else {
                body.classList.remove(darkModeClass);
                localStorage.setItem('theme', 'light');
            }
            updateThemeIcon(isDark);
        });
    }
});

// Toast notification function
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Like story functionality
function likeStory(storyId) {
    fetch(`/api/story/${storyId}/like`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const likeButton = document.querySelector(`button[onclick="likeStory(${storyId})"]`);
            const likeCount = likeButton.querySelector('i').nextSibling.textContent;
            const newCount = parseInt(likeCount.match(/\d+/)[0]) + 1;
            likeButton.querySelector('i').nextSibling.textContent = ` Like (${newCount})`;
            showToast('Story liked successfully!');
        }
    })
    .catch(error => {
        showToast('Error liking story', 'error');
    });
}

// Share story functionality
function shareStory(storyId) {
    const url = window.location.origin + `/story/${storyId}`;
    if (navigator.share) {
        navigator.share({
            title: document.title,
            url: url
        })
        .then(() => showToast('Story shared successfully!'))
        .catch(error => showToast('Error sharing story', 'error'));
    } else {
        navigator.clipboard.writeText(url)
            .then(() => showToast('Link copied to clipboard!'))
            .catch(error => showToast('Error copying link', 'error'));
    }
}

// Add to reading list functionality
function addToReadingList(storyId) {
    fetch(`/api/story/${storyId}/reading-list`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Added to reading list!');
        }
    })
    .catch(error => {
        showToast('Error adding to reading list', 'error');
    });
}

// Follow author functionality
function followAuthor(authorId) {
    fetch(`/api/user/${authorId}/follow`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const followButton = document.querySelector(`button[onclick="followAuthor(${authorId})"]`);
            followButton.textContent = 'Unfollow';
            followButton.onclick = () => unfollowAuthor(authorId);
            showToast('Author followed successfully!');
        }
    })
    .catch(error => {
        showToast('Error following author', 'error');
    });
}

// Unfollow author functionality
function unfollowAuthor(authorId) {
    fetch(`/api/user/${authorId}/unfollow`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const followButton = document.querySelector(`button[onclick="unfollowAuthor(${authorId})"]`);
            followButton.textContent = 'Follow';
            followButton.onclick = () => followAuthor(authorId);
            showToast('Author unfollowed successfully!');
        }
    })
    .catch(error => {
        showToast('Error unfollowing author', 'error');
    });
}

// Reply to comment functionality
function replyToComment(commentId) {
    const replyForm = document.createElement('form');
    replyForm.className = 'reply-form mt-2';
    replyForm.innerHTML = `
        <div class="mb-3">
            <textarea class="form-control" rows="2" placeholder="Write a reply..."></textarea>
        </div>
        <div class="d-flex gap-2">
            <button type="submit" class="btn btn-primary btn-sm">Reply</button>
            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="this.parentElement.parentElement.remove()">Cancel</button>
        </div>
    `;
    
    const commentElement = document.querySelector(`button[onclick="replyToComment(${commentId})"]`).closest('.comment');
    commentElement.appendChild(replyForm);
    
    replyForm.onsubmit = function(e) {
        e.preventDefault();
        const content = this.querySelector('textarea').value;
        
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
                location.reload();
            }
        })
        .catch(error => {
            showToast('Error posting reply', 'error');
        });
    };
}

// Save draft functionality
function saveDraft() {
    const title = document.querySelector('input[name="title"]').value;
    const summary = document.querySelector('textarea[name="summary"]').value;
    const content = quill.root.innerHTML;
    
    fetch('/api/draft/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title,
            summary,
            content,
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Draft saved successfully!');
        }
    })
    .catch(error => {
        showToast('Error saving draft', 'error');
    });
}