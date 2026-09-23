# Git & GitHub — Command Reference

The commands you'll actually use day to day, with runnable examples.

> **Convention:** lines starting with `$` are what you type; `#` lines are comments.
> Placeholders look like `<this>` — replace them, angle brackets included.

---

## Table of Contents

1. [One-time Setup](#1-one-time-setup)
2. [Starting a Repository](#2-starting-a-repository)
3. [The Everyday Loop](#3-the-everyday-loop-status--add--commit)
4. [Looking at History & Changes](#4-looking-at-history--changes)
5. [Branching](#5-branching)
6. [Merging & Resolving Conflicts](#6-merging--resolving-conflicts)
7. [Working with Remotes](#7-working-with-remotes-github)
8. [Undoing Things](#8-undoing-things)
9. [Stashing Work in Progress](#9-stashing-work-in-progress)
10. [.gitignore](#10-gitignore)
11. [Pull Requests](#11-pull-requests)
12. [A Typical Workflow](#12-a-typical-workflow)
13. [Quick Reference Table](#13-quick-reference-table)

---

## 1. One-time Setup

Tell Git who you are — this gets stamped onto every commit you make.

```bash
# Identity (use --global once per machine)
$ git config --global user.name "Shivam Prasad"
$ git config --global user.email "you@example.com"

# Make 'main' the default branch name for new repos
$ git config --global init.defaultBranch main

# Pick your editor for commit messages
$ git config --global core.editor "code --wait"     # VS Code
$ git config --global core.editor "vim"             # Vim

# See everything that's configured
$ git config --list
```

---

## 2. Starting a Repository

### Create a new repo locally

```bash
$ mkdir my-project && cd my-project
$ git init
Initialized empty Git repository in /Users/you/my-project/.git/

$ echo "# My Project" > README.md
$ git add README.md
$ git commit -m "Initial commit"
```

### Clone an existing repo from GitHub

```bash
# Over HTTPS
$ git clone https://github.com/shivam13juna/v1-aiml-mlops.git

# Over SSH (no password prompts once your key is set up)
$ git clone git@github.com:shivam13juna/v1-aiml-mlops.git

# Clone into a folder with a different name
$ git clone <url> my-folder-name
```

### Connect an existing local folder to a new GitHub repo

```bash
$ git remote add origin git@github.com:<username>/<repo>.git
$ git branch -M main
$ git push -u origin main
```

---

## 3. The Everyday Loop (status → add → commit)

This is 80% of Git usage.

```bash
# What changed? What's staged? Which branch am I on?
$ git status

# Short version — much less noise
$ git status -s
 M lec-1-git-and-github/sorting_algorithm.py     # modified, not staged
M  README.md                                     # modified, staged
?? notes.txt                                     # untracked
```

### Staging files

```bash
$ git add sorting_algorithm.py       # one file
$ git add lec-1-git-and-github/      # a whole folder
$ git add .                          # everything under the current directory
$ git add -A                         # everything in the repo, including deletions
```

### Committing

```bash
$ git commit -m "Add bubble sort implementation"

# Stage all *tracked* modified files and commit in one shot
# (does NOT include new, untracked files)
$ git commit -am "Fix off-by-one in loop bound"

# Open the editor to write a longer message
$ git commit
```

**Good commit messages:**

```
✅  Add conflict resolution example for lecture 1
✅  Fix IndexError when input list is empty
❌  update
❌  asdf
```

Rule of thumb: the subject line should complete the sentence
_"If applied, this commit will ___"_.

---

## 4. Looking at History & Changes

### `git log`

```bash
$ git log                            # full history
$ git log --oneline                  # one line per commit
$ git log --oneline -5               # last 5 commits
$ git log --oneline --graph --all    # visual branch graph ⭐
$ git log --stat                     # which files changed, how many lines
```

Example output of the graph view:

```
* 51f9c61 (HEAD -> code-v2) Merge branch 'master' into code-v2
|\
| * a641eb0 (master) Merge pull request #10 from shivam13juna/code-v1
| * d039dd3 Create sorting_algorithm.py
* | 7612b27 Create sorting_algorithm.py
|/
* f7849c0 Merge pull request #9 from shivam13juna/change-v2
```

### `git diff`

```bash
$ git diff                      # unstaged changes (working dir vs. staging)
$ git diff --staged             # staged changes (staging vs. last commit)
$ git diff main..code-v2        # difference between two branches
$ git diff --stat               # summary only — files + line counts
```

### `git show`

```bash
$ git show                      # details of the most recent commit
$ git show a641eb0              # details of a specific commit
```

---

## 5. Branching

```bash
# List branches
$ git branch                    # local
$ git branch -a                 # local + remote

# Create a branch and switch to it
$ git checkout -b feature/login     # classic
$ git switch -c feature/login       # modern equivalent ⭐

# Switch to an existing branch
$ git checkout code-v2
$ git switch code-v2                # modern equivalent

# Rename the branch you're on
$ git branch -m new-name

# Delete a branch
$ git branch -d feature/login       # safe — refuses if unmerged
$ git branch -D feature/login       # force delete

# Delete a branch on GitHub too
$ git push origin --delete feature/login
```

**Naming conventions** you'll see in real teams:

| Prefix | Used for | Example |
| --- | --- | --- |
| `feature/` | New functionality | `feature/user-auth` |
| `fix/` | Bug fixes | `fix/empty-list-crash` |
| `docs/` | Documentation only | `docs/api-reference` |

---

## 6. Merging & Resolving Conflicts

### Merging

```bash
# Bring 'feature/login' INTO the branch you're currently on
$ git switch main
$ git merge feature/login
```

### When you hit a conflict

Git stops and marks the conflicting files:

```bash
$ git merge code-v1
Auto-merging lec-1-git-and-github/conflict_file.md
CONFLICT (content): Merge conflict in lec-1-git-and-github/conflict_file.md
Automatic merge failed; fix conflicts and then commit the result.
```

Open the file — you'll see conflict markers:

```text
<<<<<<< HEAD
This line came from the branch you are ON (code-v2).
=======
This line came from the branch you are MERGING IN (code-v1).
>>>>>>> code-v1
```

Fix it in three steps:

```bash
# 1. Edit the file — delete the <<<<<<<, =======, >>>>>>> markers
#    and leave exactly the content you want to keep.

# 2. Mark it resolved
$ git add lec-1-git-and-github/conflict_file.md

# 3. Complete the merge
$ git commit                    # Git pre-fills a sensible merge message
```

Useful escape hatches:

```bash
$ git merge --abort             # bail out, restore pre-merge state
$ git status                    # lists exactly which files still conflict
```

---

## 7. Working with Remotes (GitHub)

```bash
# See where your repo points
$ git remote -v
origin  git@github.com:shivam13juna/v1-aiml-mlops.git (fetch)
origin  git@github.com:shivam13juna/v1-aiml-mlops.git (push)

# Add or change a remote
$ git remote add origin git@github.com:<username>/<repo>.git
$ git remote set-url origin git@github.com:shivam13juna/new-name.git
```

### Push

```bash
$ git push                                  # push current branch to its upstream
$ git push origin main                      # be explicit
$ git push -u origin feature/login          # first push: also sets upstream ⭐
```

### Pull & Fetch

```bash
$ git fetch origin              # download remote changes, DON'T touch your files
$ git pull                      # = fetch + merge into current branch
$ git pull origin main
```

**`fetch` vs. `pull`:** `fetch` is read-only reconnaissance — safe any time.
`pull` actually changes your working files. When unsure, `fetch` first, look at
`git log origin/main`, *then* merge.

---

## 8. Undoing Things

> ⚠️ These rewrite or discard work. Only use them on commits you **haven't pushed yet** —
> once something is on GitHub and others have pulled it, rewriting causes problems.

| Mistake | Command |
| --- | --- |
| Bad commit message | `git commit --amend -m "Better message"` |
| Forgot a file in the last commit | `git add <file>` then `git commit --amend --no-edit` |
| Staged a file by accident | `git reset <file>` |
| Undo the last commit, keep changes staged | `git reset --soft HEAD~1` |
| Undo the last commit, keep changes unstaged | `git reset HEAD~1` |
| Throw away the last commit *and* its changes | `git reset --hard HEAD~1` ⚠️ |

```bash
# Rewrite the last commit's message
$ git commit --amend -m "Add bubble sort with edge-case handling"

# Unstage a file without losing the edit
$ git reset README.md

# Undo the last commit but keep the work in your editor
$ git reset --soft HEAD~1

# Remove untracked files/folders (build artifacts, junk)
$ git clean -n          # dry run — shows what WOULD be deleted 👀
$ git clean -fd         # actually delete files (-f) and dirs (-d)
```

Always run `git clean -n` before `git clean -fd`. Untracked files aren't in Git,
so once deleted they're gone.

---

## 9. Stashing Work in Progress

You're mid-change and need to switch branches *right now*.

```bash
$ git stash                              # shelve your changes
$ git stash -u                           # include untracked files
$ git stash push -m "half-done sorting"  # with a label

$ git stash list
stash@{0}: On code-v2: half-done sorting

$ git stash pop           # re-apply the newest stash and remove it from the list
$ git stash apply         # re-apply but KEEP it in the list
$ git stash drop          # delete the newest stash
```

---

## 10. .gitignore

Files listed here are never tracked. Create `.gitignore` at the repo root:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Jupyter
.ipynb_checkpoints/

# Data & models (usually too big for Git)
data/
*.csv
*.pkl
*.h5

# Environment & secrets  🚨 never commit these
.env
credentials.json

# OS / editor noise
.DS_Store
.vscode/
.idea/
```

Already committed something you shouldn't have? Stop tracking it, but keep the
file on disk:

```bash
$ git rm --cached .env
$ echo ".env" >> .gitignore
$ git commit -m "Stop tracking .env"
```

---

## 11. Pull Requests

A **merge** and a **pull request** are not the same thing — the naming doesn't help.

- **`git merge` is a Git command.** It combines two branches on your machine,
  instantly, with nobody's permission.
- **A pull request (PR) is a GitHub feature.** It's a *proposal*: "here's my
  branch — please review it and merge it into yours." Git itself has no idea
  what a pull request is.

> A PR is a **request** for a merge. Clicking "Merge pull request" **performs**
> the merge.

Every PR ends in a merge. Not every merge needs a PR.

| | `git merge` | Pull Request |
| --- | --- | --- |
| What it is | Git command | GitHub web feature |
| Where it runs | Your laptop | GitHub's servers |
| Who approves | Nobody | Reviewers you request |
| Review & discussion | No | Yes |
| Works without GitHub | Yes | No |

You can see both in this repo's own history:

```
a641eb0 Merge pull request #10 from shivam13juna/code-v1   ← GitHub's merge button wrote this
51f9c61 Merge branch 'master' into code-v2                 ← someone typed git merge locally
```

The `Merge pull request #N from <branch>` format is generated by GitHub.
Whenever you see it, someone clicked the green button instead of merging on
their own machine.

### Opening one

```bash
$ git switch -c feature/add-quicksort
# ...write code...
$ git add lec-1-git-and-github/sorting_algorithm.py
$ git commit -m "Add quicksort implementation"
$ git push -u origin feature/add-quicksort
```

GitHub prints a link in the push output — open it, or go to the repo page and
click **Compare & pull request**. Add a title and a short description of *what*
changed and *why*, then request a reviewer.

**Why teams bother:** a local merge is silent and unilateral. A PR creates a
place to discuss a change before it lands, run tests against it, and record why
it was approved. On a solo project you can skip PRs and just merge. On a team,
the main branch is usually protected so a PR is the only way in.

> ⚠️ A **pull request** has nothing to do with **`git pull`**. `git pull`
> downloads commits *to* your machine. A pull request asks a maintainer to pull
> *your* branch into theirs. Same word, opposite directions.

---

## 12. A Typical Workflow

Start to finish, the way most teams work:

```bash
$ git switch main
$ git pull                                  # start from the latest code
$ git switch -c feature/add-quicksort       # branch off

# ...write code...

$ git status                                # check what changed
$ git add lec-1-git-and-github/sorting_algorithm.py
$ git commit -m "Add quicksort implementation"
$ git push -u origin feature/add-quicksort

# Open a Pull Request (see section 11), get it reviewed and merged, then:
$ git switch main
$ git pull                                  # sync your local main
$ git branch -d feature/add-quicksort       # clean up
```

If `main` moves ahead while you're working, bring it into your branch:

```bash
$ git switch main && git pull
$ git switch feature/add-quicksort
$ git merge main
```

---

## 13. Quick Reference Table

| Command | What it does |
| --- | --- |
| `git init` | Start tracking a folder with Git |
| `git clone <url>` | Copy a remote repo locally |
| `git status -s` | Compact view of what changed |
| `git add <file>` / `git add .` | Stage changes |
| `git commit -m "msg"` | Save a snapshot |
| `git commit --amend` | Rewrite the last commit |
| `git log --oneline --graph --all` | Visual history |
| `git diff` / `git diff --staged` | See unstaged / staged changes |
| `git show <commit>` | Inspect one commit |
| `git branch -a` | List all branches |
| `git switch -c <name>` | Create + switch branch |
| `git switch <name>` | Change branch |
| `git merge <branch>` | Combine another branch into this one |
| `git merge --abort` | Cancel a conflicted merge |
| `git fetch` | Download remote changes (safe) |
| `git pull` | Fetch + integrate |
| `git push -u origin <branch>` | Publish a branch |
| `git reset <file>` | Unstage a file |
| `git reset --soft HEAD~1` | Undo commit, keep changes staged |
| `git reset --hard HEAD~1` ⚠️ | Undo commit, delete changes |
| `git stash` / `git stash pop` | Shelve / restore work in progress |
| `git clean -fd` ⚠️ | Delete untracked files |

---

## Mental Model

Git moves your work through four places. Almost every command is just a move
between two of them:

```text
 Working Directory        Staging Area          Local Repo           Remote (GitHub)
  (your edits)              (index)              (commits)             (origin)
        │                      │                     │                     │
        │──── git add ────────▶│                     │                     │
        │                      │─── git commit ─────▶│                     │
        │                      │                     │──── git push ──────▶│
        │                      │                     │◀─── git fetch ──────│
        │◀──────────────── git pull (fetch + merge) ──────────────────────│
```

---

## Getting Help

```bash
$ git help <command>            # full manual page
$ git <command> -h              # quick flag summary
$ git status                    # honestly — it usually tells you what to do next
```

```
gu () {
	local commit_msg="$1" 
	local branch="${2:-$(git rev-parse --abbrev-ref HEAD)}" 
	local limit=$((99 * 1024 * 1024)) 
	local big_files="" 
	local f sz
	while IFS= read -r f
	do
		[ -f "$f" ] || continue
		sz=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null)  || continue
		if [ "$sz" -gt "$limit" ]
		then
			big_files+="  $f ($((sz / 1024 / 1024)) MB)"$'\n' 
		fi
	done < <(git ls-files --cached --others --exclude-standard)
	if [ -n "$big_files" ]
	then
		echo "Aborting: files >99MB not in .gitignore (GitHub rejects >100MB):"
		printf '%s' "$big_files"
		echo "Add them to .gitignore (or use Git LFS), then retry."
		return 1
	fi
	git add .
	git commit -m "$commit_msg"
	git push --set-upstream origin "$branch"
}
```