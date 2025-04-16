// Wait for DOM to load before initializing animations
document.addEventListener('DOMContentLoaded', () => {
    // Initialize animations
    initializeHeroAnimation();
    initializeFeatureCardAnimations();
    initializeFileCardAnimations();
    initializeFadeInAnimations();
});

/**
 * Creates floating animation elements in the hero section
 */
function initializeHeroAnimation() {
    const heroSection = document.querySelector('.hero');
    
    // If hero section doesn't exist, return
    if (!heroSection) return;
    
    // Create floating elements
    for (let i = 0; i < 15; i++) {
        createFloatingElement(heroSection);
    }
    
    // Animate the hero text with a fade-in effect
    const heroTitle = document.querySelector('.hero h1');
    const heroSubtitle = document.querySelector('.hero p');
    const heroButton = document.querySelector('.hero .btn');
    
    if (heroTitle) animateElement(heroTitle, 'fade-in', 0);
    if (heroSubtitle) animateElement(heroSubtitle, 'fade-in', 200);
    if (heroButton) animateElement(heroButton, 'fade-in', 400);
}

/**
 * Creates a single floating element with random properties
 * @param {HTMLElement} container - The container to append the floating element to
 */
function createFloatingElement(container) {
    const floatItem = document.createElement('div');
    floatItem.classList.add('float-item');
    
    // Random size between 20px and 100px
    const size = Math.floor(Math.random() * 80) + 20;
    floatItem.style.width = `${size}px`;
    floatItem.style.height = `${size}px`;
    
    // Random position within the container
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    
    floatItem.style.left = `${Math.random() * containerWidth}px`;
    floatItem.style.top = `${Math.random() * containerHeight}px`;
    
    // Random animation duration and delay
    const duration = (Math.random() * 20) + 10; // 10-30 seconds
    const delay = Math.random() * 5; // 0-5 seconds
    
    floatItem.style.animation = `float ${duration}s ease-in-out ${delay}s infinite`;
    
    // Add to container
    container.appendChild(floatItem);
}

/**
 * Initializes animations for feature cards
 */
function initializeFeatureCardAnimations() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach((card, index) => {
        // Add sequential fade-in animation
        animateElement(card, 'fade-in', index * 100);
        
        // Add hover effect
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px)';
            card.style.boxShadow = '0 15px 30px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.05)';
        });
    });
}

/**
 * Initializes animations for file cards
 */
function initializeFileCardAnimations() {
    const fileCards = document.querySelectorAll('.file-card');
    
    fileCards.forEach((card, index) => {
        // Add sequential fade-in animation
        animateElement(card, 'fade-in', index * 50);
    });
}

/**
 * Initializes fade-in animations for elements with the fade-in class
 */
function initializeFadeInAnimations() {
    const fadeElements = document.querySelectorAll('.fade-in');
    
    fadeElements.forEach((element, index) => {
        // Check if the element is in view
        const isInViewport = (element) => {
            const rect = element.getBoundingClientRect();
            return (
                rect.top <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.bottom >= 0
            );
        };
        
        // Function to handle scroll
        const handleScroll = () => {
            if (isInViewport(element)) {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
                window.removeEventListener('scroll', handleScroll);
            }
        };
        
        // Initial state
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        // Check on load and scroll
        if (isInViewport(element)) {
            setTimeout(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        } else {
            window.addEventListener('scroll', handleScroll);
        }
    });
}

/**
 * Helper function to animate an element with a class and delay
 * @param {HTMLElement} element - The element to animate
 * @param {string} className - The CSS class for the animation
 * @param {number} delay - The delay in milliseconds
 */
function animateElement(element, className, delay) {
    setTimeout(() => {
        element.classList.add(className);
    }, delay);
}
