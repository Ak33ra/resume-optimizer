# PRIVACY & REPO MODEL

This project is designed to be **shared publicly as a skeleton** while your
**resumes and personal data stay private** — with several guardrails so PII is
never pushed by accident.

## The two-repo model

| | **Public skeleton** (this repo) | **Your private fork** |
|---|---|---|
| Contains | Toolkit only: instructions, template, scripts, `*.example.md` | Toolkit **+** your real `source_material/`, `resumes/`, and round history |
| Remote | Public (e.g. `github.com/you/resume-optimizer`) | **Private** repo you own |
| PII | Never | Yes — but only ever pushed to the private remote |
| Purpose | Fork/share/star; receive improvements | Your day-to-day resume work, with full version history |

You keep your personal history (which is genuinely useful — the agent can see how
prior rounds went) in the **private** fork, and pull toolkit updates from the
public skeleton whenever you want.

## Why not just gitignore everything?

`resumes/` and `source_material/` **are** gitignored by default — that's the
first guardrail (a stray `git add .` can't stage them). But gitignore alone
means you get *no* history of your own work. The private-fork model gives you
that history safely.

## One-time setup for your private fork

GitHub can't make a fork of a public repo private, so create a private **mirror**
and keep the public repo as an upstream for updates:

```bash
# 1. On GitHub, create a new EMPTY, PRIVATE repo, e.g. you/resume-optimizer-private

# 2. Clone the public skeleton and re-point the remotes
git clone https://github.com/<owner>/resume-optimizer.git my-resumes
cd my-resumes
git remote rename origin upstream                      # public skeleton = upstream (read-only source of updates)
git remote set-url --push upstream DISABLED            # guardrail: you literally cannot push to the public repo
git remote add origin git@github.com:<you>/resume-optimizer-private.git

# 3. Turn on tracked git hooks + allow PII on THIS private repo only
git config core.hooksPath scripts/hooks               # enables the pre-push PII guard
git config resumeopt.allowPII true                    # you've confirmed origin is private

# 4. Version-control your real files: either uncomment the "PRIVATE FORK" block
#    in .gitignore, or force-add deliberately:
git add -f source_material resumes optimization_log.md
git commit -m "chore: seed private material"
git push -u origin main                               # goes to your PRIVATE repo
```

Pull toolkit improvements from the public skeleton later:

```bash
git fetch upstream && git merge upstream/main
```

## Guardrails (defense in depth)

1. **Gitignore** — PII paths are ignored by default; accidental `git add .` won't
   stage them.
2. **Disabled upstream push** — `set-url --push upstream DISABLED` makes pushing
   to the public repo fail outright.
3. **Pre-push hook** — `scripts/hooks/pre-push` blocks any push that carries
   files under `resumes/`/`source_material/` (other than READMEs/`*.example.md`)
   or an email/phone in `optimization_log.md`, **unless** the repo is marked
   `resumeopt.allowPII true`. Enable it with `git config core.hooksPath
   scripts/hooks` (already in the setup above). The public skeleton leaves
   `allowPII` unset, so it's protected too.

## What about the optimization log?

`optimization_log.md` is **committed** (it's the round history). Keep it to
scores + change descriptions. Referencing your own resume specifics there is
fine and useful in your private fork; avoid raw contact PII (name/email/phone) —
and the pre-push hook blocks those from reaching any non-private remote anyway.

## Contributing back to the public skeleton

Only push **toolkit** changes (instructions, template, scripts) upstream, from a
clean clone of the public repo — never from your private fork, and never
including anything under `resumes/` or `source_material/`.
