// ====================================
// Global State
// ====================================
let currentFilter = null;

// ====================================
// Dark Mode Toggle
// ====================================
const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;

const currentTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', currentTheme);

function updateThemeIcon() {
    const icon = themeToggle.querySelector('i');
    const theme = html.getAttribute('data-theme');
    icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

updateThemeIcon();

themeToggle.addEventListener('click', () => {
    const current = html.getAttribute('data-theme');
    const newTheme = current === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon();
});

// ====================================
// Modal Management - Add User
// ====================================
const addUserModal = document.getElementById('addUserModal');
const addUserBtn = document.getElementById('addUserBtn');
const addUserModalClose = addUserModal.querySelector('.modal-close');
const cancelAddUser = document.getElementById('cancelAddUser');

addUserBtn.addEventListener('click', () => {
    addUserModal.classList.add('active');
});

function closeAddUserModal() {
    addUserModal.classList.remove('active');
    document.getElementById('addUserForm').reset();
    document.getElementById('addUserProgress').style.display = 'none';
}

addUserModalClose.addEventListener('click', closeAddUserModal);
cancelAddUser.addEventListener('click', closeAddUserModal);

addUserModal.addEventListener('click', (e) => {
    if (e.target === addUserModal) {
        closeAddUserModal();
    }
});

// ====================================
// Add User Form Submission
// ====================================
const addUserForm = document.getElementById('addUserForm');
const addUserProgress = document.getElementById('addUserProgress');
const addProgressText = document.getElementById('addProgressText');

addUserForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const range = document.getElementById('range').value;

    // Show progress, hide form
    addUserForm.style.display = 'none';
    addUserProgress.style.display = 'block';
    addProgressText.textContent = 'Adding user and starting scrape...';

    try {
        const response = await fetch('/api/users/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username, range })
        });

        const data = await response.json();

        if (response.ok) {
            addProgressText.textContent = 'Scraping started! This may take a few minutes...';

            // Poll for status updates
            const statusInterval = setInterval(async () => {
                const statusResponse = await fetch('/api/scrape-status');
                const statusData = await statusResponse.json();

                addProgressText.textContent = statusData.progress;

                if (!statusData.running) {
                    clearInterval(statusInterval);

                    if (statusData.error) {
                        addProgressText.textContent = `Error: ${statusData.error}`;
                        setTimeout(() => {
                            closeAddUserModal();
                            addUserForm.style.display = 'block';
                        }, 3000);
                    } else {
                        addProgressText.textContent = 'User added successfully! Refreshing page...';
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }
                }
            }, 2000);

        } else {
            throw new Error(data.error || 'Failed to add user');
        }

    } catch (error) {
        addProgressText.textContent = `Error: ${error.message}`;
        setTimeout(() => {
            closeAddUserModal();
            addUserForm.style.display = 'block';
        }, 3000);
    }
});

// ====================================
// Refresh All Users
// ====================================
const refreshAllBtn = document.getElementById('refreshAllBtn');

if (refreshAllBtn) {
    refreshAllBtn.addEventListener('click', async () => {
        if (!confirm('Refresh all users? This will re-scrape all tracked LinkedIn profiles.')) {
            return;
        }

        const originalText = refreshAllBtn.innerHTML;
        refreshAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshAllBtn.disabled = true;

        try {
            const response = await fetch('/api/users/refresh-all', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ range: 60 })
            });

            const data = await response.json();

            if (response.ok) {
                // Poll for status updates
                const statusInterval = setInterval(async () => {
                    const statusResponse = await fetch('/api/scrape-status');
                    const statusData = await statusResponse.json();

                    refreshAllBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${statusData.progress}`;

                    if (!statusData.running) {
                        clearInterval(statusInterval);

                        if (statusData.error) {
                            alert(`Error: ${statusData.error}`);
                            refreshAllBtn.innerHTML = originalText;
                            refreshAllBtn.disabled = false;
                        } else {
                            refreshAllBtn.innerHTML = '<i class="fas fa-check"></i> Completed!';
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                        }
                    }
                }, 2000);
            } else {
                throw new Error(data.error || 'Failed to start refresh');
            }

        } catch (error) {
            alert(`Error: ${error.message}`);
            refreshAllBtn.innerHTML = originalText;
            refreshAllBtn.disabled = false;
        }
    });
}

// ====================================
// Remove User
// ====================================
async function removeUser(username, event) {
    event.stopPropagation();

    if (!confirm(`Remove ${username} from tracking?`)) {
        return;
    }

    try {
        const response = await fetch('/api/users/remove', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ username })
        });

        if (response.ok) {
            // Remove user card with animation
            const userCard = document.querySelector(`.user-card[data-username="${username}"]`);
            if (userCard) {
                userCard.style.opacity = '0';
                userCard.style.transform = 'translateX(20px)';
                setTimeout(() => {
                    window.location.reload();
                }, 300);
            }
        } else {
            const data = await response.json();
            alert(`Error: ${data.error || 'Failed to remove user'}`);
        }

    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// ====================================
// Filter Feed by User
// ====================================
async function filterByUser(username) {
    currentFilter = username;

    try {
        const response = await fetch(`/api/feed?username=${encodeURIComponent(username)}`);
        const data = await response.json();

        // Update feed title
        const feedTitle = document.getElementById('feedTitle');
        feedTitle.textContent = `${data.filtered_by}'s Posts (${data.total_posts})`;

        // Show clear filter button
        const clearFilterBtn = document.getElementById('clearFilterBtn');
        clearFilterBtn.style.display = 'inline-flex';

        // Highlight selected user
        document.querySelectorAll('.user-card').forEach(card => {
            card.style.backgroundColor = '';
        });
        const selectedCard = document.querySelector(`.user-card[data-username="${username}"]`);
        if (selectedCard) {
            selectedCard.style.backgroundColor = 'var(--bg-tertiary)';
        }

        // Filter posts in the feed
        document.querySelectorAll('.post-card').forEach(card => {
            if (card.dataset.username === username) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });

    } catch (error) {
        console.error('Error filtering feed:', error);
    }
}

// ====================================
// Clear Filter
// ====================================
const clearFilterBtn = document.getElementById('clearFilterBtn');

if (clearFilterBtn) {
    clearFilterBtn.addEventListener('click', () => {
        currentFilter = null;

        // Update feed title
        const feedTitle = document.getElementById('feedTitle');
        const totalPosts = document.querySelectorAll('.post-card').length;
        feedTitle.textContent = `All Posts (${totalPosts})`;

        // Hide clear filter button
        clearFilterBtn.style.display = 'none';

        // Reset user card highlighting
        document.querySelectorAll('.user-card').forEach(card => {
            card.style.backgroundColor = '';
        });

        // Show all posts
        document.querySelectorAll('.post-card').forEach(card => {
            card.style.display = 'block';
        });
    });
}

// ====================================
// Carousel Functionality
// ====================================
const carouselStates = {};

function initCarousels() {
    document.querySelectorAll('.carousel').forEach(carousel => {
        const postId = carousel.getAttribute('data-post');
        carouselStates[postId] = { currentIndex: 0 };
    });
}

function moveCarousel(postId, direction) {
    const carousel = document.querySelector(`.carousel[data-post="${postId}"]`);
    if (!carousel) return;

    const slides = carousel.querySelectorAll('.carousel-slide');
    const indicators = carousel.querySelectorAll('.indicator');

    if (slides.length === 0) return;

    slides[carouselStates[postId].currentIndex].classList.remove('active');
    indicators[carouselStates[postId].currentIndex].classList.remove('active');

    carouselStates[postId].currentIndex += direction;

    if (carouselStates[postId].currentIndex >= slides.length) {
        carouselStates[postId].currentIndex = 0;
    } else if (carouselStates[postId].currentIndex < 0) {
        carouselStates[postId].currentIndex = slides.length - 1;
    }

    slides[carouselStates[postId].currentIndex].classList.add('active');
    indicators[carouselStates[postId].currentIndex].classList.add('active');
}

function goToSlide(postId, index) {
    const carousel = document.querySelector(`.carousel[data-post="${postId}"]`);
    if (!carousel) return;

    const slides = carousel.querySelectorAll('.carousel-slide');
    const indicators = carousel.querySelectorAll('.indicator');

    if (slides.length === 0) return;

    slides[carouselStates[postId].currentIndex].classList.remove('active');
    indicators[carouselStates[postId].currentIndex].classList.remove('active');

    carouselStates[postId].currentIndex = index;

    slides[index].classList.add('active');
    indicators[index].classList.add('active');
}

initCarousels();

// ====================================
// Lightbox Functionality
// ====================================
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImg');
const lightboxCaption = document.querySelector('.lightbox-caption');
const lightboxClose = document.querySelector('.lightbox-close');

let currentLightboxImages = [];
let currentLightboxIndex = 0;

function openLightbox(imageSrc, caption) {
    lightboxImg.src = imageSrc;
    lightboxCaption.textContent = caption;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';

    const postCard = event.target.closest('.post-card');
    if (postCard) {
        const images = postCard.querySelectorAll('.carousel-slide img');
        currentLightboxImages = Array.from(images).map(img => ({
            src: img.src,
            alt: img.alt
        }));
        currentLightboxIndex = currentLightboxImages.findIndex(img => img.src === imageSrc);
    }
}

function closeLightbox() {
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    currentLightboxImages = [];
    currentLightboxIndex = 0;
}

function navigateLightbox(direction) {
    if (currentLightboxImages.length === 0) return;

    currentLightboxIndex += direction;

    if (currentLightboxIndex >= currentLightboxImages.length) {
        currentLightboxIndex = 0;
    } else if (currentLightboxIndex < 0) {
        currentLightboxIndex = currentLightboxImages.length - 1;
    }

    const image = currentLightboxImages[currentLightboxIndex];
    lightboxImg.src = image.src;
    lightboxCaption.textContent = image.alt;
}

lightboxClose.addEventListener('click', closeLightbox);
document.querySelector('.lightbox-prev').addEventListener('click', () => navigateLightbox(-1));
document.querySelector('.lightbox-next').addEventListener('click', () => navigateLightbox(1));

lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) {
        closeLightbox();
    }
});

document.addEventListener('keydown', (e) => {
    if (!lightbox.classList.contains('active')) return;

    switch(e.key) {
        case 'Escape':
            closeLightbox();
            break;
        case 'ArrowLeft':
            navigateLightbox(-1);
            break;
        case 'ArrowRight':
            navigateLightbox(1);
            break;
    }
});

// ====================================
// Relative Time Display
// ====================================
function updateRelativeTimes() {
    document.querySelectorAll('.relative-time').forEach(element => {
        const timestamp = element.dataset.time;
        if (timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);

            let relativeTime;
            if (minutes < 1) {
                relativeTime = 'just now';
            } else if (minutes < 60) {
                relativeTime = `${minutes}m ago`;
            } else if (hours < 24) {
                relativeTime = `${hours}h ago`;
            } else if (days < 7) {
                relativeTime = `${days}d ago`;
            } else {
                relativeTime = date.toLocaleDateString();
            }

            element.textContent = relativeTime;
        }
    });
}

// Update relative times on load and every minute
updateRelativeTimes();
setInterval(updateRelativeTimes, 60000);

// ====================================
// Auto-pause videos when scrolled out of view
// ====================================
const videos = document.querySelectorAll('.post-video');

const videoObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        const video = entry.target;
        if (!entry.isIntersecting && !video.paused) {
            video.pause();
        }
    });
}, { threshold: 0.5 });

videos.forEach(video => {
    videoObserver.observe(video);
});

// ====================================
// Console Welcome Message
// ====================================
console.log('%c LinkedIn Feed Aggregator ', 'background: #0a66c2; color: white; font-size: 20px; padding: 10px;');
console.log('%c Multi-User Feed Aggregator with Real-time Scraping ', 'font-size: 14px; color: #666;');
