/**
 * apply.js — Auto-Apply confirmation flow
 * Handles prepare → confirm → status polling for Selenium auto-apply
 */
document.addEventListener("DOMContentLoaded", () => {
    requireAuth();

    const prepareForm = document.getElementById("prepare-form");
    const previewSection = document.getElementById("apply-preview");
    const confirmBtn = document.getElementById("confirm-apply-btn");
    const cancelBtn = document.getElementById("cancel-apply-btn");
    const statusSection = document.getElementById("apply-status-section");
    const statusMsg = document.getElementById("apply-status-msg");

    let pendingData = null;

    if (prepareForm) {
        prepareForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const jobUrl = document.getElementById("apply-job-url")?.value.trim();
            const platform = document.getElementById("apply-platform")?.value || "linkedin";
            const resumeSelect = document.getElementById("apply-resume");
            const resumeId = resumeSelect?.value;
            const resumeName = resumeSelect?.options[resumeSelect.selectedIndex]?.text || "";

            if (!jobUrl) { showToast("Job URL is required", "error"); return; }

            const submitBtn = prepareForm.querySelector("button[type=submit]");
            submitBtn.disabled = true;
            submitBtn.innerHTML = `<span class="spinner"></span> Preparing...`;

            try {
                const res = await API.post("/apply/prepare", {
                    job_url: jobUrl,
                    platform,
                    resume_name: resumeName,
                });

                if (res && res.ok) {
                    const data = await res.json();
                    pendingData = { job_url: jobUrl, platform, resume_id: resumeId };

                    // Render preview
                    document.getElementById("preview-job-url").textContent = data.preview.job_url;
                    document.getElementById("preview-platform").textContent = data.preview.platform;
                    document.getElementById("preview-resume").textContent = data.preview.resume_name;
                    if (previewSection) previewSection.style.display = "block";
                    if (prepareForm) prepareForm.style.display = "none";
                } else {
                    const err = await res.json();
                    showToast(err.error || "Failed to prepare application", "error");
                }
            } catch (e) {
                showToast("An error occurred", "error");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `Preview Application`;
            }
        });
    }

    if (confirmBtn) {
        confirmBtn.addEventListener("click", async () => {
            if (!pendingData) return;

            confirmBtn.disabled = true;
            confirmBtn.innerHTML = `<span class="spinner"></span> Submitting...`;

            try {
                const res = await API.post("/apply/confirm", pendingData);
                if (res && res.ok) {
                    const data = await res.json();
                    if (previewSection) previewSection.style.display = "none";
                    if (statusSection) statusSection.style.display = "block";
                    if (statusMsg) {
                        statusMsg.innerHTML = `
                            <div class="status-card">
                                <div class="status-icon">🚀</div>
                                <h3>Application Submitted!</h3>
                                <p>${data.message}</p>
                                <button onclick="window.location.reload()" class="btn btn-outline" style="margin-top:1rem;">Close</button>
                            </div>
                        `;
                    }
                    showToast("Auto-apply initiated!");
                } else {
                    const err = await res.json();
                    showToast(err.error || "Auto-apply failed", "error");
                    confirmBtn.disabled = false;
                    confirmBtn.innerHTML = `✅ Confirm & Apply`;
                }
            } catch (e) {
                showToast("An error occurred during apply", "error");
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = `✅ Confirm & Apply`;
            }
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener("click", () => {
            pendingData = null;
            if (previewSection) previewSection.style.display = "none";
            if (prepareForm) prepareForm.style.display = "block";
        });
    }

    // Load resumes into apply-resume select
    const applyResumeSelect = document.getElementById("apply-resume");
    if (applyResumeSelect) {
        API.get("/resume/").then(async (res) => {
            if (res && res.ok) {
                const resumes = await res.json();
                resumes.forEach(r => {
                    const opt = document.createElement("option");
                    opt.value = r._id;
                    opt.textContent = r.parsed?.name || r.file_name;
                    applyResumeSelect.appendChild(opt);
                });
            }
        });
    }
});
