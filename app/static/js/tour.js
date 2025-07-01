/**
 * PenVault Onboarding Tour
 * Progressive tour system for new users
 */

class PenVaultTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.isActive = false;
        this.userId = null;
        this.tourProgress = {};
        
        // Initialize tour
        this.init();
    }
    
    init() {
        // Check if user is authenticated and tour should be shown
        if (typeof currentUser !== 'undefined' && currentUser) {
            this.userId = currentUser.id || 'anonymous';
            this.loadTourProgress();
            this.setupTourSteps();
            this.checkTourTrigger();
        }
        
        // Add tour restart button to navbar
        this.addTourRestartButton();
    }
    
    loadTourProgress() {
        try {
            // First try to load from server data if available
            if (currentUser && currentUser.tour_progress) {
                this.tourProgress = currentUser.tour_progress;
                return;
            }
            
            // Fallback to localStorage
            const saved = localStorage.getItem(`penvault_tour_${this.userId}`);
            if (saved) {
                this.tourProgress = JSON.parse(saved);
            }
        } catch (e) {
            console.error('Error loading tour progress:', e);
        }
    }
    
    saveTourProgress() {
        try {
            localStorage.setItem(`penvault_tour_${this.userId}`, JSON.stringify(this.tourProgress));
            // Also save to server if user is authenticated
            if (this.userId && this.userId !== 'anonymous') {
                this.updateServerProgress();
            }
        } catch (e) {
            console.error('Error saving tour progress:', e);
        }
    }
    
    async updateServerProgress() {
        try {
            await fetch('/api/tour/progress', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    progress: this.tourProgress,
                    completed: this.tourProgress.completed || false
                })
            });
        } catch (e) {
            console.error('Error updating server tour progress:', e);
        }
    }
    
    setupTourSteps() {
        const currentPage = window.location.pathname;
        
        // Define tour steps based on current page
        this.steps = this.getStepsForPage(currentPage);
    }
    
    getStepsForPage(page) {
        const baseSteps = [
            {
                id: 'welcome',
                title: 'Welcome to PenVault!',
                content: 'Let\'s take a quick tour to help you get started with your writing journey.',
                target: null,
                position: 'center',
                showOn: ['/']
            },
            {
                id: 'navigation',
                title: 'Navigation',
                content: 'Use the navigation bar to explore different sections of PenVault.',
                target: '.navbar-nav',
                position: 'bottom',
                showOn: ['/']
            },
            {
                id: 'write_button',
                title: 'Start Writing',
                content: 'Click here to create your first story, poem, or other content.',
                target: '#writeDropdown',
                position: 'bottom',
                showOn: ['/']
            },
            {
                id: 'profile_menu',
                title: 'Your Profile',
                content: 'Access your profile, statistics, and settings from here.',
                target: '#profileDropdown',
                position: 'bottom-left',
                showOn: ['/']
            }
        ];
        
        const pageSpecificSteps = {
            '/discover': [
                {
                    id: 'discover_page',
                    title: 'Discover Content',
                    content: 'Browse and discover stories, poems, and other writings from the community.',
                    target: '.container',
                    position: 'center',
                    showOn: ['/discover']
                }
            ],
            '/feed': [
                {
                    id: 'feed_page',
                    title: 'Your Feed',
                    content: 'See updates from writers you follow. Start following others to see their content here!',
                    target: '.container',
                    position: 'center',
                    showOn: ['/feed']
                }
            ],
            '/statistics': [
                {
                    id: 'statistics_page',
                    title: 'Your Statistics',
                    content: 'Track your writing progress, views, likes, and Pulse Score here.',
                    target: '.container',
                    position: 'center',
                    showOn: ['/statistics']
                }
            ],
            '/redeem': [
                {
                    id: 'redeem_page',
                    title: 'Redeem Points',
                    content: 'Use your earned points to unlock premium content or feature your posts.',
                    target: '.container',
                    position: 'center',
                    showOn: ['/redeem']
                }
            ],
            '/settings': [
                {
                    id: 'settings_page',
                    title: 'Settings',
                    content: 'Customize your profile, manage your account, and adjust preferences here.',
                    target: '.container',
                    position: 'center',
                    showOn: ['/settings']
                }
            ]
        };
        
        // Combine base steps with page-specific steps
        let allSteps = [...baseSteps];
        
        // Add page-specific steps if they exist
        if (pageSpecificSteps[page]) {
            allSteps = allSteps.concat(pageSpecificSteps[page]);
        }
        
        // Filter steps that should show on current page
        return allSteps.filter(step => 
            step.showOn.includes(page) || step.showOn.includes('*')
        );
    }
    
    checkTourTrigger() {
        // Check if tour should be triggered
        const shouldShowTour = !this.tourProgress.completed && 
                              !this.tourProgress.dismissed &&
                              this.steps.length > 0;
        
        if (shouldShowTour) {
            // Small delay to ensure page is loaded
            setTimeout(() => {
                this.startTour();
            }, 1000);
        }
    }
    
    startTour() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentStep = 0;
        this.showStep();
    }
    
    showStep() {
        if (this.currentStep >= this.steps.length) {
            this.completeTour();
            return;
        }
        
        const step = this.steps[this.currentStep];
        this.createTooltip(step);
    }
    
    createTooltip(step) {
        // Remove existing tooltip
        this.removeTooltip();
        
        // Create tooltip container
        const tooltip = document.createElement('div');
        tooltip.id = 'penvault-tour-tooltip';
        tooltip.className = 'penvault-tour-tooltip';
        
        // Create tooltip content
        tooltip.innerHTML = `
            <div class="tour-tooltip-content">
                <div class="tour-tooltip-header">
                    <h4 class="tour-tooltip-title">${step.title}</h4>
                    <button class="tour-tooltip-close" onclick="penvaultTour.closeTour()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="tour-tooltip-body">
                    <p>${step.content}</p>
                </div>
                <div class="tour-tooltip-footer">
                    <div class="tour-tooltip-progress">
                        ${this.currentStep + 1} of ${this.steps.length}
                    </div>
                    <div class="tour-tooltip-actions">
                        <button class="btn btn-outline-secondary btn-sm" onclick="penvaultTour.skipTour()">
                            Skip Tour
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="penvaultTour.nextStep()">
                            ${this.currentStep === this.steps.length - 1 ? 'Got it!' : 'Next'}
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add tooltip to page
        document.body.appendChild(tooltip);
        
        // Position tooltip
        this.positionTooltip(step);
        
        // Highlight target element
        if (step.target) {
            this.highlightElement(step.target);
        }
        
        // Add overlay
        this.addOverlay();
    }
    
    positionTooltip(step) {
        const tooltip = document.getElementById('penvault-tour-tooltip');
        if (!tooltip) return;
        
        let targetElement = null;
        if (step.target) {
            targetElement = document.querySelector(step.target);
        }
        
        const tooltipRect = tooltip.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        let left, top;
        
        if (targetElement) {
            const targetRect = targetElement.getBoundingClientRect();
            
            switch (step.position) {
                case 'top':
                    left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
                    top = targetRect.top - tooltipRect.height - 10;
                    break;
                case 'bottom':
                    left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
                    top = targetRect.bottom + 10;
                    break;
                case 'left':
                    left = targetRect.left - tooltipRect.width - 10;
                    top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
                    break;
                case 'right':
                    left = targetRect.right + 10;
                    top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
                    break;
                case 'bottom-left':
                    left = targetRect.left;
                    top = targetRect.bottom + 10;
                    break;
                default:
                    left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
                    top = targetRect.bottom + 10;
            }
        } else {
            // Center tooltip if no target
            left = (windowWidth / 2) - (tooltipRect.width / 2);
            top = (windowHeight / 2) - (tooltipRect.height / 2);
        }
        
        // Ensure tooltip stays within viewport
        left = Math.max(10, Math.min(left, windowWidth - tooltipRect.width - 10));
        top = Math.max(10, Math.min(top, windowHeight - tooltipRect.height - 10));
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }
    
    highlightElement(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.classList.add('penvault-tour-highlight');
        }
    }
    
    removeHighlight() {
        const highlighted = document.querySelectorAll('.penvault-tour-highlight');
        highlighted.forEach(el => el.classList.remove('penvault-tour-highlight'));
    }
    
    addOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'penvault-tour-overlay';
        overlay.className = 'penvault-tour-overlay';
        document.body.appendChild(overlay);
    }
    
    removeOverlay() {
        const overlay = document.getElementById('penvault-tour-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    removeTooltip() {
        const tooltip = document.getElementById('penvault-tour-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
        this.removeHighlight();
        this.removeOverlay();
    }
    
    nextStep() {
        // Mark current step as completed
        const currentStepData = this.steps[this.currentStep];
        if (currentStepData) {
            this.tourProgress[currentStepData.id] = true;
        }
        
        this.currentStep++;
        this.showStep();
    }
    
    skipTour() {
        this.tourProgress.dismissed = true;
        this.saveTourProgress();
        this.closeTour();
    }
    
    completeTour() {
        this.tourProgress.completed = true;
        this.saveTourProgress();
        this.closeTour();
    }
    
    closeTour() {
        this.isActive = false;
        this.removeTooltip();
    }
    
    addTourRestartButton() {
        // Do nothing: Tour button removed from navbar as per user request
    }
    
    restartTour() {
        // Reset tour progress
        this.tourProgress = {};
        this.saveTourProgress();
        
        // Restart tour
        this.startTour();
    }
}

// Initialize tour when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.penvaultTour = new PenVaultTour();
});

// Handle window resize
window.addEventListener('resize', function() {
    if (window.penvaultTour && window.penvaultTour.isActive) {
        const currentStep = window.penvaultTour.steps[window.penvaultTour.currentStep];
        if (currentStep) {
            window.penvaultTour.positionTooltip(currentStep);
        }
    }
}); 