document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    if (!navToggle || !navLinks) {
        return;
    }

    function closeDropdowns() {
        navLinks.querySelectorAll('.dropdown.open').forEach(function(dropdown) {
            dropdown.classList.remove('open');
        });
    }

    function closeMenu() {
        navLinks.classList.remove('open');
        navToggle.classList.remove('active');
        navToggle.setAttribute('aria-expanded', 'false');
        closeDropdowns();
    }

    navToggle.addEventListener('click', function() {
        const isOpen = navLinks.classList.toggle('open');
        navToggle.classList.toggle('active', isOpen);
        navToggle.setAttribute('aria-expanded', String(isOpen));
    });

    navLinks.querySelectorAll('a').forEach(function(link) {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeMenu();
            }
        });
    });

    navLinks.querySelectorAll('.dropdown .dropbtn').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (window.innerWidth > 768) {
                return;
            }

            e.preventDefault();

            const dropdown = button.closest('.dropdown');
            const willOpen = dropdown && !dropdown.classList.contains('open');
            closeDropdowns();

            if (willOpen) {
                dropdown.classList.add('open');
            }
        });
    });

    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768 && !e.target.closest('.dropdown')) {
            closeDropdowns();
        }
    });

    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    });
});