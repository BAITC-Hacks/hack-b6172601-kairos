# Competition constraints

Summarised from the official regulations, revised by the organisers on
22 September 2026, so that an agent does not have to fetch or re-read them: the
source pages are JavaScript-rendered and the task material needs a login.

This is a working summary, not the authoritative text. If a decision turns on an
exact wording, ask the author to check the regulations.

## Timetable, 23 September 2026, EXPO Astana

| Time (Astana) | Stage |
|---|---|
| 09:00-12:00 | Check-in and identification |
| 12:00-13:00 | Opening ceremony |
| **13:00-18:00** | **Competitive part: five hours of development** |
| 18:00-18:30 | Close |

The competitive part officially starts at 13:00 and ends at 18:00. Whatever the
organisers have recorded at 18:00 is the final version, regardless of when the
platform locks. Reported hours therefore end at 14:00, 15:00, 16:00, 17:00 and
18:00.

Technical review 24-28 September. Demo Day 29 September for finalists. Awards
1 October.

## The rule that outranks every other

**If the final version cannot be started from the instructions in the
repository, the team is not admitted to further selection. No additional
explanations or corrections are accepted.** (5.4.16, restated in 5.6.5.)

This is no longer a scoring criterion that can be traded against features. It is
a gate. An earlier version of the regulations let experts ask the team for setup
clarifications; that provision is gone.

Everything in this repository that looks like over-engineering around
reproducibility exists for this sentence: `scripts/verify_all.sh`, the
clean-copy simulation, the Docker path that needs neither host Python nor a
`.env`.

## Checkability without the author's accounts

5.6.6: the team must make the key functionality verifiable **without the
participants' personal accounts, subscriptions or private credentials**. When
the project uses external services or APIs, the team must supply demonstration
access, test accounts or another way to check the solution.

In practice this means a reviewer must be able to exercise the agent without
owning a model API key. The public deployment is how this project satisfies it,
plus `scripts/setup_key.sh` for a reviewer who does have a key.

## The participants' instruction

Alongside the regulations the organisers published a participant instruction.
What it adds:

- **Activate access to Codex, the OpenAI API and NVIDIA** through their separate
  activation guide. **Do not publish API keys in GitHub.**
- **Choose ONE task.** Solving every task in a track is not required, and a
  project may be submitted under one task only.
- Read that task's requirements and evaluation criteria before implementing.
- Any way of working is acceptable — the Codex app, the VS Code extension, or
  anything else — as long as an AI agent is used and the final code is in the
  team's GitHub repository.
- In five hours, implement the task's mandatory requirements and check the main
  scenario from input to result.
- Push the final version to the repository, **and then submit it**: on the tracks
  page, open your task, press the submit button ("Sdat resheniye") and fill in the
  project name and description. A submitted solution can be updated until the
  deadline.

They also published a README outline, which this README's numbered sections
follow one to one: name, summary, what is implemented, how the solution works,
technologies, architecture, installation and running, how to check, data and
integrations, limitations, link to the deployed version. Their instruction adds
one rule about it that matches this project's own: use only what the repository
can back up, and invent no functionality, technology or result that is not there.

The Russian edition of that instruction suggests writing the README in Russian;
the English edition does not. Treat the language as a choice, the outline as the
requirement. This repository is English throughout.

## The README is specified, not suggested

5.4.15 lists what the README must contain:

- what the solution is and what it is for
- the architecture
- the technologies used
- installation instructions
- how to run it
- dependencies
- environment parameters
- how to check the main scenario

It must let a technical expert understand how the solution works and deploy it
themselves. Check the README against this list literally before the deadline.

## Scoring

**There is no longer a single scoring table in the regulations.** 5.5: the
criteria, the points and the rules for awarding them are defined by the
**technical specification of each individual task**, published before the
competitive part begins. Different tasks may score differently; results are
normalised across tasks to build one finalist list.

So: read the task's technical specification first, and take its scoring table as
the authority. Do not assume the weights from any earlier version.

Demo Day, for finalists only, is judged on different criteria entirely (5.7.2):
value of the solution 25, result and quality 20, innovation 15, growth potential
20, presentation and answers 20. That stage is about the product and the pitch;
the technical selection before it is about the repository.

## Hard rules

Grounds for disqualification (5.9.2), independent of any score:

- **No confirmed intermediate result for any reported hour** of the competitive
  part. Hence `scripts/hourly_commit.sh`.
- **Main development outside the organiser-created GitHub repository**, or the
  absence of a verifiable development history in it. Private third-party
  repositories may not be used for the main development, for storing the code or
  for handing over the final version (5.4.9).
- **Presenting work created wholly or mainly by third parties without disclosing
  it.**
- Leaving the venue without permission; total absence may not exceed 60 minutes
  (5.1.7.1). Development must happen on site.
- Failing check-in, or transferring a personal participant number.

## What is explicitly allowed

- **Pre-prepared technical components, development tools, own libraries,
  templates and infrastructure** (5.4.4.2) — provided they are not a finished
  product and not the main part of the solution. The functionality that answers
  the task must be developed during the competitive part. This is the rule under
  which the scaffold in this repository is used, and why the placeholder tools
  are deleted rather than adapted.
- Open-source components, under their licences, with disclosure (5.4.4.1).
- **Any AI tools and agents**, including for code generation, architecture and
  documentation. OpenAI Codex is explicitly **not** mandatory (5.4.12).
- Cloud services, external APIs and remote development tools, provided the
  participants are physically present (5.4.12.1), and provided the main
  development still happens in the organiser's repository.

Not allowed: submitting a previously built product that already had the main
functionality before the competitive part began (5.4.5).

## Who reads this repository

Technical experts may inspect the repository, the code, the architecture, file
metadata, the development history and each participant's actual contribution
(5.4.7, 4.1). AI judges may be used as an auxiliary tool for preliminary
analysis and ranking (4.2). There is no appeal on professional judgement (5.10.3
and 5.10.4); only confirmed arithmetic or technical errors are corrected.

## What this means for the code

- The project must start from the repository. Everything else is secondary,
  because everything else is only scored if this holds.
- A reviewer without a key must still be able to exercise the main scenario.
- A canned or recorded answer presented as live output remains the most
  expensive mistake available.
- The commit history is part of the deliverable.
