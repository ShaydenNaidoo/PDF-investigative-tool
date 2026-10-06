# Keep a Render Free lab in Google Drive

Google Drive is an optional backup for PDFs, scripts, notes, results and saved runs. Render runs investigations using local files. On a fresh instance, the app restores its last completed backup before allowing imports, saves or investigations. Without the credentials below, the app keeps using temporary Render storage.

This requires one-time Google authorization and three private Render settings. Connecting Google Drive to an assistant does not configure your deployed app. Never paste credentials into chat, GitHub, the lab URL or a script.

## One-time browser setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create/select a project and enable **Google Drive API** under **APIs & Services → Library**.
2. Configure the OAuth consent screen / Google Auth Platform. Use an external audience for a personal account and add yourself as a test user while testing. Request only `https://www.googleapis.com/auth/drive.file`, which allows access to files the app creates.
3. Under **Credentials / Clients**, create an OAuth client of type **Web application**. Add `https://developers.google.com/oauthplayground` as an authorized redirect URI.
4. Open [OAuth Playground](https://developers.google.com/oauthplayground/). In settings (gear), enable **Use your own OAuth credentials**, enter your client ID and secret, and use **Offline** access with consent prompting.
5. In Step 1, enter `https://www.googleapis.com/auth/drive.file`, authorize and sign into the account that should own backups. In Step 2, exchange the code for tokens. Copy the **refresh token**, rather than the short-lived access token.
6. In Render, select **pdf-investigative-lab → Environment**. Add these values privately:

   | Variable | Value |
   | --- | --- |
   | `PDF_LAB_DRIVE_CLIENT_ID` | Your Google OAuth client ID. |
   | `PDF_LAB_DRIVE_CLIENT_SECRET` | Your Google OAuth client secret. |
   | `PDF_LAB_DRIVE_REFRESH_TOKEN` | Your refresh token from the Playground. |
   | `PDF_LAB_DRIVE_FOLDER` | Optional unique folder name; default `PDF Analyzer Lab`. Use letters, digits, spaces, `_` or `-`. |
   | `PDF_LAB_DRIVE_SCOPE` | Optional `workspace` (default: whole lab) or `dataset` (PDFs and document IDs only). |

7. Choose **Save and deploy**. First push this revision and use **Manual Deploy → Deploy latest commit** if the image does not yet include `rclone`. The service remains Free; no paid disk or database is added.
8. Reconnect to the app with your lab access key. Open **Lab setup → Google Drive backup** and wait for preparation/restore to finish. Import your PDFs and save scripts. The app backs up automatically when idle after imports, script saves, note saves and completed investigations.
9. Wait for **BACKED UP** and a completed-backup timestamp. You can also click **Back up to Google Drive** while idle. Drive should contain the private backup folder with `dataset/`, snapshot ZIPs and `latest.json`.

Use your own OAuth credentials: tokens issued with the Playground's default client can be revoked after 24 hours. External OAuth apps in **Testing** generally issue Drive refresh tokens that expire after seven days. For continued personal use, change the consent application's publishing status to **In production**, authorize again and replace the token in Render. Follow Google's displayed requirements; `drive.file` is a recommended non-sensitive scope. [OAuth Playground](https://developers.google.com/oauthplayground/), [refresh token expiration](https://developers.google.com/identity/protocols/oauth2#expiration), [Drive scopes](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)

The app creates the backup folder. With `drive.file`, it cannot read unrelated PDFs uploaded directly to Drive; upload those through **Lab setup** first. Keep the folder private. For personal Drive use OAuth on your behalf: service accounts cannot own files in a personal account. [Google ownership guidance](https://developers.google.com/workspace/drive/api/guides/folder), [rclone Drive configuration](https://rclone.org/drive/)

## Backup and restore behavior

- Original PDFs are copied incrementally with checksums. Existing different originals cause an error instead of being overwritten; unchanged copies are skipped.
- The workspace snapshot includes observation files, custom scripts, saved notes, result tables and run logs. Temporary uploads, caches, QDF scratch folders, symbolic links and the friend's `scan_resources.sh` are excluded. Unsaved editor text and browser-local search history are not backed up.
- Two snapshot slots retain the current and previous workspace snapshots. `latest.json` is updated only after PDF and snapshot transfers succeed, so an interrupted backup leaves the previous completed snapshot available. Do not manually rename, edit or delete backup files.
- A fresh instance restores exactly the PDFs listed in the committed snapshot, verifies SHA-256 checksums, then reloads the document index and run history. Baseline observation files come from the Docker image. A run interrupted before backup completion is not guaranteed to survive.
- Dataset-only mode excludes scripts, notes, results, runs and custom exemplar changes.

Imports, saves and new investigations pause during transfer so snapshots are consistent. Browsing and exporting existing results remain available. Failed backups leave local work available and show an error; retry with the manual button. A failed startup restore must be fixed and the service restarted before backing up, so an empty lab cannot replace its saved backup.

Use **one active lab per Drive folder and OAuth client**; give separate labs distinct folder names. This is a single-owner backup, not a concurrent filesystem. Existing local PDFs, custom scripts or notes prevent startup restore from overwriting local work. Use a fresh Render instance, or remove the Drive variables to return to local operation.

## Limits and troubleshooting

Drive uses your account's available storage, and Google API quotas apply. Render's bandwidth/build limits still apply and a Free instance can be interrupted during transfer. Large restores take time and need temporary local disk space. Workspace snapshots allow 8 GiB expanded / 100,000 entries, and the dataset manifest allows 20,000 PDFs. Keep local originals and downloaded reports separately. [Drive limits](https://developers.google.com/workspace/drive/api/guides/limits), [Render Free limits](https://render.com/docs/free)

| Message | Action |
| --- | --- |
| Not configured | Add all three private settings in Render and deploy. |
| Backup tool missing | Deploy this revision's Docker image, which installs `rclone`. |
| Transfer failed | Check Drive space, your client and offline token. If consent expired/revoked, authorize again with the same client and update Render. |
| Restoring PDFs | Wait before importing/saving; large datasets need time to download. |
| Existing local work kept | Use a fresh lab or disable Drive for this local workspace. |
| Checksum/manifest error | Preserve the Drive folder and originals. Check manual modifications or use a separate backup folder. |
| Old backup timestamp | Wait for completion or use the manual button; download current reports too. |

Adding these files does not connect a Google account. Live upload/restore requires your authorization and successful deployment.
