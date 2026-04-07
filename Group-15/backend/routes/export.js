const express = require("express");
const router = express.Router();
const { exportProject } = require("../services/exportService");

router.post("/", async (req, res) => {
  try {
    const { repoName, projectName } = req.body;

    if (!repoName) {
      return res.status(400).json({ error: "Repo name required" });
    }

    // Use projectName if provided, otherwise fall back to repoName
    const effectiveProjectName = projectName || repoName;

    const repoUrl = await exportProject(repoName, effectiveProjectName);

    res.json({
      success: true,
      repoUrl,
      docker: {
        build: `docker build -t ${repoName} .`,
        run: `docker run -p 8080:80 ${repoName}`,
      },
    });
  } catch (err) {
    console.error("Export error:", err.message);

    // Provide specific error messages for common failures
    if (err.message.includes("GITHUB_TOKEN")) {
      return res.status(400).json({ error: "GitHub token is not configured. Set GITHUB_TOKEN in your .env file." });
    }
    if (err.response?.status === 422) {
      return res.status(400).json({ error: `Repository "${req.body.repoName}" already exists on GitHub. Choose a different name.` });
    }
    if (err.response?.status === 401) {
      return res.status(400).json({ error: "GitHub token is invalid or expired. Please update GITHUB_TOKEN in your .env file." });
    }

    res.status(500).json({ error: err.message || "Export failed" });
  }
});

module.exports = router;
