document.addEventListener('DOMContentLoaded', function() {
    const VOTER_ID_REGEX = /^[A-Z]{3}\d{7}$/;
    const MOBILE_REGEX = /^\d{10}$/;
    const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    const page = document.body.dataset.page;
    const serverError = (document.body.dataset.error || '').trim();
    const serverSuccess = (document.body.dataset.success || '').trim();

    // ==========================================
    // 1. Voter Login Validation + Server Messages
    // ==========================================
    const voterLoginForm = document.getElementById('voterLoginForm');

    if (voterLoginForm) {
        if (serverSuccess) {
            Swal.fire({
                icon: 'success',
                title: 'Registration Successful',
                text: serverSuccess,
                confirmButtonColor: '#2f855a'
            });
        }

        if (serverError) {
            Swal.fire({
                icon: 'error',
                title: 'Login Failed',
                text: serverError,
                confirmButtonColor: '#2f855a'
            });
        }

        voterLoginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const voterIdInput = voterLoginForm.querySelector('input[name="voter_id"]');
            const voterId = voterIdInput.value.trim().toUpperCase();
            voterIdInput.value = voterId;
            const password = voterLoginForm.querySelector('input[name="password"]').value;

            if (voterId === '') {
                Swal.fire({
                    icon: 'warning',
                    title: 'Missing Voter ID',
                    text: 'Please enter your Voter ID.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (!VOTER_ID_REGEX.test(voterId)) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Voter ID Format',
                    text: 'Voter ID ka format ABC1234567 hona chahiye.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (password.trim() === '') {
                Swal.fire({
                    icon: 'warning',
                    title: 'Missing Password',
                    text: 'Please enter your password.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            Swal.fire({
                icon: 'info',
                title: 'Verifying...',
                showConfirmButton: false,
                timer: 900
            }).then(() => {
                voterLoginForm.submit();
            });
        });
    }

    // ==========================================
    // 2. Voter Registration Validation + Messages
    // ==========================================
    const voterRegisterForm = document.getElementById('voterRegisterForm');

    if (voterRegisterForm) {
        if (serverError) {
            Swal.fire({
                icon: 'error',
                title: 'Registration Failed',
                text: serverError,
                confirmButtonColor: '#c53030'
            });
        }

        if (serverSuccess) {
            Swal.fire({
                icon: 'success',
                title: 'Registration Successful',
                text: serverSuccess,
                confirmButtonColor: '#2f855a'
            });
        }

        voterRegisterForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const name = voterRegisterForm.querySelector('input[name="name"]').value.trim();
            const voterIdInput = voterRegisterForm.querySelector('input[name="voter_id"]');
            const voterId = voterIdInput.value.trim().toUpperCase();
            voterIdInput.value = voterId;
            const mobileNumber = voterRegisterForm.querySelector('input[name="mobile_number"]').value.trim();
            const email = voterRegisterForm.querySelector('input[name="email"]').value.trim().toLowerCase();
            const password = voterRegisterForm.querySelector('input[name="password"]').value;

            if (name.length < 3) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Name',
                    text: 'Name kam se kam 3 characters ka hona chahiye.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            if (!VOTER_ID_REGEX.test(voterId)) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Voter ID',
                    text: 'Voter ID ka format ABC1234567 hona chahiye.',
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

            if (!EMAIL_REGEX.test(email)) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Invalid Email',
                    text: 'Please enter a valid email address.',
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

            // Check mobile number uniqueness via AJAX
            const formData = new FormData();
            formData.append('mobile_number', mobileNumber);

            fetch('/check-voter-mobile', {
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
                    voterRegisterForm.submit();
                });
            })
            .catch(error => {
                console.error('Error checking mobile number:', error);
                Swal.fire({
                    icon: 'warning',
                    title: 'Mobile number already exists.',
                    text: 'Could not verify mobile number. Please try again.',
                    confirmButtonColor: '#3182ce'
                });
            });
        });
    }

    // ==========================================
    // 3. Dashboard Login Alert + Vote Casting
    // ==========================================
    if (page === 'voter-dashboard') {
        const showLoginAlert = document.body.dataset.showLoginAlert === 'true';
        const electionStatus = document.body.dataset.electionStatus;

        if (showLoginAlert) {
            if (electionStatus === 'started') {
                Swal.fire({
                    icon: 'success',
                    title: 'Login Successfully',
                    text: 'Election started hai. Aap ab vote cast kar sakte hain.',
                    confirmButtonColor: '#2f855a'
                });
            } else {
                Swal.fire({
                    icon: 'info',
                    title: 'Login Successfully',
                    text: 'Election abhi start nahi hua hai. Start hote hi aap vote de paayenge.',
                    confirmButtonColor: '#3182ce'
                });
            }
        }

        const voterLogoutLink = document.querySelector('a.logout-btn[href="/voter-logout"]');
        if (voterLogoutLink) {
            voterLogoutLink.addEventListener('click', function(e) {
                e.preventDefault();

                const logoutUrl = voterLogoutLink.getAttribute('href');

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
        }
    }

    const voteForm = document.getElementById('castVoteForm');

    if (voteForm) {
        voteForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const selectedCandidate = document.querySelector('input[name="candidate_id"]:checked');

            if (!selectedCandidate) {
                Swal.fire({
                    icon: 'warning',
                    title: 'No Candidate Selected!',
                    text: 'Please select a candidate before casting your vote.',
                    confirmButtonColor: '#3182ce'
                });
                return;
            }

            Swal.fire({
                title: 'Are you sure?',
                text: 'You are about to cast your vote. This action cannot be undone!',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#38a169',
                cancelButtonColor: '#e53e3e',
                confirmButtonText: 'Yes, Cast My Vote!'
            }).then((result) => {
                if (result.isConfirmed) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Casting Vote...',
                        showConfirmButton: false,
                        timer: 1500
                    }).then(() => {
                        voteForm.submit();
                    });
                }
            });
        });
    }
});