/**
 * ats.js — ATS Score Analysis UI
 * Fixed: endpoint /resume/ (was /resume/list), proper response rendering,
 * matched keyword display, and structured AI suggestions rendering.
 */
document.addEventListener("DOMContentLoaded", async () => {
    requireAuth();

    const resumeSelect = document.getElementById("resume-select");
    const jdInput = document.getElementById("jd-input");
    const scoreBtn = document.getElementById("score-btn");
    const resultsContainer = document.getElementById("results-container");
    const scoreValue = document.getElementById("score-value");
    const scoreRing = document.querySelector(".score-ring");
    const ratingLabel = document.getElementById("rating-label");
    const matchedKeywords = document.getElementById("matched-keywords");
    const missingKeywords = document.getElementById("missing-keywords");
    const skillGapMatched = document.getElementById("skill-gap-matched");
    const skillGapMissing = document.getElementById("skill-gap-missing");
    const aiSuggestions = document.getElementById("ai-suggestions");

    const proposedChangesCard = document.getElementById("proposed-changes-card");
    const proposedSummary = document.getElementById("proposed-summary");
    const proposedExperience = document.getElementById("proposed-experience");
    const proposedSkills = document.getElementById("proposed-skills");
    const applyChangesBtn = document.getElementById("apply-changes-btn");
    
    let currentAtsData = null;

    // Check if we came from job recommendations with a pending job description
    const pendingJd = sessionStorage.getItem("pending_jd");
    if (pendingJd && jdInput) {
        jdInput.value = pendingJd;
        sessionStorage.removeItem("pending_jd");
    }

    // Load resumes into select — FIXED: was /resume/list, now /resume/
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
                // active_resume_id might be stored as an object { $oid: "..." } if using MongoJSONProvider, or a string
                activeResumeId = userData.active_resume_id?.$oid || userData.active_resume_id;
            }

            if (resumeSelect) {
                if (resumes.length === 0) {
                    resumeSelect.innerHTML = `<option value="">No resumes — upload one first</option>`;
                } else {
                    resumes.forEach(r => {
                        const opt = document.createElement("option");
                        // r._id might be an object or string depending on MongoJSONProvider
                        const rId = r._id?.$oid || r._id;
                        opt.value = rId;
                        opt.textContent = r.parsed?.name || r.file_name;
                        if (activeResumeId && rId === activeResumeId) {
                            opt.selected = true;
                        }
                        resumeSelect.appendChild(opt);
                    });
                    
                    // If no resume was marked as selected but we have resumes, the first one will be selected by default by the browser.
                }
            }
            
            // Check for persisted analysis AFTER loading resumes
            const persistedAnalysis = sessionStorage.getItem("ats_analysis_data");
            if (persistedAnalysis) {
                try {
                    const parsed = JSON.parse(persistedAnalysis);
                    if (jdInput && parsed.jd) jdInput.value = parsed.jd;
                    if (resumeSelect && parsed.resumeId) resumeSelect.value = parsed.resumeId;
                    renderResults(parsed.data, false);
                } catch(e) {}
            }
        }
    } catch (e) {
        console.error("Failed to load resumes", e);
    }

    if (scoreBtn) {
        scoreBtn.addEventListener("click", async () => {
            const resumeId = resumeSelect ? resumeSelect.value : "";
            const jd = jdInput ? jdInput.value.trim() : "";

            if (!jd) {
                showToast("Please paste a job description", "error");
                return;
            }
            if (!resumeId) {
                showToast("Please select a resume", "error");
                return;
            }

            scoreBtn.disabled = true;
            scoreBtn.innerHTML = `<span class="spinner"></span> Calculating...`;

            try {
                const payload = { job_description: jd, resume_id: resumeId };
                const res = await API.post("/ats/score", payload);
                if (res && res.ok) {
                    const data = await res.json();
                    sessionStorage.setItem("ats_analysis_data", JSON.stringify({
                        jd: jd,
                        resumeId: resumeId,
                        data: data
                    }));
                    renderResults(data, true);
                } else {
                    const err = await res.json();
                    showToast(err.error || "Failed to calculate score", "error");
                }
            } catch (e) {
                showToast("An error occurred", "error");
                console.error(e);
            } finally {
                scoreBtn.disabled = false;
                scoreBtn.innerHTML = `📊 Calculate ATS Score`;
            }
        });
    }

    function renderResults(data, scroll = true) {
        currentAtsData = data;
        if (resultsContainer) resultsContainer.style.display = "block";

        const score = data.ats?.score ?? 0;
        if (scoreRing) {
            scoreRing.style.setProperty("--pct", score);
            // Color based on score
            const color = score >= 80 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--danger)";
            scoreRing.style.background = `conic-gradient(${color} calc(${score} * 3.6deg), rgba(255,255,255,0.1) 0deg)`;
        }
        if (scoreValue) scoreValue.textContent = `${score}%`;
        if (ratingLabel) {
            ratingLabel.textContent = data.ats?.rating ?? "—";
            const ratingColor = score >= 80 ? "var(--success)" : score >= 60 ? "var(--warning)" : "var(--danger)";
            ratingLabel.style.color = ratingColor;
        }

        // Matched keywords
        if (matchedKeywords) {
            const matched = data.ats?.matched_keywords || [];
            matchedKeywords.innerHTML = matched.length
                ? matched.map(k => `<span class="kw-tag kw-matched">${k}</span>`).join("")
                : `<span style="color:var(--text-muted)">None detected</span>`;
        }

        // Missing keywords
        if (missingKeywords) {
            const missing = data.ats?.missing_keywords || [];
            missingKeywords.innerHTML = missing.length
                ? missing.map(k => `<span class="kw-tag kw-missing">${k}</span>`).join("")
                : `<span style="color:var(--success)">🎉 All keywords covered!</span>`;
        }

        // Skill gap
        if (skillGapMatched) {
            const sgMatched = data.skill_gap?.matched_skills || [];
            skillGapMatched.innerHTML = sgMatched.length
                ? sgMatched.map(s => `<span class="kw-tag kw-matched">${s}</span>`).join("")
                : `<span style="color:var(--text-muted)">None</span>`;
        }
        if (skillGapMissing) {
            const sgMissing = data.skill_gap?.missing_skills || [];
            skillGapMissing.innerHTML = sgMissing.length
                ? sgMissing.map(s => `<span class="kw-tag kw-missing">${s}</span>`).join("")
                : `<span style="color:var(--success)">✅ All skills present!</span>`;
        }

        // AI suggestions
        if (aiSuggestions) {
            const sugg = data.suggestions;
            if (!sugg || sugg.error) {
                aiSuggestions.innerHTML = `<p style="color:var(--text-muted)">No suggestions available.</p>`;
                return;
            }
            let html = "";
            if (sugg.improvements?.length) {
                html += `<h4 style="color:var(--primary);margin-bottom:.5rem;">💡 Improvements</h4><ul class="sugg-list">`;
                sugg.improvements.forEach(i => { html += `<li>${i}</li>`; });
                html += `</ul>`;
            }
            if (sugg.keyword_suggestions?.length) {
                html += `<h4 style="color:var(--secondary);margin:.75rem 0 .5rem;">🔑 Keyword Tips</h4><ul class="sugg-list">`;
                sugg.keyword_suggestions.forEach(k => { html += `<li>${k}</li>`; });
                html += `</ul>`;
            }
            if (sugg.language_upgrades?.length) {
                html += `<h4 style="color:var(--warning);margin:.75rem 0 .5rem;">✍️ Language Upgrades</h4><ul class="sugg-list">`;
                sugg.language_upgrades.forEach(l => { html += `<li>${l}</li>`; });
                html += `</ul>`;
            }
            aiSuggestions.innerHTML = html || `<p style="color:var(--text-muted)">No specific suggestions.</p>`;
        }
        
        // Proposed Changes
        if (proposedChangesCard) {
            const sugg = data.suggestions || {};
            const missing = data.ats?.missing_keywords || [];
            
            let hasChanges = false;
            
            if (proposedSummary && sugg.revised_summary) {
                proposedSummary.textContent = sugg.revised_summary;
                proposedSummary.parentElement.style.display = "block";
                hasChanges = true;
            } else if (proposedSummary) {
                proposedSummary.parentElement.style.display = "none";
            }
            
            if (proposedExperience && sugg.revised_experience && sugg.revised_experience.length > 0) {
                let html = "";
                sugg.revised_experience.forEach(ex => {
                    html += `<div style="margin-bottom:0.75rem;"><strong>${ex.title || ''} at ${ex.company || ''}</strong><br/>`;
                    html += `<span style="color:var(--text-muted);font-size:0.8rem;">${ex.start || ''} - ${ex.end || ''}</span>`;
                    if (ex.bullets && ex.bullets.length) {
                        html += `<ul style="margin:0.25rem 0 0 1.2rem;padding:0;">`;
                        ex.bullets.forEach(b => html += `<li>${b}</li>`);
                        html += `</ul>`;
                    }
                    html += `</div>`;
                });
                proposedExperience.innerHTML = html;
                proposedExperience.parentElement.style.display = "block";
                hasChanges = true;
            } else if (proposedExperience) {
                proposedExperience.parentElement.style.display = "none";
            }
            
            if (proposedSkills) {
                if (missing.length > 0) {
                    proposedSkills.innerHTML = missing.map(k => `<span class="kw-tag kw-matched">${k}</span>`).join("");
                    proposedSkills.parentElement.style.display = "block";
                    hasChanges = true;
                } else {
                    proposedSkills.parentElement.style.display = "none";
                }
            }
            
            if (hasChanges) {
                proposedChangesCard.style.display = "block";
                // Show the proposed changes card when rendering results
                document.getElementById("proposed-changes-card").style.display = "block";
            } else {
                proposedChangesCard.style.display = "none";
            }
        }

        // Scroll to results
        if (scroll && resultsContainer) {
            resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        // Notify template to show keyword/suggestions sections
        document.dispatchEvent(new Event("ats:results"));
    }
    
    if (applyChangesBtn) {
        applyChangesBtn.addEventListener("click", async () => {
            if (!currentAtsData) return;
            const resumeId = resumeSelect ? resumeSelect.value : "";
            if (!resumeId) return;
            
            const payload = {
                resume_id: resumeId,
                revised_summary: currentAtsData.suggestions?.revised_summary,
                revised_experience: currentAtsData.suggestions?.revised_experience,
                missing_keywords: currentAtsData.ats?.missing_keywords || []
            };
            
            applyChangesBtn.disabled = true;
            applyChangesBtn.innerHTML = `<span class="spinner"></span> Applying...`;
            
            try {
                const res = await API.post("/ats/apply-changes", payload);
                if (res && res.ok) {
                    showToast("Profile and resume updated successfully!", "success");
                    if (proposedChangesCard) proposedChangesCard.style.display = "none";
                    sessionStorage.removeItem("ats_analysis_data");
                } else {
                    const err = await res.json();
                    showToast(err.error || "Failed to apply changes", "error");
                }
            } catch (e) {
                showToast("An error occurred", "error");
                console.error(e);
            } finally {
                applyChangesBtn.disabled = false;
                applyChangesBtn.innerHTML = `✅ Apply Changes to Resume`;
            }
        });
    }
});
