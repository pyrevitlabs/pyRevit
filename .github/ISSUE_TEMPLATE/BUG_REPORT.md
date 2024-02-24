---
name: Bug report
about: Create a report to help us improve
labels: Bug

---
---

**🚧 If you have SentinelOne installed as an antivirus, look no further. You will need to create exceptions for Revit and pyRevit, both on the software and the %appdata% folders.**

---

**🙏 Please use the search in the issue section before filing a new issue**

---

# 🐞 Describe the bug

Replace these lines with your description. Be as specific as possible and list steps to reproduce the issue. If you have any suggestions for the solution please list that as well.

If you have installed pyRevit, and the installation completed with no errors but pyRevit doesn't load, please run the command below in terminal / command line. This should fix the issue on your machine, however, please continue filing the issue with instructions below.

👉 `pyrevit attach master 2711 --installed`

If it does not work, try to disable your revit addins, all of them. Then, one at a time, reactivate them and restart Revit to figure out which one is interacting badly with pyRevit and Report.

# ♻️ To Reproduce

Steps to reproduce the behavior:

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

# ⏲️ Expected behavior

A clear and concise description of what you expected to happen.

# 🖼 Screenshots of the issue

If applicable, add screenshots to help explain your problem.

# 🖥️ Hardware and Software Setup (please complete the following information)

- OS: [e.g. iOS]
- pyRevit Version [e.g. 22]
- pyRevit Environment: Open a command prompt 🖥 and run the command below. Replace these lines with the results. Take a look at this markdown guide and wrap the command results in ``` when pasting here for correct formatting.

👉 `pyrevit env`

# Additional context

Add any other context about the problem here.
