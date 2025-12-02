const app = {
  // Check authentication on page load
  checkAuth: async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const portal = urlParams.get('portal');

    // If portal parameter exists, show that portal
    if (portal === 'admin') {
      const userRole = sessionStorage.getItem('user_role');
      if (userRole === 'admin') {
        app.showAdminPortal();
      } else {
        window.location.href = '/static/admin_login.html';
      }
    } else if (portal === 'recruiter') {
      const userRole = sessionStorage.getItem('user_role');
      if (userRole === 'recruiter') {
        app.showRecruiterPortal();
      } else {
        window.location.href = '/static/recruiter_login.html';
      }
    }
  },

  // Navigation Logic
  showLanding: () => {
    document.getElementById('landing-page').classList.remove('hidden');
    document.getElementById('admin-portal').classList.add('hidden');
    document.getElementById('recruiter-portal').classList.add('hidden');
  },

  showAdminPortal: () => {
    document.getElementById('landing-page').classList.add('hidden');
    document.getElementById('admin-portal').classList.remove('hidden');
    document.getElementById('recruiter-portal').classList.add('hidden');
  },

  showRecruiterPortal: () => {
    document.getElementById('landing-page').classList.add('hidden');
    document.getElementById('admin-portal').classList.add('hidden');
    document.getElementById('recruiter-portal').classList.remove('hidden');
    // Default to first step
    app.showStep('step-jd');
  },

  logout: async () => {
    try {
      await fetch('/auth/logout', { method: 'POST' });
      sessionStorage.clear();
      window.location.href = '/';
    } catch (err) {
      console.error('Logout error:', err);
      sessionStorage.clear();
      window.location.href = '/';
    }
  },

  showStep: (stepId) => {
    // 1. Hide all step contents
    document.querySelectorAll('.step-content').forEach(el => el.classList.add('hidden'));

    // 2. Show selected step content
    document.getElementById(stepId).classList.remove('hidden');

    // 3. Update active state on nodes
    document.querySelectorAll('.step-node').forEach(el => el.classList.remove('active'));

    // Map step IDs to node IDs
    const nodeMap = {
      'step-jd': 'node-jd',
      'step-analysis': 'node-analysis',
      'step-outreach': 'node-outreach',
      'step-interview': 'node-interview'
    };

    const nodeId = nodeMap[stepId];
    if (nodeId) {
      document.getElementById(nodeId).classList.add('active');
    }
  },

  handleTopKChange: () => {
    const select = document.getElementById('top-k-select');
    const customGroup = document.getElementById('custom-top-k-group');

    if (select.value === 'custom') {
      customGroup.style.display = 'block';
    } else {
      customGroup.style.display = 'none';
    }
  },

  checkInterviewStatus: async () => {
    const tbody = document.getElementById('interview-status-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">Loading status...</td></tr>';

    try {
      const res = await fetch('/interviews/status');
      const data = await res.json();

      tbody.innerHTML = '';
      if (!data.interviews || data.interviews.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No interviews scheduled yet</td></tr>';
        return;
      }

      data.interviews.forEach(interview => {
        const statusClass = interview.status === 'confirmed' ? 'score-high' :
          interview.status === 'pending' ? 'score-medium' : 'score-low';

        // Create actions cell with both Meeting and Calendar links
        let actionsHTML = 'Pending';
        if (interview.event_link) {
          actionsHTML = `
            <a href="${interview.event_link}" target="_blank" style="margin-right: 8px;">📅 Calendar</a>
            <a href="${interview.event_link}" target="_blank">🎥 Meet</a>
          `;
        }

        // Format time if available
        let timeDisplay = 'TBD';
        if (interview.confirmed_time) {
          timeDisplay = new Date(interview.confirmed_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else if (interview.selected_slot) {
          timeDisplay = interview.selected_slot;
        }

        const row = `
          <tr>
            <td><strong>${interview.candidate_name}</strong></td>
            <td>${interview.candidate_email}</td>
            <td>${interview.jd_title}</td>
            <td>${new Date(interview.interview_date).toLocaleDateString()}</td>
            <td>${timeDisplay}</td>
            <td><span class="score-badge ${statusClass}">${interview.status}</span></td>
            <td>${actionsHTML}</td>
            <td>${interview.interviewer_email || 'N/A'}</td>
          </tr>
        `;
        tbody.innerHTML += row;
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" style="color: red; text-align:center;">Error: ${err.message}</td></tr>`;
    }
  },

  loadOutreachLogs: async () => {
    const tbody = document.getElementById('outreach-logs-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading...</td></tr>';

    try {
      const res = await fetch('/outreach/logs');
      const data = await res.json();

      tbody.innerHTML = '';
      if (data.logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No outreach logs yet</td></tr>';
        return;
      }

      data.logs.forEach(log => {
        const statusClass = log.acknowledgement === 'interested' ? 'score-high' :
          log.acknowledgement === 'not_interested' ? 'score-low' : 'score-medium';
        const statusText = log.acknowledgement === 'interested' ? '✅ Interested' :
          log.acknowledgement === 'not_interested' ? '❌ Not Interested' : '⏳ Pending';

        const row = `
          <tr>
            <td><strong>${log.candidate_name || 'Unknown'}</strong></td>
            <td>${log.candidate_email}</td>
            <td><span class="score-badge ${statusClass}">${log.ats_score}%</span></td>
            <td>${statusText}</td>
            <td>${new Date(log.sent_at).toLocaleString()}</td>
          </tr>
        `;
        tbody.innerHTML += row;
      });

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="color: red; text-align:center;">Error: ${err.message}</td></tr>`;
    }
  },

  init: () => {
    // Check authentication on page load
    app.checkAuth();

    // Helper to fetch rankings using JD embedding
    const fetchRankings = async (jdId, topK) => {
      const resultsArea = document.getElementById('results-area');
      const tbody = document.getElementById('results-body');
      const noResults = document.getElementById('no-results-placeholder');

      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Loading analysis...</td></tr>';
      resultsArea.classList.remove('hidden');
      noResults.classList.add('hidden');

      // Switch to Analysis tab automatically
      app.showStep('step-analysis');

      const formData = new FormData();
      formData.append('jd_id', jdId);
      formData.append('top_k', topK);

      try {
        const res = await fetch('/match/top-by-jd', {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        tbody.innerHTML = '';
        if (data.matches.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No matches found.</td></tr>';
          return;
        }

        // Store candidate IDs for email sending
        const candidateIds = [];

        data.matches.forEach(match => {
          candidateIds.push(match.resume_id);
          const scoreClass = match.ats_score >= 80 ? 'score-high' : (match.ats_score >= 50 ? 'score-medium' : 'score-low');
          const row = `
            <tr>
              <td>#${match.rank}</td>
              <td><strong>${match.candidate_name || 'Unknown'}</strong></td>
              <td><span class="score-badge ${scoreClass}">${match.ats_score}%</span></td>
              <td>${match.file_name}</td>
              <td id="status-${match.resume_id}">Pending</td>
            </tr>
          `;
          tbody.innerHTML += row;
        });

        // Automatically send emails to all matched candidates
        if (candidateIds.length > 0) {
          // Update status column to "Sending..."
          candidateIds.forEach(id => {
            const statusCell = document.getElementById(`status-${id}`);
            if (statusCell) statusCell.innerText = 'Sending Email...';
          });

          await sendEmailsToCandidates(jdId, candidateIds);
        }

      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" style="color: red; text-align:center;">Error: ${err.message}</td></tr>`;
      }
    };

    // Helper to send emails to candidates
    const sendEmailsToCandidates = async (jdId, candidateIds) => {
      try {
        const formData = new FormData();
        formData.append('jd_id', jdId);
        candidateIds.forEach(id => formData.append('candidate_ids', id));

        const res = await fetch('/send-emails', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        // Update status in the table
        candidateIds.forEach(id => {
          const statusCell = document.getElementById(`status-${id}`);
          if (statusCell) {
            statusCell.innerHTML = '<span style="color: green">Email Sent ✅</span>';
          }
        });

      } catch (err) {
        console.error("Email error:", err);
        // Update status to error
        candidateIds.forEach(id => {
          const statusCell = document.getElementById(`status-${id}`);
          if (statusCell) {
            statusCell.innerHTML = '<span style="color: red">Failed ❌</span>';
          }
        });
      }
    };

    // Admin: Resume Upload
    document.getElementById('admin-upload-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const files = document.getElementById('resume-files').files;
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      const output = document.getElementById('admin-output');
      output.innerHTML = '<span class="pulse-animation">Uploading...</span>';

      try {
        const res = await fetch('/resumes/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        output.innerHTML = `<div style="color: var(--success-color)">Successfully processed ${data.count} resumes.</div>`;

      } catch (err) {
        output.innerHTML = `<div style="color: var(--danger-color)">Error: ${err.message}</div>`;
      }
    });

    // Admin: Init DB
    document.getElementById('init-db-btn').addEventListener('click', async () => {
      const output = document.getElementById('init-output');
      output.innerHTML = 'Initializing...';
      try {
        const res = await fetch('/init-db', { method: 'POST' });
        const data = await res.json();
        output.innerHTML = 'Database Initialized!';
      } catch (err) {
        output.innerHTML = `Error: ${err.message}`;
      }
    });

    // Recruiter: JD Upload & Rank
    document.getElementById('jd-upload-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const file = document.getElementById('jd-file').files[0];

      // Get topK based on selection
      const topKSelect = document.getElementById('top-k-select').value;
      let topK;

      if (topKSelect === 'all') {
        topK = 1000; // Large number to get all results
      } else {
        topK = parseInt(document.getElementById('top-k-input').value) || 5;
      }

      const formData = new FormData();
      formData.append('file', file);

      const output = document.getElementById('jd-output');
      output.innerHTML = 'Uploading and analyzing JD...';

      try {
        const res = await fetch('/jd/analyze/pdf', {
          method: 'POST',
          body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        const detectedRole = data.role || 'Unknown';
        output.innerHTML = `<div style="color: var(--success-color)">JD Analyzed! Role detected: <b>${detectedRole}</b></div>`;

        // Store the database ID for embedding-based matching
        const jdId = data.id;

        if (!jdId) {
          output.innerHTML += `<div style="color: red; margin-top: 5px;">Error: JD ID not returned from server.</div>`;
          return;
        }

        document.getElementById('jd-database-id').value = jdId;

        // Auto-fetch rankings using embedding similarity
        output.innerHTML += `<div style="color: var(--primary-color); margin-top: 5px;">Auto-fetching top ${topK} matches...</div>`;
        await fetchRankings(jdId, topK);

      } catch (err) {
        output.innerHTML = `<div style="color: red">Error: ${err.message}</div>`;
      }
    });
  }
};

// Initialize app
document.addEventListener('DOMContentLoaded', app.init);
