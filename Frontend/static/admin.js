document.addEventListener('DOMContentLoaded', function() {

    // ==========================================
    // 0. Admin Registration Form Validation
    // ==========================================
    const adminRegisterForm = document.getElementById('adminRegisterForm');
    const MOBILE_REGEX = /^\d{10}$/;

    if (adminRegisterForm) {
        // Show error message from server if exists
        const errorElement = document.querySelector('[data-error]');
        if (errorElement) {
            const serverError = (errorElement.dataset.error || '').trim();
            if (serverError) {
                Swal.fire({
                    icon: 'error',
                    title: 'Registration Failed',
                    text: serverError,
                    confirmButtonColor: '#c53030'
                });
            }
        }

        adminRegisterForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const username = adminRegisterForm.querySelector('input[name="username"]').value.trim();
            const mobileNumber = adminRegisterForm.querySelector('input[name="mobile_number"]').value.trim();
            const password = adminRegisterForm.querySelector('input[name="password"]').value;
            const confirmPassword = adminRegisterForm.querySelector('input[name="confirm_password"]').value;

            if (username.length < 3) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Username',
                    text: 'Username kam se kam 3 characters ka hona chahiye.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (!MOBILE_REGEX.test(mobileNumber)) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Mobile Number',
                    text: 'Mobile number 10 digits ka hona chahiye.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (password.length < 6) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Weak Password',
                    text: 'Password minimum 6 characters ka hona chahiye.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (password !== confirmPassword) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Password Mismatch',
                    text: 'Password aur Confirm Password match nahi kar rahe.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            // Check mobile number uniqueness via AJAX
            const formData = new FormData();
            formData.append('mobile_number', mobileNumber);

            fetch('/check-mobile', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (!data.available) {
                    Swal.fire({
                        icon: 'error',
                        title: 'Mobile Number Exists',
                        text: data.message,
                        confirmButtonColor: '#c53030'
                    });
                    return;
                }

                Swal.fire({
                    icon: 'success',
                    title: 'Submitting Registration...',
                    showConfirmButton: false,
                    timer: 900
                }).then(() => {
                    adminRegisterForm.submit();
                });
            })
            .catch(error => {
                console.error('Error checking mobile number:', error);
                Swal.fire({
                    icon: 'warning',
                    title: 'Network Error',
                    text: 'Could not verify mobile number. Please try again.',
                    confirmButtonColor: '#3182ce'
                });
            });
        });
    }

    // ==========================================
    // 1. Add Candidate Form Validation (Dashboard)
    // ==========================================
    const addCandidateForm = document.getElementById('addCandidateForm');
    
    if (addCandidateForm) {
        addCandidateForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Form ko direct submit hone se rokna

            const name = document.getElementById('candidateName').value.trim();
            const party = document.getElementById('candidateParty').value.trim();

            // Check karna ki koi field khali toh nahi hai
            if (name === "" || party === "") {
                Swal.fire({
                    icon: 'warning',
                    title: 'Incomplete Details',
                    text: 'Candidate Name aur Party dono daalna zaroori hai!',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            // Agar sab sahi hai, toh success popup dikhakar form submit karna
            Swal.fire({
                icon: 'success',
                title: 'Adding Candidate...',
                showConfirmButton: false,
                timer: 1500
            }).then(() => {
                this.submit(); // Asli submission
            });
        });
    }

    // ==========================================
    // 2. Delete Voter Confirmation (Manage Voters)
    // ==========================================
    const deleteForms = document.querySelectorAll('.delete-voter-form');
    
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault(); // Direct delete hone se rokna

            Swal.fire({
                title: 'Are you sure?',
                text: "You want to delete this voter? This action cannot be undone!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#e53e3e',
                cancelButtonColor: '#718096',
                confirmButtonText: 'Yes, delete it!'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Agar admin ne 'Yes' daba diya, tabhi form submit hoga
                    form.submit(); 
                }
            });
        });
    });

    // ==========================================
    // 2.1 Delete Candidate Confirmation (Dashboard)
    // ==========================================
    const deleteCandidateForms = document.querySelectorAll('.delete-candidate-form');

    deleteCandidateForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            Swal.fire({
                title: 'Delete Candidate?',
                text: 'Candidate ka record aur logo file permanently delete ho jayega.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#e53e3e',
                cancelButtonColor: '#718096',
                confirmButtonText: 'Yes, delete it!'
            }).then((result) => {
                if (result.isConfirmed) {
                    form.submit();
                }
            });
        });
    });

    // ==========================================
    // 3. Election Toggle Confirmation
    // ==========================================
    const electionToggleForm = document.querySelector('form[action="/toggle-election"]');

    if (electionToggleForm) {
        electionToggleForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const statusInput = electionToggleForm.querySelector('input[name="status"]');
            const nextStatus = statusInput ? statusInput.value : '';
            const isStarting = nextStatus === 'started';

            Swal.fire({
                title: isStarting ? 'Start Election?' : 'Stop Election?',
                text: isStarting
                    ? 'Election start hote hi voters vote de paayenge.'
                    : 'Election stop hone par voters vote nahi de paayenge.',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: isStarting ? '#38a169' : '#e53e3e',
                cancelButtonColor: '#718096',
                confirmButtonText: isStarting ? 'Yes, Start' : 'Yes, Stop'
            }).then((result) => {
                if (result.isConfirmed) {
                    electionToggleForm.submit();
                }
            });
        });
    }

    // ==========================================
    // 4. Admin Logout Confirmation + Message
    // ==========================================
    const adminLogoutLinks = document.querySelectorAll('a.logout-btn[href="/admin-logout"]');

    adminLogoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const logoutUrl = link.getAttribute('href');

            Swal.fire({
                title: 'Logout Confirmation',
                text: 'Kya aap sure hain ki aap logout karna chahte hain?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#e53e3e',
                cancelButtonColor: '#718096',
                confirmButtonText: 'Yes, Logout'
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Logout Successfully',
                        showConfirmButton: false,
                        timer: 1200
                    }).then(() => {
                        window.location.href = logoutUrl;
                    });
                }
            });
        });
    });
});