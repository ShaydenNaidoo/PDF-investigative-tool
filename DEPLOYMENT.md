# PDF Analyzer on GitHub Pages and Render

GitHub Pages hosts the interface. Render Free runs the Docker lab with Python, Bash, qpdf, Poppler and scripts. Connect each device to the same active Render lab to share PDFs, saved scripts, results and notes during a session. Remote storage is temporary; keep originals and scripts on your device and download results as you work.

The repository includes `.github/workflows/pages.yml` and `render.yaml`. These prepare deployment; the website is live only after GitHub and Render report successful deployments.

## Publish the interface

1. Push these changes to `main` in [ShaydenNaidoo/PDF-investigative-tool](https://github.com/ShaydenNaidoo/PDF-investigative-tool).
2. In the repository’s **Settings → Pages**, select **GitHub Actions** as the publishing source.
3. Open **Actions → Publish PDF Analyzer interface**, run the workflow on `main`, and wait for `build` and `deploy` to succeed. Future interface changes trigger it automatically.
4. Open the deployment URL. The expected project URL is `https://shaydennaidoo.github.io/PDF-investigative-tool/`.

Only HTML, CSS, JavaScript, the scene and licensed PDF assets are included. The Pages artifact excludes Python files, scripts, PDFs, archives, results, personal notes and access keys. Assets use relative paths so the repository subdirectory works correctly.

GitHub Pages cannot execute Python or Bash. The interface therefore asks for a Render lab URL and access key until connected. [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

## Deploy the free backend

1. Sign in to Render and connect this GitHub repository.
2. Choose **New → Blueprint**, select this repository and `main`, and use `render.yaml`.
3. Check that the service uses the **Free** instance type. The blueprint requests one Docker web service, with no persistent disk or database. Free services sleep after 15 minutes without requests and take about a minute to wake. Uploaded files and workspace changes are lost on sleep, restart or redeploy. [Free service limitations](https://render.com/docs/free)
4. Confirm the deployment. The Docker build installs the lab tools. Each fresh instance receives the baseline observation files; the server and scripts run as the unprivileged `lab` user. Upload your PDFs through the app.
5. Wait for the service to be **Live** and healthy. Copy its actual HTTPS URL from Render. The assigned hostname may include a suffix; do not assume an example hostname is yours.
6. In the service’s **Environment** settings, copy the generated `PDF_LAB_ACCESS_KEY` directly into the app’s connection form. Keep it out of GitHub, URLs and chat messages.

| Setting | Purpose |
| --- | --- |
| `PDF_LAB_REMOTE=1` | Protect every evidence, result, script and upload API. |
| `PDF_LAB_ACCESS_KEY` | Generated private key. Remote startup rejects a missing key or one shorter than 32 characters. |
| `PDF_LAB_ALLOWED_ORIGINS=https://shaydennaidoo.github.io` | Permit authenticated requests from Pages. An origin has no repository path or trailing slash. |
| `RENDER_EXTERNAL_HOSTNAME` | Render supplies its assigned hostname; the backend permits it automatically. |
| `PORT` | Render supplies the HTTP port; the server and health check respect it. |
| `PDF_LAB_EPHEMERAL=1` | Show the temporary-storage notice in Lab setup. This does not provide backups. |

You can also open the Render URL directly and connect with the same key. For another hostname, configure `PDF_LAB_ALLOWED_HOSTS` as an explicit comma-separated list. For another interface origin, extend `PDF_LAB_ALLOWED_ORIGINS`. Wildcard hosts and origins are rejected.

This is a private single-owner lab. Anyone with its key can read the workspace and run scripts inside its container. Keep the key private; unrelated users should deploy separate labs. Requests send the key in an authorization header. It is stored only for the browser session, rather than in permanent browser storage or attachment URLs.

## Use another device

1. Open the deployed Pages URL on your phone, tablet or computer.
2. Choose **Connect lab**, enter the actual Render HTTPS URL and access key, and select **Connect to lab**.
3. Open **Lab setup** and import the assignment PDFs or ZIP. Your existing local corpus and runs are separate and are not automatically uploaded.
4. Use **Script studio** to build and run scripts, **Evidence explorer** to inspect PDFs, and **Run history** to reopen saved results.
5. On another device, connect to the same Render URL. Lab work is shared while that instance remains active; document search history stays specific to each browser. After a sleep or restart, import your PDFs and save your scripts again.

The browser remembers the URL. A new browser session may require the key again. **Connect lab → Disconnect** removes the connection from that browser without deleting remote evidence.

## Export results as PDF

- **Evidence explorer → Export PDF:** every document/resource row matching the search and filters, across all pages.
- **Tool comparison → Export PDF:** the full tool matrix and sparse-evidence threshold.
- **Investigation results → Export PDF:** every matching row in the selected saved table, including the run ID, table name and search.
- **Live output → Export entire run PDF:** all tables in a completed run without search filters, plus complete output and progress/error logs.
- **Results summary → Export PDF:** counts, active scope, the selected bar-chart measure and every summary category across all pages.
- **Document dossier → Export view PDF:** the selected resources, numbering/reuse, toolmarks, strings/tags, metadata or notes view. Resource/numbering exports include all entries. Strings include all matching indexed records and disclose index limits. Metadata includes matching fields and XMP within its reported preview limit.
- **Object preview → Export PDF:** the current original object definition or decoded stream, with source references and any preview limit.
- **Field notebook → Export PDF:** current notebook text and saved document notes. The dossier notes export includes current editor text too.

PDFs download directly without a print dialog or external CDN. Reports use A4 landscape pages, readable tables, embedded fonts, generation timestamps and page numbers. Detailed large tables can create long PDFs; summary exports provide a compact report. Progress appears during generation.

## Download and preserve evidence

Automatic backend deployment is disabled so a push does not interrupt an investigation. When the lab is idle, choose **Render → Manual Deploy** for the new commit. Pages publishing remains automatic; deploy the matching backend when an update changes the API.

Render Free has no persistent disk. `/workspace/dataset`, `/workspace/environment/observations` and `/workspace/home` are temporary, including uploaded PDFs, custom scripts, notes and runs. Baseline observation files bundled in the image are restored when a new instance starts; your added work is not. Keeping the browser open is not a backup, and Render may restart free instances at any time.

For each investigation:

1. Keep the original PDFs/assignment ZIP and the script source on your device.
2. Import the originals and paste/save your script in the remote GUI.
3. Run the investigation, then download its result tables as CSV and its complete run or summary as PDF.
4. Export notebook/document notes as PDF and retain editable notes separately.
5. Confirm that the downloads are saved on your device before leaving. These downloads survive a server reset; the app does not automatically restore them into Run history.

Local Docker still uses its persistent volume. Your local lab is separate from Render and remains an option for larger investigations or long-term workspace storage. Never commit a workspace backup to the public repository.

Render includes 750 free instance hours per workspace each month, shared by free web services. Bandwidth and build usage also have limits; check the dashboard's usage and spending settings. A Free instance does not guarantee unlimited free usage. [Render's usage limits](https://render.com/docs/free)

## Troubleshooting

| Problem | Check |
| --- | --- |
| Pages returns 404 | Enable GitHub Actions as its source and check the deployment workflow. |
| Connection fails | Use the actual Render HTTPS base URL and wait for the service to be Live. |
| Key requested again | Enter the current `PDF_LAB_ACCESS_KEY`; it is not permanently saved in the browser. |
| Cross-origin request fails | Allow `https://shaydennaidoo.github.io` exactly, without the repository path. |
| Startup fails | Check the generated key, Docker runtime, `PORT` and environment settings. |
| PDFs missing remotely | Import them into this lab; local data is a separate workspace. |
| Uploaded PDFs, scripts or runs disappeared | Free storage resets on sleep, restart and redeploy. Reimport originals and recreate scripts from your device copies; use downloaded PDF/CSV files for previous evidence. |
| First connection takes about a minute | The free service may be waking. Wait for Live status and retry connecting. |
| PDF export reports an old server | Deploy the matching backend revision. Local users should rebuild Docker and refresh. |
| Investigation exceeds memory | Increase the service’s compute plan or investigate smaller sets. |

## Local validation

```bash
python3 -m unittest discover -s pdf-analyzer -v
python3 pdf-analyzer/build_pages.py
```

The generated `.pages-build/` folder is ignored by Git. Native and local Docker operation remain available without remote credentials.
