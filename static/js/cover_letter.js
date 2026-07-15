/**
 * cover_letter.js — AI Cover Letter Generator
 * Fixed: API response uses `content` not `cover_letter`; added resume/job dropdowns;
 * added role & company inputs; implemented Save handler.
 */
document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();

    const generateBtn = document.getElementById("generate-btn");
    const saveBtn = document.getElementById("save-cl-btn");
    const editor = document.getElementById("cl-editor");
    const jdInput = document.getElementById("cl-jd");
    const resumeSelect = document.getElementById("cl-resume");
    const roleInput = document.getElementById("cl-role");
    const companyInput = document.getElementById("cl-company");
    const historyList = document.getElementById("cl-history");

    let currentLetterId = null;

    // Check if we came from job recommendations with pending data
    const pendingJd = sessionStorage.getItem("pending_cl_jd");
    if (pendingJd && jdInput) {
        jdInput.value = pendingJd;
        sessionStorage.removeItem("pending_cl_jd");
    }
    const pendingRole = sessionStorage.getItem("pending_cl_role");
    if (pendingRole && roleInput) {
        roleInput.value = pendingRole;
        sessionStorage.removeItem("pending_cl_role");
    }
    const pendingCompany = sessionStorage.getItem("pending_cl_company");
    if (pendingCompany && companyInput) {
        companyInput.value = pendingCompany;
        sessionStorage.removeItem("pending_cl_company");
    }

    // Load resumes into dropdown
    async function loadResumes() {
        if (!resumeSelect) return;
        try {
            const [res, userRes] = await Promise.all([
                API.get("/resume/"),
                API.get("/auth/me")
            ]);
            
            if (res && res.ok) {
                const resumes = await res.json();
                let activeResumeId = null;
                
                if (userRes && userRes.ok) {
                    const userData = await userRes.json();
                    activeResumeId = userData.active_resume_id?.$oid || userData.active_resume_id;
                }
                
                // Clear the "Loading..." option
                resumeSelect.innerHTML = "";

                if (resumes.length === 0) {
                    resumeSelect.innerHTML = `<option value="">No resumes — upload one first</option>`;
                } else {
                    resumes.forEach(r => {
                        const opt = document.createElement("option");
                        const rId = r._id?.$oid || r._id;
                        opt.value = rId;
                        opt.textContent = r.parsed?.name || r.file_name;
                        if (activeResumeId && rId === activeResumeId) {
                            opt.selected = true;
                        }
                        resumeSelect.appendChild(opt);
                    });
                }
            }
        } catch (e) {
            console.error("Failed to load resumes", e);
        }
    }

    // Load cover letter history
    async function loadHistory() {
        if (!historyList) return;
        try {
            const res = await API.get("/cover-letter/");
            if (res && res.ok) {
                const letters = await res.json();
                if (letters.length === 0) {
                    historyList.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:1rem;">No saved cover letters yet.</p>`;
                    return;
                }
                historyList.innerHTML = "";
                letters.forEach(l => {
                    const item = document.createElement("div");
                    item.className = "cl-history-item";
                    item.innerHTML = `
                        <div class="cl-history-info">
                            <strong>${l.role || "Untitled"}</strong>
                            <span>${l.company || "—"}</span>
                        </div>
                        <button class="btn btn-outline btn-sm" onclick="loadLetter('${l._id}', \`${escapeBacktick(l.content)}\`)">Load</button>
                    `;
                    historyList.appendChild(item);
                });
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    function escapeBacktick(str) {
        return (str || "").replace(/`/g, "\\`").replace(/\$/g, "\\$");
    }

    await loadResumes();
    await loadHistory();

    if (generateBtn) {
        generateBtn.addEventListener("click", async () => {
            const resumeId = resumeSelect ? resumeSelect.value : "";
            const jd = jdInput ? jdInput.value.trim() : "";
            const role = roleInput ? roleInput.value.trim() : "";
            const company = companyInput ? companyInput.value.trim() : "";

            if (!resumeId) {
                showToast("Please select a resume", "error");
                return;
            }
            if (!jd) {
                showToast("Please paste a job description", "error");
                return;
            }

            generateBtn.disabled = true;
            generateBtn.innerHTML = `<span class="spinner"></span> Generating...`;
            if (editor) editor.value = "✨ AI is crafting your cover letter... Please wait (10-20 seconds)";

            try {
                const res = await API.post("/cover-letter/generate", {
                    resume_id: resumeId,
                    job_description: jd,
                    role: role,
                    company: company,
                });

                if (res && res.ok) {
                    const data = await res.json();
                    // FIXED: API returns `content`, not `cover_letter`
                    if (editor) editor.value = data.content || "No content returned.";
                    currentLetterId = data.cover_letter_id;
                    showToast("Cover letter generated!");
                    await loadHistory();
                } else {
                    const err = await res.json();
                    if (editor) editor.value = "";
                    showToast(err.error || "Failed to generate cover letter", "error");
                }
            } catch (e) {
                if (editor) editor.value = "";
                showToast("An error occurred while generating", "error");
                console.error(e);
            } finally {
                generateBtn.disabled = false;
                generateBtn.innerHTML = `✨ Generate Cover Letter`;
            }
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener("click", async () => {
            const content = editor ? editor.value.trim() : "";
            if (!content) {
                showToast("Nothing to save — generate a cover letter first.", "error");
                return;
            }
            // Copy to clipboard
            try {
                await navigator.clipboard.writeText(content);
                showToast("Cover letter copied to clipboard!");
            } catch (e) {
                showToast("Could not copy — please copy manually.", "error");
            }
        });
    }

    // Copy button
    const copyBtn = document.getElementById("copy-cl-btn");
    if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
            const content = editor ? editor.value.trim() : "";
            if (!content) return;
            try {
                await navigator.clipboard.writeText(content);
                showToast("Copied to clipboard!");
            } catch (e) {
                showToast("Could not copy automatically.", "error");
            }
        });
    }
});

function loadLetter(id, content) {
    const editor = document.getElementById("cl-editor");
    if (editor) {
        editor.value = content;
        editor.scrollIntoView({ behavior: "smooth" });
        showToast("Cover letter loaded.");
    }
}
