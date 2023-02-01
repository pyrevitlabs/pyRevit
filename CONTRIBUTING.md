# Important Files

This is how the pyRevit repository is organized:

- `bin/`
    - `engines/`
- `dev/`
    - `pyRevitLabs.` assemblies
- `extensions/`
- `pyrevitlib/`
    - `pyrevit`
    - `rjm/`
    - `rpw/`
    - `rpws/`
    - `rsparam/`
- `site-packages`/
- `static/`

[pyRevitFile](https://www.notion.so/pyRevitFile-193584aa3c7c4f03ba6ef2fc9886bb03)

# Building pyRevit Source

This is a bit more involved so here a pretty page that is just about building pyRevit. You don’t have to do this unless you are making changes  to the pyRevit runtime that is in C#, or merging PRs that includes such changes. Make sure to build and test locally and then push to origin.

[Building pyRevit Source](https://www.notion.so/Building-pyRevit-Source-1d56c772b4f54516ab93da299419d581)

# Committing Changes

When working on pyRevit repository, you should create a specific branch for the changes that you are making. After making and committing all your changes, your branch can be squish-merged into `develop`. This way there would a single commit for every bug fix, feature, or other changes. This makes it very easy to find when a specific change has been introduced to pyRevit and “revert” the changes later if necessary.

We follow a `dev/*` pattern for development branch names:

- For bugs `dev/000` where `000` is the issue number
- For PRs `dev/pr000` where `000` is the PR number

Not following this pattern does not break anything, but it makes harder for others to see the upcoming changes

# Merging Pull Requests (PR)

Reviewing changes in a PR is important. You want to make sure:

- The proposed changes actually work and compile
- The changes follow pyRevit’s conventions. There is no document on this. Follow the patterns you see already in the pyRevit source and make sure to communicate with other collaborators in case you are not sure.
- The changes does not break anything else

To review a PR, create a `dev/pr000` (where `000` is the PR number) branch, merge the PR into this branch, review the code changes, and then merge this branch into `develop`

# Continuous Build

- Any changes to `develop` branch triggers a new work-in-progress build. the WIP installers will be available after. Try to create your own develop branches and merge into `develop` in one commit so we don’t have to pay for the continuous builds on Github and also the WIP installers don’t include unfinished changes.

# Documentation & Guides

pyRevit repo contains all the documentation for the `pyrevit` module (as python *docstrings*)

- `pyrevit` module on **ReadTheDocs**
    
    [pyRevit Python Module](https://www.notion.so/pyRevit-Python-Module-0c0e118ba8984a308399e470a39c45cd)
    
- pyRevit Wiki at [wiki.pyrevitlabs.io](https://wiki.pyrevitlabs.io) on Notion

# Release Process

- `main`
- Build tools `dev/`
- Release files `release/`

[Continuous Builds](https://www.notion.so/Continuous-Builds-aa5f96812949413287163eddf2d646c7)


# Contributors

<a href="https://github.com/eirannejad/pyRevit/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=eirannejad/pyRevit" />
</a>

Made with [contrib.rocks](https://contrib.rocks).
