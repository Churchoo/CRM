# How to Release a New Version

This guide explains how to create a new release with automatically built executables for Windows and macOS.

## Quick Release Process

1. **Make your changes** to the code
2. **Commit and push** to GitHub:
   ```bash
   git add .
   git commit -m "Your changes description"
   git push
   ```

3. **Create a version tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

4. **Wait for builds** - GitHub Actions will automatically:
   - Build Windows `.exe` on a Windows runner
   - Build macOS `.app` and `.dmg` on a macOS runner
   - Create a GitHub Release with both files attached

## Manual Build Trigger

You can also trigger builds manually without creating a release:

1. Go to your GitHub repository
2. Click **Actions** tab
3. Select **Build Executables** workflow
4. Click **Run workflow** button
5. Download artifacts from the workflow run

## Version Numbering

Use semantic versioning: `vMAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (v2.0.0)
- **MINOR**: New features (v1.1.0)
- **PATCH**: Bug fixes (v1.0.1)

Examples:
- `v1.0.0` - First release
- `v1.0.1` - Bug fix
- `v1.1.0` - Added new feature
- `v2.0.0` - Major rewrite

## What Gets Built

### Windows
- **File**: `CRM.exe`
- **Size**: ~50-80 MB (includes Python + all dependencies)
- **Runs on**: Windows 10/11 (no Python installation needed)

### macOS
- **Files**: 
  - `CRM.app` - Application bundle
  - `CRM.dmg` - Disk image installer (easier to distribute)
- **Size**: ~60-90 MB (includes Python + all dependencies)
- **Runs on**: macOS 10.13+ (no Python installation needed)

## Downloading Releases

### For End Users
1. Go to your GitHub repository
2. Click **Releases** on the right sidebar
3. Download the appropriate file:
   - Windows users: `CRM.exe`
   - Mac users: `CRM.dmg`

### For Developers (Artifacts)
If you triggered a manual build:
1. Go to **Actions** tab
2. Click on the workflow run
3. Scroll to **Artifacts** section
4. Download the platform-specific artifact

## Troubleshooting

### Build Failed
- Check the **Actions** tab for error logs
- Common issues:
  - Missing dependencies in `requirements.txt`
  - Syntax errors in Python code
  - PyInstaller compatibility issues

### Can't Create Release
- Make sure you pushed the tag: `git push origin v1.0.0`
- Tag must start with `v` (e.g., `v1.0.0`, not `1.0.0`)
- Check repository permissions (need write access)

## First Time Setup

Before you can use GitHub Actions, you need to:

1. **Create a GitHub repository** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/CRM.git
   git push -u origin main
   ```

2. **Push the workflow file**:
   ```bash
   git add .github/workflows/build.yml
   git commit -m "Add GitHub Actions build workflow"
   git push
   ```

3. **Create your first release**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

That's it! GitHub Actions will automatically build both executables.
