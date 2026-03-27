document.addEventListener('DOMContentLoaded', function() {

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